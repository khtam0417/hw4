"""The Campus Customs shop agent: creating it and running it for one chat message.

PydanticAI is the agent framework: it holds the system prompt (prompts/prompt.md), the tools
(tools.py), the structured reply (models.AgentReply) and the agent loop. PydanticAI has no built-in
model for Claude through a Claude Code subscription login, so claude_turn() fills that gap with
PydanticAI's FunctionModel, as in Homework 3: each agent turn becomes one Claude call through the
Claude Agent SDK, which runs Claude Code on the login in .env (CLAUDE_CODE_OAUTH_TOKEN, or ANTHROPIC_API_KEY).
Claude answers every turn by choosing one tool, or the reply_to_customer tool to finish.
"""

from __future__ import annotations

import asyncio
import collections
import contextlib
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultError, ResultMessage, query
from dotenv import dotenv_values
from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput, UsageLimits, capture_run_messages
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from audit import CURRENT_RUN, RunRecord
from db import PROJECT_ROOT
from models import AgentReply, ChatResponse, ChatTurn, UserOut
from tools import (
    PageView,
    ShopDeps,
    check_size_stock,
    get_product_details,
    list_categories,
    product_cards,
    resolve_product_id,
    search_products,
    unknown_product_ids,
)

MODEL = "claude-opus-5-5"
EFFORT = "low"  # chat replies are short; low effort keeps them quick
AGENT_MODEL_NAME = f"claude-code:{MODEL}"
PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "prompt.md"
MAX_MODEL_TURNS = 6  # Claude calls allowed for one customer message
CALL_TIMEOUT_SECONDS = 90  # one Claude call
CHAT_TIMEOUT_SECONDS = 180  # everything for one customer message
HISTORY_TURNS = 12  # earlier chat turns the agent sees

log = logging.getLogger("uvicorn.error")

LOOKUP_TOOLS = {"search_products", "get_product_details", "check_size_stock", "list_categories"}
PRODUCT_TOOLS = {"get_product_details", "check_size_stock"}
# Words that point at the item on the customer's screen ("Do you have this in pink?").
REFERS_TO_PAGE_ITEM = re.compile(r"\b(this|these|it|its|it's|this one|that one)\b", re.IGNORECASE)
# A price ("$68") or a stock claim ("5 left", "sold out") in a reply must come from a lookup made this turn.
PRICE_OR_STOCK = re.compile(r"\$\s?\d|\b\d+\s+(?:left|in stock|available|remaining)\b|\bsold out\b|\bout of stock\b", re.IGNORECASE)
# Each amount of money in a reply ("$68", "$68.00") must be a price from this turn's lookups (or a number the
# customer gave, such as a budget).
MONEY = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?")
PRICE_FIELDS = {"price", "price_from", "price_to", "max_price"}
# Email addresses a reply may contain: the shop's, and the logged-in customer's own.
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
SHOP_EMAIL = "orderdept@campuscustoms.com"
# Things the tools can't do, claimed as done: placing or holding orders, discounts, price changes, refunds.
CLAIMED_ACTION = re.compile(
    r"\b(?:i|we)(?:'ve| have)? (?:placed|submitted|processed|confirmed) (?:an?|your|the) order"
    r"|\byour order (?:is|has been) (?:placed|confirmed|reserved|on its way)"
    r"|\b(?:i|we)(?:'ve| have)? (?:reserved|held|set aside|put aside|put on hold) (?:it|them|one|an?|the|your|this)\b"
    r"|\b(?:i|we)(?:'ve| have)? (?:applied|added) (?:an?|the|your) (?:discount|coupon|promo)"
    r"|\b(?:i|we)(?:'ve| have)? (?:changed|lowered|reduced|updated) the price"
    r"|\b(?:i|we)(?:'ve| have)? (?:refunded|issued (?:a|your) refund|cancell?ed your order)",
    re.IGNORECASE,
)

REPLY_FORMAT = """

## How to respond
You are the model inside a PydanticAI agent. Respond only through the structured output by choosing \
the next step: call exactly one of these tools with arguments that match its schema. Look things up \
first, then call reply_to_customer to answer.
{tool_list}
"""

