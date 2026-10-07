# Usability improvements (Problem 9)

Earlier problems built the Products page (search, category chips, sort), product pages with stock for every size, accounts, the shop agent and its lookup tools, chat searches that update the page, and saved conversations for logged-in customers. This problem adds four things the site didn't do yet: two in the frontend, one in the agent and one in the backend.

| # | Improvement | Type | What it adds |
| --- | --- | --- | --- |
| 1 | Shop by size | Frontend | An "In stock in size" filter on the Products page; cards and product pages show stock in that size |
| 2 | Suggested questions in the chat | Frontend | One-click questions that fit the page, and an "Ask about this item" button on product pages |
| 3 | In-stock alternatives when a size is sold out | Agent | `check_size_stock` also returns similar products that have that size, and the agent offers them |
| 4 | Instant answers to repeated questions | Backend | A guest's opening question that was answered recently is answered again from a cache, without calling Claude |

## 1. Shop by size (frontend)

**What it adds**

- A row of size buttons on the Products page: Any, XS, S, M, L, XL, XXL. Each button shows how many styles have that size in stock for the current search and category, for example "M 80".
- Picking a size shows only styles in stock in that size and works together with the search, category and sort. The result line says "Showing 21 of 102 products in stock in size M".
- With a size picked, each card shows the stock in that size ("Size M: 12 in stock", or "Size M: Only 5 left" in red) instead of "4 of 6 sizes in stock".
- The size stays in the address (`/products?size=M`), so refresh, the back button and shared links keep it. Cards carry it to the product page, which shows "Your size, M: 12 in stock" under the price and marks the M box "Your size". Its "More Hoodies in size M" section shows only items in that size. "Back to all products" and the breadcrumbs keep the size.

**Why it helps:** 145 of the 612 product sizes are sold out, so a shopper browsing by style often opens a product only to find their size gone. Now they see only what they can buy in their size, so it takes fewer clicks and they hit fewer dead ends. For the business, shoppers who can see their size in stock are more likely to buy.

**Code:**
- `frontend/src/pages/ProductsPage.tsx`: the filter row.
- `frontend/src/catalogue.ts`: `filterProducts` and `countInStockBySize`.
- `frontend/src/format.ts`: `quantityIn` and `toSize`.
- `frontend/src/components/ProductCard.tsx`: the size stock line on cards.
- `frontend/src/pages/ProductPage.tsx`: the size highlight and links.
- Styles in `frontend/src/index.css`.

**Tested in the running app:**
- **Button counts match the database:** XS 75, S 78, M 80, L 78, XL 77, XXL 79.
- **Hoodies in M:** shows 21 of 102 products, the same count as a direct SQL query. Each card's M stock matches the database, for example Basic Hoodie Big Yale "Only 5 left" and Volleyball Left Chest Hoodie "Only 2 left".
- **Product page:** opening the Yale Dad Hoodie from that list showed "Your size, M: 12 in stock" with M marked. "More Hoodies in size M" listed only hoodies with M in stock, and the back link and breadcrumbs pointed to `/products?size=M`.
- **Phone width (375 px):** the size row wraps onto two lines, the page doesn't scroll sideways, and the card labels fit.

## 2. Suggested questions in the chat (frontend)

**What it adds**

- Above the message box, the chat panel shows two or three questions the shopper can send with one click. They change with the page:
  - **Home, Products and other pages:** "What hoodies do you have?", "Gift ideas under $50" and "What's in stock in size XL?".
  - **Product page:** "What sizes are left in this one?", "What colors does this come in?" and "Show me similar items". With a size picked on the Products page, the first one becomes "Do you have this in size M?".
  - **Chat search results page:** "Which of these come in size M?" and "Which of these are under $50?". Each is left out if the search is already narrowed that way.
- The suggestions hide while the shopper types or waits for a reply, and after they ask something on that page. They come back on the next page, so after a chat search the results page offers follow-ups for narrowing it down.
- Product pages have an "Ask about this item" button that opens the chat with the cursor in the message box and that product's questions ready.

