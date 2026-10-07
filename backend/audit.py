"""The append-only audit trail of agent runs: output/audit_trail.json (Homework 4, Problem 12).

Every chat message the backend accepts adds one entry: when it arrived, whether a guest or a logged-in
customer asked (never who), the page, each step the agent took (tool name, short argument and result
summaries, and any answer the code checks sent back), the Claude calls used, why the run stopped and a
summary of the reply. Replies from the reply cache, rate-limited messages and failed runs are recorded too,
with the reason and the error.

Never written: the customer's message or the reply text (they can hold names, emails or a password), names,
emails, user ids, client addresses, passwords, hashes, cookies, tokens or keys. Every string that does go
in is shortened by redact(), which also blanks anything shaped like an email address, a long number or a
secret.

The file is one JSON array that only grows. A new entry replaces the closing "]" with ",<entry>]", so the
bytes of earlier entries are never rewritten. A lock (in this process, and on the file where the system
supports it) keeps two runs from writing at once, and the file is on disk, so entries survive restarts.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from pydantic_ai.messages import ModelMessage, ModelRequest, RetryPromptPart, ToolCallPart, ToolReturnPart, UserPromptPart

from db import PROJECT_ROOT
from models import ChatResponse, PageContext

try:
    import fcntl  # file locking on macOS and Linux
except ImportError:  # Windows has no flock; the in-process lock below still keeps writes apart
    fcntl = None

AUDIT_FILE = PROJECT_ROOT / "output" / "audit_trail.json"
MAX_TEXT = 80  # characters kept from one argument or other short string
MAX_SUMMARY = 200  # characters kept from one result summary
MAX_IDS = 4  # product ids listed in one result summary
REPLY_TOOL = "reply_to_customer"
NO_RESULT = "no result (the run stopped first)"

log = logging.getLogger("uvicorn.error")
_write_lock = threading.Lock()
# The run being recorded, so agent.claude_turn can count Claude calls.
CURRENT_RUN: ContextVar[RunRecord | None] = ContextVar("audit_run", default=None)

_SECRET_PREFIX = re.compile(r"\b(?:sk-|pbkdf2)\S*", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_LONG_WORD = re.compile(r"[A-Za-z0-9_\-+/=.]{20,}")
_LONG_NUMBER = re.compile(r"\d(?:[\s-]?\d){7,}")  # 8 or more digits: phone, card or account numbers


def redact(value: object, limit: int = MAX_TEXT) -> str:
    """value as one short line, with emails, long numbers and anything key- or token-shaped blanked out.
    A long word counts as a token if it mixes digits and capitals (product ids are lower case)."""
    text = " ".join(str(value).split())
    text = _SECRET_PREFIX.sub("[secret]", text)
    text = _EMAIL.sub("[email]", text)
    text = _LONG_WORD.sub(
        lambda m: "[secret]" if any(c.isdigit() for c in m.group()) and any(c.isupper() for c in m.group()) else m.group(),
        text,
    )
    text = _LONG_NUMBER.sub("[number]", text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _args_summary(part: ToolCallPart) -> dict[str, Any]:
    try:
        args = part.args_as_dict()
    except Exception:  # arguments that aren't valid JSON
        return {"unreadable_args": redact(part.args)}
    if part.tool_name == REPLY_TOOL:  # the reply itself is never logged, only its size and the products it names
        ids = args.get("product_ids")
        return {
            "reply_chars": len(str(args.get("message", ""))),
            "product_ids": [redact(i, 60) for i in ids[:MAX_IDS]] if isinstance(ids, list) else [],
        }
    return {
        key: value if isinstance(value, (int, float, bool)) else redact(value)
        for key, value in args.items()
        if value not in (None, "")
    }


def _ids(items: list[dict]) -> str:
    ids = [item["product_id"] for item in items]
    return ", ".join(ids[:MAX_IDS]) + ("…" if len(ids) > MAX_IDS else "")


def _result_summary(content: Any) -> str:
    """One line about what a lookup tool returned (tools.py), by the shape of its result."""
    data = content.model_dump() if hasattr(content, "model_dump") else content
    if not isinstance(data, dict):
        return redact(data, MAX_SUMMARY)
    if "problem" in data:
        text = f"lookup problem: {data['problem']} ({len(data.get('candidates', []))} candidates)"
    elif "total_matches" in data:
        text = f"{data['total_matches']} matches" + (f": {_ids(data['products'])}" if data.get("products") else "")
        text += f"; note: {data['note']}" if data.get("note") else ""
    elif "size_asked" in data:
        text = f"{data['product_id']} {data.get('size') or data['size_asked']}: {data['quantity']} ({data['status']}), ${data['price']:.2f}"
        text += f"; similar in stock: {_ids(data['similar_in_stock'])}" if data.get("similar_in_stock") else ""
    elif "stock" in data:
        text = (f"{data['product_id']}: ${data['price']:.2f}; in stock {', '.join(data['sizes_in_stock']) or 'none'}; "
                f"sold out {', '.join(data['sizes_sold_out']) or 'none'}")
    elif "categories" in data:
        text = f"{len(data['categories'])} categories, {data['total_styles']} styles"
    else:
        text = json.dumps(data)
    return redact(text, MAX_SUMMARY)


def _retry_summary(content: Any) -> str:
    if isinstance(content, str):
        return "sent back: " + redact(content, MAX_SUMMARY - 11)
    problems = "; ".join(f"{'.'.join(map(str, e.get('loc', ())))}: {e.get('msg', '')}" for e in content[:3] if isinstance(e, dict))
    return "sent back, invalid arguments: " + redact(problems, MAX_SUMMARY - 30)


def page_label(page: PageContext | None) -> str:
    """The page's path only: a query string can hold whatever the shopper typed into a search box."""
    return redact(page.path.split("?", 1)[0], 120) if page else "(not sent)"


