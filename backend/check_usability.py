"""Checks the agent and backend usability improvements (Homework 4, Problem 9).

Run from the homework 4 folder while the backend is running:
    .venv/bin/python backend/check_usability.py
(add BACKEND_PORT=8001 in front if the backend runs on port 8001)

Part 1 needs no server: it compares check_size_stock's similar_in_stock suggestions with the database for
every sold-out size. Part 2 sends real chat messages to check the reply cache, so it takes about a minute
and adds one exchange to the Problem 4 test account's saved history. The two frontend improvements (size
filter, suggested questions) were tested in the browser; see output/usability.md.
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # import the backend modules as the server does

import reply_cache  # noqa: E402
from check_memory import MAIN_ACCOUNT, Browser  # noqa: E402
from db import DB_PATH  # noqa: E402
from models import PageContext, SizeStockCheck  # noqa: E402
from tools import _design_words, _catalogue, check_size_stock, page_view  # noqa: E402

results: list[bool] = []


def check(ok: bool, description: str) -> None:
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {description}")


def fingerprint(con: sqlite3.Connection) -> str:
    rows = [con.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall() for table in ("catalogue", "inventory")]
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def check_similar_in_stock(con: sqlite3.Connection) -> None:
    print("Improvement 3: in-stock alternatives when a size is sold out")
    stock = {(pid, size): qty for pid, size, qty in con.execute("SELECT product_id, size, quantity FROM inventory")}
    products = {product.product_id: product for product in _catalogue()}
    sold_out = [(pid, size) for (pid, size), qty in stock.items() if qty == 0]
    problems, with_suggestions = [], 0
    for pid, size in sold_out:
        result = check_size_stock(pid, size)
        assert isinstance(result, SizeStockCheck)
        suggestions = result.similar_in_stock
        with_suggestions += bool(suggestions)
        for s in suggestions:
            other, original = products[s.product_id], products[pid]
            shares_design = bool(_design_words(original) & _design_words(other))
            same_category = other.category == original.category
            label_ok = {"same design and category": shares_design and same_category,
                        "same design": shares_design and not same_category,
                        "same category": same_category and not shares_design}[s.similar_because]
            if s.product_id == pid or stock[(s.product_id, size)] == 0 or s.quantity != stock[(s.product_id, size)] or not label_ok:
                problems.append((pid, size, s.product_id))
        if len(suggestions) > 3:
            problems.append((pid, size, "more than 3"))
    check(not problems, f"for all {len(sold_out)} sold-out sizes, every suggestion has that size in stock (exact "
                        f"quantity from the database), is a different product and is similar as labelled")
    print(f"      {with_suggestions} of {len(sold_out)} sold-out sizes get at least one suggestion")

    dad = check_size_stock("yale-dad-crewneck", "medium")
    first_two = [s.product_id for s in dad.similar_in_stock[:2]]
    check(first_two == ["yale-dad-hoodie", "yale-dad-t-shirt"],
          f"Yale Dad Crewneck in M (sold out) suggests the same design first: {', '.join(first_two)}")
    in_stock = [check_size_stock(pid, size) for (pid, size), qty in stock.items() if qty > 0]
    check(all(not r.similar_in_stock for r in in_stock), f"no suggestions when the size is in stock ({len(in_stock)} sizes)")
    xxxl = check_size_stock("yale-dad-crewneck", "XXXL")
    check(xxxl.status == "size not offered" and not xxxl.similar_in_stock, "no suggestions for a size the shop doesn't make (XXXL)")


def chat(browser: Browser, message: str, page: dict, history: list[dict] | None = None) -> tuple[dict, float]:
    started = time.perf_counter()
    status, body = browser.call("POST", "/api/chat", {"message": message, "page": page, "history": history or []})
    assert status == 200, f"chat failed ({status}): {body}"
    return body, time.perf_counter() - started


def check_reply_cache() -> None:
    print("\nImprovement 4: instant answers to repeated opening questions (needs the backend)")
    product = random.choice(_catalogue())  # a fresh question each run, so the first answer isn't already stored
    question = f"How much is the {product.name}?"
    home = {"path": "/"}

    first, first_time = chat(Browser(), question, home)
    second, second_time = chat(Browser(), question.lower().rstrip("?"), home)
    same = all(first[field] == second[field] for field in ("reply", "products", "page_results"))
    check(second["cached"] is True and same and second_time < 1,
          f"a second guest asking the same opening question gets the same answer from the cache "
          f"({first_time:.1f}s with Claude, {second_time:.2f}s from the cache)")
    print(f"      Q: {question}\n      A: {first['reply'][:110]}...")

    other_page = {"path": "/products/boola-boola-t-shirt", "product_id": "boola-boola-t-shirt"}
    reply, _ = chat(Browser(), question, other_page)
    check(reply["cached"] is False, "the same question on a different page is answered fresh")
    turns = [{"role": "user", "content": "Hi!"}, {"role": "assistant", "content": first["reply"]}]
    reply, _ = chat(Browser(), question, home, history=turns)
    check(reply["cached"] is False, "a guest's follow-up question (with earlier turns) is answered fresh")
    shopper = Browser()
    shopper.log_in(MAIN_ACCOUNT)
    reply, _ = chat(shopper, question, home)
    check(reply["cached"] is False and reply["saved"] is True,
          "a logged-in customer is answered fresh, and the exchange is saved to their history")

    page = page_view(PageContext(path="/"))
    key = reply_cache.key_for(question, page)
    real_fingerprint = reply_cache._catalogue_fingerprint
    reply_cache._catalogue_fingerprint = lambda: "a price or stock level changed"
    changed = reply_cache.key_for(question, page)
    reply_cache._catalogue_fingerprint = real_fingerprint
    check(key != changed and key == reply_cache.key_for(question, page),
          "a change to the catalogue or stock gives a new cache key, so old answers are never reused")


def main() -> int:
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    before = fingerprint(con)
    check_similar_in_stock(con)
    check_reply_cache()
    print()
    check(fingerprint(con) == before, "catalogue and inventory are unchanged")
    failed = results.count(False)
    print(f"\n{len(results) - failed} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
