#!/usr/bin/env python3
"""
Debug: Test connection to the Madrid page.
Run: python tests/debug_connection.py
"""

from src.config import APPOINTMENTS_URL
from src.browser import create_driver, save_screenshot

print(f"Connecting to: {APPOINTMENTS_URL}")
print("-" * 50)

try:
    with create_driver() as driver:
        driver.get(APPOINTMENTS_URL)

        print(f"Title: {driver.title}")
        print(f"Current URL: {driver.current_url}")

        screenshot = save_screenshot(driver, "_debug_connection")
        print(f"Screenshot: {screenshot}")

        print("\nConnection successful!")

except Exception as e:
    print(f"\nERROR: {e}")