# Error text from Claude Code that means the login or the plan is the problem, not this one message.
LOGIN_PROBLEMS = ("not logged in", "failed to authenticate", "invalid api key", "authentication", "oauth token", "unauthorized")
USAGE_PROBLEMS = ("usage limit", "rate limit")


class AssistantUnavailable(RuntimeError):
    """The chat can't answer right now. The message is safe to show to the customer."""


class ClaudeCallError(RuntimeError):
    """One Claude call finished without a usable answer."""


def use_subscription_login() -> bool:
    """Prepare this process so Claude Code signs in with the credentials in .env: CLAUDE_CODE_OAUTH_TOKEN
    (a Claude subscription token from `claude setup-token`) or, if that isn't set, ANTHROPIC_API_KEY.

    When the backend is started from inside Claude Code (for example the desktop app), it inherits
    variables that tie it to that parent session and its login, and Claude Code would inherit them
    too. Drop those and any inherited API-key credentials, then use the ones from .env (an OAuth token
    already in the environment also counts). Returns whether a credential is available. Their values
    are never printed.
    """
    env_file = dotenv_values(PROJECT_ROOT / ".env")
    token = env_file.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    api_key = env_file.get("ANTHROPIC_API_KEY")  # only from .env, never inherited from a parent session
    for name in list(os.environ):
        parent_session_var = name.startswith("CLAUDE") and name != "CLAUDE_CODE_OAUTH_TOKEN"
        other_credential = name in {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "USE_LOCAL_OAUTH", "USE_STAGING_OAUTH"}
        if parent_session_var or other_credential:
            del os.environ[name]
    if token:
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = token
    elif api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
    return bool(token or api_key)


HAS_CLAUDE_LOGIN = use_subscription_login()


def _failure(status: int | None, detail: str) -> Exception:
    log.warning("Claude call failed: %s", detail[:500])
    lowered = detail.lower()
    if status in (401, 403) or any(marker in lowered for marker in LOGIN_PROBLEMS):
        return AssistantUnavailable("The shop assistant can't sign in to Claude right now. Please try again later.")
    if any(marker in lowered for marker in USAGE_PROBLEMS):
        return AssistantUnavailable("The shop assistant is very busy right now. Please try again in a little while.")
    return ClaudeCallError(detail)


async def ask_claude(transcript: str, system_prompt: str, schema: dict) -> dict:
    """One Claude call through Claude Code: a transcript in, JSON matching `schema` out.

    Claude Code runs with all of its own tools switched off and without user or project settings,
    so the model only sees the prompt and transcript it is given.
    """
    stderr_tail: collections.deque[str] = collections.deque(maxlen=15)
    options = ClaudeAgentOptions(
        model=MODEL,
        effort=EFFORT,
        system_prompt=system_prompt,
        output_format={"type": "json_schema", "schema": schema},
        tools=[],  # no file, shell or web tools
        setting_sources=[],  # ignore user and project Claude Code settings and instruction files
        max_turns=4,
        cwd=tempfile.gettempdir(),
        extra_args={"no-session-persistence": None},  # don't save these one-off sessions to disk
        stderr=stderr_tail.append,
    )
    result: ResultMessage | None = None
    try:
        async with contextlib.aclosing(query(prompt=transcript, options=options)) as messages:
            async for message in messages:
                if isinstance(message, ResultMessage):
                    result = message
    except ResultError as exc:  # Claude Code exited after reporting an error result
        raise _failure(exc.api_error_status, "; ".join(exc.errors) or exc.result or str(exc)) from None
    if result is None:
        raise _failure(None, "Claude Code exited without a result: " + " | ".join(stderr_tail))
    if result.is_error or result.structured_output is None:
        detail = "; ".join(result.errors or []) or result.result or ""
        raise _failure(result.api_error_status, f"{result.subtype}: {detail}")
    return result.structured_output


