"""Appointment checking logic."""

import time

from .config import (
    logger, APPOINTMENTS_URL, CATEGORY_SEARCH, PROCEDURE_SEARCH
)
from .browser import (
    create_driver, save_screenshot,
    click_unidentified_access, click_earliest_appointment_link,
    get_page_text, select_combobox_option,
    verify_combobox_selection, wait_for_procedure_options,
    get_combobox_state
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
    "citas disponibles",
    "seleccione una fecha",
    "horarios disponibles",
    "elegir cita",
    "reservar cita",
    "fechas disponibles"
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
    Navigate the form by selecting category and procedure via combobox inputs.
    Uses explicit element IDs and verifies each step before proceeding.
    Returns True if successful.
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

    # Log final state before attempting link click
    cat_state = get_combobox_state(driver, CATEGORY_INPUT_ID, CATEGORY_SELECT_ID)
    proc_state = get_combobox_state(driver, PROCEDURE_INPUT_ID, PROCEDURE_SELECT_ID)
    logger.info(
        f"Pre-link state: category={cat_state}, procedure={proc_state}"
    )

    # Step 4: Click earliest appointment link
    if click_earliest_appointment_link(driver):
        time.sleep(3)
        return True

    logger.warning("Could not click on 'cita más temprana' link")
    save_screenshot(driver, "_link_fail")
    return False


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
                time.sleep(3)

                click_unidentified_access(driver)
                time.sleep(2)

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

            # Initial screenshot
            screenshot_path = save_screenshot(driver)

            # Navigate the form
            if _navigate_form(driver):
                save_screenshot(driver, "_result")

            # Analyze result
            page_text = get_page_text(driver)
            has_appointments, indicator = _analyze_availability(page_text)

            if has_appointments is True:
                message = f"APPOINTMENTS AVAILABLE! Detected: '{indicator}'"
                logger.info(message)
            elif has_appointments is False:
                message = f"No appointments available. Detected: '{indicator}'"
                logger.info(message)
            else:
                message = f"Uncertain status. Check manually: {APPOINTMENTS_URL}"
                logger.warning(message)

            return has_appointments, message, screenshot_path

    except Exception as e:
        logger.error(f"Error checking appointments: {e}")
        return None, f"Error: {str(e)}", screenshot_path
