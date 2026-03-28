"""Manejo del navegador con Selenium."""

import os
import time
from datetime import datetime
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from .config import logger, SCREENSHOTS_DIR


def _get_chrome_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    # En CI, apuntar al binario de Chrome instalado por la action
    if os.getenv("CI"):
        import shutil
        chrome_path = shutil.which("google-chrome") or shutil.which("chromium-browser")
        if chrome_path:
            options.binary_location = chrome_path

    return options


def _get_chromedriver_path():
    """Obtiene el path correcto del chromedriver."""
    # En CI, usar el chromedriver del sistema
    if os.getenv("CI"):
        import shutil
        path = shutil.which("chromedriver")
        if path:
            return path

    # En local, usar webdriver-manager
    from webdriver_manager.chrome import ChromeDriverManager
    driver_path = ChromeDriverManager().install()
    if driver_path.endswith("THIRD_PARTY_NOTICES.chromedriver"):
        driver_path = driver_path.replace(
            "THIRD_PARTY_NOTICES.chromedriver", "chromedriver"
        )
    import stat
    os.chmod(driver_path, os.stat(driver_path).st_mode | stat.S_IEXEC)
    return driver_path


@contextmanager
def crear_driver():
    """Context manager para el driver de Chrome."""
    driver = None
    try:
        service = Service(executable_path=_get_chromedriver_path())
        driver = webdriver.Chrome(service=service, options=_get_chrome_options())
        driver.implicitly_wait(10)
        yield driver
    finally:
        if driver:
            driver.quit()


def guardar_screenshot(driver, sufijo=""):
    """Guarda un screenshot y retorna el path."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"pagina_{timestamp}{sufijo}.png"
    path = os.path.join(SCREENSHOTS_DIR, filename)
    driver.save_screenshot(path)
    logger.info(f"Screenshot guardado: {path}")
    return path


def seleccionar_opcion_por_texto(select_element, texto_parcial):
    """Selecciona una opcion del dropdown que contenga el texto parcial."""
    for option in select_element.options:
        if texto_parcial.lower() in option.text.lower():
            select_element.select_by_visible_text(option.text)
            logger.info(f"Seleccionado: {option.text}")
            return True
    return False


def encontrar_selects(driver):
    """Encuentra todos los elementos select en la pagina."""
    return driver.find_elements(By.TAG_NAME, "select")


def log_opciones_select(driver):
    """Loguea las opciones de todos los selects para debug."""
    all_selects = encontrar_selects(driver)
    logger.info(f"Encontrados {len(all_selects)} selectores en la pagina")

    for i, sel in enumerate(all_selects):
        try:
            select_obj = Select(sel)
            opciones = [opt.text for opt in select_obj.options]
            logger.info(f"Select {i}: {opciones[:5]}...")
        except Exception as e:
            logger.warning(f"Error leyendo select {i}: {e}")


def click_boton_buscar(driver):
    """Busca y hace click en el boton de buscar/continuar."""
    selectores_css = (
        "button[type='submit'], input[type='submit'], "
        "button.btn, .boton, #buscar, #continuar"
    )
    botones = driver.find_elements(By.CSS_SELECTOR, selectores_css)

    if not botones:
        selectores_xpath = (
            "//button[contains(text(), 'Buscar')] | "
            "//button[contains(text(), 'Continuar')] | "
            "//input[@value='Buscar']"
        )
        botones = driver.find_elements(By.XPATH, selectores_xpath)

    if botones:
        botones[0].click()
        return True
    return False


def obtener_texto_pagina(driver):
    """Obtiene el texto de la pagina."""
    return driver.find_element(By.TAG_NAME, "body").text.lower()