def render_messages(messages: list[ModelMessage]) -> tuple[str, str]:
    """PydanticAI's message history as a system prompt plus a plain-text transcript for Claude."""
    system, lines = [], []
    for message in messages:
        for part in message.parts:
            if isinstance(part, SystemPromptPart):
                system.append(part.content)
            elif isinstance(part, UserPromptPart):
                lines.append(f"Customer: {part.content}")
            elif isinstance(part, TextPart):
                lines.append(f"You replied: {part.content}")
            elif isinstance(part, ToolCallPart):
                lines.append(f"You called {part.tool_name} with {part.args_as_json_str()}")
            elif isinstance(part, ToolReturnPart):
                lines.append(f"{part.tool_name} returned: {part.model_response_str()}")
            elif isinstance(part, RetryPromptPart):
                lines.append(f"That did not work; please correct it: {part.model_response()}")
    return "\n\n".join(system), "\n\n".join(lines)


async def claude_turn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """One PydanticAI model turn, answered by Claude through Claude Code: call one tool or reply."""
    tools = [*info.function_tools, *info.output_tools]
    choices = [
        {
            "type": "object",
            "properties": {"tool_name": {"enum": [tool.name]}, "arguments": tool.parameters_json_schema},
            "required": ["tool_name", "arguments"],
            "additionalProperties": False,
        }
        for tool in tools
    ]
    schema = {
        "type": "object",
        "properties": {"next_step": {"anyOf": choices}},
        "required": ["next_step"],
        "additionalProperties": False,
    }
    system, transcript = render_messages(messages)
    if (run := CURRENT_RUN.get()) is not None:
        run.claude_calls += 1
    system = "\n\n".join(filter(None, [system, info.instructions])) + REPLY_FORMAT.format(
        tool_list="\n".join(f"- {tool.name}: {tool.description or ''}" for tool in tools)
    )
    started = time.perf_counter()
    answer = await asyncio.wait_for(ask_claude(transcript, system, schema), CALL_TIMEOUT_SECONDS)
    step = answer["next_step"]
    arguments = json.dumps(step["arguments"])
    log.info("Shop agent turn: %s %s (%.1fs)", step["tool_name"], arguments[:160], time.perf_counter() - started)
    return ModelResponse(parts=[ToolCallPart(step["tool_name"], step["arguments"])], model_name=AGENT_MODEL_NAME)


agent = Agent(
    FunctionModel(claude_turn, model_name=AGENT_MODEL_NAME),
    deps_type=ShopDeps,
    output_type=ToolOutput(
        AgentReply, name="reply_to_customer", description="Send your reply to the customer. This ends your turn."
    ),
    tools=[search_products, get_product_details, check_size_stock, list_categories],
    name="campus_customs_shop_agent",
    retries=2,
)


@agent.instructions
def shop_prompt() -> str:
    """The system prompt, read from prompts/prompt.md on every run so edits apply without a restart."""
    return PROMPT_FILE.read_text(encoding="utf-8")


@agent.instructions
def customer_context(ctx: RunContext[ShopDeps]) -> str:
    """Who the customer is (from their session) and which page they're on. Names and email are the
    customer's own account details, quoted and treated only as data."""
    customer = ctx.deps.customer
    if customer:
        lines = [
            f'The customer is logged in as "{customer.first_name} {customer.last_name}", email "{customer.email}". '
            "Their conversation is saved to their account, so earlier messages may be from a previous visit."
        ]
    else:
        lines = ["The customer is a guest (not logged in). This conversation is not saved."]
    page = ctx.deps.page
    if page:
        lines.append(f"They are looking at {page.description}.")
        if page.product_id:
            lines.append(
                f'When they say "this", "it" or "this one", they mean that product: look it up with product_id '
                f"{page.product_id} before you answer."
            )
    return "\n".join(lines)


def _parts_this_turn(messages: list[ModelMessage]) -> list:
    """Every message part since the customer's latest message: tool calls, tool results and retries."""
    parts: list = []
    for message in reversed(messages):
        if isinstance(message, ModelRequest) and any(isinstance(part, UserPromptPart) for part in message.parts):
            break
        parts[:0] = message.parts
    return parts


