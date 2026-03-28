"""Logica de verificacion de citas."""

import time
from selenium.webdriver.support.ui import Select

from .config import (
    logger, URL_CITAS, CATEGORIA_BUSCAR, TRAMITE_BUSCAR
)
from .browser import (
    crear_driver, guardar_screenshot, seleccionar_opcion_por_texto,
    encontrar_selects, log_opciones_select, click_boton_buscar,
    click_acceso_sin_identificar, click_consultar_cita_temprana,
    obtener_texto_pagina
)

# Indicadores de disponibilidad
NO_CITAS_INDICADORES = [
    "no hay citas disponibles",
    "no existen citas",
    "sin disponibilidad",
    "no quedan citas",
    "agotadas",
    "no hay huecos",
    "actualmente no hay",
    "no se pueden solicitar citas",
    "no hay turnos disponibles",
    "no se ha encontrado hueco disponible"]

SI_CITAS_INDICADORES = [
    "citas disponibles",
    "seleccione una fecha",
    "horarios disponibles",
    "elegir cita",
    "reservar cita",
    "fechas disponibles"
]

ERRORES_CONEXION_INDICADORES = [
    "err_connection_closed",
    "this site can't be reached",
    "this site cant be reached",
    "se ha cerrado la conexion",
    "se ha cerrado la conexión",
]


def _analizar_disponibilidad(page_text):
    """
    Analiza el texto de la pagina para detectar disponibilidad.
    Retorna: (hay_citas: bool|None, indicador: str)
    """
    for indicador in NO_CITAS_INDICADORES:
        if indicador in page_text:
            return False, indicador

    for indicador in SI_CITAS_INDICADORES:
        if indicador in page_text:
            return True, indicador

    return None, "no se encontraron indicadores claros"


def _navegar_formulario(driver):
    """
    Navega el formulario seleccionando categoria y tramite.
    Retorna True si tuvo exito.
    """
    all_selects = encontrar_selects(driver)

    if not all_selects:
        log_opciones_select(driver)
        return False

    # Seleccionar categoria (primer select)
    categoria_select = Select(all_selects[0])
    if not seleccionar_opcion_por_texto(categoria_select, CATEGORIA_BUSCAR):
        logger.warning(f"No se encontro categoria con '{CATEGORIA_BUSCAR}'")
        return False

    time.sleep(2)

    # Buscar de nuevo los selects (pueden haber cambiado)
    all_selects = encontrar_selects(driver)
    if len(all_selects) < 2:
        logger.warning("No se encontro selector de tramite")
        return False

    # Seleccionar tramite (segundo select)
    tramite_select = Select(all_selects[1])
    if not seleccionar_opcion_por_texto(tramite_select, TRAMITE_BUSCAR):
        logger.warning(f"No se encontro tramite con '{TRAMITE_BUSCAR}'")
        return False

    time.sleep(2)

    # Hacer click en buscar
    click_boton_buscar(driver)
    time.sleep(3)

    return True


def verificar_citas():
    """
    Verifica la disponibilidad de citas.

    Retorna:
        tuple: (hay_citas: bool|None, mensaje: str, screenshot_path: str|None)
            - hay_citas: True si hay, False si no, None si incierto
            - mensaje: Descripcion del resultado
            - screenshot_path: Path al screenshot capturado
    """
    screenshot_path = None

    try:
        logger.info("Iniciando verificacion de citas...")

        with crear_driver() as driver:
            # Navegar a la pagina y superar la portada inicial
            acceso_ok = False
            for intento in range(1, 4):
                logger.info(f"Navegando a {URL_CITAS} (intento {intento}/3)")
                driver.get(URL_CITAS)
                time.sleep(3)

                click_acceso_sin_identificar(driver)
                time.sleep(2)

                page_text = obtener_texto_pagina(driver)
                if any(err in page_text for err in ERRORES_CONEXION_INDICADORES):
                    logger.warning("Error de conexion detectado tras el acceso inicial.")
                    continue

                acceso_ok = True
                break

            if not acceso_ok:
                mensaje = (
                    "No se pudo cargar correctamente la web tras 3 intentos. "
                    "Revisar conexion o bloqueo temporal del sitio."
                )
                logger.warning(mensaje)
                return None, mensaje, screenshot_path

            # Screenshot inicial
            screenshot_path = guardar_screenshot(driver)

            # Navegar el formulario
            if _navegar_formulario(driver):
                guardar_screenshot(driver, "_resultado")

            # Analizar resultado
            page_text = obtener_texto_pagina(driver)
            hay_citas, indicador = _analizar_disponibilidad(page_text)

            if hay_citas is True:
                mensaje = f"HAY CITAS DISPONIBLES! Detectado: '{indicador}'"
                logger.info(mensaje)
            elif hay_citas is False:
                mensaje = f"No hay citas disponibles. Detectado: '{indicador}'"
                logger.info(mensaje)
            else:
                mensaje = f"Estado incierto. Revisar manualmente: {URL_CITAS}"
                logger.warning(mensaje)

            return hay_citas, mensaje, screenshot_path

    except Exception as e:
        logger.error(f"Error verificando citas: {e}")
        return None, f"Error: {str(e)}", screenshot_path
