#!/usr/bin/env python3
"""
Debug: Ejecuta el flujo completo de verificacion.
Ejecutar: python tests/debug_verificacion.py
"""

from src.checker import verificar_citas, NO_CITAS_INDICADORES, SI_CITAS_INDICADORES

print("Ejecutando verificacion completa...")
print("=" * 60)

hay_citas, mensaje, screenshot = verificar_citas()

print("\n" + "=" * 60)
print("RESULTADO:")
print("-" * 60)

if hay_citas is True:
    print("HAY CITAS DISPONIBLES!")
elif hay_citas is False:
    print("No hay citas disponibles")
else:
    print("Estado incierto - revisar manualmente")

print(f"\nMensaje: {mensaje}")
print(f"Screenshot: {screenshot}")

print("\n" + "=" * 60)
print("INDICADORES CONFIGURADOS:")
print("-" * 60)
print("NO hay citas si aparece:")
for ind in NO_CITAS_INDICADORES:
    print(f"  - {ind}")

print("\nSI hay citas si aparece:")
for ind in SI_CITAS_INDICADORES:
    print(f"  - {ind}")
