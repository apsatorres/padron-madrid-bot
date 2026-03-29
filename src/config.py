"""Configuration for the appointment checker bot."""

import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

# URLs
APPOINTMENTS_URL = "https://servpub.madrid.es/GNSIS_WBCIUDADANO/tramite.do"

# Search terms (Spanish - must match website)
CATEGORY_SEARCH = "Padrón y censo"
PROCEDURE_SEARCH = "Altas, bajas y cambio de domicilio en Padrón"

# Preferred offices to check first (in priority order, closest to you)
PREFERRED_OFFICES = [
    "OAC Ciudad Lineal",
    "OAC Chamberí",
    "OAC Centro",
    "OAC Retiro",
    "OAC Salamanca"
]

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Intervals
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 30))

# Directories
SCREENSHOTS_DIR = "screenshots"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('cita_checker.log', maxBytes=500_000, backupCount=3),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
