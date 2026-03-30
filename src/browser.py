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
    TimeoutException, ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

from .config import logger, SCREENSHOTS_DIR

_cached_chromedriver_path = None


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
    options.page_load_strategy = "eager"
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-default-apps")
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
    """Get the correct chromedriver path. Cached after first resolution."""
    global _cached_chromedriver_path
    if _cached_chromedriver_path:
        return _cached_chromedriver_path

    if os.getenv("CI"):
        import shutil
        path = shutil.which("chromedriver")
        if path:
            _cached_chromedriver_path = path
            return path

    driver_path = ChromeDriverManager().install()
    if driver_path.endswith("THIRD_PARTY_NOTICES.chromedriver"):
        driver_path = driver_path.replace(
            "THIRD_PARTY_NOTICES.chromedriver", "chromedriver"
        )
    os.chmod(driver_path, os.stat(driver_path).st_mode | stat.S_IEXEC)
    _cached_chromedriver_path = driver_path
    return driver_path


@contextmanager
def create_driver():
    """Context manager for Chrome driver."""
    driver = None
    try:
        service = Service(executable_path=_get_chromedriver_path())
        driver = webdriver.Chrome(service=service, options=_get_chrome_options())
        driver.implicitly_wait(3)
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


def get_combobox_state(driver, input_id, select_id):
    """Read current state of a combobox pair (visible input + hidden select)."""
    return driver.execute_script("""
        var selectEl = document.getElementById(arguments[0]);
        var inputEl = document.getElementById(arguments[1]);
        var result = {};

        if (selectEl) {
            result.select_value = selectEl.value;
            var idx = selectEl.selectedIndex;
            result.select_text = (idx >= 0 && selectEl.options[idx])
                ? selectEl.options[idx].text : '';
            result.option_count = selectEl.options.length;
        }

        if (inputEl) {
            result.input_value = inputEl.value;
        }

        return result;
    """, select_id, input_id)


def verify_combobox_selection(driver, input_id, select_id, expected_text):
    """Verify combobox selection matches expected text in both layers."""
    state = get_combobox_state(driver, input_id, select_id)
    if not state:
        logger.warning(f"Could not read combobox state for #{input_id}/#{select_id}")
        return False

    select_value = state.get("select_value", "-1")
    select_text = state.get("select_text", "")
    input_value = state.get("input_value", "")

    logger.info(
        f"Combobox #{input_id}: input='{input_value}', "
        f"select='{select_text}' (value={select_value})"
    )

    if select_value in ("-1", "", None):
        logger.warning(f"Hidden select #{select_id} still at default value")
        return False

    expected_lower = expected_text.lower()
    if (
        expected_lower in (select_text or "").lower()
        or expected_lower in (input_value or "").lower()
    ):
        return True

    logger.warning(
        f"Expected '{expected_text}' not found in combobox state. "
        f"input='{input_value}', select='{select_text}'"
    )
    return False


def _try_combobox_ui_interaction(driver, combo_input, partial_text, timeout):
    """Type into combobox input and click matching autocomplete menu item."""
    try:
        combo_input.click()
        time.sleep(0.1)

        driver.execute_script("arguments[0].value = '';", combo_input)
        combo_input.send_keys(partial_text)
        time.sleep(0.3)

        menu_timeout = min(5, timeout)
        menu_selectors = [
            "ul.ui-autocomplete li.ui-menu-item",
            ".ui-autocomplete .ui-menu-item",
        ]

        for selector in menu_selectors:
            try:
                items = WebDriverWait(driver, menu_timeout).until(
                    EC.visibility_of_any_elements_located(
                        (By.CSS_SELECTOR, selector)
                    )
                )
                for item in items:
                    item_text = item.text.strip()
                    if partial_text.lower() in item_text.lower():
                        clickable = item.find_elements(
                            By.CSS_SELECTOR, "a, div.ui-menu-item-wrapper"
                        )
                        (clickable[0] if clickable else item).click()
                        logger.info(f"Selected from autocomplete: {item_text}")
                        time.sleep(0.3)
                        return True
            except TimeoutException:
                continue

    except Exception as e:
        logger.debug(f"Combobox UI interaction failed: {e}")

    return False


