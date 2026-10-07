"""Checks the audit trail, output/audit_trail.json (Homework 4, Problem 12).

Run from the homework 4 folder while the backend is running:
    .venv/bin/python backend/check_audit.py
(add BACKEND_PORT=8001 in front if the backend runs on port 8001)

It sends four real chat messages (about 30 seconds; one is as the Problem 4 test account and is saved to its
history), then checks that each one added exactly one entry, that the earlier entries are still there byte
for byte, what the entries record, and that no private details or secrets are in the file. Run it again
after restarting the backend to check that entries survive restarts. Finally it sends quick repeats of a
cached question until the chat's per-minute limit refuses one, so wait a minute before chatting again.
"""

from __future__ import annotations

import json
import random
import sys
from contextlib import closing
from pathlib import Path

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_memory import MAIN_ACCOUNT, OTHER_ACCOUNT, Browser  # noqa: E402
from db import PROJECT_ROOT, read_only  # noqa: E402

AUDIT_FILE = PROJECT_ROOT / "output" / "audit_trail.json"
results: list[bool] = []


def check(ok: bool, description: str) -> None:
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {description}")


def snapshot() -> tuple[bytes, list[dict]]:
    if not AUDIT_FILE.exists():
        return b"", []
    data = AUDIT_FILE.read_bytes()
    return data, json.loads(data)


def main() -> int:
    before_bytes, before = snapshot()
    print(f"The audit trail has {len(before)} entries before this run.\n")
    with closing(read_only()) as con:
        name = random.choice([row[0] for row in con.execute("SELECT name FROM catalogue")])  # a fresh question each run

    print("Four chat messages")
    question = f"How much is the {name}, and which sizes are in stock?"
    Browser().chat(question)  # 1. a guest's opening question: the agent runs
    Browser().chat(question)  # 2. the same opening question from another guest: the reply cache answers
    shopper = Browser()
    shopper.log_in(MAIN_ACCOUNT)
    shopper.chat(f"Is the {name} in stock in medium?")  # 3. a logged-in customer: saved to their history
    private = "Hi, I'm Jane Doe, jane.doe@example.org, card 4111 1111 1111 1111. Do you have navy hoodies?"
    Browser().chat(private)  # 4. a guest who types private details into the chat

    after_bytes, after = snapshot()
    new = after[len(before):]
    check(len(after) == len(before) + 4, f"each message added exactly one entry ({len(before)} -> {len(after)})")
    kept = before_bytes.rstrip()[:-1].rstrip() if before_bytes else b""
    check(after_bytes.startswith(kept) and after[: len(before)] == before,
          "earlier entries are unchanged, byte for byte (only the closing bracket was moved)")

    agent_run, cached, logged_in, guest = new
    tools = [step["tool"] for step in agent_run["steps"]]
    check(agent_run["source"] == "agent" and agent_run["stop_reason"] == "replied" and agent_run["claude_calls"] >= 2
          and any(t in ("get_product_details", "check_size_stock", "search_products") for t in tools)
          and agent_run["steps"][-1]["tool"] == "reply_to_customer" and agent_run["steps"][-1]["result"] == "accepted",
          f"an agent run records its time, tools ({', '.join(tools)}), Claude calls and why it stopped")
    print(f"      e.g. {agent_run['steps'][0]['tool']} {json.dumps(agent_run['steps'][0]['args'])} -> {agent_run['steps'][0]['result']}")
    check(cached["source"] == "reply cache" and cached["stop_reason"] == "cached reply" and cached["steps"] == []
          and cached["claude_calls"] == 0, f"a cached reply is recorded as one: \"{cached['note']}\"")
    check(logged_in["customer"] == "logged-in customer" and logged_in["history_turns"] > 0 and logged_in["saved_to_history"],
          f"a logged-in run records that history was used ({logged_in['history_turns']} turns) and the exchange saved, but not who")

    print("\nPrivate details and secrets")
    secrets = {key: value for key, value in dotenv_values(PROJECT_ROOT / ".env").items() if value and len(value) >= 8}
    text = AUDIT_FILE.read_text()
    found = [label for label, value in [
        *((f".env {key}", value) for key, value in secrets.items()),
        ("test account passwords", MAIN_ACCOUNT["password"]), ("test account emails", MAIN_ACCOUNT["email"]),
        ("the other account's email", OTHER_ACCOUNT["email"]), ("a customer's surname", "Tester"),
        ("password hashes", "pbkdf2"), ("session cookies", "cc_session"),
        ("the typed name", "Jane"), ("the typed email", "jane.doe"), ("the typed card number", "4111"),
        ("message text", "which sizes are in stock"), ("message text", "navy hoodies?"),
    ] if value in text]
    check(not found, "no passwords, tokens, secrets, emails, names, card numbers or message text in the file"
          + (f" (found: {', '.join(found)})" if found else ""))
    check(guest["message_chars"] == len(private) and "Jane" not in json.dumps(guest),
          "the run with private details records only the message's length and the product search")

    print("\nThe chat's per-minute limit")
    statuses = []
    for _ in range(25):
        status, _ = Browser().call("POST", "/api/chat", {"message": question, "page": {"path": "/"}})
        statuses.append(status)
        if status == 429:
            break
    last = json.loads(AUDIT_FILE.read_bytes())[-1]
    check(statuses[-1] == 429 and last["stop_reason"] == "rate limited" and last["source"] == "none",
          f"once the limit is reached the message is refused (429 after {len(statuses) - 1} cached replies) and recorded")
    print("      Chat stays limited for about a minute from now.")

    failed = results.count(False)
    print(f"\n{len(results) - failed} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
