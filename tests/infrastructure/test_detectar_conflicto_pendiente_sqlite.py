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
    return solicitud_repo.create(
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


def test_dup_exacto_mismo_tramo_retorna_duplicado(solicitud_repo, persona_id: int) -> None:
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


def test_solape_parcial_retorna_solape(solicitud_repo, persona_id: int) -> None:
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


def test_misma_fecha_sin_solape_retorna_none(solicitud_repo, persona_id: int) -> None:
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


def test_completo_vs_parcial_retorna_tipo_correcto(solicitud_repo, persona_id: int) -> None:
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


def test_no_conflicto_fecha_distinta_comparando_con_existentes(solicitud_repo, persona_id: int) -> None:
    _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-03-03",
        desde_min=9 * 60,
        hasta_min=10 * 60,
        completo=False,
        generated=True,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-07-17", 9 * 60, 17 * 60, False)

    assert conflicto is None


def test_no_conflicto_tramos_contiguos_misma_fecha(solicitud_repo, persona_id: int) -> None:
    _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-07-17",
        desde_min=9 * 60,
        hasta_min=10 * 60,
        completo=False,
        generated=False,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-07-17", 10 * 60, 11 * 60, False)

    assert conflicto is None


def test_conflicto_si_solape_en_historico(solicitud_repo, persona_id: int) -> None:
    existente = _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-07-17",
        desde_min=9 * 60,
        hasta_min=11 * 60,
        completo=False,
        generated=True,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-07-17", 10 * 60, 12 * 60, False)

    assert conflicto is not None
    assert conflicto.tipo == "SOLAPE"
    assert conflicto.id_existente == existente.id


def test_conflicto_si_solape_en_pendientes(solicitud_repo, persona_id: int) -> None:
    _crear_solicitud(
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


def test_conflicto_si_duplicado_exacto_en_historico_o_pendientes(solicitud_repo, persona_id: int) -> None:
    existente = _crear_solicitud(
        solicitud_repo,
        persona_id=persona_id,
        fecha="2026-07-17",
        desde_min=17 * 60,
        hasta_min=18 * 60,
        completo=False,
        generated=True,
    )

    conflicto = solicitud_repo.detectar_conflicto_pendiente(persona_id, "2026-07-17", 17 * 60, 18 * 60, False)

    assert conflicto is not None
    assert conflicto.tipo == "DUPLICADO"
    assert conflicto.id_existente == existente.id
