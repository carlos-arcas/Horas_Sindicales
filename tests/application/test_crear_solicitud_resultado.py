from __future__ import annotations

import logging

from app.application.dto import SolicitudDTO
from app.domain.models import Persona


def _build_dto(persona_id: int, *, desde: str = "09:00", hasta: str = "11:00", horas: float = 2.0) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2025-01-10",
        fecha_pedida="2025-01-15",
        desde=desde,
        hasta=hasta,
        completo=False,
        horas=horas,
        observaciones="Obs",
        pdf_path=None,
        pdf_hash=None,
        notas="Nota",
    )


def test_crear_peticion_con_saldo_suficiente_ok(solicitud_use_cases, persona_id: int) -> None:
    resultado = solicitud_use_cases.crear_resultado(_build_dto(persona_id))

    assert resultado.success is True
    assert resultado.errores == []
    assert resultado.warnings == []
    assert resultado.entidad is not None


def test_crear_peticion_con_saldo_insuficiente_retorna_warning_y_persiste(
    solicitud_use_cases,
    persona_repo,
    caplog,
) -> None:
    persona = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Sin Saldo",
            genero="F",
            horas_mes_min=30,
            horas_ano_min=30,
            is_active=True,
            cuad_lun_man_min=240,
            cuad_lun_tar_min=0,
            cuad_mar_man_min=240,
            cuad_mar_tar_min=0,
            cuad_mie_man_min=240,
            cuad_mie_tar_min=0,
            cuad_jue_man_min=240,
            cuad_jue_tar_min=0,
            cuad_vie_man_min=240,
            cuad_vie_tar_min=0,
            cuad_sab_man_min=0,
            cuad_sab_tar_min=0,
            cuad_dom_man_min=0,
            cuad_dom_tar_min=0,
        )
    )
    persona_id = int(persona.id or 0)

    with caplog.at_level(logging.WARNING):
        resultado = solicitud_use_cases.crear_resultado(_build_dto(persona_id, desde="08:00", hasta="10:00"))

    assert resultado.success is True
    assert resultado.errores == []
    assert resultado.warnings == ["Saldo insuficiente. La petición se ha registrado igualmente."]
    assert resultado.entidad is not None
    assert any("Saldo insuficiente. La petición se ha registrado igualmente." in r.getMessage() for r in caplog.records)

    pendientes = list(solicitud_use_cases.listar_pendientes_por_persona(persona_id))
    assert len(pendientes) == 1


def test_crear_peticion_con_error_de_validacion_retorna_success_false(solicitud_use_cases) -> None:
    dto_invalido = _build_dto(persona_id=0)

    resultado = solicitud_use_cases.crear_resultado(dto_invalido)

    assert resultado.success is False
    assert resultado.entidad is None
    assert resultado.errores


def test_crear_peticion_persiste_con_saldo_negativo(solicitud_use_cases, persona_repo) -> None:
    persona = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Saldo Negativo",
            genero="F",
            horas_mes_min=120,
            horas_ano_min=120,
            is_active=True,
            cuad_lun_man_min=240,
            cuad_lun_tar_min=0,
            cuad_mar_man_min=240,
            cuad_mar_tar_min=0,
            cuad_mie_man_min=240,
            cuad_mie_tar_min=0,
            cuad_jue_man_min=240,
            cuad_jue_tar_min=0,
            cuad_vie_man_min=240,
            cuad_vie_tar_min=0,
            cuad_sab_man_min=0,
            cuad_sab_tar_min=0,
            cuad_dom_man_min=0,
            cuad_dom_tar_min=0,
        )
    )
    persona_id = int(persona.id or 0)

    resultado = solicitud_use_cases.crear_resultado(_build_dto(persona_id, desde="08:00", hasta="11:00", horas=3.0))

    assert resultado.success is True
    assert resultado.entidad is not None
    assert resultado.warnings

    pendientes = list(solicitud_use_cases.listar_pendientes_por_persona(persona_id))
    assert len(pendientes) == 1
