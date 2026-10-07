"""The shop agent's tools: read-only lookups in data/campus_customs.db.

- search_products       find products from the customer's words and filters; its matches are also
                        shown on the website's results page
- get_product_details   one product's description, price, colors and stock in every size
- check_size_stock      the exact stock of one size of one product, and when it's sold out, similar
                        products that have that size in stock
- list_categories       what the shop sells, with price ranges

Every tool reads through a read-only connection (db.read_only), so the agent can look things up but
never change them, and no tool can see accounts, passwords or other customers. Results use the
structured types at the bottom of models.py. get_product_details and check_size_stock accept a
product_id or the product's name as the customer said it; when a name could mean several products,
or none, they return candidates instead of guessing.

page_results() runs the same search for the website's results page: GET /api/search calls it, and
each search_products call stores its results in the run's deps so the chat reply can carry them.
"""

from __future__ import annotations

import re
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import parse_qs

from pydantic import Field
from pydantic_ai import RunContext

from db import SIZE_ORDER, load_products, read_only
from models import (
    LOW_STOCK,
    MAX_REPLY_PRODUCTS,
    CatalogueOverview,
    CategorySummary,
    PageContext,
    PageResults,
    Product,
    ProductCandidate,
    ProductCard,
    ProductDetails,
    ProductLookupProblem,
    ProductMatch,
    ProductSearchResult,
    SimilarInStock,
    SizeStock,
    SizeStockCheck,
    StockStatus,
    UserOut,
)

MAX_RESULTS = 8  # search matches the agent sees; the results page shows them all
MAX_CANDIDATES = 6
MAX_CARDS = MAX_REPLY_PRODUCTS  # product cards under one reply
MAX_SIMILAR = 3  # similar products offered when a size is sold out
SHORT_DESCRIPTION = 100  # characters of description on a product card

# Size words customers use, written without spaces or hyphens, and the shop's label for each.
SIZE_WORDS = {
    "xs": "XS", "xsmall": "XS", "extrasmall": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "xlarge": "XL", "extralarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xxlarge": "XXL", "2xlarge": "XXL", "extraextralarge": "XXL", "doubleextralarge": "XXL",
}
# Words are matched whole, so "red" doesn't match "centered" and "shorts" doesn't match "short-sleeve".
# Two-word and hyphenated garment terms become one word ("t shirt", "T-Shirt" -> "tshirt").
COMPOUNDS = {
    ("t", "shirt"): "tshirt", ("quarter", "zip"): "quarterzip", ("full", "zip"): "fullzip", ("half", "zip"): "halfzip",
    ("long", "sleeve"): "longsleeve", ("short", "sleeve"): "shortsleeve", ("crew", "neck"): "crewneck", ("zip", "up"): "zipup",
}
WORD_ALIASES = {"tee": "tshirt", "hoody": "hoodie", "grey": "gray"}  # customers' words -> the catalogue's
TERM_ALTERNATIVES = {  # a search word that should also match these compound words
    "shirt": {"tshirt"},
    "zip": {"fullzip", "quarterzip", "halfzip", "zipup"},
    "sleeve": {"longsleeve", "shortsleeve"},
}
IGNORED_WORDS = {"the", "a", "an", "my", "your", "this", "that", "of", "in", "for", "and", "with", "one", "please"}

# Bounds on what the agent may pass to a tool. An argument outside them is sent back to the agent to fix
# before the tool runs (PydanticAI validates tool arguments against these types).
MAX_TOOL_TEXT = 100
SearchWords = Annotated[str, Field(max_length=MAX_TOOL_TEXT)]
ProductName = Annotated[str, Field(min_length=1, max_length=MAX_TOOL_TEXT)]
CategoryName = Annotated[str, Field(max_length=40)]
SizeWord = Annotated[str, Field(min_length=1, max_length=20)]
Budget = Annotated[float, Field(gt=0, le=1000)]
# Words in product names that describe the garment or are shared by unrelated designs. The other name words
# name the design ("Dad", "Pierson", "Baseball", "Champion"), so products that share one look alike.
# "field" is here because it's in both "Track Field" and "Field Hockey"; "crew" is a garment word here.
GENERIC_NAME_WORDS = {
    "yale", "university", "college", "school", "of", "the", "and", "vs", "sports", "field", "left", "chest", "logo",
    "crest", "crewneck", "creqneck", "crew", "mockneck", "hoodie", "hood", "shirt", "long", "sleeve", "zip", "full",
    "fleece", "jacket", "sweater", "tri", "blend", "double", "knit", "heavyweight", "super", "premium", "basic",
    "mens", "tech",
}


