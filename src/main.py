#!/usr/bin/env python3
"""Entry point for the appointment checker bot."""

import sys
import asyncio
import html
from datetime import datetime, timezone, timedelta

from .config import logger, APPOINTMENTS_URL, TELEGRAM_CHAT_ID, CHECK_INTERVAL_MINUTES
from .db import init_db, get_all_active_checks
from .checker import check_appointments
from .notifier import send_notification_standalone

MADRID_TZ = timezone(timedelta(hours=2))


def _format_message(has_appointments, message):
    timestamp = datetime.now(MADRID_TZ).strftime("%d/%m/%Y %H:%M")
    safe = html.escape(message or "")

    if has_appointments is True:
        return (
            f"<b>CITA DISPONIBLE!</b>\n\n"
            f"{safe}\n\n"
            f"<b>Reserva ahora:</b>\n{APPOINTMENTS_URL}\n\n"
            f"<i>Verificado: {timestamp}</i>"
        )
    if has_appointments is None:
        return (
            f"<b>Verificacion de citas - Revisar</b>\n\n"
            f"{safe}\n\n"
            f"<i>Verificado: {timestamp}</i>"
        )
    return None


def run_once():
    """Single check run (for CI / cron / manual testing).

    Uses DB checks if any exist, otherwise falls back to TELEGRAM_CHAT_ID.
    """
    init_db()
    checks = get_all_active_checks()

    if checks:
        for check in checks:
            logger.info(f"Running check #{check['id']} for chat {check['chat_id']}")
            has, message, screenshot = check_appointments(
                check["category"],
                check["procedure"],
                check["preferred_offices"] or None,
            )
            text = _format_message(has, message)
            if text:
                asyncio.run(send_notification_standalone(
                    text, screenshot, [check["chat_id"]]
                ))
            else:
                logger.info(f"No notification: {message}")
    elif TELEGRAM_CHAT_ID:
        logger.warning(
            "No checks in DB. Use the bot to /add checks, "
            "or this is a legacy CI run."
        )
    else:
        logger.warning("No checks configured and no TELEGRAM_CHAT_ID set.")


def run_bot():
    """Start the interactive bot with scheduled checks."""
    from .bot import create_bot
    from .scheduler import register_jobs

    app = create_bot()
    register_jobs(app)

    logger.info("Starting interactive bot with scheduled checks...")
    app.run_polling()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        run_bot()


if __name__ == "__main__":
    main()
