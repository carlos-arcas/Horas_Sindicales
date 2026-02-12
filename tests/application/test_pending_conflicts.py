from __future__ import annotations

from app.application.dto import SolicitudDTO


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
