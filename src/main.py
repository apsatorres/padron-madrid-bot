#!/usr/bin/env python3
"""Entry point for the appointment checker bot."""

import sys
import html
import time
from datetime import datetime, timezone, timedelta

import schedule

from .config import logger, APPOINTMENTS_URL, CHECK_INTERVAL_MINUTES
from .checker import check_appointments
from .notifier import send_notification


def _format_appointment_message(has_appointments, message):
    """Format the message for Telegram."""
    madrid_tz = timezone(timedelta(hours=2))
    timestamp = datetime.now(madrid_tz).strftime("%d/%m/%Y %H:%M")
    safe_message = html.escape(message or "")

    if has_appointments is True:
        return f"""
<b>CITA DISPONIBLE!</b>

{safe_message}

<b>Reserva ahora:</b>
{APPOINTMENTS_URL}

<i>Verificado: {timestamp}</i>
"""
    elif has_appointments is None:
        return f"""
<b>Verificacion de citas - Revisar</b>

{safe_message}

<i>Verificado: {timestamp}</i>
"""
    return None


def run_check():
    """Run the check and notify if appropriate."""
    logger.info("=" * 50)
    logger.info(f"Running check: {datetime.now()}")

    has_appointments, message, screenshot = check_appointments()

    # Only notify if appointments found or error
    text = _format_appointment_message(has_appointments, message)
    if text:
        send_notification(text, screenshot)
    else:
        logger.info(f"No appointments: {message}")


def run_once():
    """Run a single check."""
    run_check()


def run_scheduled():
    """Run scheduled checks."""
    logger.info(f"Starting bot. Checking every {CHECK_INTERVAL_MINUTES} minutes.")

    # Run immediately
    run_check()

    # Schedule runs
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(run_check)

    # Main loop
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        run_scheduled()


if __name__ == "__main__":
    main()
