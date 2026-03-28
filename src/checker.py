"""Appointment checking logic."""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .config import (
    logger, APPOINTMENTS_URL, CATEGORY_SEARCH, PROCEDURE_SEARCH
)
from .browser import (
    create_driver, save_screenshot,
    click_unidentified_access, click_earliest_appointment_link,
    get_page_text, select_combobox_option,
    verify_combobox_selection, wait_for_procedure_options,
    get_combobox_state, get_selected_office, click_siguiente,
    get_first_available_date, get_first_available_time
)

CATEGORY_INPUT_ID = "cpTramite_combo0"
CATEGORY_SELECT_ID = "selectCategorias"
PROCEDURE_INPUT_ID = "cpTramite_combo1"
PROCEDURE_SELECT_ID = "selectTramites"

# Availability indicators (Spanish - must match website text)
NO_APPOINTMENTS_INDICATORS = [
    "no hay citas disponibles",
    "no existen citas",
    "sin disponibilidad",
    "no quedan citas",
    "agotadas",
    "no hay huecos",
    "actualmente no hay",
    "no se pueden solicitar citas",
    "no hay turnos disponibles",
    "no se ha encontrado hueco disponible"
]

YES_APPOINTMENTS_INDICATORS = [
    "seleccione una fecha disponible",
    "seleccione una hora disponible",
    "elija una de las fechas y horas disponibles",
]

CONNECTION_ERROR_INDICATORS = [
    "err_connection_closed",
    "this site can't be reached",
    "this site cant be reached",
    "se ha cerrado la conexion",
    "se ha cerrado la conexión",
]


def _analyze_availability(page_text):
    """
    Analyze page text to detect availability.
    Returns: (has_appointments: bool|None, indicator: str)
    """
    for indicator in NO_APPOINTMENTS_INDICATORS:
        if indicator in page_text:
            return False, indicator

    for indicator in YES_APPOINTMENTS_INDICATORS:
        if indicator in page_text:
            return True, indicator

    return None, "no clear indicators found"


def _navigate_form(driver):
    """
    Navigate the form, select category/procedure, click earliest appointment,
    and if available, extract office/date/time details.

    Returns:
        dict with keys {office, date, time} if appointment details found,
        True if form navigated but no detail extraction possible,
        False if navigation failed.
    """
    # Step 1: Select category
    logger.info(f"Selecting category: '{CATEGORY_SEARCH}'")
    if not select_combobox_option(
        driver, CATEGORY_INPUT_ID, CATEGORY_SELECT_ID, CATEGORY_SEARCH
    ):
        logger.warning(f"Failed to select category '{CATEGORY_SEARCH}'")
        save_screenshot(driver, "_category_fail")
        return False

    # Step 2: Wait for procedure options to repopulate after category change
    logger.info("Waiting for procedure options to load...")
    if not wait_for_procedure_options(
        driver, PROCEDURE_SELECT_ID, PROCEDURE_SEARCH, timeout=10
    ):
        logger.warning("Procedure options did not load after category selection")
        save_screenshot(driver, "_procedure_wait_fail")
        return False

    # Step 3: Select procedure
    logger.info(f"Selecting procedure: '{PROCEDURE_SEARCH}'")
    if not select_combobox_option(
        driver, PROCEDURE_INPUT_ID, PROCEDURE_SELECT_ID, PROCEDURE_SEARCH
    ):
        logger.warning(f"Failed to select procedure '{PROCEDURE_SEARCH}'")
        save_screenshot(driver, "_procedure_fail")
        return False

    # Step 4: Click earliest appointment link
    if not click_earliest_appointment_link(driver):
        logger.warning("Could not click on 'cita más temprana' link")
        save_screenshot(driver, "_link_fail")
        return False

    # Wait for page to settle: either no-appointment text or office populated
    try:
        WebDriverWait(driver, 10).until(
            lambda d: (
                any(ind in d.find_element(By.TAG_NAME, "body").text.lower()
                    for ind in NO_APPOINTMENTS_INDICATORS)
                or (d.find_elements(By.ID, "cpTramite_combo2")
                    and d.find_element(By.ID, "cpTramite_combo2").get_attribute("value")
                    and d.find_element(By.ID, "cpTramite_combo2").get_attribute("value")
                    != "-- Seleccione o teclee --")
            )
        )
    except TimeoutException:
        logger.warning("Page did not settle after 'cita más temprana' click")

    page_text = get_page_text(driver)
    for ind in NO_APPOINTMENTS_INDICATORS:
        if ind in page_text:
            logger.info(f"No appointments after link click: '{ind}'")
            return True

    # Step 5: Extract appointment details
    office = get_selected_office(driver)
    logger.info(f"Office: {office}")

    if not click_siguiente(driver, wait_for=".datepicker"):
        logger.warning("Could not click Siguiente after office selection")
        save_screenshot(driver, "_siguiente_fail")
        return True

    date_str = get_first_available_date(driver)
    if not date_str:
        logger.warning("No available date found in calendar")
        save_screenshot(driver, "_calendar_fail")
        return True

    time_str = get_first_available_time(driver)
    if not time_str:
        logger.warning("No time slots found after date click")
        save_screenshot(driver, "_timeslot_fail")
        return True

    details = {"office": office, "date": date_str, "time": time_str}
    logger.info(f"Appointment details: {details}")
    return details


