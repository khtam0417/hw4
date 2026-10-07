"""SQLite access for the Campus Customs backend.

Product reads use read_only(), so the catalogue and inventory can never change through them.
The only writes (new accounts, saved chat messages) go through customer_writer(): a normal connection
whose SQLite authorizer refuses any write outside the users and chat_messages tables, so even a bug
in that code cannot touch the catalogue or inventory.
load_products() is the one place that turns catalogue and inventory rows into Product objects,
for both the product API and the shop agent's tools.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from models import Product, StockLevel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
MEDIA_URL = "/media"  # a product's image_url is MEDIA_URL + "/" + its image_file_path
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

if not DB_PATH.exists():
    raise RuntimeError(f"Database not found at {DB_PATH}. Unzip the data so data/campus_customs.db exists.")

# Reading and transactions are always allowed. Writes are allowed only on these tables
# (adding a row also updates the table's counter that SQLite keeps in sqlite_sequence).
_ALWAYS_ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_TRANSACTION}
_WRITES = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
_WRITABLE_TABLES = {"users", "chat_messages", "sqlite_sequence"}

# garment_type is free text with 22 spellings, so group it into a few shop categories.
# The first keyword found in the lower-cased garment_type wins; everything else is a crewneck.
CATEGORY_RULES = [
    ("t-shirt", "T-Shirts"),
    ("hood", "Hoodies"),
    ("quarter-zip", "Quarter-Zips"),
    ("jacket", "Jackets & Fleece"),
    ("long-sleeve", "Long Sleeves"),
]
DEFAULT_CATEGORY = "Crewnecks"


def read_only() -> sqlite3.Connection:
    """Open the database read-only (mode=ro): nothing can be changed through this connection."""
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _allow_customer_tables(action: int, table: str | None, *_: str | None) -> int:
    if action in _ALWAYS_ALLOWED or (action in _WRITES and table in _WRITABLE_TABLES):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def customer_writer() -> sqlite3.Connection:
    """Open the database for writing, limited by an authorizer to the users and chat_messages tables."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.set_authorizer(_allow_customer_tables)
    return con


def category_for(garment_type: str) -> str:
    text = garment_type.lower()
    return next((label for keyword, label in CATEGORY_RULES if keyword in text), DEFAULT_CATEGORY)


def load_products(con: sqlite3.Connection, product_id: str | None = None) -> list[Product]:
    """Catalogue rows joined with their inventory; all products, or just one when product_id is given."""
    where, params = ("WHERE product_id = ?", (product_id,)) if product_id else ("", ())
    stock: dict[str, list[StockLevel]] = {}
    for row in con.execute(f"SELECT product_id, size, quantity FROM inventory {where}", params):
        stock.setdefault(row["product_id"], []).append(StockLevel(size=row["size"], quantity=row["quantity"]))
    for sizes in stock.values():
        sizes.sort(key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER))

    products = []
    for row in con.execute(f"SELECT * FROM catalogue {where} ORDER BY name", params):
        sizes = stock.get(row["product_id"], [])
        products.append(Product(
            product_id=row["product_id"],
            name=row["name"],
            garment_type=row["garment_type"],
            category=category_for(row["garment_type"]),
            description=row["description"],
            colors=json.loads(row["colors"]),
            search_tags=json.loads(row["search_tags"]),
            image_file_path=row["image_file_path"],
            image_url=f"{MEDIA_URL}/{row['image_file_path']}",
            price=row["price"],
            inventory=sizes,
            total_stock=sum(s.quantity for s in sizes),
        ))
    return products
