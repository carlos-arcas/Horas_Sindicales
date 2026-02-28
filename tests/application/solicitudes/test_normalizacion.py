from __future__ import annotations

from dataclasses import replace

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.normalizacion_solicitud import normalizar_solicitud


def _dto_base() -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=7,
        fecha_solicitud="2025-02-10",
        fecha_pedida="2025-2-12",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=0.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )


def test_normalizacion_parcial_calcula_minutos_y_fecha_canonica() -> None:
    normalizada = normalizar_solicitud(_dto_base())

    assert normalizada.fecha == "2025-02-12"
    assert normalizada.minutos == 120
    assert normalizada.tipo == "PARCIAL"


def test_normalizacion_completo_sin_cuadrante() -> None:
    normalizada = normalizar_solicitud(replace(_dto_base(), completo=True, desde=None, hasta=None, horas=8.0))

    assert normalizada.desde == "COMPLETO"
    assert normalizada.hasta == "COMPLETO"
    assert normalizada.minutos == 480
