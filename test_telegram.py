#!/usr/bin/env python3
"""Script para probar la conexion con Telegram."""

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.notifier import enviar_notificacion


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env")
        print("Ver README.md para instrucciones")
        return

    print(f"Token: {TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"Chat ID: {TELEGRAM_CHAT_ID}")

    if enviar_notificacion(
        "Bot de citas Madrid funcionando!\n"
        "Recibiras notificaciones cuando haya citas disponibles."
    ):
        print("Mensaje enviado! Revisa Telegram.")
    else:
        print("Error enviando mensaje.")


if __name__ == "__main__":
    main()
