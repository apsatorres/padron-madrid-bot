#!/usr/bin/env python3
"""
Debug: Prueba la conexion a la pagina de Madrid.
Ejecutar: python tests/debug_connection.py
"""

from src.config import URL_CITAS
from src.browser import crear_driver, guardar_screenshot

print(f"Conectando a: {URL_CITAS}")
print("-" * 50)

try:
    with crear_driver() as driver:
        driver.get(URL_CITAS)

        print(f"Titulo: {driver.title}")
        print(f"URL actual: {driver.current_url}")

        screenshot = guardar_screenshot(driver, "_debug_connection")
        print(f"Screenshot: {screenshot}")

        print("\nConexion exitosa!")

except Exception as e:
    print(f"\nERROR: {e}")
