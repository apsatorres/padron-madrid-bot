"""Notificaciones por Telegram."""

import os
import asyncio
import telegram

from .config import logger, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _is_configured():
    """Verifica si Telegram esta configurado."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


async def _enviar_mensaje_async(mensaje, foto_path=None):
    """Envia mensaje por Telegram (async)."""
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=mensaje,
        parse_mode='HTML'
    )
    logger.info("Mensaje de Telegram enviado")

    if foto_path and os.path.exists(foto_path):
        with open(foto_path, 'rb') as foto:
            await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=foto)
        logger.info("Screenshot enviado por Telegram")


def enviar_notificacion(mensaje, foto_path=None):
    """Envia una notificacion por Telegram."""
    if not _is_configured():
        logger.error(
            "Telegram no configurado. "
            "Revisa TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env"
        )
        return False

    try:
        asyncio.run(_enviar_mensaje_async(mensaje, foto_path))
        return True
    except Exception as e:
        logger.error(f"Error enviando Telegram: {e}")
        return False
