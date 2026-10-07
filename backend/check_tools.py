"""Checks the shop agent's lookup tools against the database (Homework 4, Problem 6).

Run from the homework 4 folder; no server is needed:
    .venv/bin/python backend/check_tools.py

For every product and size it compares get_product_details and check_size_stock with a direct SQL
query, then checks how product names and size words are understood, and that the tools are read-only.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))  # import the backend modules as the server does

from db import DB_PATH, SIZE_ORDER, read_only  # noqa: E402
from models import LOW_STOCK, ProductDetails, ProductLookupProblem, SizeStockCheck  # noqa: E402
from tools import (  # noqa: E402
    ShopDeps,
    check_size_stock,
    get_product_details,
    list_categories,
    page_results,
    search_products,
)

results: list[bool] = []


def check(ok: bool, description: str) -> None:
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {description}")


def expected_status(quantity: int) -> str:
    return "sold out" if quantity == 0 else "low stock" if quantity <= LOW_STOCK else "in stock"


def fingerprint(con: sqlite3.Connection) -> str:
    rows = [con.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall() for table in ("catalogue", "inventory")]
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def main() -> int:
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    before = fingerprint(con)
    catalogue = con.execute("SELECT product_id, name, description, price, colors FROM catalogue").fetchall()
    stock = {(pid, size): qty for pid, size, qty in con.execute("SELECT product_id, size, quantity FROM inventory")}

    print("Every product and size against the database")
    detail_problems, size_problems = [], []
    for product_id, name, description, price, colors in catalogue:
        details = get_product_details(product_id)
        ok = (
            isinstance(details, ProductDetails)
            and (details.name, details.description, details.price) == (name, description, price)
            and details.colors_on_product == json.loads(colors)
            and [s.size for s in details.stock] == SIZE_ORDER
            and all(s.quantity == stock[(product_id, s.size)] and s.status == expected_status(s.quantity) for s in details.stock)
            and details.total_stock == sum(stock[(product_id, size)] for size in SIZE_ORDER)
            and details.sizes_sold_out == [size for size in SIZE_ORDER if stock[(product_id, size)] == 0]
        )
        if not ok:
            detail_problems.append(product_id)
        for size in SIZE_ORDER:
            answer = check_size_stock(product_id, size)
            quantity = stock[(product_id, size)]
            if not (isinstance(answer, SizeStockCheck) and answer.price == price and answer.size == size
                    and answer.quantity == quantity and answer.status == expected_status(quantity)
                    and all(o.quantity == stock[(product_id, o.size)] > 0 for o in answer.other_sizes_in_stock)):
                size_problems.append(f"{product_id}/{size}")
    check(not detail_problems, f"get_product_details: description, price, colors and stock match for all {len(catalogue)} products {detail_problems[:3]}")
    check(not size_problems, f"check_size_stock: price, quantity and status match for all {len(stock)} product sizes {size_problems[:3]}")
    sold_out = sum(1 for qty in stock.values() if qty == 0)
    check(sum(check_size_stock(pid, size).status == "sold out" for pid, size in stock) == sold_out,
          f"all {sold_out} sold-out sizes are reported as sold out")

    print("\nProduct names as customers say them")
    for said, product_id in {
        "Boola Boola tee": "boola-boola-t-shirt",
        "the bomber jacket": "brooks-brothers-bomber-jacket-yale",
        "Benjamin Franklin quarter-zip": "benjamin-franklin-1-4-zip",
        "yale mom crewnecks": "yale-mom-crewneck",
        "Basic Hoodie Big Yale": "basic-hoodie-big-yale",
        " BOOLA-BOOLA-T-SHIRT ": "boola-boola-t-shirt",
    }.items():
        found = get_product_details(said)
        check(isinstance(found, ProductDetails) and found.product_id == product_id, f'"{said.strip()}" -> {product_id}')
    ambiguous = get_product_details("Yale Mom")
    check(isinstance(ambiguous, ProductLookupProblem)
          and {c.product_id for c in ambiguous.candidates} == {"yale-mom-crewneck", "yale-mom-hoodie"},
          '"Yale Mom" -> asks which one: Yale Mom Crewneck or Yale Mom Hoodie')
    check(isinstance(get_product_details("gym shorts"), ProductLookupProblem), '"gym shorts" -> no such product (not a guess)')

    print("\nSize words")
    for said, label in {"large": "L", "extra large": "XL", "x-small": "XS", "2XL": "XXL", "med": "M"}.items():
        check(check_size_stock("boola-boola-t-shirt", said).size == label, f'"{said}" -> {label}')
    not_offered = check_size_stock("boola-boola-t-shirt", "3XL")
    check(not_offered.status == "size not offered" and not_offered.size is None and not_offered.quantity == 0,
          '"3XL" -> size not offered')

    print("\nOther tools")
    overview = list_categories()
    db_prices = con.execute("SELECT MIN(price), MAX(price), COUNT(*) FROM catalogue").fetchone()
    check(overview.total_styles == db_prices[2]
          and min(c.price_from for c in overview.categories) == db_prices[0]
          and max(c.price_to for c in overview.categories) == db_prices[1],
          f"list_categories: {overview.total_styles} styles, ${db_prices[0]:.0f} to ${db_prices[1]:.0f}")
    run = SimpleNamespace(deps=ShopDeps())  # stands in for the agent's RunContext
    search = search_products(run, "navy hoodie", size="M", max_price=70)
    check(search.total_matches > 0 and all(p.price <= 70 and "M" in p.sizes_in_stock for p in search.products),
          f"search_products filters by size and price ({search.total_matches} navy hoodies in M under $70)")

    print("\nResults page (page_results, GET /api/search)")
    page = run.deps.page_results
    check(page is not None and [c.product_id for c in page.products][:len(search.products)] == [p.product_id for p in search.products]
          and page.total_matches == search.total_matches,
          "search_products puts its full results on the page; the agent sees the first 8")
    hoodies = page_results(category="Hoodies")
    db_hoodies = {pid for (pid,) in con.execute("SELECT product_id FROM catalogue")} & {c.product_id for c in hoodies.products}
    check(hoodies.total_matches == 27 == len(hoodies.products) == len(db_hoodies) and hoodies.title == "Hoodies",
          f"category Hoodies -> all {hoodies.total_matches} hoodies, titled \"{hoodies.title}\"")
    card = next(c for c in hoodies.products if c.product_id == "basic-hoodie-big-yale")
    db_name, db_price, db_description = con.execute(
        "SELECT name, price, description FROM catalogue WHERE product_id = 'basic-hoodie-big-yale'").fetchone()
    check((card.name, card.price, card.image_url) == (db_name, db_price, "/media/products/basic-hoodie-big-yale.jpg")
          and db_description.startswith(card.short_description.rstrip("…")) and len(card.short_description) <= 101,
          "result cards carry the database's name, price, image path and a short description")
    none = page_results("gym shorts")
    check(none.total_matches == 0 and none.products == [], '"gym shorts" -> no matches (the page says so)')
    odd_size = page_results("hoodie", size="3XL")
    check(odd_size.total_matches == 0 and "XS to XXL" in (odd_size.note or ""), "a size the shop doesn't make -> a note for the page")

    print("\nLookup guard (agent.py)")
    from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, UserPromptPart

    from agent import PRICE_OR_STOCK, _looked_up_this_turn

    asked = ModelRequest(parts=[UserPromptPart(content="How much is the bomber?")])
    looked_up = ModelResponse(parts=[ToolCallPart("get_product_details", {"product": "bomber"})])
    earlier = [ModelRequest(parts=[UserPromptPart(content="Hi")]), looked_up, ModelResponse(parts=[TextPart(content="Hello!")])]
    check(all(PRICE_OR_STOCK.search(text) for text in ("It's $98.00", "only 5 left", "sold out in XL", "15 in stock")),
          "prices and stock claims in a reply are recognized")
    check(not PRICE_OR_STOCK.search("Ask me which sizes are in stock!"), "a general mention of stock is not treated as a claim")
    check(_looked_up_this_turn([asked, looked_up]), "a reply after a lookup this turn is accepted")
    check(not _looked_up_this_turn([*earlier, asked]), "a lookup from an earlier turn doesn't count: the agent must look again")

    print("\nRead-only")
    with read_only() as ro:
        try:
            ro.execute("UPDATE catalogue SET price = 0")
            refused = False
        except sqlite3.OperationalError:
            refused = True
    check(refused, "the tools' connection refuses writes")
    check(fingerprint(con) == before, "catalogue and inventory are unchanged")

    failed = results.count(False)
    print(f"\n{len(results) - failed} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
