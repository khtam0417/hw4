# Campus Customs — Homework 4

A storefront for Campus Customs (Yale Bulldog Blue) with a chat assistant:

- **Frontend:** a React + TypeScript site built with Vite, in `frontend/`.
- **Backend:** a FastAPI app in `backend/` that reads the shop's SQLite database.
- **Shop agent:** a PydanticAI agent powered by Claude through the Claude Agent SDK. It looks up products, prices and exact stock, shows search results on the page, and remembers logged-in customers.

Everything the agent does is recorded in `output/audit_trail.json`, and `output/harness.md` explains how it all works.

```
hw4/
├── AI_prompts.md            prompts used to build the project, one section per problem
├── README.md                this file
├── requirements.txt         Python packages for the backend
├── .env.example             settings template (copy to .env)
├── frontend/                Vite + React + TypeScript site (package.json, src/)
├── backend/
│   ├── main.py              FastAPI app: uvicorn main:app --reload --port 8000
│   ├── agent.py             the PydanticAI shop agent and its Claude connection
│   ├── models.py            request, response and tool result shapes
│   ├── tools.py             the agent's read-only lookup tools
│   ├── prompts/prompt.md    the agent's system prompt
│   ├── auth.py, db.py, history.py, reply_cache.py, audit.py, limits.py   supporting modules
│   └── check_*.py           test scripts (see "Check that it works")
└── output/
    ├── harness.md           how the backend and agent work: models, tools, safety rules, limits, setup
    ├── usability.md         the Problem 9 improvements
    ├── design.md            the Problem 10 design
    ├── app_check.html       screenshot report (Problem 11); open it directly in a browser
    ├── app_check_images/    the screenshots it shows
    └── audit_trail.json     append-only log of agent runs (Problem 12)
```

The data pack (`data/campus_customs.db` and the product photos in `data/products/`) is not in this repository; step 2 below puts it in place.

## What you need

- **Python** 3.11 or newer (tested with 3.12).
- **Node.js** 20.19 or newer, or 22.12 or newer, with npm.
- **The data pack** from the course (`data.zip`).
- **A Claude login:** either a Claude subscription (Pro, Max, Team or Enterprise) or an Anthropic API key. The agent uses Claude Opus 5.5 (`claude-opus-5-5`).

## 1. Install dependencies

From the repository folder (`hw4`):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm --prefix frontend install
```

On Windows, use `.venv\Scripts\pip` instead of `.venv/bin/pip`. The Python packages are FastAPI, Uvicorn, python-dotenv, PydanticAI and the Claude Agent SDK. The SDK includes its own copy of Claude Code, so no separate Claude install is needed.

## 2. Place the data pack

Unzip the data pack into the repository folder, so these paths exist:

```
hw4/data/campus_customs.db
hw4/data/products/<product photos>.jpg
```

The backend reads the catalogue and stock from the database and serves the photos from `data/products/`. `data/` is listed in `.gitignore`, so it is never committed. The backend only adds rows to the `users` and `chat_messages` tables; the catalogue and inventory are never changed.

## 3. Configure your own Claude authentication

Copy the settings template:

```bash
cp .env.example .env
```

Then edit `.env`:

- **`SESSION_SECRET`:** any long random string. It signs login cookies. Create one with:

  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

- **A Claude credential:** set one of the following.
  - **Claude subscription:** set `CLAUDE_CODE_OAUTH_TOKEN`. To create the token, run:

    ```bash
    .venv/lib/python3.12/site-packages/claude_agent_sdk/_bundled/claude setup-token
    ```

    Use `python3.11` in the path for Python 3.11, or plain `claude setup-token` if Claude Code is installed. Sign in in the browser it opens, then paste the printed token into `.env`.
  - **Anthropic API key:** uncomment `ANTHROPIC_API_KEY` and paste a key from https://console.anthropic.com. Calls are billed to that API account. The key is used only when no `CLAUDE_CODE_OAUTH_TOKEN` is set. This option hasn't been tested with a live key; the subscription token is the tested setup. A wrong key doesn't fail quickly: Claude Code keeps retrying, so chat answers end with "Sorry, that took too long".

The backend reads these only from `.env`. It ignores any Claude login or API key already in your shell, so the agent always uses the account you chose. Never commit `.env`; it is git-ignored.

## 4. Run the backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

You can also activate the environment with `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows) and run `uvicorn main:app --reload --port 8000` from `backend/`. The API is then at http://localhost:8000, and its docs are at http://localhost:8000/docs.

## 5. Run the frontend

In a second terminal, from the repository folder:

```bash
npm --prefix frontend run dev
```

Open **http://localhost:5174**. Vite forwards `/api` and `/media` to the backend on port 8000.

**If a port is busy:**
- **Backend:** run it with, for example, `--port 8001`, then start the frontend with `BACKEND_PORT=8001 npm --prefix frontend run dev`.
- **Frontend:** use `npm --prefix frontend run dev -- --port 5175`.

Try the chat button in the corner: ask "What hoodies do you have?", or log in with the assignment's test account (`test@campuscustoms.yale.edu`, password `password`).

## 6. Check that it works (optional)

Run these from the repository folder while the backend is running. Add `BACKEND_PORT=8001` in front if it isn't on port 8000.

```bash
.venv/bin/python backend/check_tools.py      # the lookup tools against the database (no backend needed)
.venv/bin/python backend/check_auth.py       # accounts and logins; also creates the test account the next checks use
.venv/bin/python backend/check_memory.py     # saved conversations and page context
.venv/bin/python backend/check_usability.py  # the Problem 9 backend improvements
.venv/bin/python backend/check_safety.py     # safety rules and limits
.venv/bin/python backend/check_audit.py      # the audit trail
```

Before you run them, note:
- **Claude usage:** the checks after `check_auth.py` make real Claude calls (a few dozen in all) and take a minute or two each.
- **Order:** run `check_auth.py` before `check_memory.py`, `check_usability.py`, `check_safety.py` and `check_audit.py`.
- **Chat limit:** `check_audit.py` ends by hitting the chat's limit of 20 messages a minute on purpose, so wait a minute after it before chatting.
- **Test account:** the test account the scripts create (`bulldog.tester@example.com`) exists only in your local database.

## Outputs

- **`output/app_check.html`:** double-click to open in a browser. Its screenshots are in `output/app_check_images/` and display without the app running.
- **`output/harness.md`:** the full technical description: models and their fields, tools, safety rules (prompt instructions versus code checks), limits, the Claude and login setup, and how to run everything.
- **`output/audit_trail.json`:** grows by one entry for every chat message. It is append-only and holds no message text or customer details.