def _select_combobox_js_fallback(driver, input_id, select_id, partial_text):
    """Set combobox value via JS, updating both hidden select and visible input."""
    try:
        result = driver.execute_script("""
            var selectEl = document.getElementById(arguments[0]);
            var inputEl = document.getElementById(arguments[1]);
            var searchText = arguments[2].toLowerCase();

            if (!selectEl) return {error: 'select not found: ' + arguments[0]};
            if (!inputEl) return {error: 'input not found: ' + arguments[1]};

            var targetOption = null;
            for (var i = 0; i < selectEl.options.length; i++) {
                if (selectEl.options[i].text.toLowerCase().indexOf(searchText) !== -1) {
                    targetOption = selectEl.options[i];
                    break;
                }
            }

            if (!targetOption) return {error: 'option not found for: ' + arguments[2]};

            selectEl.value = targetOption.value;
            inputEl.value = targetOption.text;

            ['change', 'input', 'blur'].forEach(function(t) {
                selectEl.dispatchEvent(new Event(t, {bubbles: true}));
            });

            if (typeof jQuery !== 'undefined') {
                jQuery(selectEl).val(targetOption.value).trigger('change');
                jQuery(inputEl).val(targetOption.text);
            }

            return {value: targetOption.value, text: targetOption.text};
        """, select_id, input_id, partial_text)

        if isinstance(result, dict) and "error" not in result:
            logger.info(f"Selected (JS fallback): {result.get('text', '?')}")
            return True
        logger.warning(f"JS fallback issue: {result}")
    except Exception as e:
        logger.warning(f"JS fallback exception: {e}")
    return False


def select_combobox_option(driver, input_id, select_id, partial_text, timeout=10):
    """Select option in a jQuery UI combobox via user-like interaction.

    Tries UI interaction first (type in autocomplete input + pick from menu),
    then falls back to JS-based selection if UI path fails.
    Verifies result by checking both visible input and hidden select.
    """
    try:
        combo_input = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, input_id))
        )
    except TimeoutException:
        logger.warning(f"Combobox input #{input_id} not found or not clickable")
        return False

    if _try_combobox_ui_interaction(driver, combo_input, partial_text, timeout):
        if verify_combobox_selection(driver, input_id, select_id, partial_text):
            return True
        logger.warning("UI interaction ran but verification failed; trying JS fallback")

    logger.info(f"Trying JS fallback for #{input_id}")
    if _select_combobox_js_fallback(driver, input_id, select_id, partial_text):
        time.sleep(0.3)
        if verify_combobox_selection(driver, input_id, select_id, partial_text):
            return True

    logger.warning(f"All selection methods failed for #{input_id}")
    return False


def wait_for_procedure_options(driver, select_id, expected_text, timeout=10):
    """Wait until procedure select contains the expected option after category change."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            select_el = driver.find_element(By.ID, select_id)
            options = Select(select_el).options
            for opt in options:
                if expected_text.lower() in _get_option_text(opt).lower():
                    logger.info(
                        f"Procedure option '{expected_text}' found "
                        f"({len(options)} options loaded)"
                    )
                    return True
        except (StaleElementReferenceException, Exception):
            pass
        time.sleep(0.5)

    logger.warning(f"Timed out waiting for '{expected_text}' in #{select_id}")
    return False


OFFICE_INPUT_ID = "cpTramite_combo2"
OFFICE_SELECT_ID = "selectOficinas"


def fetch_site_options(category=None):
    """Fetch available options from the live site.

    If category is None, returns {"categories": [...]}.
    If category is given, selects it and returns:
      {"procedures": [...], "offices": [...]}.
    """
    from .config import APPOINTMENTS_URL

    result = {}
    try:
        with create_driver() as driver:
            driver.get(APPOINTMENTS_URL)
            click_unidentified_access(driver)
            WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.ID, "cpTramite_combo0"))
            )

            cat_sel = driver.find_element(By.ID, "selectCategorias")
            cats = [
                _get_option_text(o) for o in Select(cat_sel).options
                if _get_option_text(o) and _get_option_text(o) != "-- Seleccione o teclee --"
            ]
            result["categories"] = cats

            if category:
                select_combobox_option(driver, "cpTramite_combo0", "selectCategorias", category)
                time.sleep(1)

                proc_sel = driver.find_element(By.ID, "selectTramites")
                procs = [
                    _get_option_text(o) for o in Select(proc_sel).options
                    if _get_option_text(o) and _get_option_text(o) != "-- Seleccione o teclee --"
                ]
                result["procedures"] = procs

                office_sel = driver.find_element(By.ID, "selectOficinas")
                offices = [
                    _get_option_text(o) for o in Select(office_sel).options
                    if _get_option_text(o) and _get_option_text(o) != "-- Seleccione o teclee --"
                ]
                result["offices"] = offices

    except Exception as e:
        logger.warning(f"Error fetching site options: {e}")

    return result


def select_office(driver, office_name):
    """Select a specific office from the oficinas combobox."""
    logger.info(f"Selecting office: '{office_name}'")
    return select_combobox_option(
        driver, OFFICE_INPUT_ID, OFFICE_SELECT_ID, office_name
    )


MONTH_MAP = {
    "ene": "01", "feb": "02", "mar": "03", "abr": "04",
    "may": "05", "jun": "06", "jul": "07", "ago": "08",
    "sep": "09", "oct": "10", "nov": "11", "dic": "12",
}


def get_selected_office(driver, timeout=10):
    """Read the auto-selected office name after clicking 'cita más temprana'."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: (
                d.find_elements(By.ID, "cpTramite_combo2")
                and d.find_element(By.ID, "cpTramite_combo2").get_attribute("value")
                and d.find_element(By.ID, "cpTramite_combo2").get_attribute("value")
                != "-- Seleccione o teclee --"
            )
        )
        return driver.find_element(By.ID, "cpTramite_combo2").get_attribute("value")
    except TimeoutException:
        pass

    sel = driver.find_elements(By.ID, "selectOficinas")
    if sel:
        try:
            selected = Select(sel[0]).first_selected_option
            text = selected.text.strip()
            if text and text != "Seleccione":
                return text
        except Exception:
            pass

    return None


