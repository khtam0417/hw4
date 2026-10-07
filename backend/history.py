"""Saved conversations for logged-in customers, in the existing chat_messages table.

Each exchange adds two rows: the customer's message (role "user", products_json NULL) and the
assistant's reply (role "assistant", products_json = the product cards shown with it, or []). That
is the same layout as the 22 messages that came with the database, so those load the same way.
Every query is filtered by the logged-in customer's user id, which comes from their session cookie,
never from the request body, so nobody can read or add to someone else's history. Guests' chats are
never stored.
"""

from __future__ import annotations

import json
from contextlib import closing

from db import customer_writer, read_only
from models import ChatResponse, ChatTurn, SavedMessage
from tools import product_cards

SHOWN_MESSAGES = 50  # most recent messages reloaded into the chat panel


def _product_ids(products_json: str | None) -> list[str]:
    """The product ids in a saved reply's products_json, whatever shape the cards were saved in."""
    try:
        items = json.loads(products_json or "[]")
    except json.JSONDecodeError:
        return []
    return [item["product_id"] for item in items if isinstance(item, dict) and isinstance(item.get("product_id"), str)]


def load_history(user_id: int, limit: int = SHOWN_MESSAGES) -> list[SavedMessage]:
    """The customer's most recent saved messages, oldest first. Product cards are rebuilt from the saved
    product ids, so they show today's prices and stock."""
    with closing(read_only()) as con:
        rows = con.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [
        SavedMessage(role=row["role"], content=row["content"], products=product_cards(_product_ids(row["products_json"])),
                     created_at=row["created_at"])
        for row in reversed(rows)
        if row["role"] in ("user", "assistant")
    ]


def recent_turns(user_id: int, limit: int) -> list[ChatTurn]:
    """The customer's last few saved turns, oldest first, as context for the agent."""
    with closing(read_only()) as con:
        rows = con.execute(
            "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ).fetchall()
    return [ChatTurn(role=row["role"], content=row["content"]) for row in reversed(rows) if row["role"] in ("user", "assistant")]


def save_exchange(user_id: int, message: str, reply: ChatResponse) -> None:
    """Store the customer's message and the agent's reply (with its product cards) in one transaction."""
    cards = json.dumps([card.model_dump() for card in reply.products])
    with closing(customer_writer()) as con:
        con.execute("INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
                    (user_id, message))
        con.execute("INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
                    (user_id, reply.reply, cards))
        con.commit()
