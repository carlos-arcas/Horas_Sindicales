from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.domain.models import Persona


def _build_solicitud(
    persona_id: int,
    fecha_pedida: str,
    desde: str | None,
    hasta: str | None,
    completo: bool,
) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2025-01-01",
        fecha_pedida=fecha_pedida,
        desde=desde,
        hasta=hasta,
        completo=completo,
        horas=0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )


def test_detectar_conflictos_pendientes_solape_parcial(
    solicitud_use_cases,
    persona_id: int,
) -> None:
    pendientes = [
        _build_solicitud(persona_id, "2025-01-15", "08:00", "12:00", False),
        _build_solicitud(persona_id, "2025-01-15", "09:00", "12:00", False),
        _build_solicitud(persona_id, "2025-01-16", "09:00", "10:00", False),
    ]

    conflicts = solicitud_use_cases.detectar_conflictos_pendientes(pendientes)

    assert conflicts == {0, 1}


def test_detectar_conflictos_pendientes_contiguo_no_conflicto(
    solicitud_use_cases,
    persona_id: int,
) -> None:
    pendientes = [
        _build_solicitud(persona_id, "2025-01-15", "08:00", "09:00", False),
        _build_solicitud(persona_id, "2025-01-15", "09:00", "12:00", False),
    ]

    conflicts = solicitud_use_cases.detectar_conflictos_pendientes(pendientes)

    assert conflicts == set()


def test_detectar_conflictos_pendientes_completo_vs_parcial(
    solicitud_use_cases,
    persona_id: int,
) -> None:
    pendientes = [
        _build_solicitud(persona_id, "2025-01-15", None, None, True),
        _build_solicitud(persona_id, "2025-01-15", "10:00", "11:00", False),
    ]

    conflicts = solicitud_use_cases.detectar_conflictos_pendientes(pendientes)

    assert conflicts == {0, 1}


def test_detectar_conflictos_pendientes_misma_hora_distinta_delegada_permitido(
    solicitud_use_cases,
    persona_id: int,
    persona_repo,
) -> None:
    segunda = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Segunda",
            genero="F",
            horas_mes_min=600,
            horas_ano_min=7200,
            is_active=True,
            cuad_lun_man_min=240,
            cuad_lun_tar_min=240,
            cuad_mar_man_min=240,
            cuad_mar_tar_min=240,
            cuad_mie_man_min=240,
            cuad_mie_tar_min=240,
            cuad_jue_man_min=240,
            cuad_jue_tar_min=240,
            cuad_vie_man_min=240,
            cuad_vie_tar_min=240,
            cuad_sab_man_min=0,
            cuad_sab_tar_min=0,
            cuad_dom_man_min=0,
            cuad_dom_tar_min=0,
        )
    )
    segunda_id = int(segunda.id or 0)
    pendientes = [
        _build_solicitud(persona_id, "2025-01-15", "08:00", "10:00", False),
        _build_solicitud(segunda_id, "2025-01-15", "08:30", "09:30", False),
    ]

    conflicts = solicitud_use_cases.detectar_conflictos_pendientes(pendientes)

    assert conflicts == set()


def test_detectar_conflictos_pendientes_solape_parcial_misma_delegada_conflicto(
    solicitud_use_cases,
    persona_id: int,
) -> None:
    pendientes = [
        _build_solicitud(persona_id, "2025-01-20", "08:00", "10:00", False),
        _build_solicitud(persona_id, "2025-01-20", "09:30", "11:30", False),
    ]

    conflicts = solicitud_use_cases.detectar_conflictos_pendientes(pendientes)

    assert conflicts == {0, 1}
