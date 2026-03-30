"""Appointment checking logic."""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .config import logger, APPOINTMENTS_URL
from .browser import (
    create_driver, save_screenshot,
    click_unidentified_access, click_earliest_appointment_link,
    get_page_text, select_combobox_option,
    wait_for_procedure_options, get_selected_office,
    click_siguiente, get_first_available_date,
    get_first_available_time, select_office
)

CATEGORY_INPUT_ID = "cpTramite_combo0"
CATEGORY_SELECT_ID = "selectCategorias"
PROCEDURE_INPUT_ID = "cpTramite_combo1"
PROCEDURE_SELECT_ID = "selectTramites"

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
    """Analyze page text to detect availability."""
    for indicator in NO_APPOINTMENTS_INDICATORS:
        if indicator in page_text:
            return False, indicator

    for indicator in YES_APPOINTMENTS_INDICATORS:
        if indicator in page_text:
            return True, indicator

    return None, "no clear indicators found"


def _load_page_and_access(driver):
    """Navigate to the site and click through the access gate."""
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

        return True

    return False


def _select_category_and_procedure(driver, category, procedure):
    """Select category and procedure in the form."""
    logger.info(f"Selecting category: '{category}'")
    if not select_combobox_option(
        driver, CATEGORY_INPUT_ID, CATEGORY_SELECT_ID, category
    ):
        logger.warning(f"Failed to select category '{category}'")
        save_screenshot(driver, "_category_fail")
        return False

    logger.info("Waiting for procedure options to load...")
    if not wait_for_procedure_options(
        driver, PROCEDURE_SELECT_ID, procedure, timeout=10
    ):
        logger.warning("Procedure options did not load after category selection")
        save_screenshot(driver, "_procedure_wait_fail")
        return False

    logger.info(f"Selecting procedure: '{procedure}'")
    if not select_combobox_option(
        driver, PROCEDURE_INPUT_ID, PROCEDURE_SELECT_ID, procedure
    ):
        logger.warning(f"Failed to select procedure '{procedure}'")
        save_screenshot(driver, "_procedure_fail")
        return False

    return True


def _extract_date_and_time(driver):
    """From the calendar/time page, extract first available date and time."""
    date_str = get_first_available_date(driver)
    if not date_str:
        return None

    time_str = get_first_available_time(driver)
    if not time_str:
        return None

    return {"date": date_str, "time": time_str}


def _try_office(driver, office_name):
    """Select a specific office, click Siguiente, extract date/time."""
    if not select_office(driver, office_name):
        logger.info(f"Could not select office '{office_name}'")
        return None

    if not click_siguiente(driver, wait_for=".datepicker"):
        logger.warning(f"Siguiente failed after selecting '{office_name}'")
        return None

    result = _extract_date_and_time(driver)
    if result:
        result["office"] = office_name
        logger.info(f"Found appointment at {office_name}: {result}")
        return result

    logger.info(f"No available dates/times at '{office_name}'")
    return None


def _try_earliest_appointment(driver):
    """Click 'cita más temprana' and extract appointment details."""
    if not click_earliest_appointment_link(driver):
        logger.warning("Could not click on 'cita más temprana' link")
        save_screenshot(driver, "_link_fail")
        return None

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
            logger.info(f"No appointments via 'cita más temprana': '{ind}'")
            return None

    office = get_selected_office(driver)
    logger.info(f"Earliest appointment office: {office}")

    if not click_siguiente(driver, wait_for=".datepicker"):
        logger.warning("Could not click Siguiente after 'cita más temprana'")
        return None

    result = _extract_date_and_time(driver)
    if result:
        result["office"] = office
        return result

    return None


def check_appointments(category, procedure, preferred_offices=None):
    """
    Check appointment availability for a specific category/procedure.

    Args:
        category: Category name (e.g. "Padrón y censo")
        procedure: Procedure name (e.g. "Altas, bajas y cambio de domicilio en Padrón")
        preferred_offices: Optional list of office names to try first

    Returns:
        tuple: (has_appointments: bool|None, message: str, screenshot_path: str|None)
    """
    preferred = preferred_offices or []
    screenshot_path = None

    try:
        logger.info(f"Checking: {category} / {procedure}")

        with create_driver() as driver:
            if not _load_page_and_access(driver):
                message = (
                    "Could not load website correctly after 3 attempts. "
                    "Check connection or temporary site block."
                )
                logger.warning(message)
                return None, message, screenshot_path

            if not _select_category_and_procedure(driver, category, procedure):
                return False, "Failed to select category/procedure", screenshot_path

            # Try preferred offices first
            for office_name in preferred:
                result = _try_office(driver, office_name)
                if result:
                    message = (
                        f"Trámite: {category} / {procedure}\n\n"
                        f"Cita mas cercana en {result['office']}, "
                        f"{result['date']} a las {result['time']}"
                    )
                    logger.info(message)
                    screenshot_path = save_screenshot(driver, "_available")
                    return True, message, screenshot_path

                logger.info(f"No appointments at '{office_name}', going back...")
                driver.back()
                try:
                    WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located(
                            (By.ID, "cpTramite_combo2")
                        )
                    )
                except TimeoutException:
                    logger.warning("Back navigation failed, reloading page...")
                    if not _load_page_and_access(driver):
                        break
                    if not _select_category_and_procedure(driver, category, procedure):
                        break

            # Fallback: cita más temprana
            logger.info("Trying 'cita más temprana' fallback...")

            result = _try_earliest_appointment(driver)
            if result:
                fallback_note = ""
                if preferred:
                    fallback_note = "\n(ninguna oficina preferida disponible)"
                message = (
                    f"Trámite: {category} / {procedure}\n\n"
                    f"Cita mas cercana en {result['office']}, "
                    f"{result['date']} a las {result['time']}"
                    f"{fallback_note}"
                )
                logger.info(message)
                screenshot_path = save_screenshot(driver, "_available")
                return True, message, screenshot_path

            # No appointments anywhere
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
