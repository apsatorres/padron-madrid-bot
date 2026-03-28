#!/usr/bin/env python3
"""
Debug: Explore the Madrid page form via jQuery UI combobox interaction.
Shows combobox state (visible input + hidden select) after each step.
Run: python tests/debug_formulario.py
"""

import os
import sys
import time

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from src.config import APPOINTMENTS_URL, CATEGORY_SEARCH, PROCEDURE_SEARCH
from src.browser import (
    create_driver, save_screenshot, find_selects,
    click_unidentified_access, click_earliest_appointment_link,
    select_combobox_option, get_combobox_state,
    verify_combobox_selection, wait_for_procedure_options,
    _get_option_text,
)

CATEGORY_INPUT_ID = "cpTramite_combo0"
CATEGORY_SELECT_ID = "selectCategorias"
PROCEDURE_INPUT_ID = "cpTramite_combo1"
PROCEDURE_SELECT_ID = "selectTramites"


def print_combobox_state(driver, label, input_id, select_id):
    state = get_combobox_state(driver, input_id, select_id)
    if state:
        print(f"  [{label}] input_value = '{state.get('input_value', '')}'")
        print(f"  [{label}] select_value = {state.get('select_value', '?')}")
        print(f"  [{label}] select_text  = '{state.get('select_text', '')}'")
        print(f"  [{label}] option_count = {state.get('option_count', '?')}")
    else:
        print(f"  [{label}] Could not read state")
    return state


def print_select_options(driver, select_id, label, max_show=10):
    try:
        el = driver.find_element(By.ID, select_id)
        sel = Select(el)
        options = [_get_option_text(o) for o in sel.options]
        print(f"\n  {label} ({len(options)} options):")
        for i, opt in enumerate(options[:max_show]):
            print(f"    [{i}] {opt}")
        if len(options) > max_show:
            print(f"    ... and {len(options) - max_show} more")
    except Exception as e:
        print(f"  Could not read #{select_id}: {e}")


print(f"Navigating to: {APPOINTMENTS_URL}")
print("=" * 60)

try:
    with create_driver() as driver:
        driver.get(APPOINTMENTS_URL)
        time.sleep(3)
        click_unidentified_access(driver)
        time.sleep(2)

        save_screenshot(driver, "_debug_initial")

        # Show all selects
        selects = find_selects(driver)
        print(f"\nFound {len(selects)} <select> elements:")
        for i, sel in enumerate(selects):
            sel_id = sel.get_attribute("id")
            sel_name = sel.get_attribute("name")
            displayed = sel.is_displayed()
            print(f"  [{i}] id='{sel_id}' name='{sel_name}' displayed={displayed}")

        # Show combobox inputs
        print("\nCombobox visible inputs:")
        for cid in [CATEGORY_INPUT_ID, PROCEDURE_INPUT_ID]:
            els = driver.find_elements(By.ID, cid)
            if els:
                e = els[0]
                print(
                    f"  #{cid}: displayed={e.is_displayed()}, "
                    f"value='{e.get_attribute('value')}'"
                )
            else:
                print(f"  #{cid}: NOT FOUND")

        # Initial state
        print("\n" + "-" * 60)
        print("INITIAL STATE:")
        print_combobox_state(driver, "category", CATEGORY_INPUT_ID, CATEGORY_SELECT_ID)
        print_combobox_state(driver, "procedure", PROCEDURE_INPUT_ID, PROCEDURE_SELECT_ID)
        print_select_options(driver, CATEGORY_SELECT_ID, "Category options")
        print_select_options(driver, PROCEDURE_SELECT_ID, "Procedure options (before category)")

        # Step 1: Select category
        print("\n" + "=" * 60)
        print(f"STEP 1: Selecting category '{CATEGORY_SEARCH}'...")
        ok = select_combobox_option(
            driver, CATEGORY_INPUT_ID, CATEGORY_SELECT_ID, CATEGORY_SEARCH
        )
        print(f"  Result: {'OK' if ok else 'FAILED'}")
        print("\n  State after category selection:")
        print_combobox_state(driver, "category", CATEGORY_INPUT_ID, CATEGORY_SELECT_ID)

        if not ok:
            save_screenshot(driver, "_debug_category_fail")
            print("  Screenshot saved. Aborting.")
        else:
            # Step 2: Wait for procedure options
            print("\n" + "=" * 60)
            print(f"STEP 2: Waiting for procedure options containing '{PROCEDURE_SEARCH}'...")
            loaded = wait_for_procedure_options(
                driver, PROCEDURE_SELECT_ID, PROCEDURE_SEARCH, timeout=10
            )
            print(f"  Result: {'OK' if loaded else 'TIMED OUT'}")
            print_select_options(driver, PROCEDURE_SELECT_ID, "Procedure options (after category)")

            if not loaded:
                save_screenshot(driver, "_debug_procedure_wait_fail")
                print("  Screenshot saved. Aborting.")
            else:
                # Step 3: Select procedure
                print("\n" + "=" * 60)
                print(f"STEP 3: Selecting procedure '{PROCEDURE_SEARCH}'...")
                ok2 = select_combobox_option(
                    driver, PROCEDURE_INPUT_ID, PROCEDURE_SELECT_ID, PROCEDURE_SEARCH
                )
                print(f"  Result: {'OK' if ok2 else 'FAILED'}")
                print("\n  State after procedure selection:")
                print_combobox_state(driver, "procedure", PROCEDURE_INPUT_ID, PROCEDURE_SELECT_ID)
                save_screenshot(driver, "_debug_after_selections")

                if not ok2:
                    save_screenshot(driver, "_debug_procedure_fail")
                    print("  Screenshot saved. Aborting.")
                else:
                    # Step 4: Click earliest appointment link
                    print("\n" + "=" * 60)
                    print("STEP 4: Clicking 'cita más temprana' link...")
                    ok3 = click_earliest_appointment_link(driver)
                    print(f"  Result: {'OK' if ok3 else 'LINK NOT FOUND'}")
                    if ok3:
                        time.sleep(3)
                        save_screenshot(driver, "_debug_result")
                    else:
                        save_screenshot(driver, "_debug_link_fail")

        # Final page text
        print("\n" + "=" * 60)
        print("PAGE TEXT (first 1500 chars):")
        print("-" * 60)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(body_text[:1500])

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
