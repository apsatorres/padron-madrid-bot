"""Telegram notifications."""

import os
import asyncio
import telegram

from .config import logger, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _is_configured():
    """Check if Telegram is configured."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


async def _send_message_async(message, photo_path=None):
    """Send message via Telegram to all configured chat IDs."""
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    chat_ids = [cid.strip() for cid in TELEGRAM_CHAT_ID.split(",") if cid.strip()]

    for chat_id in chat_ids:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        logger.info(f"Telegram message sent to {chat_id}")

        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                await bot.send_photo(chat_id=chat_id, photo=photo)
            logger.info(f"Screenshot sent to {chat_id}")


def send_notification(message, photo_path=None):
    """Send a notification via Telegram."""
    if not _is_configured():
        logger.error(
            "Telegram not configured. "
            "Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
        )
        return False

    try:
        asyncio.run(_send_message_async(message, photo_path))
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram: {e}")
        return False
