from __future__ import annotations

from dataclasses import replace

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validar_datos_basicos import validar_datos_basicos


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


def test_validacion_basica_caso_valido() -> None:
    assert validar_datos_basicos(_dto_base()).errores == []


def test_validacion_basica_fecha_invalida() -> None:
    errores = validar_datos_basicos(replace(_dto_base(), fecha_pedida="2025/02/12")).errores

    assert errores == ["fecha_pedida debe tener formato YYYY-MM-DD."]


def test_validacion_basica_tramo_invalido() -> None:
    errores = validar_datos_basicos(replace(_dto_base(), desde="12:00", hasta="11:00")).errores

    assert errores == ["El campo hasta debe ser mayor que desde."]
