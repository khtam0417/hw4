"""Accounts and sessions for Campus Customs.

Routes, all under /api/auth:
- POST /register  create an account and log in: first name, last name, email, password and confirmation
- POST /login     log in with email and password
- POST /logout    log out
- GET  /me        the logged-in user, or null; the site asks on every page load to keep people logged in

Passwords are hashed with PBKDF2-HMAC-SHA256 and a random salt; only the hash is stored. A session is
a signed, HttpOnly cookie holding just the user id and an expiry time. Responses (and, later, anything
given to the chatbot) only ever contain a user's id, names and email, never a password or its hash.
After FAILED_LOGIN_LIMIT wrong passwords for one email from one address within FAILED_LOGIN_MINUTES,
logins for that email are refused (429) until the window passes, so passwords can't be guessed at speed.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from db import PROJECT_ROOT, customer_writer, read_only
from limits import SlidingWindow
from models import UserOut

load_dotenv(PROJECT_ROOT / ".env")

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------- Password hashing ----------

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 600_000  # OWASP's current recommendation for PBKDF2-HMAC-SHA256
# Accounts that came with the database are stored as pbkdf2_sha256$<salt>$<hex digest>,
# made with 120,000 iterations; new hashes also record their iteration count.
LEGACY_ITERATIONS = 120_000


def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()


def hash_password(password: str) -> str:
    """Returns pbkdf2_sha256$<iterations>$<random salt>$<hex digest>."""
    salt = secrets.token_hex(16)
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${salt}${_pbkdf2(password, salt, HASH_ITERATIONS)}"


def verify_password(password: str, stored_hash: str) -> bool:
    parts = stored_hash.split("$")
    if len(parts) == 4 and parts[0] == HASH_ALGORITHM and parts[1].isdigit():
        _, iterations, salt, digest = parts
        return hmac.compare_digest(_pbkdf2(password, salt, int(iterations)), digest)
    if len(parts) == 3 and parts[0] == HASH_ALGORITHM:
        _, salt, digest = parts
        return hmac.compare_digest(_pbkdf2(password, salt, LEGACY_ITERATIONS), digest)
    return False


# Checked against when an email is unknown, so a wrong email takes as long as a wrong password.
_UNKNOWN_EMAIL_HASH = hash_password(secrets.token_hex(16))

# ---------- Sessions ----------

SESSION_COOKIE = "cc_session"
SESSION_SECONDS = 7 * 24 * 60 * 60
# Set SESSION_SECRET in .env so sessions survive restarts; without it a temporary key is used.
_SESSION_KEY = (os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(48)).encode()
_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"}


def _sign(payload: str) -> str:
    digest = hmac.new(_SESSION_KEY, payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _user_id_from(token: str | None) -> int | None:
    """The user id in a genuine, unexpired session token ("<user id>.<expiry>.<signature>"), else None."""
    payload, _, signature = (token or "").rpartition(".")
    if not payload or not hmac.compare_digest(signature.encode(), _sign(payload).encode()):
        return None
    user_id, _, expires = payload.partition(".")
    if not (user_id.isdigit() and expires.isdigit()) or int(expires) < time.time():
        return None
    return int(user_id)


def _start_session(response: Response, user_id: int) -> None:
    payload = f"{user_id}.{int(time.time()) + SESSION_SECONDS}"
    response.set_cookie(
        SESSION_COOKIE,
        f"{payload}.{_sign(payload)}",
        max_age=SESSION_SECONDS,
        httponly=True,  # page scripts can't read it
        samesite="lax",  # other sites can't send it with their own requests
        secure=_COOKIE_SECURE,
        path="/",
    )


def _end_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax", secure=_COOKIE_SECURE, path="/")


# ---------- Users ----------


class RegisterRequest(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    password: str = ""
    confirm_password: str = ""


class LoginRequest(BaseModel):
    email: str = ""
    password: str = ""


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# After this many wrong passwords for one email from one address, logins for it are refused for the window,
# even with the right password, so passwords can't be guessed by trying many.
FAILED_LOGIN_LIMIT = 5
FAILED_LOGIN_MINUTES = 15
_failed_logins = SlidingWindow(FAILED_LOGIN_LIMIT, FAILED_LOGIN_MINUTES * 60)
NAME_MAX = 50
EMAIL_MAX = 254
PASSWORD_MIN = 8
PASSWORD_MAX = 128


def _user_out(row: sqlite3.Row) -> UserOut:
    full_name = (row["name"] or "").split(maxsplit=1)
    return UserOut(
        id=row["id"],
        first_name=row["first_name"] or (full_name[0] if full_name else ""),
        last_name=row["last_name"] or (full_name[1] if len(full_name) > 1 else ""),
        email=row["email"],
    )


def _form_error(status: int, message: str, fields: dict[str, str] | None = None) -> HTTPException:
    """An error the site shows as-is: one sentence for the form, plus a message per field."""
    return HTTPException(status_code=status, detail={"message": message, "fields": fields or {}})


# A message that mentions a password gets checked for the customer's real one (see remove_own_password).
PASSWORD_HINT = re.compile(r"\bpass(word|code)?s?\b|\bpw\b", re.IGNORECASE)
MAX_WORDS_CHECKED = 10


def remove_own_password(user_id: int, message: str) -> str:
    """Replace the customer's own password, if they typed it into the chat, before the message is sent to
    the agent or saved. Only messages that mention a password are checked, and only words that could be a
    password (8 to 128 characters), compared with their stored hash."""
    if not PASSWORD_HINT.search(message):
        return message
    with closing(read_only()) as con:
        row = con.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return message
    words = list(dict.fromkeys(re.findall(r"\S{%d,%d}" % (PASSWORD_MIN, PASSWORD_MAX), message)))[:MAX_WORDS_CHECKED]
    for word in words:
        if any(verify_password(candidate, row["password_hash"]) for candidate in {word, word.strip(".,!?;:'\"()")}):
            message = message.replace(word, "[password removed]")
    return message


def current_user(request: Request) -> UserOut | None:
    """The logged-in user for this request, or None."""
    user_id = _user_id_from(request.cookies.get(SESSION_COOKIE))
    if user_id is None:
        return None
    with closing(read_only()) as con:
        row = con.execute("SELECT id, name, first_name, last_name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_out(row) if row else None


@router.post("/register", status_code=201)
def register(body: RegisterRequest, response: Response) -> UserOut:
    first, last, email = body.first_name.strip(), body.last_name.strip(), body.email.strip().lower()
    errors: dict[str, str] = {}
    for field, label, value in (("first_name", "first name", first), ("last_name", "last name", last)):
        if not value:
            errors[field] = f"Enter your {label}."
        elif len(value) > NAME_MAX:
            errors[field] = f"Keep your {label} to {NAME_MAX} characters or fewer."
    if len(email) > EMAIL_MAX or not EMAIL_PATTERN.match(email):
        errors["email"] = "Enter a valid email address, like name@example.com."
    if len(body.password) < PASSWORD_MIN:
        errors["password"] = f"Use at least {PASSWORD_MIN} characters."
    elif len(body.password) > PASSWORD_MAX:
        errors["password"] = f"Use {PASSWORD_MAX} characters or fewer."
    if body.confirm_password != body.password:
        errors["confirm_password"] = "The passwords don't match."
    if errors:
        raise _form_error(400, "Please fix the highlighted fields.", errors)

    already_registered = _form_error(
        409, "An account with this email already exists.", {"email": "This email is already registered."}
    )
    with closing(customer_writer()) as con:
        if con.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise already_registered
        try:
            cursor = con.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                (f"{first} {last}", email, hash_password(body.password), first, last),
            )
            con.commit()
        except sqlite3.IntegrityError:  # the same email was registered a moment ago
            raise already_registered from None
    user = UserOut(id=cursor.lastrowid, first_name=first, last_name=last, email=email)
    _start_session(response, user.id)
    return user


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response) -> UserOut:
    email = body.email.strip().lower()
    missing = {
        field: message
        for field, message, value in (("email", "Enter your email.", email), ("password", "Enter your password.", body.password))
        if not value
    }
    if missing:
        raise _form_error(400, "Enter your email and password.", missing)
    attempts = f"{email}|{request.client.host if request.client else 'unknown'}"
    if _failed_logins.full(attempts):
        raise _form_error(
            429, f"Too many wrong passwords for this email. Please wait {FAILED_LOGIN_MINUTES} minutes and try again."
        )
    with closing(read_only()) as con:
        row = con.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    password_ok = verify_password(body.password, row["password_hash"] if row else _UNKNOWN_EMAIL_HASH)
    if row is None or not password_ok:
        _failed_logins.add(attempts)
        raise _form_error(401, "That email and password don't match our records. Please try again.")
    _failed_logins.clear(attempts)
    _start_session(response, row["id"])
    return _user_out(row)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    _end_session(response)


@router.get("/me")
def me(request: Request) -> UserOut | None:
    return current_user(request)