def _calls_this_turn(messages: list[ModelMessage]) -> list[ToolCallPart]:
    """The tool calls made since the customer's latest message."""
    return [part for part in _parts_this_turn(messages) if isinstance(part, ToolCallPart)]


def _amounts(text: str) -> set[float]:
    return {float(match.group(1).replace(",", "") + "." + (match.group(2) or "0")) for match in MONEY.finditer(text)}


def _prices_this_turn(messages: list[ModelMessage]) -> set[float]:
    """Every price in this turn's tool results, and any max_price the agent searched with."""
    prices: set[float] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in PRICE_FIELDS and isinstance(item, (int, float)):
                    prices.add(round(float(item), 2))
                else:
                    collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    for part in _parts_this_turn(messages):
        if isinstance(part, ToolReturnPart):
            collect(part.content.model_dump() if hasattr(part.content, "model_dump") else part.content)
        elif isinstance(part, ToolCallPart) and part.tool_name in LOOKUP_TOOLS:
            collect(part.args_as_dict())
    return prices


def _looked_up_this_turn(messages: list[ModelMessage]) -> bool:
    """Whether a lookup tool was called since the customer's latest message."""
    return any(call.tool_name in LOOKUP_TOOLS for call in _calls_this_turn(messages))


def _looked_up_page_item(messages: list[ModelMessage], product_id: str) -> bool:
    """Whether the product on the customer's page was looked up since their latest message."""
    return any(
        call.tool_name in PRODUCT_TOOLS and resolve_product_id(str(call.args_as_dict().get("product", ""))) == product_id
        for call in _calls_this_turn(messages)
    )


@agent.output_validator
def check_reply(ctx: RunContext[ShopDeps], reply: AgentReply) -> AgentReply:
    """The safety rules enforced in code: send the reply back for correction if it answers about the item on
    the customer's page without looking it up, states prices or stock it didn't look up this turn, quotes a
    price no lookup returned, names products that don't exist, shares an email address other than the shop's
    or the customer's own, claims to have done something the tools can't do, or looks like it contains a
    password hash."""
    page = ctx.deps.page
    asked = ctx.prompt if isinstance(ctx.prompt, str) else ""
    if page and page.product_id and REFERS_TO_PAGE_ITEM.search(asked) and not _looked_up_page_item(ctx.messages, page.product_id):
        raise ModelRetry(
            f"The customer is on the product page for product_id {page.product_id} and seems to mean that product. "
            "Look it up with get_product_details or check_size_stock before answering."
        )
    if PRICE_OR_STOCK.search(reply.message) and not _looked_up_this_turn(ctx.messages):
        raise ModelRetry(
            "Your reply states a price or stock level without a lookup since the customer's last message. "
            "Call a lookup tool first: prices and stock must come from this turn's tool results."
        )
    allowed = _prices_this_turn(ctx.messages) | {round(float(n), 2) for n in re.findall(r"\d+(?:\.\d+)?", asked)}
    unsupported = sorted(amount for amount in _amounts(reply.message) if round(amount, 2) not in allowed)
    if unsupported:
        raise ModelRetry(
            f"These amounts aren't prices from this turn's lookups: {', '.join(f'${a:.2f}' for a in unsupported)}. "
            "Quote prices exactly as the tools return them, or leave them out."
        )
    unknown = unknown_product_ids(reply.product_ids)
    if unknown:
        raise ModelRetry(f"These product ids don't exist: {', '.join(unknown)}. Only use ids a tool returned.")
    own = {SHOP_EMAIL} | ({ctx.deps.customer.email.lower()} if ctx.deps.customer else set())
    if any(email.lower() not in own for email in EMAIL.findall(reply.message)):
        raise ModelRetry(
            "Don't include email addresses other than the shop's (orderdept@campuscustoms.com) or the logged-in "
            "customer's own. Rewrite the reply without them."
        )
    if CLAIMED_ACTION.search(reply.message):
        raise ModelRetry(
            "Your tools only look up the catalogue: you can't place, hold or change orders, change prices, apply "
            "discounts or give refunds. Don't say you did; tell the customer what you can do and point them to the "
            "shop at 57 Broadway or orderdept@campuscustoms.com."
        )
    if "pbkdf2" in reply.message.lower() or "password_hash" in reply.message.lower():
        raise ModelRetry("Never include password hashes or other secrets in a reply.")
    return reply


