"""Configuracion del bot de citas."""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# URLs
URL_CITAS = "https://servpub.madrid.es/GNSIS_WBCIUDADANO/tramite.do"

# Busqueda
CATEGORIA_BUSCAR = "Padrón"
TRAMITE_BUSCAR = "Altas"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Intervalos
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 30))

# Directorios
SCREENSHOTS_DIR = "screenshots"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cita_checker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
