#!/usr/bin/env python3
"""
Debug: Run the full verification flow.
Run: python tests/debug_verificacion.py
"""

from src.checker import (
    check_appointments,
    NO_APPOINTMENTS_INDICATORS,
    YES_APPOINTMENTS_INDICATORS
)

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
print("CONFIGURED INDICATORS:")
print("-" * 60)
print("NO appointments if found:")
for ind in NO_APPOINTMENTS_INDICATORS:
    print(f"  - {ind}")

print("\nYES appointments if found:")
for ind in YES_APPOINTMENTS_INDICATORS:
    print(f"  - {ind}")
