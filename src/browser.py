"""Browser automation with Selenium."""

import os
import stat
import time
from datetime import datetime
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager

from .config import logger, SCREENSHOTS_DIR


def _get_option_text(option):
    """Get useful text from an <option> element."""
    return (
        (option.text or "").strip()
        or (option.get_attribute("label") or "").strip()
        or (option.get_attribute("value") or "").strip()
    )


def _get_chrome_options():
    """Configure Chrome options."""
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

    # In CI, point to Chrome binary installed by the action
    if os.getenv("CI"):
        import shutil
        chrome_path = shutil.which("google-chrome") or shutil.which("chromium-browser")
        if chrome_path:
            options.binary_location = chrome_path

    return options


def _get_chromedriver_path():
    """Get the correct chromedriver path."""
    # In CI, use system chromedriver
    if os.getenv("CI"):
        import shutil
        path = shutil.which("chromedriver")
        if path:
            return path

    # Locally, use webdriver-manager
    driver_path = ChromeDriverManager().install()
    if driver_path.endswith("THIRD_PARTY_NOTICES.chromedriver"):
        driver_path = driver_path.replace(
            "THIRD_PARTY_NOTICES.chromedriver", "chromedriver"
        )
    os.chmod(driver_path, os.stat(driver_path).st_mode | stat.S_IEXEC)
    return driver_path


@contextmanager
def create_driver():
    """Context manager for Chrome driver."""
    driver = None
    try:
        service = Service(executable_path=_get_chromedriver_path())
        driver = webdriver.Chrome(service=service, options=_get_chrome_options())
        driver.implicitly_wait(10)
        yield driver
    finally:
        if driver:
            driver.quit()


