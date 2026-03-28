"""Configuration for the appointment checker bot."""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# URLs
APPOINTMENTS_URL = "https://servpub.madrid.es/GNSIS_WBCIUDADANO/tramite.do"

# Search terms (Spanish - must match website)
CATEGORY_SEARCH = "Padrón y censo"
PROCEDURE_SEARCH = "Altas, bajas y cambio de domicilio en Padrón"

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
        logging.FileHandler('cita_checker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
