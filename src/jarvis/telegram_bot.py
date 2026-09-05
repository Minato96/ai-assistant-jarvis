"""Telegram front door. Incoming messages invoke the graph; replies go back
to the same chat. thread_id == chat_id, so LangGraph checkpoints per-chat.

Inline buttons attach to two specific outcomes of a graph run: a task just
got marked done (offer to log how it went — the outcome data the pattern-
mining/reflection work will eventually read), or a calendar event just got
created (offer a quick edit/replan entry point). Both are detected by reading
the actual tool calls the agent made this turn, not by guessing from the
reply text.
"""
from __future__ import annotations

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Settings, load_settings
from .db import init_db, log_task_outcome
from .graph import build_graph
from .memory import build_memory

logger = logging.getLogger("jarvis.telegram")

OUTCOME_LABELS = {"good": "went well 👍", "meh": "okay 😐", "bad": "didn't go well 👎"}


def _tool_result(messages: list, call_id: str) -> dict | None:
    for m in messages:
        if isinstance(m, ToolMessage) and m.tool_call_id == call_id:
            try:
                return json.loads(m.content)
            except (json.JSONDecodeError, TypeError):
                return None
    return None


def _find_completed_task_ids(messages: list) -> list[int]:
    ids = []
    for m in messages:
        if not (isinstance(m, AIMessage) and m.tool_calls):
            continue
        for call in m.tool_calls:
            if call["name"] == "update_task" and call["args"].get("done") is True:
                result = _tool_result(messages, call["id"])
                if result and result.get("updated"):
                    ids.append(call["args"]["task_id"])
    return ids


def _find_created_events(messages: list) -> list[dict]:
    events = []
    for m in messages:
        if not (isinstance(m, AIMessage) and m.tool_calls):
            continue
        for call in m.tool_calls:
            if call["name"] == "add_calendar_event" and call["args"].get("confirm") is True:
                result = _tool_result(messages, call["id"])
                if result and result.get("created"):
                    events.append(result)
    return events


def _build_reply_markup(messages: list) -> InlineKeyboardMarkup | None:
    rows = []
    for task_id in _find_completed_task_ids(messages):
        rows.append(
            [
                InlineKeyboardButton("👍 Went well", callback_data=f"outcome|{task_id}|good"),
                InlineKeyboardButton("😐 Okay", callback_data=f"outcome|{task_id}|meh"),
                InlineKeyboardButton("👎 Didn't focus", callback_data=f"outcome|{task_id}|bad"),
            ]
        )
    for event in _find_created_events(messages):
        rows.append(
            [
                InlineKeyboardButton("✏️ Edit", callback_data=f"cal|edit|{event['id']}"),
                InlineKeyboardButton("🔄 Replan", callback_data=f"cal|replan|{event['id']}"),
            ]
        )
    return InlineKeyboardMarkup(rows) if rows else None


async def reply_formatted(
    message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    """Try Telegram-flavored Markdown; fall back to plain text if the LLM's
    output isn't valid Markdown (unbalanced `*`/`_`/backticks, etc.)."""
    try:
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except BadRequest:
        logger.warning("Reply wasn't valid Markdown; sending as plain text")
        await message.reply_text(text, reply_markup=reply_markup)


def _is_authorized(settings: Settings, user) -> bool:
    if settings.allowed_telegram_user_id is None:
        logger.warning(
            "ALLOWED_TELEGRAM_USER_ID is not set — anyone with this bot's username can "
            "use it. Your telegram user_id is %s; set that in .env to lock the bot to you.",
            user.id if user else "unknown",
        )
        return True
    if user is None or user.id != settings.allowed_telegram_user_id:
        logger.warning("Ignoring interaction from unauthorized user_id=%s", user.id if user else None)
        return False
    return True


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    _is_authorized(settings, update.effective_user)
    if update.message is not None:
        await reply_formatted(update.message, "Hey, I'm online. Just message me normally.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    chat = update.effective_chat
    if chat is None or update.message is None or not update.message.text:
        return
    if not _is_authorized(settings, update.effective_user):
        return

    graph = context.bot_data["graph"]
    thread_id = str(chat.id)

    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    result = graph.invoke(
        {"messages": [HumanMessage(content=update.message.text)], "user_id": thread_id},
        config={"configurable": {"thread_id": thread_id}},
    )
    reply = result["messages"][-1].content
    await reply_formatted(update.message, reply, reply_markup=_build_reply_markup(result["messages"]))


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    query = update.callback_query
    if query is None or query.data is None:
        return
    if not _is_authorized(settings, update.effective_user):
        await query.answer()
        return

    await query.answer()
    kind, *rest = query.data.split("|")

    if kind == "outcome":
        task_id, value = rest
        log_task_outcome(int(task_id), value)
        base = query.message.text or ""
        await query.edit_message_text(f"{base}\n\nLogged: {OUTCOME_LABELS[value]}")
    elif kind == "cal":
        action, _event_id = rest
        await query.edit_message_reply_markup(reply_markup=None)
        prompt = {
            "edit": "Sure — what would you like to change about it?",
            "replan": "Let's find a better time — what's the constraint?",
        }[action]
        await context.bot.send_message(chat_id=query.message.chat_id, text=prompt)


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    init_db()
    memory = build_memory(settings)
    graph = build_graph(settings, memory)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["graph"] = graph
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Jarvis Telegram bot starting (long polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
