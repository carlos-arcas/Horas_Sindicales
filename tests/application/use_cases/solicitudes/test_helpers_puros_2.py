from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.helpers_puros_2 import (
    correlation_id_or_new,
    debe_emitir_evento,
    mensaje_duplicado_desde_estado,
    notas_para_guardar,
    payload_evento_exito,
    payload_evento_inicio,
    rango_en_minutos,
    solicitud_desde_dto,
)


def _dto_base(**overrides: object) -> SolicitudDTO:
    data = {
        "id": None,
        "persona_id": 4,
        "fecha_solicitud": "2025-03-01",
        "fecha_pedida": "2025-03-04",
        "desde": "09:00",
        "hasta": "12:30",
        "completo": False,
        "horas": 3.5,
        "observaciones": "Obs original",
        "pdf_path": "archivo.pdf",
        "pdf_hash": "abc123",
        "notas": "Nota explícita",
        "generated": False,
    }
    data.update(overrides)
    return SolicitudDTO(**data)


def test_correlation_id_or_new_retorna_existente() -> None:
    assert correlation_id_or_new("CID-1", "CID-2") == "CID-1"


def test_correlation_id_or_new_retorna_generado_si_none() -> None:
    assert correlation_id_or_new(None, "CID-2") == "CID-2"


def test_correlation_id_or_new_retorna_generado_si_vacio() -> None:
    assert correlation_id_or_new("", "CID-2") == "CID-2"


@pytest.mark.parametrize("valor,esperado", [(None, False), ("", False), ("CID", True)])
def test_debe_emitir_evento(valor: str | None, esperado: bool) -> None:
    assert debe_emitir_evento(valor) is esperado


def test_payload_evento_inicio_incluye_persona_y_fecha() -> None:
    payload = payload_evento_inicio(_dto_base(persona_id=11, fecha_pedida="2025-06-10"))

    assert payload == {"persona_id": 11, "fecha_pedida": "2025-06-10"}


def test_payload_evento_exito_con_id() -> None:
    assert payload_evento_exito(99, 5) == {"solicitud_id": 99, "persona_id": 5}


def test_payload_evento_exito_sin_id() -> None:
    assert payload_evento_exito(None, 5) == {"solicitud_id": None, "persona_id": 5}


def test_rango_en_minutos_convierte_hhmm() -> None:
    assert rango_en_minutos("09:15", "11:45") == (555, 705)


def test_rango_en_minutos_admite_none_completo() -> None:
    assert rango_en_minutos(None, None) == (None, None)


def test_rango_en_minutos_none_parcial_inicio() -> None:
    assert rango_en_minutos(None, "11:00") == (None, 660)


def test_rango_en_minutos_none_parcial_fin() -> None:
    assert rango_en_minutos("08:30", None) == (510, None)


def test_rango_en_minutos_lanza_error_en_formato_invalido() -> None:
    with pytest.raises(ValueError):
        rango_en_minutos("8", "11:00")


@pytest.mark.parametrize(
    "notas,observaciones,esperado",
    [
        ("Nota", "Obs", "Nota"),
        ("", "Obs", ""),
        (None, "Obs", "Obs"),
        (None, None, None),
    ],
)
def test_notas_para_guardar(notas: str | None, observaciones: str | None, esperado: str | None) -> None:
    assert notas_para_guardar(notas, observaciones) == esperado


def test_solicitud_desde_dto_mapea_campos_principales() -> None:
    dto = _dto_base()

    entidad = solicitud_desde_dto(dto, minutos=210, desde_min=540, hasta_min=750)

    assert entidad.id is None
    assert entidad.persona_id == dto.persona_id
    assert entidad.fecha_solicitud == dto.fecha_solicitud
    assert entidad.fecha_pedida == dto.fecha_pedida
    assert entidad.desde_min == 540
    assert entidad.hasta_min == 750
    assert entidad.horas_solicitadas_min == 210


def test_solicitud_desde_dto_prioriza_notas() -> None:
    dto = _dto_base(notas="Nota nueva", observaciones="Obs vieja")

    entidad = solicitud_desde_dto(dto, minutos=30, desde_min=10, hasta_min=40)

    assert entidad.notas == "Nota nueva"


def test_solicitud_desde_dto_usa_observaciones_si_notas_none() -> None:
    dto = _dto_base(notas=None, observaciones="Solo observacion")

    entidad = solicitud_desde_dto(dto, minutos=30, desde_min=10, hasta_min=40)

    assert entidad.notas == "Solo observacion"


def test_solicitud_desde_dto_traslada_datos_pdf() -> None:
    dto = _dto_base(pdf_path="/tmp/a.pdf", pdf_hash="hash-1")

    entidad = solicitud_desde_dto(dto, minutos=30, desde_min=10, hasta_min=40)

    assert entidad.pdf_path == "/tmp/a.pdf"
    assert entidad.pdf_hash == "hash-1"


def test_solicitud_desde_dto_admite_rango_none() -> None:
    dto = _dto_base(completo=True, desde=None, hasta=None)

    entidad = solicitud_desde_dto(dto, minutos=480, desde_min=None, hasta_min=None)

    assert entidad.completo is True
    assert entidad.desde_min is None
    assert entidad.hasta_min is None


@pytest.mark.parametrize(
    "generated,esperado",
    [(True, "Duplicado confirmado"), (False, "Duplicado pendiente")],
)
def test_mensaje_duplicado_desde_estado(generated: bool, esperado: str) -> None:
    assert mensaje_duplicado_desde_estado(generated) == esperado
