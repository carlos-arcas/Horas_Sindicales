from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import (
    clave_duplicado,
    detectar_duplicados_en_pendientes,
    hay_duplicado_distinto,
    normalizar_clave_pendiente,
    validar_solicitud_dto_declarativo,
)
from app.domain.services import ValidacionError


def _dto(**overrides: object) -> SolicitudDTO:
    base = dict(
        id=1,
        persona_id=10,
        fecha_solicitud="2026-01-01",
        fecha_pedida="2026-01-10",
        desde="08:00",
        hasta="10:00",
        completo=False,
        horas=2.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
        generated=False,
    )
    base.update(overrides)
    return SolicitudDTO(**base)


def test_validar_solicitud_declarativo_agrega_multiples_errores() -> None:
    solicitud = _dto(
        persona_id=0,
        fecha_solicitud="2026/01/01",
        fecha_pedida="",
        desde=None,
        hasta=None,
        horas=25,
    )

    with pytest.raises(ValidacionError) as exc:
        validar_solicitud_dto_declarativo(solicitud)

    message = str(exc.value)
    assert "Debe seleccionar una delegada válida." in message
    assert "fecha_solicitud debe tener formato YYYY-MM-DD." in message
    assert "La fecha pedida es obligatoria." in message
    assert "Desde y hasta son obligatorios para peticiones parciales." in message
    assert "Las horas no pueden superar 24 en una sola petición." in message


def test_validar_solicitud_declarativo_completo_no_admite_horas_negativas() -> None:
    solicitud = _dto(completo=True, desde=None, hasta=None, horas=-1)

    with pytest.raises(ValidacionError, match="Las horas no pueden ser negativas"):
        validar_solicitud_dto_declarativo(solicitud)


def test_claves_normalizadas_para_completo_y_parcial() -> None:
    parcial = _dto(fecha_pedida="10/01/2026", desde="8:0", hasta="9:30")
    completo = _dto(completo=True, desde=None, hasta=None)

    assert clave_duplicado(parcial) == (10, "2026-01-10", "08:00", "09:30")
    assert normalizar_clave_pendiente(completo) == (
        10,
        "2026-01-10",
        "COMPLETO",
        "COMPLETO",
        "COMPLETO",
    )


def test_detectar_duplicados_en_pendientes_ignora_registros_invalidos() -> None:
    base = _dto(id=None, fecha_pedida="2026-01-10", desde="08:00", hasta="09:00")
    duplicado = _dto(id=None, fecha_pedida="10/01/2026", desde="8:0", hasta="9:0")
    invalido = _dto(id=None, desde="no-es-hora", hasta="09:00")

    duplicados = detectar_duplicados_en_pendientes([base, duplicado, invalido])

    assert duplicados == {(10, "2026-01-10", "08:00", "09:00", "PARCIAL")}


def test_hay_duplicado_distinto_respeta_exclusiones_de_edicion() -> None:
    objetivo = _dto(id=100)
    existente_mismo_id = _dto(id=100)
    existente_sin_id = _dto(id=None)

    assert hay_duplicado_distinto(objetivo, [existente_mismo_id], excluir_por_id=100) is False
    assert hay_duplicado_distinto(objetivo, [existente_sin_id], excluir_por_indice=0) is False
    assert hay_duplicado_distinto(objetivo, [existente_sin_id], excluir_por_indice=1) is True