def check_appointments():
    """
    Check appointment availability.

    Returns:
        tuple: (has_appointments: bool|None, message: str, screenshot_path: str|None)
            - has_appointments: True if available, False if not, None if uncertain
            - message: Result description
            - screenshot_path: Path to captured screenshot
    """
    screenshot_path = None

    try:
        logger.info("Starting appointment check...")

        with create_driver() as driver:
            # Navigate to page and pass initial landing
            access_ok = False
            for attempt in range(1, 4):
                logger.info(f"Navigating to {APPOINTMENTS_URL} (attempt {attempt}/3)")
                driver.get(APPOINTMENTS_URL)

                click_unidentified_access(driver)

                try:
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located((By.ID, CATEGORY_INPUT_ID))
                    )
                except TimeoutException:
                    logger.warning("Form did not load after access click.")

                page_text = get_page_text(driver)
                if any(err in page_text for err in CONNECTION_ERROR_INDICATORS):
                    logger.warning("Connection error detected after initial access.")
                    continue

                access_ok = True
                break

            if not access_ok:
                message = (
                    "Could not load website correctly after 3 attempts. "
                    "Check connection or temporary site block."
                )
                logger.warning(message)
                return None, message, screenshot_path

            # Navigate the form and extract details
            result = _navigate_form(driver)

            if isinstance(result, dict):
                office = result.get("office", "?")
                date = result.get("date", "?")
                appt_time = result.get("time", "?")
                message = (
                    f"Cita mas cercana en {office}, "
                    f"{date} a las {appt_time}"
                )
                logger.info(message)
                screenshot_path = save_screenshot(driver, "_available")
                return True, message, screenshot_path

            # No details extracted -- fall back to page text analysis
            page_text = get_page_text(driver)
            has_appointments, indicator = _analyze_availability(page_text)

            if has_appointments is True:
                message = f"APPOINTMENTS AVAILABLE! Detected: '{indicator}'"
                logger.info(message)
                screenshot_path = save_screenshot(driver, "_available")
            elif has_appointments is False:
                message = f"No appointments available. Detected: '{indicator}'"
                logger.info(message)
            else:
                message = f"Uncertain status. Check manually: {APPOINTMENTS_URL}"
                logger.warning(message)
                screenshot_path = save_screenshot(driver, "_uncertain")

            return has_appointments, message, screenshot_path

    except Exception as e:
        logger.error(f"Error checking appointments: {e}")
        return None, f"Error: {str(e)}", screenshot_path
