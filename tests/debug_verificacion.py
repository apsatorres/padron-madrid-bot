#!/usr/bin/env python3
"""
Debug: Run the full verification flow.
Run: python tests/debug_verificacion.py
"""

import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from src.checker import check_appointments, NO_APPOINTMENTS_INDICATORS

print("Running full verification...")
print("=" * 60)

has_appointments, message, screenshot = check_appointments()

print("\n" + "=" * 60)
print("RESULT:")
print("-" * 60)

if has_appointments is True:
    print("APPOINTMENTS AVAILABLE!")
elif has_appointments is False:
    print("No appointments available")
else:
    print("Uncertain status - check manually")

print(f"\nMessage: {message}")
print(f"Screenshot: {screenshot}")

print("\n" + "=" * 60)
print("DETECTION METHOD:")
print("-" * 60)
print("Primary: navigate office -> calendar -> time slots")
print("Fallback: scan page text for indicators")
print("\nNO appointments if page text contains:")
for ind in NO_APPOINTMENTS_INDICATORS:
    print(f"  - {ind}")
