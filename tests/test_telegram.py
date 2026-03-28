#!/usr/bin/env python3
"""
Debug: Prueba el envio de mensajes por Telegram.
Ejecutar: python tests/test_telegram.py
"""

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.notifier import enviar_notificacion

print("Probando conexion con Telegram...")
print("=" * 60)

if not TELEGRAM_BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN no configurado en .env")
    exit(1)

if not TELEGRAM_CHAT_ID:
    print("ERROR: TELEGRAM_CHAT_ID no configurado en .env")
    print("\nPara obtenerlo:")
    print("1. Envia un mensaje a tu bot en Telegram")
    print(f"2. Visita: https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates")
    print("3. Busca 'chat':{id':XXXXXXX} - ese es tu CHAT_ID")
    exit(1)

print(f"Token: {TELEGRAM_BOT_TOKEN[:20]}...")
print(f"Chat ID: {TELEGRAM_CHAT_ID}")
print("-" * 60)

if enviar_notificacion("Bot de citas Madrid - Test de conexion OK!"):
    print("\nMensaje enviado! Revisa Telegram.")
else:
    print("\nERROR enviando mensaje.")
