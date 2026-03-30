"""Periodic appointment checker for all active user configurations."""

import html
from datetime import datetime, timezone, timedelta

from .config import logger, APPOINTMENTS_URL, CHECK_INTERVAL_MINUTES
from .db import get_all_active_checks
from .checker import check_appointments
from .notifier import send_to_chat

MADRID_TZ = timezone(timedelta(hours=2))


def _format_message(has_appointments, message):
    """Format the Telegram notification."""
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


async def run_all_checks(context):
    """Job callback: check all active user configs and notify."""
    bot = context.bot
    checks = get_all_active_checks()

    if not checks:
        logger.info("No active checks configured.")
        return

    # Group by (category, procedure) to avoid redundant browser sessions
    # when multiple users watch the same tramite
    groups = {}
    for check in checks:
        key = (check["category"], check["procedure"])
        groups.setdefault(key, []).append(check)

    for (category, procedure), user_checks in groups.items():
        # Collect all preferred offices across users for this tramite
        all_preferred = set()
        for uc in user_checks:
            all_preferred.update(uc["preferred_offices"])

        logger.info(
            f"Checking {category} / {procedure} "
            f"for {len(user_checks)} user(s), "
            f"{len(all_preferred)} preferred offices"
        )

        has_appointments, message, screenshot = check_appointments(
            category, procedure, list(all_preferred) if all_preferred else None
        )

        # Notify each user who has this tramite configured
        for uc in user_checks:
            text = _format_message(has_appointments, message)
            if text:
                try:
                    await send_to_chat(bot, uc["chat_id"], text, screenshot)
                except Exception as e:
                    logger.error(f"Failed to notify {uc['chat_id']}: {e}")
            else:
                logger.info(
                    f"No notification for {uc['chat_id']} "
                    f"(check #{uc['id']}): {message}"
                )


def register_jobs(app):
    """Register the periodic check job on the Application's JobQueue."""
    job_queue = app.job_queue
    if job_queue is None:
        logger.error(
            "JobQueue not available. "
            "Install python-telegram-bot[job-queue]."
        )
        return

    interval_seconds = CHECK_INTERVAL_MINUTES * 60
    job_queue.run_repeating(
        run_all_checks,
        interval=interval_seconds,
        first=10,
        name="appointment_checker",
    )
    logger.info(
        f"Scheduled appointment checks every {CHECK_INTERVAL_MINUTES} minutes."
    )
