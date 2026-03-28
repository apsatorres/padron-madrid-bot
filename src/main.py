#!/usr/bin/env python3
"""Punto de entrada del bot de citas."""

import sys
from datetime import datetime

import schedule

from .config import logger, URL_CITAS, CHECK_INTERVAL_MINUTES
from .checker import verificar_citas
from .notifier import enviar_notificacion


def _formatear_mensaje_cita(hay_citas, mensaje):
    """Formatea el mensaje para Telegram."""
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    if hay_citas is True:
        return f"""
<b>CITA DISPONIBLE!</b>

{mensaje}

<b>Reserva ahora:</b>
{URL_CITAS}

<i>Verificado: {timestamp}</i>
"""
    elif hay_citas is None:
        return f"""
<b>Verificacion de citas - Revisar</b>

{mensaje}

<i>Verificado: {timestamp}</i>
"""
    return None


def ejecutar_verificacion():
    """Ejecuta la verificacion y notifica si corresponde."""
    logger.info("=" * 50)
    logger.info(f"Ejecutando verificacion: {datetime.now()}")

    hay_citas, mensaje, screenshot = verificar_citas()

    # Solo notificar si hay citas o hay error
    texto = _formatear_mensaje_cita(hay_citas, mensaje)
    if texto:
        enviar_notificacion(texto, screenshot)
    else:
        logger.info(f"Sin citas: {mensaje}")


def run_once():
    """Ejecuta una sola verificacion."""
    ejecutar_verificacion()


def run_scheduled():
    """Ejecuta verificaciones programadas."""
    logger.info(f"Iniciando bot. Verificando cada {CHECK_INTERVAL_MINUTES} minutos.")

    # Ejecutar inmediatamente
    ejecutar_verificacion()

    # Programar ejecuciones
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(ejecutar_verificacion)

    # Loop principal
    import time
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    """Funcion principal."""
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        run_scheduled()


if __name__ == "__main__":
    main()
