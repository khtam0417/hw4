"""Pydantic shapes shared by the Campus Customs backend.

- StockLevel / Product: one catalogue item with its stock, as GET /api/products returns it.
- UserOut: the logged-in shopper as the site and the agent may see them (never the password or its hash).
- ChatTurn / PageContext / ChatRequest / ChatResponse: what the chat panel sends to POST /api/chat and
  gets back. SavedMessage / ChatHistory: a logged-in shopper's saved conversation (GET /api/chat/history).
- AgentReply: the structured answer the shop agent must give for each customer message.
- ProductCard: a product shown under a chat reply. The agent only names product ids; the backend
  builds the cards from the database, so the names, prices and sizes on them are always real.
- Tool results (the bottom of this file): what each of the agent's lookup tools returns.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MAX_CUSTOMER_MESSAGE = 1000  # characters in one customer message
MAX_TURNS_SENT = 40  # chat turns the site may send in one request
MAX_TURN_CHARS = 2000  # characters in one earlier turn: customer messages are capped at 1000, replies at 1500
MAX_REPLY_CHARS = 1500  # characters in one agent reply; replies are meant to be two to four sentences
MAX_REPLY_PRODUCTS = 4  # products one reply may show as cards


class StockLevel(BaseModel):
    size: str
    quantity: int


class Product(BaseModel):
    product_id: str
    name: str
    garment_type: str
    category: str
    description: str
    colors: list[str]
    search_tags: list[str]
    image_file_path: str
    image_url: str
    price: float
    inventory: list[StockLevel]
    total_stock: int


class UserOut(BaseModel):
    """Everything the site or the shop agent may know about a user: no password, no hash."""

    id: int
    first_name: str
    last_name: str
    email: str


class ProductCard(BaseModel):
    """A product card for the website (under a chat reply, or on the results page), built from the
    database rather than written by the model."""

    product_id: str
    name: str
    category: str
    price: float
    image_url: str
    short_description: str  # the description cut to about 100 characters
    sizes_in_stock: list[str]


class PageResults(BaseModel):
    """A catalogue search for the website's results page: every product that matches all the search
    words and filters. Comes with a chat reply when the agent searched, or from GET /api/search."""

    title: str  # what was searched for, e.g. "Hoodies" or '"bulldog" · size M'
    query: str
    category: str | None
    max_price: float | None
    size: str | None  # the shop's size label, e.g. "M"
    total_matches: int
    note: str | None  # e.g. why nothing matched
    products: list[ProductCard]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_TURN_CHARS)


class PageContext(BaseModel):
    """The page the customer is looking at when they send a message."""

    path: str = Field(default="/", max_length=500)  # e.g. "/products/boola-boola-t-shirt" or "/search?q=bulldog"
    product_id: str | None = Field(default=None, max_length=200)  # set on a product page


class ChatRequest(BaseModel):
    """A new customer message, with the page they're on. history (earlier turns, oldest first) is used for
    guests only; a logged-in customer's history comes from the database instead."""

    message: str = Field(min_length=1, max_length=8000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_TURNS_SENT)
    page: PageContext | None = None


class AgentReply(BaseModel):
    """The shop agent's answer to one customer message."""

    message: str = Field(max_length=MAX_REPLY_CHARS, description="Your reply to the customer, in plain text.")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_REPLY_PRODUCTS,
        description=(
            "The product_id of each product your message recommends or describes, at most 4, in the order "
            "you mention them. Only use ids a tool returned in this conversation; the site shows them as cards."
        ),
    )


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard]  # cards under the reply: the products it names (at most 4)
    page_results: PageResults | None = None  # the agent's latest search this turn, for the results page
    saved: bool = False  # True when the exchange was saved to the logged-in customer's history
    cached: bool = False  # True when a recent answer to the same opening question was reused (reply_cache.py)


class SavedMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard]  # rebuilt from the saved product ids, so prices and stock are current
    created_at: str  # UTC, as SQLite stores it


class ChatHistory(BaseModel):
    saved: bool  # False for guests: nothing is stored and messages is empty
    messages: list[SavedMessage]  # oldest first


# ---------- Tool results: what the shop agent's lookups in tools.py return ----------

LOW_STOCK = 5  # a size with 1 to 5 units left is "low stock", matching the website's "Only N left"
StockStatus = Literal["in stock", "low stock", "sold out"]


class SizeStock(BaseModel):
    """One size of one product: the exact number on hand and what that means for a customer."""

    size: str
    quantity: int
    status: StockStatus


class ProductMatch(BaseModel):
    """A search result: enough to recommend a product, with its id for any follow-up lookup."""

    product_id: str
    name: str
    category: str
    price: float
    colors_on_product: list[str]  # every color in the design, print included; one colorway per product
    sizes_in_stock: list[str]
    description: str


class ProductSearchResult(BaseModel):
    total_matches: int
    products: list[ProductMatch]  # the first 8 matches
    note: str | None = None  # set when nothing matched every search word, or nothing matched at all


class ProductDetails(BaseModel):
    """Everything about one product: description, price, colors and the stock of every size."""

    product_id: str
    name: str
    category: str
    garment_type: str
    description: str
    price: float
    colors_on_product: list[str]
    stock: list[SizeStock]  # XS to XXL, in size order
    total_stock: int
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]


class SimilarInStock(BaseModel):
    """Another product with the size the customer asked for in stock, offered when that size is sold out."""

    product_id: str
    name: str
    category: str
    price: float
    quantity: int  # units in stock in the size the customer asked about
    status: StockStatus
    similar_because: Literal["same design and category", "same design", "same category"]


class SizeStockCheck(BaseModel):
    """The stock of one size of one product, as the customer asked about it."""

    product_id: str
    name: str
    price: float
    size_asked: str  # the size as the customer said it, for example "large"
    size: str | None  # the shop's size label (XS to XXL), or None if the shop doesn't make that size
    quantity: int  # units in stock in that size; 0 when sold out or not offered
    status: Literal["in stock", "low stock", "sold out", "size not offered"]
    other_sizes_in_stock: list[SizeStock]  # alternatives to offer, with their quantities
    # Set when the size is sold out (or this product doesn't come in it): up to 3 similar products that
    # have that size in stock, most similar first. Empty when the size is in stock.
    similar_in_stock: list[SimilarInStock] = Field(default_factory=list)


class ProductCandidate(BaseModel):
    product_id: str
    name: str
    price: float


class ProductLookupProblem(BaseModel):
    """Returned instead of a product when a name matches several products, or none."""

    problem: str
    candidates: list[ProductCandidate]


class CategorySummary(BaseModel):
    name: str
    styles: int
    price_from: float
    price_to: float


class CatalogueOverview(BaseModel):
    total_styles: int
    sizes_offered: list[str]
    categories: list[CategorySummary]
