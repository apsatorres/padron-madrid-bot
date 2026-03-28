#!/usr/bin/env python3
"""
Debug: Explore the Madrid page form.
Shows all selectors and their options.
Run: python tests/debug_formulario.py
"""

import os
import sys
import time

# Run from project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from selenium.webdriver.support.ui import Select

from src.config import APPOINTMENTS_URL, CATEGORY_SEARCH, PROCEDURE_SEARCH
from src.browser import (
    create_driver, save_screenshot, find_selects,
    select_option_by_text, click_unidentified_access,
    click_earliest_appointment_link
)

print(f"Navigating to: {APPOINTMENTS_URL}")
print("=" * 60)

try:
    with create_driver() as driver:
        driver.get(APPOINTMENTS_URL)
        time.sleep(3)
        click_unidentified_access(driver)
        time.sleep(2)

        # Show all selects
        selects = find_selects(driver)
        print(f"\nFound {len(selects)} selectors:\n")

        for i, sel in enumerate(selects):
            try:
                select_obj = Select(sel)
                options = [
                    (opt.text or opt.get_attribute("label") or "").strip()
                    for opt in select_obj.options
                ]
                print(f"SELECT {i}:")
                for j, opt in enumerate(options):
                    print(f"  [{j}] {opt}")
                print()
            except Exception as e:
                print(f"SELECT {i}: Error - {e}\n")

        save_screenshot(driver, "_debug_form_initial")

        # Debug: show select element details
        print("-" * 60)
        print("SELECT ELEMENT DETAILS:")
        for i, sel in enumerate(selects):
            sel_id = sel.get_attribute("id")
            sel_name = sel.get_attribute("name")
            print(f"  Select {i}: id='{sel_id}' name='{sel_name}'")

        # Debug: show what's around the first select
        print("\nHTML around selectCategorias:")
        html = driver.execute_script(
            "return document.getElementById('selectCategorias').parentElement.innerHTML.substring(0, 500);"
        )
        print(html)

        # Debug: show Select2 containers
        select2_containers = driver.find_elements(
            "css selector", "span.select2-selection"
        )
        print(f"\nFound {len(select2_containers)} Select2 containers")

        # Check for other common widget patterns
        for pattern in ["span.select2", "div.select2", "span[class*='select']"]:
            found = driver.find_elements("css selector", pattern)
            print(f"Found {len(found)} elements matching '{pattern}'")

        # Try to select category
        print("-" * 60)
        print(f"Trying to select category: '{CATEGORY_SEARCH}'")

        if selects:
            category_select = Select(selects[0])
            if select_option_by_text(category_select, CATEGORY_SEARCH, driver):
                print("OK - Category selected")
                time.sleep(2)

                # Check if new options appeared
                selects = find_selects(driver)
                print(f"\nAfter selecting category: {len(selects)} selectors")

                if len(selects) > 1:
                    procedure_select = Select(selects[1])
                    procedure_options = [
                        (opt.text or opt.get_attribute("label") or "").strip()
                        for opt in procedure_select.options
                    ]
                    print(f"\nProcedure options:")
                    for j, opt in enumerate(procedure_options):
                        print(f"  [{j}] {opt}")

                    # Try to select procedure
                    print(f"\nTrying to select procedure: '{PROCEDURE_SEARCH}'")
                    if select_option_by_text(procedure_select, PROCEDURE_SEARCH, driver):
                        print("OK - Procedure selected")
                        time.sleep(2)
                        save_screenshot(driver, "_debug_form_selected")

                        # Try to click "cita más temprana" link
                        print("\n" + "-" * 60)
                        print("Trying to click 'cita más temprana' link...")
                        if click_earliest_appointment_link(driver):
                            print("OK - Link clicked")
                            time.sleep(3)
                            save_screenshot(driver, "_debug_form_result")
                        else:
                            print("ERROR - Link not found")
            else:
                print(f"ERROR - Category '{CATEGORY_SEARCH}' not found")

        # Show page text
        print("\n" + "=" * 60)
        print("PAGE TEXT (first 1000 chars):")
        print("-" * 60)
        body_text = driver.find_element("tag name", "body").text
        print(body_text[:1000])

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