**Why it helps:** shoppers who open the chat often don't know what it can do or how to phrase a question. The suggestions show what it's good at (stock by size, colors, budgets, browsing), take one tap on a phone, and the product-page questions use "this", which the agent already ties to the product on screen. The button makes the assistant visible right where shoppers decide. For the business, more shoppers get answers instead of leaving. The suggested questions are worded the same every time, so they also get the most out of improvement 4.

**Code:**
- `frontend/src/chat.ts`: `suggestedQuestions()`, plus `openChat()` and `onOpenChat()` for the button.
- `frontend/src/components/ChatPanel.tsx`: shows the suggestions; clicking one sends it like a typed message.
- `frontend/src/pages/ProductPage.tsx`: the button.
- Styles in `frontend/src/index.css`.

**Tested in the running app:**
- **"What hoodies do you have?"** on the home page: the agent searched and the page switched to the 27 hoodies (7.3 s). The suggestions then changed to the results-page ones. "Which of these come in size M?" narrowed the page to "Hoodies · size M", with 21 products, the same number as the size filter.
- **"Ask about this item"** on the Yale Dad Hoodie (opened with `?size=M`): the button opened the chat with the cursor in the message box, offering "Do you have this in size M?", "What colors does this come in?" and "Show me similar items".
  - "What colors does this come in?" got the right answer: one colorway (navy with a white graphic), $68.00, with XS and S down to 5 each. This matches the database.
- **Logged in as the Problem 4 test account:** the suggestions appeared under the saved conversation. "What sizes are left in this one?" on the Davenport College Crewneck was answered correctly: XS 20, M 5, L 12, XL 20 and XXL 8, with S sold out. The exchange was saved and was still there after a refresh.
- **Phone width:** the three suggestions fit above the message box.

## 3. In-stock alternatives when a size is sold out (agent)

**What it adds**

- When the size a customer asks about is sold out, `check_size_stock` returns a new field, `similar_in_stock`. It holds up to three other products that have that size in stock, each with its exact quantity and status in that size, its price, and `similar_because`.
- The most similar come first:
  - the same design in the same category (a shared design word in the name, such as "Dad", "Pierson", "Baseball" or "Champion");
  - then the same design in another style;
  - then the same category.
  - Ties go to more shared name words ("College Crewneck"), then the closest price, then the most stock.
- Generic words like "Yale", "College", "Left Chest" and garment names don't count as design words. Nothing is suggested when the size is in stock, or for a size the shop doesn't make.
- The prompt (`backend/prompts/prompt.md`) tells the agent to offer one or two of them with price and exact stock in that size, and to show them as product cards. If there are none, it says so and offers to search.

**Why it helps:** with 145 sold-out sizes, "Sorry, that's sold out" used to be a dead end, unless the customer wanted a different size of the same item. Now a customer who needs a medium hears about the same design in another style, or a similar item, that is actually in their size. They find something, and the shop keeps the sale. The suggestions come from the database, so the existing check that prices and stock come from a fresh lookup still applies.

**Code:**
- `backend/tools.py`: `_similar_in_stock()`, `GENERIC_NAME_WORDS` and `check_size_stock`.
- `backend/models.py`: `SimilarInStock` and `SizeStockCheck.similar_in_stock`.
- `backend/prompts/prompt.md`: the "Answering with what you find" section.

**Tested:**
- **`backend/check_usability.py`, run against every sold-out size:**
  - For all 145, every suggestion has that size in stock with its exact quantity from the database, is a different product, and is similar in the way its label says.
  - 142 of the 145 get at least one suggestion. The other 3 are long-sleeve tees (Dry Zone XS and L, UA Tech L): the shop has only two long sleeves, both out of those sizes, and nothing shares their designs.
  - The Yale Dad Crewneck in M suggests the Yale Dad Hoodie and Yale Dad T Shirt first.
  - No suggestions for the 467 in-stock sizes, or for XXXL.
