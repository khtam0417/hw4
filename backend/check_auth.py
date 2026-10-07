"""Checks for accounts and sessions (Homework 4, Problem 4).

Run while the backend is running, from the homework 4 folder:
    .venv/bin/python backend/check_auth.py
(add BACKEND_PORT=8001 in front if the backend runs on port 8001)

It logs in with the account that came with the data and with the Problem 4 test account (creating that
account first if it doesn't exist yet). It also checks that wrong passwords, bad sign-up details and an
already registered email are refused with clear messages, that no response ever contains a password or a
password hash, and that the catalogue and inventory tables do not change.
"""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

# The backend under test; set BACKEND_PORT when it isn't running on port 8000.
BASE_URL = f"http://127.0.0.1:{os.environ.get('BACKEND_PORT', '8000')}"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"

# The account that came with the database (credentials given in the assignment).
EXISTING_ACCOUNT = {"email": "test@campuscustoms.yale.edu", "password": "password"}
# The test account created for Problem 4.
NEW_ACCOUNT = {
    "first_name": "Bulldog",
    "last_name": "Tester",
    "email": "bulldog.tester@example.com",
    "password": "BoolaBoola-2026",
}
USER_FIELDS = {"id", "first_name", "last_name", "email"}

results: list[bool] = []
response_texts: list[str] = []
user_objects: list[dict] = []


def check(ok: bool, description: str) -> None:
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {description}")


class Browser:
    """Makes requests with its own cookie jar, like one visitor's browser."""

    def __init__(self) -> None:
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def call(self, method: str, path: str, body: dict | None = None, headers: dict | None = None) -> tuple[int, object]:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(BASE_URL + path, data=data, method=method, headers=headers or {})
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(request) as response:
                status, text = response.status, response.read().decode()
        except urllib.error.HTTPError as error:
            status, text = error.code, error.read().decode()
        response_texts.append(text)
        parsed = json.loads(text) if text else None
        if isinstance(parsed, dict) and "email" in parsed:
            user_objects.append(parsed)
        return status, parsed

    def has_httponly_session(self) -> bool:
        return any(c.name == "cc_session" and c.has_nonstandard_attr("HttpOnly") for c in self.cookies)


def error_fields(body: object) -> dict:
    return body.get("detail", {}).get("fields", {}) if isinstance(body, dict) else {}


def error_message(body: object) -> str:
    return body.get("detail", {}).get("message", "") if isinstance(body, dict) else ""


def protected_tables_fingerprint() -> str:
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    rows = [con.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall() for table in ("catalogue", "inventory")]
    con.close()
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def main() -> int:
    tables_before = protected_tables_fingerprint()

    print("Existing test account")
    browser = Browser()
    status, body = browser.call("GET", "/api/auth/me")
    check(status == 200 and body is None, "nobody is logged in at the start")
    status, body = browser.call("POST", "/api/auth/login", EXISTING_ACCOUNT)
    check(status == 200 and isinstance(body, dict) and body.get("email") == EXISTING_ACCOUNT["email"], "logs in")
    check(browser.has_httponly_session(), "gets an HttpOnly session cookie")
    browser.call("GET", "/api/products")
    status, body = browser.call("GET", "/api/auth/me")
    check(isinstance(body, dict) and body.get("email") == EXISTING_ACCOUNT["email"], "stays logged in while browsing")
    status, _ = browser.call("POST", "/api/auth/logout")
    _, body = browser.call("GET", "/api/auth/me")
    check(status == 204 and body is None, "logs out")
    status, body = Browser().call("POST", "/api/auth/login", {**EXISTING_ACCOUNT, "password": "not-the-password"})
    check(status == 401 and "don't match" in error_message(body), "wrong password is refused with a clear message")
    status, body = Browser().call("POST", "/api/auth/login", {"email": "nobody@example.com", "password": "whatever-123"})
    check(status == 401 and "don't match" in error_message(body), "unknown email gets the same message")

    print("\nNew test account")
    signup = {**NEW_ACCOUNT, "confirm_password": NEW_ACCOUNT["password"]}
    status, body = Browser().call("POST", "/api/auth/register", signup)
    check(status in (201, 409), "created" if status == 201 else "already exists from an earlier run")
    browser = Browser()
    status, body = browser.call("POST", "/api/auth/login", {"email": NEW_ACCOUNT["email"], "password": NEW_ACCOUNT["password"]})
    check(status == 200 and isinstance(body, dict) and body.get("email") == NEW_ACCOUNT["email"], "logs in")
    _, body = browser.call("GET", "/api/auth/me")
    check(isinstance(body, dict) and body.get("first_name") == NEW_ACCOUNT["first_name"], "stays logged in")
    status, _ = Browser().call("POST", "/api/auth/login", {"email": NEW_ACCOUNT["email"], "password": "BoolaBoola-2025"})
    check(status == 401, "wrong password is refused")

    print("\nSign-up checks (none of these create an account)")
    def register(**changes: str) -> tuple[int, object]:
        return Browser().call("POST", "/api/auth/register", {**signup, "email": "someone.new@example.com", **changes})

    status, body = register(email="  BULLDOG.Tester@Example.com ")
    check(status == 409 and error_fields(body).get("email") == "This email is already registered.",
          "an already registered email is refused, whatever its case")
    status, body = register(confirm_password="something-else")
    check(status == 400 and "confirm_password" in error_fields(body), "a confirmation that doesn't match is refused")
    status, body = register(email="not-an-email")
    check(status == 400 and "email" in error_fields(body), "an invalid email is refused")
    status, body = register(password="short", confirm_password="short")
    check(status == 400 and "password" in error_fields(body), "a password under 8 characters is refused")
    status, body = register(first_name=" ", last_name="")
    check(status == 400 and {"first_name", "last_name"} <= error_fields(body).keys(), "missing names are refused")

    print("\nSessions and privacy")
    _, body = Browser().call("GET", "/api/auth/me", headers={"Cookie": "cc_session=1.9999999999.forged-signature"})
    check(body is None, "a forged session cookie is ignored")
    leaks = [text for text in response_texts if "pbkdf2" in text or "password_hash" in text or NEW_ACCOUNT["password"] in text]
    check(not leaks, f"no response contains a password or a password hash ({len(response_texts)} responses checked)")
    check(all(set(user) == USER_FIELDS for user in user_objects),
          f"user responses contain only id, first_name, last_name and email ({len(user_objects)} checked)")
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    stored = con.execute("SELECT password_hash FROM users WHERE email = ?", (NEW_ACCOUNT["email"],)).fetchone()
    con.close()
    check(stored is not None and stored[0].startswith("pbkdf2_sha256$600000$") and NEW_ACCOUNT["password"] not in stored[0],
          "the new password is stored only as a salted PBKDF2 hash")
    check(protected_tables_fingerprint() == tables_before, "catalogue and inventory are unchanged")

    failed = results.count(False)
    print(f"\n{len(results) - failed} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
