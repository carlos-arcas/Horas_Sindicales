from __future__ import annotations

from app.domain.models import Solicitud


def _crear_solicitud(
    solicitud_repo,
    *,
    persona_id: int,
    fecha: str,
    desde_min: int | None,
    hasta_min: int | None,
    completo: bool,
    generated: bool = False,
) -> Solicitud:
    solicitud = solicitud_repo.create(
        Solicitud(
            id=None,
            persona_id=persona_id,
            fecha_solicitud=fecha,
            fecha_pedida=fecha,
            desde_min=desde_min,
            hasta_min=hasta_min,
            completo=completo,
            horas_solicitadas_min=120 if not completo else 480,
            observaciones=None,
            notas=None,
            pdf_path=None,
            pdf_hash=None,
            generated=generated,
        )
    )
    if generated and solicitud.id is not None:
        solicitud_repo.mark_generated(int(solicitud.id), True)
    return solicitud


def test_dup_exacto_mismo_tramo_pendiente_retorna_duplicado(solicitud_repo, persona_id: int) -> None:
    existente = _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-05-10",
        desde_min=9 * 60,
        hasta_min=11 * 60,
        completo=False,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-05-10", 9 * 60, 11 * 60, False)

    assert conflicto is not None
    assert conflicto.tipo == "DUPLICADO"
    assert conflicto.id_existente == existente.id


def test_solape_parcial_en_pendiente_retorna_solape(solicitud_repo, persona_id: int) -> None:
    existente = _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-05-11",
        desde_min=9 * 60,
        hasta_min=11 * 60,
        completo=False,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-05-11", 10 * 60, 12 * 60, False)

    assert conflicto is not None
    assert conflicto.tipo == "SOLAPE"
    assert conflicto.id_existente == existente.id


def test_tramos_contiguos_en_pendiente_no_generan_conflicto(solicitud_repo, persona_id: int) -> None:
    _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-05-12",
        desde_min=9 * 60,
        hasta_min=11 * 60,
        completo=False,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-05-12", 11 * 60, 12 * 60, False)

    assert conflicto is None


def test_completo_vs_parcial_pendiente_retorna_tipo_correcto(solicitud_repo, persona_id: int) -> None:
    existente = _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-05-13",
        desde_min=9 * 60,
        hasta_min=10 * 60,
        completo=False,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-05-13", None, None, True)

    assert conflicto is not None
    assert conflicto.tipo == "SOLAPE"
    assert conflicto.id_existente == existente.id


def test_excluye_soft_deleted(solicitud_repo, persona_id: int) -> None:
    existente = _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-05-14",
        desde_min=9 * 60,
        hasta_min=10 * 60,
        completo=False,
    )
    solicitud_repo.delete(int(existente.id or 0))

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-05-14", 9 * 60, 10 * 60, False)

    assert conflicto is None


def test_fecha_distinta_no_conflicta_con_pendiente_existente(solicitud_repo, persona_id: int) -> None:
    _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-03-03",
        desde_min=9 * 60,
        hasta_min=10 * 60,
        completo=False,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-07-17", 9 * 60, 17 * 60, False)

    assert conflicto is None


def test_registro_confirmado_no_bloquea_pendiente_nueva(solicitud_repo, persona_id: int) -> None:
    _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-07-17",
        desde_min=9 * 60,
        hasta_min=11 * 60,
        completo=False,
        generated=True,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-07-17", 10 * 60, 12 * 60, False)

    assert conflicto is None


def test_conflicto_si_solape_en_pendientes(solicitud_repo, persona_id: int) -> None:
    existente = _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-07-17",
        desde_min=9 * 60,
        hasta_min=11 * 60,
        completo=False,
        generated=False,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-07-17", 10 * 60, 12 * 60, False)

    assert conflicto is not None
    assert conflicto.tipo == "SOLAPE"
    assert conflicto.id_existente == existente.id


def test_excluir_solicitud_id_omite_el_registro_actual(solicitud_repo, persona_id: int) -> None:
    existente = _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-07-18",
        desde_min=8 * 60,
        hasta_min=10 * 60,
        completo=False,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(
        persona_id,
        "2026-07-18",
        8 * 60,
        10 * 60,
        False,
        excluir_solicitud_id=int(existente.id or 0),
    )

    assert conflicto is None
