"""Telegram bot runner — starts/stops bots based on DB config."""

import asyncio
import logging
import re
from typing import Dict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import async_session
from models import Bot, BotStatus
from crypto import get_price, get_market_overview, get_top_movers, COIN_IDS

logger = logging.getLogger(__name__)

# Track running bot applications instances keyed by bot DB id
_running_bots: Dict[int, Application] = {}


async def _load_bot_config(bot_id: int) -> Bot | None:
    async with async_session() as session:
        result = await session.execute(
            select(Bot)
            .options(
                selectinload(Bot.commands),
                selectinload(Bot.auto_replies),
                selectinload(Bot.scheduled_messages),
            )
            .where(Bot.id == bot_id)
        )
        return result.scalar_one_or_none()


def _make_message_handler(bot_config: Bot):
    """Create a catch-all message handler using the bot's config."""

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        user_text = update.message.text.lower().strip()

        # 1. Check if user typed "price <coin>" pattern
        price_match = re.match(r'^price\s+(\w+)', user_text)
        if price_match:
            symbol = price_match.group(1)
            await update.message.reply_text("Fetching price...")
            result = await get_price(symbol)
            await update.message.reply_text(result)
            return

        # 2. Check commands (e.g. /start, /help)
        for cmd in bot_config.commands:
            if user_text == cmd.command.lower():
                await update.message.reply_text(cmd.response)
                return

        # 3. Check auto-replies (keyword match)
        for ar in bot_config.auto_replies:
            if ar.trigger.lower() in user_text:
                await update.message.reply_text(ar.reply)
                return

        # 4. Welcome message for greetings
        greetings = {"hi", "hello", "hey", "start"}
        if user_text in greetings:
            await update.message.reply_text(bot_config.welcome_message)
            return

        # 5. Fallback
        await update.message.reply_text(bot_config.fallback_message)

    return handle_message


def _make_command_handlers(bot_config: Bot) -> list[CommandHandler]:
    """Create CommandHandlers for each configured command."""
    handlers = []
    for cmd in bot_config.commands:
        cmd_name = cmd.command.lstrip("/")

        # Special live handlers for crypto commands
        if cmd_name.lower() == "price":
            async def price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
                if not update.message:
                    return
                args = context.args
                if args:
                    symbol = args[0].strip().lower()
                    await update.message.reply_text("Fetching price...")
                    result = await get_price(symbol)
                    await update.message.reply_text(result)
                else:
                    await update.message.reply_text(
                        "Usage: /price <coin>\n\n"
                        "Examples:\n"
                        "  /price BTC\n"
                        "  /price ETH\n"
                        "  /price SOL\n"
                        "  /price DOGE\n\n"
                        f"Supported: {', '.join(sorted(COIN_IDS.keys())[:10])}..."
                    )
            handlers.append(CommandHandler(cmd_name, price_handler))

        elif cmd_name.lower() == "market":
            async def market_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
                if update.message:
                    await update.message.reply_text("Loading market data...")
                    result = await get_market_overview()
                    await update.message.reply_text(result)
            handlers.append(CommandHandler(cmd_name, market_handler))

        elif cmd_name.lower() == "movers":
            async def movers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
                if update.message:
                    await update.message.reply_text("Fetching top movers...")
                    result = await get_top_movers()
                    await update.message.reply_text(result)
            handlers.append(CommandHandler(cmd_name, movers_handler))

        else:
            async def handler(update: Update, context, _response=cmd.response):
                if update.message:
                    await update.message.reply_text(_response)
            handlers.append(CommandHandler(cmd_name, handler))

    return handlers


async def start_bot(bot_id: int) -> bool:
    """Start a Telegram bot. Returns True on success."""
    if bot_id in _running_bots:
        logger.info(f"Bot {bot_id} already running")
        return True

    config = await _load_bot_config(bot_id)
    if not config:
        logger.error(f"Bot {bot_id} not found in DB")
        return False

    try:
        app = Application.builder().token(config.token).build()

        # Register command handlers
        for handler in _make_command_handlers(config):
            app.add_handler(handler)

        # Register catch-all message handler
        msg_handler = _make_message_handler(config)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

        # Start polling
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        _running_bots[bot_id] = app
        logger.info(f"Bot {bot_id} ({config.name}) started successfully")

        # Update status in DB
        async with async_session() as session:
            bot = await session.get(Bot, bot_id)
            if bot:
                bot.status = BotStatus.ACTIVE
                await session.commit()

        return True

    except Exception as e:
        logger.error(f"Failed to start bot {bot_id}: {e}")
        async with async_session() as session:
            bot = await session.get(Bot, bot_id)
            if bot:
                bot.status = BotStatus.ERROR
                await session.commit()
        return False


async def stop_bot(bot_id: int) -> bool:
    """Stop a running bot."""
    app = _running_bots.pop(bot_id, None)
    if not app:
        return False

    try:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info(f"Bot {bot_id} stopped")

        async with async_session() as session:
            bot = await session.get(Bot, bot_id)
            if bot:
                bot.status = BotStatus.PAUSED
                await session.commit()

        return True
    except Exception as e:
        logger.error(f"Error stopping bot {bot_id}: {e}")
        return False


async def restart_bot(bot_id: int) -> bool:
    """Restart a bot (stop then start)."""
    await stop_bot(bot_id)
    return await start_bot(bot_id)


async def stop_all_bots():
    """Gracefully stop all running bots on shutdown."""
    for bot_id in list(_running_bots.keys()):
        await stop_bot(bot_id)


def get_running_bot_ids() -> list[int]:
    return list(_running_bots.keys())
