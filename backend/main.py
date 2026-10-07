"""Campus Customs backend (Homework 4).

Run from the backend folder:
    uvicorn main:app --reload --port 8000

Routes:
- GET  /api/products               every catalogue item, with its sizes and stock
- GET  /api/products/{product_id}  one catalogue item, with its sizes and stock
- GET  /media/products/<file>      product photos from data/products/
- /api/auth/...                    create an account, log in, log out (auth.py)
- POST /api/chat                   the shop agent's reply to a chat message (agent.py); saved for
                                   logged-in customers (history.py), and reused for a guest who opens
                                   with a question answered recently on the same page (reply_cache.py).
                                   Every message it accepts is recorded in output/audit_trail.json
                                   (audit.py), and each client may send CHAT_MESSAGES_PER_MINUTE.
- GET  /api/chat/history           the logged-in customer's saved conversation
- GET  /api/search                 a catalogue search for the website's results page (tools.page_results)

Products are read through a read-only connection, so the catalogue and inventory never change; the
only writes are new accounts and saved chat messages, through a connection limited to the users and
chat_messages tables (db.py). A product's image_url is "/media/" + its image_file_path from the database.
"""

from __future__ import annotations

from contextlib import closing

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles

import audit
import reply_cache
from agent import HISTORY_TURNS, AssistantUnavailable, run_chat
from auth import current_user, remove_own_password
from auth import router as auth_router
from db import DATA_DIR, MEDIA_URL, load_products, read_only
from history import load_history, recent_turns, save_exchange
from limits import SlidingWindow
from models import MAX_CUSTOMER_MESSAGE, ChatHistory, ChatRequest, ChatResponse, PageResults, Product
from tools import MAX_TOOL_TEXT, page_results, page_view

CHAT_MESSAGES_PER_MINUTE = 20  # per client address; a person typing sends far fewer
_chat_messages = SlidingWindow(CHAT_MESSAGES_PER_MINUTE, 60)

app = FastAPI(title="Campus Customs API")
app.mount(f"{MEDIA_URL}/products", StaticFiles(directory=DATA_DIR / "products"), name="product-images")
app.include_router(auth_router)


@app.get("/")
def index() -> dict[str, str]:
    return {"service": "Campus Customs API", "products": "/api/products", "auth": "/api/auth/me",
            "chat": "/api/chat", "search": "/api/search", "docs": "/docs"}


@app.get("/api/products")
def list_products() -> list[Product]:
    with closing(read_only()) as con:
        return load_products(con)


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> Product:
    with closing(read_only()) as con:
        products = load_products(con, product_id)
    if not products:
        raise HTTPException(status_code=404, detail=f"No product with id '{product_id}'")
    return products[0]


@app.get("/api/search")
def search(
    q: str = Query("", max_length=MAX_TOOL_TEXT),
    category: str | None = Query(None, max_length=40),
    max_price: float | None = Query(None, gt=0, le=1000),
    size: str | None = Query(None, max_length=20),
) -> PageResults:
    """The same search the shop agent runs, so a results page opened from a link or reloaded shows the same products."""
    return page_results(q, category, max_price, size)


@app.get("/api/chat/history")
def chat_history(request: Request) -> ChatHistory:
    """The logged-in customer's saved conversation, oldest first. Guests get an empty, unsaved history."""
    user = current_user(request)
    if user is None:
        return ChatHistory(saved=False, messages=[])
    return ChatHistory(saved=True, messages=load_history(user.id))


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    """The shop agent's reply to a new message. Who the customer is comes only from their session cookie:
    a logged-in customer's earlier turns are read from, and the new exchange saved to, their own history.
    A guest's earlier turns come from the chat panel and nothing is saved."""
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail={"message": "Please type a message.", "fields": {}})
    if len(message) > MAX_CUSTOMER_MESSAGE:
        detail = f"Please keep messages under {MAX_CUSTOMER_MESSAGE:,} characters."
        raise HTTPException(status_code=400, detail={"message": detail, "fields": {}})
    user = current_user(request)
    run = audit.RunRecord(customer="logged-in customer" if user else "guest", page=audit.page_label(body.page))
    run.message_chars = len(message)
    if not _chat_messages.hit(request.client.host if request.client else "unknown"):
        run.stop("rate limited", f"more than {CHAT_MESSAGES_PER_MINUTE} chat messages a minute from one address", source="none")
        audit.record(run)
        detail = "You're sending messages very quickly. Please wait a minute and try again."
        raise HTTPException(status_code=429, detail={"message": detail, "fields": {}})
    if user:
        message = remove_own_password(user.id, message)
    history = recent_turns(user.id, HISTORY_TURNS) if user else body.history
    run.history_turns = min(len(history), HISTORY_TURNS)
    page = page_view(body.page)
    # A guest's opening question can reuse a recent answer to the same question on the same page (reply_cache.py).
    cache_key = reply_cache.key_for(message, page) if user is None and not history else None
    if cache_key and (hit := reply_cache.get(cache_key)):
        answer, age = hit
        run.cached(answer, age)
        audit.record(run)
        return answer
    try:
        reply = await run_chat(message, history, customer=user, page=page, record=run)
    except AssistantUnavailable as error:
        audit.record(run)  # run_chat noted why it stopped
        raise HTTPException(status_code=503, detail={"message": str(error), "fields": {}}) from None
    if cache_key:
        reply_cache.put(cache_key, reply)
    if user:
        save_exchange(user.id, message, reply)
        reply.saved = True
    run.replied(reply)
    audit.record(run)
    return reply
