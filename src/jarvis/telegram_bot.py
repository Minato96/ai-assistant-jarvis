"""Telegram front door. Incoming messages invoke the graph; replies go back
to the same chat. thread_id == chat_id, so LangGraph checkpoints per-chat.
"""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage
from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .config import Settings, load_settings
from .db import init_db
from .graph import build_graph
from .memory import build_memory

logger = logging.getLogger("jarvis.telegram")


async def reply_formatted(message: Message, text: str) -> None:
    """Try Telegram-flavored Markdown; fall back to plain text if the LLM's
    output isn't valid Markdown (unbalanced `*`/`_`/backticks, etc.)."""
    try:
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        logger.warning("Reply wasn't valid Markdown; sending as plain text")
        await message.reply_text(text)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    user = update.effective_user
    if settings.allowed_telegram_user_id is None:
        logger.warning(
            "ALLOWED_TELEGRAM_USER_ID is not set — your telegram user_id is %s; "
            "set that in .env to lock the bot to you.",
            user.id if user else "unknown",
        )
    if update.message is not None:
        await reply_formatted(update.message, "Hey, I'm online. Just message me normally.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or update.message is None or not update.message.text:
        return

    if settings.allowed_telegram_user_id is None:
        logger.warning(
            "ALLOWED_TELEGRAM_USER_ID is not set — anyone with this bot's username can "
            "talk to it. Your telegram user_id is %s; set that in .env to lock the bot to you.",
            user.id if user else "unknown",
        )
    elif user is None or user.id != settings.allowed_telegram_user_id:
        logger.warning("Ignoring message from unauthorized user_id=%s", user.id if user else None)
        return

    graph = context.bot_data["graph"]
    thread_id = str(chat.id)

    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    result = graph.invoke(
        {"messages": [HumanMessage(content=update.message.text)], "user_id": thread_id},
        config={"configurable": {"thread_id": thread_id}},
    )
    reply = result["messages"][-1].content
    await reply_formatted(update.message, reply)


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

    logger.info("Jarvis Telegram bot starting (long polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
