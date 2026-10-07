"""Instant answers to repeated opening questions (Homework 4, Problem 9).

Many guests open the chat with the same question, often one of the suggested questions the chat panel
offers. When a guest's first message is a question that was answered recently on the same page, with the
same catalogue, stock and system prompt, the earlier answer is sent again instead of asking Claude. It
arrives at once and uses none of the Claude plan.

Why reusing an answer is safe:
- The key covers everything the answer depended on: the question (ignoring capitals, extra spaces and end
  punctuation), the page the customer is on as the agent was told it, a fingerprint of the catalogue and
  inventory tables, and a fingerprint of prompts/prompt.md. If a price, a stock level or the prompt
  changes, the key changes, so an answer is never reused with old numbers.
- Only guests' opening questions are reused. A logged-in customer's answer can use their name and saved
  history, and a follow-up question depends on the conversation before it.
- Only answers the agent finished are stored. Nothing about the customer is stored, only the question
  and the answer, and an answer is only given to someone who asks the same question.

Answers stay in memory for an hour (at most MAX_ANSWERS, oldest dropped first); a restart clears them.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from contextlib import closing

from agent import MODEL, PROMPT_FILE
from db import read_only
from models import ChatResponse
from tools import PageView

KEEP_SECONDS = 60 * 60
MAX_ANSWERS = 200

log = logging.getLogger("uvicorn.error")
_answers: OrderedDict[str, tuple[float, ChatResponse]] = OrderedDict()  # key -> (time stored, answer)


def _catalogue_fingerprint() -> str:
    """A hash of every catalogue row and stock level (about 1 ms), so any change gives a new key."""
    digest = hashlib.sha256()
    with closing(read_only()) as con:
        for row in con.execute("SELECT * FROM catalogue ORDER BY product_id"):
            digest.update(json.dumps(tuple(row)).encode())
        for row in con.execute("SELECT product_id, size, quantity FROM inventory ORDER BY product_id, size"):
            digest.update(json.dumps(tuple(row)).encode())
    return digest.hexdigest()


def _question(message: str) -> str:
    """The question without capitals, extra spaces or end punctuation, so that "What hoodies do you have?"
    and "what hoodies  do you have" count as the same question."""
    return " ".join(message.lower().split()).rstrip("?!. ")


def key_for(message: str, page: PageView | None) -> str:
    parts = [
        _question(message),
        page.description if page else "",
        (page.product_id or "") if page else "",
        _catalogue_fingerprint(),
        hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest(),
        MODEL,
    ]
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()


def get(key: str) -> tuple[ChatResponse, float] | None:
    """A copy of the stored answer marked cached=True and its age in seconds, or None if there isn't one
    from the last hour."""
    entry = _answers.get(key)
    if entry is None:
        return None
    stored_at, answer = entry
    age = time.monotonic() - stored_at
    if age > KEEP_SECONDS:
        del _answers[key]
        return None
    _answers.move_to_end(key)
    log.info("Chat answered from the reply cache (answer stored %.0fs ago)", age)
    return answer.model_copy(update={"cached": True}, deep=True), age


def put(key: str, answer: ChatResponse) -> None:
    _answers[key] = (time.monotonic(), answer.model_copy(deep=True))
    _answers.move_to_end(key)
    while len(_answers) > MAX_ANSWERS:
        _answers.popitem(last=False)