@dataclass
class PageView:
    """The page the customer is looking at, checked against the catalogue (see page_view)."""

    description: str  # e.g. 'the product page for "Boola Boola T Shirt" (product_id boola-boola-t-shirt)'
    product_id: str | None = None  # set only on a product page, and only for a product that exists


@dataclass
class ShopDeps:
    """Per-message context for the agent run.

    customer comes from the session cookie (None for a guest): id, names and email, never the password.
    page is what they're looking at. page_results is filled by search_products, so the chat reply can
    show the latest search on the results page.
    """

    customer: UserOut | None = None
    page: PageView | None = None
    page_results: PageResults | None = None


# ---------- Helpers ----------


def _catalogue() -> list[Product]:
    with closing(read_only()) as con:
        return load_products(con)


def _normalize(text: str) -> str:
    """Lower case, with hyphens and slashes as spaces and other punctuation removed: "T-Shirt" -> "t shirt"."""
    return " ".join(re.sub(r"[^a-z0-9& ]", "", re.sub(r"[-/–]", " ", text.lower())).split())


def _singular(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _words(text: str) -> list[str]:
    """Lower-case words with compounds joined ("T-Shirt", "t shirts" -> "tshirt"), plurals trimmed and aliases applied."""
    raw = [word.replace("-", "") for word in re.sub(r"[^a-z0-9\- ]", " ", text.lower().replace("/", " ")).split()]
    words, i = [], 0
    while i < len(raw):
        pair = (raw[i], _singular(raw[i + 1])) if i + 1 < len(raw) else None
        if pair in COMPOUNDS:
            words.append(COMPOUNDS[pair])
            i += 2
        else:
            words.append(raw[i])
            i += 1
    return [WORD_ALIASES.get(_singular(word), _singular(word)) for word in words if word]


def _terms(text: str) -> list[str]:
    """The words of a customer's query to look for."""
    return [word for word in _words(text) if len(word) > 1 and word not in IGNORED_WORDS]


def _has(words: set[str], term: str) -> bool:
    return term in words or bool(TERM_ALTERNATIVES.get(term, set()) & words)


def _status(quantity: int) -> StockStatus:
    if quantity == 0:
        return "sold out"
    return "low stock" if quantity <= LOW_STOCK else "in stock"


def _stock(product: Product) -> list[SizeStock]:
    return [SizeStock(size=level.size, quantity=level.quantity, status=_status(level.quantity)) for level in product.inventory]


def _sizes_in_stock(product: Product) -> list[str]:
    return [level.size for level in product.inventory if level.quantity > 0]


def _size_label(size: str) -> str | None:
    return SIZE_WORDS.get(re.sub(r"[\s\-]", "", size.lower()))


def _candidate(product: Product) -> ProductCandidate:
    return ProductCandidate(product_id=product.product_id, name=product.name, price=product.price)


def _short_description(text: str) -> str:
    if len(text) <= SHORT_DESCRIPTION:
        return text
    return text[:SHORT_DESCRIPTION].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _card(product: Product) -> ProductCard:
    return ProductCard(
        product_id=product.product_id,
        name=product.name,
        category=product.category,
        price=product.price,
        image_url=product.image_url,
        short_description=_short_description(product.description),
        sizes_in_stock=_sizes_in_stock(product),
    )


@dataclass
class _Search:
    exact: list[Product]  # match every search word
    close: list[Product]  # match some of the words, best first
    size_label: str | None
    filter_problem: str | None  # a size or category the shop doesn't have

    def note_for_agent(self) -> str | None:
        if self.filter_problem:
            return self.filter_problem
        if not self.exact and self.close:
            return "Nothing matched every word; these products match some of them."
        if not self.exact:
            return "Nothing in the catalogue matches. Say so honestly and suggest something close if you can."
        return None


def _run_search(query: str, category: str | None, max_price: float | None, size: str | None) -> _Search:
    """The catalogue search behind both search_products and the results page."""
    catalogue = _catalogue()
    terms = _terms(query)
    size_label = _size_label(size) if size else None
    categories = sorted({product.category for product in catalogue})
    filter_problem = None
    if size and size_label is None:
        filter_problem = f'The shop doesn\'t make size "{size}"; sizes run XS to XXL.'
    elif category and category.strip().lower() not in {name.lower() for name in categories}:
        filter_problem = f'There is no category called "{category}". Categories: {", ".join(categories)}.'

    scored: list[tuple[int, Product]] = []
    for product in catalogue:
        if category and product.category.lower() != category.strip().lower():
            continue
        if max_price is not None and product.price > max_price:
            continue
        if size and size_label not in _sizes_in_stock(product):
            continue
        words = set(_words(" ".join([product.name, product.garment_type, product.category, product.description,
                                     *product.colors, *product.search_tags])))
        scored.append((sum(_has(words, term) for term in terms), product))
    exact = [product for hits, product in scored if hits == len(terms)]
    close = [product for hits, product in sorted(scored, key=lambda pair: -pair[0]) if 0 < hits < len(terms)]
    return _Search(exact=exact, close=close, size_label=size_label, filter_problem=filter_problem)


def _search_title(query: str, category: str | None, max_price: float | None, size_label: str | None) -> str:
    parts = [f"\u201c{query.strip()}\u201d" if query.strip() else None, category,
             f"size {size_label}" if size_label else None, f"up to ${max_price:g}" if max_price is not None else None]
    return " \u00b7 ".join(part for part in parts if part) or "All products"


def _find(product: str, catalogue: list[Product]) -> Product | ProductLookupProblem:
    """The product a customer means, from a product_id or a name as they said it ("Boola Boola tee")."""
    wanted = product.strip().lower()
    for item in catalogue:
        if item.product_id == wanted:
            return item
    terms = _terms(product)
    if not terms:
        return ProductLookupProblem(problem="Give the product's name or product_id.", candidates=[])

    def name_words(item: Product) -> set[str]:
        return set(_words(f"{item.name} {item.garment_type} {item.category}"))

    scored = [(sum(_has(name_words(item), term) for term in terms), item) for item in catalogue]
    full = [item for hits, item in scored if hits == len(terms)]
    if len(full) == 1:
        return full[0]
    exact = [item for item in full if _normalize(item.name) == _normalize(product)]
    if len(exact) == 1:
        return exact[0]
    if full:
        return ProductLookupProblem(
            problem=f'"{product}" could be {len(full)} products. Use the one the customer means, or ask them.',
            candidates=[_candidate(item) for item in full[:MAX_CANDIDATES]],
        )
    best = max(hits for hits, _ in scored)
    closest = [item for hits, item in scored if best > 0 and hits == best]
    return ProductLookupProblem(
        problem=f'No product is called "{product}".' + (" These are the closest names." if closest else ""),
        candidates=[_candidate(item) for item in closest[:MAX_CANDIDATES]],
    )


def _design_words(product: Product) -> set[str]:
    return {word for word in _normalize(product.name).split() if len(word) > 1 and word not in GENERIC_NAME_WORDS}


def _similar_in_stock(product: Product, size: str, catalogue: list[Product]) -> list[SimilarInStock]:
    """Up to MAX_SIMILAR other products with `size` in stock that are like `product`: the same design (a
    shared design word such as "Dad" or "Pierson") or the same category. The same design in the same
    category comes first, then the same design in another style, then the same category; ties go to more
    shared name words ("College Crewneck"), the closest price, then the most stock."""
    design = _design_words(product)
    name_words = set(_normalize(product.name).split())
    ranked = []
    for other in catalogue:
        quantity = next((level.quantity for level in other.inventory if level.size == size), 0)
        if other.product_id == product.product_id or quantity == 0:
            continue
        shared_design = len(design & _design_words(other))
        same_category = other.category == product.category
        if not shared_design and not same_category:
            continue
        shared_words = len(name_words & set(_normalize(other.name).split()))
        rank = (not shared_design, not same_category, -shared_design, -shared_words,
                abs(other.price - product.price), -quantity, other.name)
        because = ("same design and category" if shared_design and same_category
                   else "same design" if shared_design else "same category")
        ranked.append((rank, SimilarInStock(
            product_id=other.product_id, name=other.name, category=other.category, price=other.price,
            quantity=quantity, status=_status(quantity), similar_because=because,
        )))
    ranked.sort(key=lambda entry: entry[0])
    return [similar for _, similar in ranked[:MAX_SIMILAR]]


# ---------- Tools ----------


def page_results(
    query: str = "",
    category: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
) -> PageResults:
    """Every product that matches all the search words and filters, as cards for the results page."""
    return _page(_run_search(query, category, max_price, size), query, category, max_price, size)


def _page(found: _Search, query: str, category: str | None, max_price: float | None, size: str | None) -> PageResults:
    return PageResults(
        title=_search_title(query, category, max_price, found.size_label),
        query=query.strip(),
        category=category,
        max_price=max_price,
        size=found.size_label or size,
        total_matches=len(found.exact),
        note=found.filter_problem,
        products=[_card(product) for product in found.exact],
    )


def search_products(
    ctx: RunContext[ShopDeps],
    query: SearchWords = "",
    category: CategoryName | None = None,
    max_price: Budget | None = None,
    size: SizeWord | None = None,
) -> ProductSearchResult:
    """Find products from the customer's words and filters. All matches are shown as product cards on the website's results page; you get the first 8, with price, sizes in stock, colors_on_product (every color in the design; one colorway per product) and description.

    Args:
        query: Words that describe the products, for example "navy hoodie", "mom" or "bulldog". Leave out filler words like "cozy" or "nice", and leave it empty to browse a whole category.
        category: Only this category: Hoodies, Crewnecks, T-Shirts, Quarter-Zips, Jackets & Fleece or Long Sleeves.
        max_price: Only products at or under this price, in US dollars.
        size: Only products with this size in stock, for example "M" or "large".
    """
    found = _run_search(query, category, max_price, size)
    ctx.deps.page_results = _page(found, query, category, max_price, size)  # the latest search goes on the page
    shown = found.exact or found.close
    return ProductSearchResult(
        total_matches=len(shown),
        products=[
            ProductMatch(
                product_id=p.product_id, name=p.name, category=p.category, price=p.price,
                colors_on_product=p.colors, sizes_in_stock=_sizes_in_stock(p), description=p.description,
            )
            for p in shown[:MAX_RESULTS]
        ],
        note=found.note_for_agent(),
    )


def get_product_details(product: ProductName) -> ProductDetails | ProductLookupProblem:
    """One product's description, price, colors and exact stock in every size (XS to XXL).

    Args:
        product: The product_id, or the product's name as the customer said it, for example "Boola Boola tee".
    """
    found = _find(product, _catalogue())
    if isinstance(found, ProductLookupProblem):
        return found
    stock = _stock(found)
    return ProductDetails(
        product_id=found.product_id,
        name=found.name,
        category=found.category,
        garment_type=found.garment_type,
        description=found.description,
        price=found.price,
        colors_on_product=found.colors,
        stock=stock,
        total_stock=found.total_stock,
        sizes_in_stock=[level.size for level in stock if level.quantity > 0],
        sizes_sold_out=[level.size for level in stock if level.quantity == 0],
    )


def check_size_stock(product: ProductName, size: SizeWord) -> SizeStockCheck | ProductLookupProblem:
    """The exact number in stock for one size of one product, whether that size is sold out, and the other sizes that are in stock. When the size is sold out, similar_in_stock lists up to 3 similar products (same design or same category) that have that size in stock.

    Args:
        product: The product_id, or the product's name as the customer said it, for example "Boola Boola tee".
        size: The size the customer asked about, for example "L", "large" or "extra large".
    """
    catalogue = _catalogue()
    found = _find(product, catalogue)
    if isinstance(found, ProductLookupProblem):
        return found
    stock = _stock(found)
    label = _size_label(size)
    level = next((entry for entry in stock if entry.size == label), None)
    unavailable = level is None or level.quantity == 0
    return SizeStockCheck(
        product_id=found.product_id,
        name=found.name,
        price=found.price,
        size_asked=size,
        size=level.size if level else None,
        quantity=level.quantity if level else 0,
        status=level.status if level else "size not offered",
        other_sizes_in_stock=[entry for entry in stock if entry.quantity > 0 and entry.size != label],
        # Only for a size the shop makes (XS to XXL) that this product is out of.
        similar_in_stock=_similar_in_stock(found, label, catalogue) if label and unavailable else [],
    )


def list_categories() -> CatalogueOverview:
    """What the shop sells: each category with its number of styles and price range, plus the sizes offered."""
    catalogue = _catalogue()
    by_category: dict[str, list[Product]] = defaultdict(list)
    for product in catalogue:
        by_category[product.category].append(product)
    return CatalogueOverview(
        total_styles=len(catalogue),
        sizes_offered=SIZE_ORDER,
        categories=[
            CategorySummary(name=name, styles=len(items), price_from=min(p.price for p in items),
                            price_to=max(p.price for p in items))
            for name, items in sorted(by_category.items())
        ],
    )


# ---------- Used by agent.py, not given to the agent ----------

PAGE_NAMES = {
    "/": "the home page",
    "/products": "the all-products page",
    "/about": "the About Us page",
    "/login": "the log in page",
    "/create-account": "the create account page",
}


def page_view(page: PageContext | None) -> PageView | None:
    """Describe the customer's page for the agent. A product id from the page only counts if it's a real
    product, so the agent is never told about an item that doesn't exist."""
    if page is None:
        return None
    if page.product_id:
        product = next((p for p in _catalogue() if p.product_id == page.product_id.strip()), None)
        if product:
            return PageView(f'the product page for "{product.name}" (product_id {product.product_id})', product.product_id)
    path, _, query = page.path.partition("?")
    if path == "/search":
        params = {key: values[0] for key, values in parse_qs(query).items()}
        try:
            max_price = float(params["max_price"]) if "max_price" in params else None
        except ValueError:
            max_price = None
        size = params.get("size")
        title = _search_title(params.get("q", ""), params.get("category"), max_price, _size_label(size) if size else None)
        return PageView(f"the search results page for {title}")
    return PageView(PAGE_NAMES.get(path.rstrip("/") or "/", "a page of the shop's website"))


def resolve_product_id(product: str) -> str | None:
    """The product_id a lookup tool would use for this product_id or name, or None if it's unclear."""
    found = _find(product, _catalogue())
    return found.product_id if isinstance(found, Product) else None


def unknown_product_ids(product_ids: list[str]) -> list[str]:
    known = {product.product_id for product in _catalogue()}
    return [product_id for product_id in product_ids if product_id not in known]


def product_cards(product_ids: list[str]) -> list[ProductCard]:
    """Cards for the products a reply names, straight from the database (repeats and unknown ids skipped)."""
    by_id = {product.product_id: product for product in _catalogue()}
    return [_card(by_id[pid]) for pid in dict.fromkeys(product_ids) if pid in by_id][:MAX_CARDS]