- **In the browser (as a guest on the Yale Dad Crewneck page):** I asked "Do you have this in a medium?". The agent called `check_size_stock("yale-dad-crewneck", "M")` and replied in 5.7 s.
  - It said medium is sold out, but XS (15), S (8) and XXL (15) are in stock.
  - It offered the same Yale Dad design in M: the Yale Dad Hoodie ($68.00, 12 left) and the Yale Dad T Shirt ($32.00, 20 left), with both product cards. Every number matches the database.

## 4. Instant answers to repeated questions (backend)

**What it adds**

- `backend/reply_cache.py` remembers answers to guests' opening questions for an hour, at most 200 of them. When a guest's first message is the same question asked recently on the same page, the backend sends that answer again (`cached: true` in the response) instead of calling Claude.
- Capitals, extra spaces and end punctuation don't matter, so "What hoodies do you have?" and "what hoodies do you have" match.
- The answer comes with the same text, product cards and results page, so a cached search still opens the results page.

**Why reusing an answer is safe:**
- **The key covers everything the answer depended on:** the question, the page as the agent was told it, a hash of every catalogue row and stock level, the prompt file, and the model. If a price, a stock level or the prompt changes, the key changes, so an answer is never reused with old numbers.
- **Only guests' opening questions qualify:**
  - Logged-in customers always get a fresh answer, because it can use their name and saved history, and it is saved to their account.
  - Follow-up questions also get a fresh answer, because they depend on the conversation before them.
- **Only finished answers are stored.** Nothing about the customer is kept, and an answer only goes to someone who asks the same question.

**Why it helps:** a Claude answer takes about 6–9 seconds (two Claude calls). A cached one arrives in about 10 ms, so the many shoppers who open with the same question get an instant reply. For the business, every cache hit uses none of the Claude plan, so it saves cost and leaves more headroom before usage limits. Suggested questions (improvement 2) are worded the same every time, so they are the most likely to be answered from the cache.

**Code:**
- `backend/reply_cache.py`.
- The chat route in `backend/main.py`.
- `ChatResponse.cached` in `backend/models.py`.

**Tested:**
- **In the browser:**
  - A guest's "What colors does this come in?" on the Yale Dad Hoodie took 7.2 s. After a reload (a new guest), the same suggestion got the identical answer and product card, with the request taking 0.01 s. The backend log shows "Chat answered from the reply cache (answer stored 11s ago)" and no Claude calls.
  - A new guest's "What hoodies do you have?" on the home page was answered from the cache and still opened the 27-hoodie results page, 0.09 s after the click.
- **`backend/check_usability.py` against the running backend:**
  - A random product's price question took 7.0 s the first time. A second guest asking it in lower case without the "?" got the same answer, cards and results in 0.00 s.
  - The same question on a different page, as a follow-up, or from a logged-in customer was answered fresh. The logged-in exchange was saved.
  - A changed catalogue or stock fingerprint gives a new key.

**Limits:** answers are kept in memory, so restarting the backend clears them. Only the same wording counts as the same question.

## Checks that the existing shop still works

- **Automated checks (`.venv/bin/python backend/<script>`, with `BACKEND_PORT=8001` for the preview):**
  - `check_auth.py`: 21 of 21 (sign-up, login, wrong passwords, logout, no hashes in responses).
  - `check_tools.py`: 30 of 30 (every product and size against SQL, name and size matching, read-only tools).
  - `check_memory.py`: 15 of 15 (guest chat unsaved, history after refresh and re-login, separate accounts, page context, password removal).
  - `check_usability.py`: 10 of 10.
  - Each one confirms the catalogue and inventory are unchanged.
- **In the browser:**
  - Logging in through the form loaded the saved conversation with "Welcome back, Bulldog!" and "saved to your account".
  - A new question was saved and came back after a refresh.
  - Logging out cleared the panel to the guest greeting ("guest chat, not saved").
  - Chat searches still open the results page, and product cards still open product pages.
- **Frontend:** `npm run lint` (oxlint) and `npm run build` (TypeScript and Vite) finish with no errors.
