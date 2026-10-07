"""Checks customer memory and page context (Homework 4, Problem 8).

Run while the backend is running, from the homework 4 folder:
    .venv/bin/python backend/check_memory.py
(add BACKEND_PORT=8001 in front if the backend runs on port 8001)

It sends real chat messages as a guest and as the Problem 4 test account, so it takes about a minute and
adds those exchanges to that account's saved history. The Test User account is only read, never chatted as.
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

BASE_URL = f"http://127.0.0.1:{os.environ.get('BACKEND_PORT', '8000')}"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"
OTHER_ACCOUNT = {"email": "test@campuscustoms.yale.edu", "password": "password"}  # given in the assignment
MAIN_ACCOUNT = {"email": "bulldog.tester@example.com", "password": "BoolaBoola-2026"}  # made in Problem 4

results: list[bool] = []
response_texts: list[str] = []


def check(ok: bool, description: str) -> None:
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {description}")


class Browser:
    """One visitor's browser, with its own cookie jar."""

    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(BASE_URL + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(request, timeout=240) as response:
                status, text = response.status, response.read().decode()
        except urllib.error.HTTPError as error:
            status, text = error.code, error.read().decode()
        response_texts.append(text)
        return status, (json.loads(text) if text else {})

    def log_in(self, account: dict) -> None:
        status, _ = self.call("POST", "/api/auth/login", account)
        assert status == 200, f"could not log in as {account['email']}"

    def chat(self, message: str, page: dict | None = None) -> dict:
        status, body = self.call("POST", "/api/chat", {"message": message, "page": page or {"path": "/"}})
        assert status == 200, f"chat failed ({status}): {body}"
        return body

    def history(self) -> list[dict]:
        return self.call("GET", "/api/chat/history")[1]["messages"]


def counts() -> dict[int, int]:
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    rows = dict(con.execute("SELECT user_id, COUNT(*) FROM chat_messages GROUP BY user_id").fetchall())
    con.close()
    return rows


def last_saved(user_id: int) -> list[str]:
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    rows = [content for (content,) in con.execute(
        "SELECT content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT 2", (user_id,))]
    con.close()
    return rows


def protected_tables() -> str:
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    rows = [con.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall() for table in ("catalogue", "inventory")]
    con.close()
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def main() -> int:
    tables_before, before = protected_tables(), counts()

    print("Guest")
    guest = Browser()
    check(guest.call("GET", "/api/chat/history")[1] == {"saved": False, "messages": []}, "a guest has no saved history")
    reply = guest.chat("Hi! What kinds of things do you sell?")
    check(reply["saved"] is False and counts() == before, "a guest can chat, and nothing is saved")

    print("\nSaving and reloading a customer's conversation")
    shopper = Browser()
    shopper.log_in(MAIN_ACCOUNT)
    user_id = shopper.call("GET", "/api/auth/me")[1]["id"]
    saved_before = len(shopper.history())
    reply = shopper.chat("Hi! I'm shopping for my brother Sam, who loves navy hoodies.")
    after = counts()
    check(reply["saved"] is True and after.get(user_id, 0) == before.get(user_id, 0) + 2,
          "a logged-in customer's message and the reply are saved (2 new rows)")
    check({k: v for k, v in after.items() if k != user_id} == {k: v for k, v in before.items() if k != user_id},
          "no other customer's history changed")
    history = shopper.history()
    check(len(history) == min(saved_before + 2, 50) and "my brother Sam" in history[-2]["content"]
          and history[-1]["role"] == "assistant", "the saved conversation comes back after a refresh")

    print("\nLogging out and back in")
    shopper.call("POST", "/api/auth/logout")
    check(shopper.history() == [], "after logging out, no history is returned")
    returning = Browser()
    returning.log_in(MAIN_ACCOUNT)
    check(any("my brother Sam" in m["content"] for m in returning.history()), "logging back in brings the history back")
    reply = returning.chat("Remind me: who did I say I'm shopping for?")
    check("Sam" in reply["reply"] or "brother" in reply["reply"].lower(),
          f"the agent continues the saved conversation: \"{reply['reply'][:90]}...\"")

    print("\nAnother account")
    other = Browser()
    other.log_in(OTHER_ACCOUNT)
    other_history = other.history()
    other_id = other.call("GET", "/api/auth/me")[1]["id"]
    check(not any("Sam" in m["content"] for m in other_history) and len(other_history) == min(counts().get(other_id, 0), 50),
          f"Test User sees only their own {len(other_history)} messages, none of Bulldog Tester's")

    print("\nShopper details")
    reply = returning.chat("Which email is my account under? And what's the email of the Test User account?")
    check(MAIN_ACCOUNT["email"] in reply["reply"] and OTHER_ACCOUNT["email"] not in reply["reply"],
          "the agent knows the shopper's own email and won't give out another customer's")

    print("\nPage context")
    reply = returning.chat("Do you have this in pink?", {"path": "/products/boola-boola-t-shirt", "product_id": "boola-boola-t-shirt"})
    check("Boola Boola" in reply["reply"], f"on the Boola Boola T Shirt page, \"this\" is that shirt: \"{reply['reply'][:90]}...\"")
    reply = returning.chat("Is this one available in XL?", {"path": "/products/basic-hoodie-big-yale", "product_id": "basic-hoodie-big-yale"})
    check("Basic Hoodie" in reply["reply"] and "2" in reply["reply"],
          f"on the Basic Hoodie Big Yale page, XL stock is that hoodie's (2 left): \"{reply['reply'][:90]}...\"")

    print("\nPasswords")
    returning.chat(f"Oops, my password is {MAIN_ACCOUNT['password']} - should I change it?")
    saved = last_saved(user_id)
    check(all(MAIN_ACCOUNT["password"] not in text for text in saved) and "[password removed]" in saved[1],
          "a password typed into the chat is removed before it reaches the agent or the database")
    leaks = [t for t in response_texts if "pbkdf2" in t or "password_hash" in t or MAIN_ACCOUNT["password"] in t]
    check(not leaks, f"no response contains a password or a password hash ({len(response_texts)} checked)")
    check(protected_tables() == tables_before, "catalogue and inventory are unchanged")

    failed = results.count(False)
    print(f"\n{len(results) - failed} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