def _history(turns: list[ChatTurn]) -> list[ModelMessage]:
    """Earlier chat turns from the website, as PydanticAI message history."""
    return [
        ModelRequest(parts=[UserPromptPart(content=turn.content)])
        if turn.role == "user"
        else ModelResponse(parts=[TextPart(content=turn.content)], model_name=AGENT_MODEL_NAME)
        for turn in turns
    ]


async def run_chat(
    message: str,
    history: list[ChatTurn],
    customer: UserOut | None,
    page: PageView | None,
    record: RunRecord | None = None,
) -> ChatResponse:
    """The agent's reply to the customer's new message, with cards for the products it names and, if it
    searched the catalogue, that search's results for the website's results page.

    history is the conversation so far (saved history for a logged-in customer, the chat panel's for a
    guest); customer comes from the session cookie, and page from the chat panel, checked by tools.page_view.
    record collects the run for the audit trail (audit.py): its steps, Claude calls and why it stopped,
    including when it fails; the caller writes it out.
    """
    record = record or RunRecord(customer="logged-in customer" if customer else "guest", page="(not given)")
    if not HAS_CLAUDE_LOGIN:
        log.warning("Chat unavailable: set CLAUDE_CODE_OAUTH_TOKEN (from `claude setup-token`) or ANTHROPIC_API_KEY in .env.")
        record.stop("Claude unavailable", "neither CLAUDE_CODE_OAUTH_TOKEN nor ANTHROPIC_API_KEY is set")
        raise AssistantUnavailable("The shop assistant isn't available right now. Please try again later.")
    deps = ShopDeps(customer=customer, page=page)
    started = time.perf_counter()
    counting = CURRENT_RUN.set(record)
    with capture_run_messages() as messages:
        try:
            result = await asyncio.wait_for(
                agent.run(
                    message,
                    message_history=_history(history[-HISTORY_TURNS:]),
                    deps=deps,
                    usage_limits=UsageLimits(request_limit=MAX_MODEL_TURNS),
                ),
                CHAT_TIMEOUT_SECONDS,
            )
        except AssistantUnavailable as error:
            record.stop("Claude unavailable", str(error))
            raise
        except TimeoutError:
            record.stop("timed out", f"no reply within the time limit ({CALL_TIMEOUT_SECONDS} s a call, {CHAT_TIMEOUT_SECONDS} s a message)")
            raise AssistantUnavailable("Sorry, that took too long. Please try asking again.") from None
        except UsageLimitExceeded as error:
            record.stop("turn limit reached", f"more than {MAX_MODEL_TURNS} Claude calls ({error})")
            raise AssistantUnavailable("Sorry, I couldn't finish looking that up. Could you ask in a simpler way?") from None
        except UnexpectedModelBehavior as error:
            record.stop("answer kept failing checks", str(error))
            log.warning("Shop agent gave up: %s", error)
            raise AssistantUnavailable("Sorry, something went wrong on my side. Please try again.") from None
        except Exception as error:
            record.stop("error", f"{type(error).__name__}: {error}")
            log.exception("Shop agent failed")
            raise AssistantUnavailable("Sorry, something went wrong on my side. Please try again.") from None
        finally:
            CURRENT_RUN.reset(counting)
            record.add_steps(messages)
    reply = result.output
    log.info("Shop agent replied in %.1fs", time.perf_counter() - started)
    return ChatResponse(
        reply=reply.message.strip(),
        products=product_cards(reply.product_ids),
        page_results=deps.page_results,  # set when the agent searched the catalogue this turn
    )
