from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_RUTA_ESTILOS = Path(__file__).resolve().parent


def _leer_plantilla(nombre_archivo: str) -> str:
    ruta = _RUTA_ESTILOS / nombre_archivo
    try:
        return ruta.read_text(encoding="utf-8")
    except OSError:
        logger.exception("No se pudo leer plantilla de estilos", extra={"ruta": str(ruta)})
        return ""


def construir_estilo_tarjeta_toast(*, color_texto: str, color_acento: str, color_acento_suave: str, color_fondo: str, color_cerrar_hover: str, color_cerrar_pressed: str) -> str:
    plantilla = _leer_plantilla("toast_tarjeta.qss")
    if not plantilla:
        return ""
    return plantilla.format(
        color_texto=color_texto,
        color_acento=color_acento,
        color_acento_suave=color_acento_suave,
        color_fondo=color_fondo,
        color_cerrar_hover=color_cerrar_hover,
        color_cerrar_pressed=color_cerrar_pressed,
    )


def construir_estilo_dialogo_operacion_feedback() -> str:
    return _leer_plantilla("dialogo_operacion_feedback.qss")


def construir_estilo_dialogo_confirmacion_resumen(*, color_borde: str) -> str:
    plantilla = _leer_plantilla("dialogo_confirmacion_resumen.qss")
    if not plantilla:
        return ""
    return plantilla.format(color_borde=color_borde)