@dataclass
class RunRecord:
    """One chat message, from arrival to reply or refusal, as it will appear in the audit trail."""

    customer: str  # "guest" or "logged-in customer"; never who
    page: str
    time: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    run: str = field(default_factory=lambda: secrets.token_hex(4))
    started: float = field(default_factory=monotonic)
    message_chars: int = 0
    history_turns: int = 0  # earlier turns given to the agent
    source: str = "agent"  # "agent", "reply cache" or "none" (refused before the agent)
    steps: list[dict[str, Any]] = field(default_factory=list)
    claude_calls: int = 0
    stop_reason: str = ""
    error: str | None = None
    note: str | None = None
    reply: dict[str, Any] | None = None
    saved_to_history: bool = False

    def stop(self, reason: str, error: str | None = None, source: str | None = None) -> None:
        self.stop_reason = reason
        self.error = redact(error, MAX_SUMMARY) if error else None
        if source:
            self.source = source

    def add_steps(self, messages: list[ModelMessage]) -> None:
        """This run's tool calls, results and sent-back answers, from PydanticAI's messages after the
        customer's latest message (earlier ones are the conversation history)."""
        start = 0
        for index, message in enumerate(messages):
            if isinstance(message, ModelRequest) and any(isinstance(part, UserPromptPart) for part in message.parts):
                start = index + 1
        by_call: dict[str, dict[str, Any]] = {}
        for message in messages[start:]:
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    step = {"tool": part.tool_name, "args": _args_summary(part), "result": NO_RESULT}
                    self.steps.append(step)
                    by_call[part.tool_call_id] = step
                elif isinstance(part, ToolReturnPart) and part.tool_call_id in by_call:
                    by_call[part.tool_call_id]["result"] = "accepted" if part.tool_name == REPLY_TOOL else _result_summary(part.content)
                elif isinstance(part, RetryPromptPart):
                    step = by_call.get(part.tool_call_id)
                    if step is None:
                        self.steps.append({"tool": part.tool_name or "(answer)", "result": _retry_summary(part.content)})
                    else:
                        step["result"] = _retry_summary(part.content)
        if self.stop_reason == "answer kept failing checks":  # the last answer failed too; nothing more was sent back
            last_reply = next((s for s in reversed(self.steps) if s["tool"] == REPLY_TOOL and s["result"] == NO_RESULT), None)
            if last_reply:
                last_reply["result"] = "failed the checks again; no retries left"

    def _reply_summary(self, response: ChatResponse) -> dict[str, Any]:
        results = response.page_results
        return {
            "chars": len(response.reply),
            "product_cards": [card.product_id for card in response.products],
            "results_page": {"title": redact(results.title), "matches": results.total_matches} if results else None,
        }

    def replied(self, response: ChatResponse) -> None:
        self.stop("replied")
        self.reply = self._reply_summary(response)
        self.saved_to_history = response.saved
        for step in self.steps:
            if step["tool"] == REPLY_TOOL and step["result"] == NO_RESULT:
                step["result"] = "accepted"

    def cached(self, response: ChatResponse, age_seconds: float) -> None:
        self.stop("cached reply", source="reply cache")
        self.note = f"the same opening question was answered {age_seconds:.0f} s earlier; no Claude call"
        self.reply = self._reply_summary(response)

    def entry(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "run": self.run,
            "customer": self.customer,
            "page": self.page,
            "message_chars": self.message_chars,
            "history_turns": self.history_turns,
            "source": self.source,
            "steps": self.steps,
            "claude_calls": self.claude_calls,
            "stop_reason": self.stop_reason,
            "error": self.error,
            "note": self.note,
            "reply": self.reply,
            "saved_to_history": self.saved_to_history,
            "duration_s": round(monotonic() - self.started, 2),
        }


TAIL_BYTES = 4096  # how much of the end of the file is read to find the closing bracket


def append(entry: dict[str, Any]) -> None:
    """Add one entry to the end of the JSON array in AUDIT_FILE without rewriting earlier entries: only the
    closing "]" (and the whitespace around it) at the very end is cut and written again after the entry."""
    text = json.dumps(entry, ensure_ascii=False, indent=2).encode()
    with _write_lock:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_FILE, "a+b") as file:  # appending: every write goes to the end
            if fcntl:
                fcntl.flock(file, fcntl.LOCK_EX)
            try:
                size = file.seek(0, os.SEEK_END)
                start = max(0, size - TAIL_BYTES)
                file.seek(start)
                content = file.read().rstrip()
                if content.endswith(b"]"):
                    content = content[:-1].rstrip()  # the end of the last entry, or the opening "["
                if not content and start == 0:  # a new, empty file
                    file.truncate(0)
                    file.write(b"[\n" + text + b"\n]\n")
                elif content.endswith((b"}", b"[")):
                    # Also continues a file whose last write stopped before its closing bracket.
                    file.truncate(start + len(content))
                    file.write((b"\n" if content.endswith(b"[") else b",\n") + text + b"\n]\n")
                else:
                    raise ValueError(f"{AUDIT_FILE.name} doesn't end like a JSON array; nothing was written to it")
                file.flush()
                os.fsync(file.fileno())
            finally:
                if fcntl:
                    fcntl.flock(file, fcntl.LOCK_UN)


def record(run: RunRecord) -> None:
    """Append the run to the audit trail. A failure here is logged but never breaks the chat."""
    try:
        append(run.entry())
    except Exception:
        log.exception("Could not write to the audit trail")
