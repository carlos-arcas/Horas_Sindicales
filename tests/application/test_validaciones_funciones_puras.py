from __future__ import annotations

from dataclasses import replace

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import (
    validar_campos_obligatorios,
    validar_formato_fechas,
    validar_jornada_parcial,
    validar_limite_horas,
)


def _dto_base() -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=7,
        fecha_solicitud="2025-02-10",
        fecha_pedida="2025-02-12",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )


def test_validar_campos_obligatorios_ok() -> None:
    assert validar_campos_obligatorios(_dto_base()) == []


def test_validar_formato_fechas_error() -> None:
    dto = replace(_dto_base(), fecha_pedida="12/02/2025")

    errores = validar_formato_fechas(dto)

    assert errores == ["fecha_pedida debe tener formato YYYY-MM-DD."]


def test_validar_jornada_parcial_limite_horario_igual() -> None:
    errores = validar_jornada_parcial("09:00", "09:00")

    assert errores == ["El campo hasta debe ser mayor que desde."]


def test_validar_limite_horas_error_supera_24() -> None:
    assert validar_limite_horas(24.1) == ["Las horas no pueden superar 24 en una sola petición."]