def save_screenshot(driver, suffix=""):
    """Save a screenshot and return the path."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"page_{timestamp}{suffix}.png"
    path = os.path.join(SCREENSHOTS_DIR, filename)
    driver.save_screenshot(path)
    logger.info(f"Screenshot saved: {path}")
    return path


def select_option_by_text(select_element, partial_text, driver=None):
    """Select a dropdown option containing the partial text.

    Handles native HTML selects and various JS dropdown widgets.
    """
    # Get driver reference
    if driver is None:
        driver = select_element._el.parent

    select_el = select_element._el
    select_id = select_el.get_attribute("id")

    # Find matching option value and text
    target_value = None
    target_text = None
    for option in select_element.options:
        option_text = _get_option_text(option)
        if partial_text.lower() in option_text.lower():
            target_value = option.get_attribute("value")
            target_text = option_text
            break

    if not target_value:
        logger.warning(f"Option containing '{partial_text}' not found")
        return False

    # Method 1: Try native select
    try:
        select_element.select_by_value(target_value)
        logger.info(f"Selected (native): {target_text}")
        return True
    except Exception:
        pass

    # Method 2: Click on adjacent span/container (common pattern)
    try:
        # Find clickable container next to select
        containers = driver.find_elements(
            By.XPATH,
            f"//select[@id='{select_id}']/following-sibling::span[1]"
        )
        if not containers:
            containers = driver.find_elements(
                By.XPATH,
                f"//select[@id='{select_id}']/parent::*/span[contains(@class, 'select')]"
            )

        for container in containers:
            if container.is_displayed():
                container.click()
                time.sleep(0.5)

                # Look for dropdown options (various patterns)
                option_selectors = [
                    "li.select2-results__option",
                    "ul.dropdown-menu li",
                    "div.dropdown-menu a",
                    "li[role='option']",
                    "div[role='option']",
                ]
                for opt_selector in option_selectors:
                    options = driver.find_elements(By.CSS_SELECTOR, opt_selector)
                    for opt in options:
                        if partial_text.lower() in opt.text.lower():
                            opt.click()
                            logger.info(f"Selected (click widget): {target_text}")
                            time.sleep(0.5)
                            return True

                # Close if not found
                driver.find_element(By.TAG_NAME, "body").click()
    except Exception as e:
        logger.debug(f"Click widget failed: {e}")

    # Method 3: Use jQuery/JS to properly trigger change
    try:
        result = driver.execute_script(
            """
            var select = arguments[0];
            var value = arguments[1];

            // Set value
            select.value = value;

            // Try multiple event types to trigger listeners
            var events = ['change', 'input', 'blur'];
            events.forEach(function(eventType) {
                var evt = new Event(eventType, { bubbles: true, cancelable: true });
                select.dispatchEvent(evt);
            });

            // Also try jQuery if available
            if (typeof jQuery !== 'undefined') {
                jQuery(select).val(value).trigger('change').trigger('select2:select');
            }

            // Try triggering change on the form
            var form = select.closest('form');
            if (form) {
                form.dispatchEvent(new Event('change', { bubbles: true }));
            }

            return true;
            """,
            select_el,
            target_value,
        )
        if result:
            logger.info(f"Selected (JS events): {target_text}")
            time.sleep(1)  # Wait for any AJAX updates
            return True
    except Exception as e:
        logger.warning(f"JS select failed: {e}")

    return False


def find_selects(driver):
    """Find all select elements on the page."""
    return driver.find_elements(By.TAG_NAME, "select")


def log_select_options(driver):
    """Log options from all selects for debugging."""
    all_selects = find_selects(driver)
    logger.info(f"Found {len(all_selects)} selects on the page")

    for i, sel in enumerate(all_selects):
        try:
            select_obj = Select(sel)
            options = [_get_option_text(opt) for opt in select_obj.options]
            logger.info(f"Select {i}: {options[:5]}...")
        except Exception as e:
            logger.warning(f"Error reading select {i}: {e}")


def click_search_button(driver):
    """Find and click the search/continue button."""
    css_selectors = (
        "button[type='submit'], input[type='submit'], "
        "button.btn, .boton, #buscar, #continuar"
    )
    buttons = driver.find_elements(By.CSS_SELECTOR, css_selectors)

    if not buttons:
        xpath_selectors = (
            "//button[contains(text(), 'Buscar')] | "
            "//button[contains(text(), 'Continuar')] | "
            "//input[@value='Buscar']"
        )
        buttons = driver.find_elements(By.XPATH, xpath_selectors)

    if buttons:
        buttons[0].click()
        return True
    return False


def _close_cookie_banner(driver):
    """Try to close/accept the cookie banner if present."""
    selectors = [
        (By.ID, "iam-cookie-control-dismiss"),
        (By.ID, "iam-cookie-control-save"),
        (By.ID, "iam-cookie-control-accept-all"),
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'abcdefghijklmnopqrstuvwxyzáéíóúüñ', "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ'), "
            "'ACEPTAR')]",
        ),
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'abcdefghijklmnopqrstuvwxyzáéíóúüñ', "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ'), "
            "'GUARDAR')]",
        ),
    ]

    for by, selector in selectors:
        buttons = driver.find_elements(by, selector)
        for button in buttons:
            if button.is_displayed():
                try:
                    button.click()
                    logger.info("Cookie banner handled.")
                    return True
                except Exception:
                    continue

    return False


def click_unidentified_access(driver, timeout=3):
    """Click 'Acceso SIN Identificar' if present."""
    locators = [
        (By.ID, "accesoNoIdentificado"),
        (By.LINK_TEXT, "Acceso SIN Identificar"),
        (By.PARTIAL_LINK_TEXT, "SIN Identificar"),
        (
            By.XPATH,
            "//a[contains(translate(normalize-space(.), "
            "'abcdefghijklmnopqrstuvwxyzáéíóúüñ', "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ'), "
            "'ACCESO SIN IDENTIFICAR')]",
        ),
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'abcdefghijklmnopqrstuvwxyzáéíóúüñ', "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ'), "
            "'ACCESO SIN IDENTIFICAR')]",
        ),
        (
            By.XPATH,
            "//input[contains(translate(@value, "
            "'abcdefghijklmnopqrstuvwxyzáéíóúüñ', "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ'), "
            "'ACCESO SIN IDENTIFICAR')]",
        ),
    ]

    for by, selector in locators:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            try:
                element.click()
            except ElementClickInterceptedException:
                _close_cookie_banner(driver)
                driver.execute_script(
                    "const backdrop = document.getElementById('iam-cookie-control-modal-backdrop');"
                    "if (backdrop) { backdrop.style.display = 'none'; }"
                )
                driver.execute_script("arguments[0].click();", element)
            logger.info("Click on 'Acceso SIN Identificar' completed.")
            return True
        except TimeoutException:
            continue

    logger.info(
        "Button 'Acceso SIN Identificar' not found; "
        "continuing with current flow."
    )
    return False


def click_earliest_appointment_link(driver, timeout=5):
    """Click 'consultar la oficina con cita más temprana' link."""
    locators = [
        (By.PARTIAL_LINK_TEXT, "cita más temprana"),
        (By.PARTIAL_LINK_TEXT, "cita mas temprana"),
        (By.XPATH, "//a[contains(text(), 'cita más temprana')]"),
        (By.XPATH, "//a[contains(text(), 'cita mas temprana')]"),
        (By.XPATH, "//a[contains(@href, 'temprana')]"),
    ]

    for by, selector in locators:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            element.click()
            logger.info("Click on 'consultar oficina con cita más temprana' completed.")
            return True
        except TimeoutException:
            continue

    logger.warning("Link 'cita más temprana' not found")
    return False


def get_page_text(driver):
    """Get the page text content."""
    return driver.find_element(By.TAG_NAME, "body").text.lower()