def click_siguiente(driver, timeout=5, wait_for=None):
    """Click the visible 'Siguiente' button.

    Args:
        wait_for: Optional CSS selector to wait for after clicking.
    """
    clicked = False
    for btn_id in ["botonTramites", "botonSiguienteHora"]:
        els = driver.find_elements(By.ID, btn_id)
        for el in els:
            if el.is_displayed():
                el.click()
                logger.info(f"Clicked Siguiente (#{btn_id})")
                clicked = True
                break
        if clicked:
            break

    if not clicked:
        try:
            btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[normalize-space(text())='Siguiente']")
                )
            )
            btn.click()
            logger.info("Clicked Siguiente (text match)")
            clicked = True
        except TimeoutException:
            pass

    if not clicked:
        logger.warning("Siguiente button not found")
        return False

    if wait_for:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
            )
        except TimeoutException:
            logger.warning(f"Element '{wait_for}' did not appear after Siguiente")

    return True


def get_first_available_date(driver, timeout=5):
    """Wait for calendar, click the first available date, return DD/MM string."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "td.disponible"))
        )
    except TimeoutException:
        logger.warning("No available dates in calendar")
        return None

    headers = driver.find_elements(By.CSS_SELECTOR, "th.datepicker-switch")
    month_year = ""
    for h in headers:
        if h.is_displayed() and h.text.strip():
            month_year = h.text.strip()
            break

    month_num = "??"
    year = "????"
    if month_year:
        parts = month_year.split()
        if len(parts) == 2:
            month_abbr = parts[0].lower()[:3]
            month_num = MONTH_MAP.get(month_abbr, "??")
            year = parts[1]

    cells = driver.find_elements(By.CSS_SELECTOR, "td.disponible")
    for cell in cells:
        if cell.is_displayed():
            day = cell.text.strip()
            driver.execute_script("arguments[0].scrollIntoView(true);", cell)
            driver.execute_script("arguments[0].click();", cell)
            logger.info(f"Clicked available date: {day}/{month_num}/{year}")
            time.sleep(0.5)
            return f"{day.zfill(2)}/{month_num}"

    logger.warning("Available date cells found but none clickable")
    return None


def get_first_available_time(driver, timeout=5):
    """After a date is clicked, read the first available time slot."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.horario button"))
        )
    except TimeoutException:
        logger.warning("No time slots appeared after date click")
        return None

    buttons = driver.find_elements(By.CSS_SELECTOR, "div.horario button")
    for btn in buttons:
        text = btn.text.strip()
        if text and ":" in text and len(text) <= 5:
            logger.info(f"First available time: {text}")
            return text

    logger.warning("Time slot buttons found but no valid time text")
    return None


def get_page_text(driver):
    """Get the page text content."""
    return driver.find_element(By.TAG_NAME, "body").text.lower()
