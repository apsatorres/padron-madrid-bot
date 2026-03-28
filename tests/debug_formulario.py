#!/usr/bin/env python3
"""
Debug: Explora el formulario de la pagina de Madrid.
Muestra todos los selectores y sus opciones.
Ejecutar: python tests/debug_formulario.py
"""

import time
from selenium.webdriver.support.ui import Select

from src.config import URL_CITAS, CATEGORIA_BUSCAR, TRAMITE_BUSCAR
from src.browser import (
    crear_driver, guardar_screenshot, encontrar_selects,
    seleccionar_opcion_por_texto
)

print(f"Navegando a: {URL_CITAS}")
print("=" * 60)

try:
    with crear_driver() as driver:
        driver.get(URL_CITAS)
        time.sleep(3)

        # Mostrar todos los selects
        selects = encontrar_selects(driver)
        print(f"\nEncontrados {len(selects)} selectores:\n")

        for i, sel in enumerate(selects):
            try:
                select_obj = Select(sel)
                opciones = [opt.text for opt in select_obj.options]
                print(f"SELECT {i}:")
                for j, opt in enumerate(opciones):
                    print(f"  [{j}] {opt}")
                print()
            except Exception as e:
                print(f"SELECT {i}: Error - {e}\n")

        guardar_screenshot(driver, "_debug_form_inicial")

        # Intentar seleccionar categoria
        print("-" * 60)
        print(f"Intentando seleccionar categoria: '{CATEGORIA_BUSCAR}'")

        if selects:
            select_categoria = Select(selects[0])
            if seleccionar_opcion_por_texto(select_categoria, CATEGORIA_BUSCAR):
                print("OK - Categoria seleccionada")
                time.sleep(2)

                # Ver si aparecieron nuevas opciones
                selects = encontrar_selects(driver)
                print(f"\nDespues de seleccionar categoria: {len(selects)} selectores")

                if len(selects) > 1:
                    select_tramite = Select(selects[1])
                    opciones_tramite = [opt.text for opt in select_tramite.options]
                    print(f"\nOpciones de tramite:")
                    for j, opt in enumerate(opciones_tramite):
                        print(f"  [{j}] {opt}")

                    # Intentar seleccionar tramite
                    print(f"\nIntentando seleccionar tramite: '{TRAMITE_BUSCAR}'")
                    if seleccionar_opcion_por_texto(select_tramite, TRAMITE_BUSCAR):
                        print("OK - Tramite seleccionado")
                        time.sleep(2)
                        guardar_screenshot(driver, "_debug_form_seleccionado")
            else:
                print(f"ERROR - No se encontro '{CATEGORIA_BUSCAR}'")

        # Mostrar texto de la pagina
        print("\n" + "=" * 60)
        print("TEXTO DE LA PAGINA (primeros 1000 chars):")
        print("-" * 60)
        body_text = driver.find_element("tag name", "body").text
        print(body_text[:1000])

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
