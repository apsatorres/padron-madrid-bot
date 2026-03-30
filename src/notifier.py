"""Telegram notifications."""

import os

from .config import logger, TELEGRAM_BOT_TOKEN


async def send_to_chat(bot, chat_id, message, photo_path=None):
    """Send a message (and optional photo) to a specific chat_id using an existing bot."""
    await bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
    logger.info(f"Message sent to {chat_id}")

    if photo_path and os.path.exists(photo_path):
        with open(photo_path, "rb") as photo:
            await bot.send_photo(chat_id=chat_id, photo=photo)
        logger.info(f"Screenshot sent to {chat_id}")


async def send_notification_standalone(message, photo_path=None, chat_ids=None):
    """Send notification without a running bot (for --once mode / CI).

    Creates a temporary Bot instance from TELEGRAM_BOT_TOKEN.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured.")
        return False

    if not chat_ids:
        logger.error("No chat_ids provided for standalone notification.")
        return False

    import telegram
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        for chat_id in chat_ids:
            await send_to_chat(bot, chat_id, message, photo_path)
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram: {e}")
        return False
