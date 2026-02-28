from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import detectar_duplicados_en_pendientes
from app.ui.vistas.pending_duplicate_presenter import (
    PendingDuplicateDecision,
    PendingDuplicateEntrada,
    resolve_pending_duplicate_row,
)


def _solicitud(
    *,
    id: int | None,
    persona_id: int = 1,
    fecha: str = "2026-01-10",
    desde: str | None = "08:00",
    hasta: str | None = "10:00",
    completo: bool = False,
) -> SolicitudDTO:
    return SolicitudDTO(
        id=id,
        persona_id=persona_id,
        fecha_solicitud="2026-01-01",
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=completo,
        horas=8 if completo else 2,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
        generated=False,
    )


def _resolver(
    *,
    solicitud: SolicitudDTO,
    pending: list[SolicitudDTO],
    editing_id: int | None = None,
    editing_row: int | None = None,
    duplicated_keys: set[tuple[int, str, str, str, str]] | None = None,
) -> PendingDuplicateDecision:
    keys = detectar_duplicados_en_pendientes(pending) if duplicated_keys is None else duplicated_keys
    return resolve_pending_duplicate_row(
        PendingDuplicateEntrada(
            solicitud=solicitud,
            pending_solicitudes=pending,
            editing_pending_id=editing_id,
            editing_row=editing_row,
            duplicated_keys=keys,
        )
    )


@pytest.mark.parametrize(
    ("pending", "solicitud", "editing_id", "editing_row", "expected_row", "expected_reason"),
    [
        ([], _solicitud(id=None), None, None, None, "key_not_marked_duplicated"),
        ([_solicitud(id=1)], _solicitud(id=None), None, None, None, "key_not_marked_duplicated"),
        ([_solicitud(id=1), _solicitud(id=2)], _solicitud(id=None), None, None, 0, "matched_duplicate_row"),
        ([_solicitud(id=10), _solicitud(id=11)], _solicitud(id=None), 10, 0, 1, "matched_duplicate_row"),
        ([_solicitud(id=None), _solicitud(id=2)], _solicitud(id=None), None, 0, 1, "matched_duplicate_row"),
        ([_solicitud(id=1), _solicitud(id=2), _solicitud(id=3)], _solicitud(id=None), None, None, 0, "matched_duplicate_row"),
        (
            [_solicitud(id=1), _solicitud(id=2, fecha="2026-01-11")],
            _solicitud(id=None),
            None,
            None,
            None,
            "key_not_marked_duplicated",
        ),
        (
            [_solicitud(id=1, persona_id=2), _solicitud(id=2, persona_id=2)],
            _solicitud(id=None, persona_id=1),
            None,
            None,
            None,
            "key_not_marked_duplicated",
        ),
        (
            [_solicitud(id=1, desde="09:00", hasta="11:00"), _solicitud(id=2, desde="09:00", hasta="11:00")],
            _solicitud(id=None, desde="08:00", hasta="10:00"),
            None,
            None,
            None,
            "key_not_marked_duplicated",
        ),
        (
            [_solicitud(id=1, completo=True, desde=None, hasta=None), _solicitud(id=2, completo=True, desde=None, hasta=None)],
            _solicitud(id=None, completo=True, desde=None, hasta=None),
            None,
            None,
            0,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2), _solicitud(id=3, fecha="2026-01-12")],
            _solicitud(id=None),
            1,
            0,
            1,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2), _solicitud(id=3)],
            _solicitud(id=None),
            2,
            1,
            0,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2), _solicitud(id=3)],
            _solicitud(id=None),
            1,
            0,
            1,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2)],
            _solicitud(id=None),
            999,
            1,
            0,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=None), _solicitud(id=None)],
            _solicitud(id=None),
            None,
            1,
            0,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2), _solicitud(id=3, fecha="2026-01-11")],
            _solicitud(id=None),
            None,
            2,
            0,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2)],
            _solicitud(id=None),
            None,
            None,
            0,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2), _solicitud(id=3)],
            _solicitud(id=None),
            1,
            None,
            1,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2)],
            _solicitud(id=None),
            None,
            99,
            0,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2)],
            _solicitud(id=None),
            "1",  # type: ignore[arg-type]
            None,
            1,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1, desde="8:00", hasta="10:00"), _solicitud(id=2, desde="08:00", hasta="10:00")],
            _solicitud(id=None, desde="08:00", hasta="10:00"),
            None,
            None,
            0,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2), _solicitud(id=3)],
            _solicitud(id=None),
            2,
            2,
            0,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2), _solicitud(id=3)],
            _solicitud(id=None),
            1,
            2,
            1,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1), _solicitud(id=2, completo=True, desde=None, hasta=None), _solicitud(id=3, completo=True, desde=None, hasta=None)],
            _solicitud(id=None, completo=True, desde=None, hasta=None),
            None,
            None,
            1,
            "matched_duplicate_row",
        ),
        (
            [_solicitud(id=1, persona_id=9), _solicitud(id=2, persona_id=9)],
            _solicitud(id=None, persona_id=9),
            1,
            None,
            1,
            "matched_duplicate_row",
        ),
    ],
)
def test_resolve_pending_duplicate_row_cases(pending, solicitud, editing_id, editing_row, expected_row, expected_reason):
    decision = _resolver(
        solicitud=solicitud,
        pending=pending,
        editing_id=editing_id,
        editing_row=editing_row,
    )
    assert decision.row_index == expected_row
    assert decision.reason_code == expected_reason


def test_precedence_target_key_invalid_over_anything_else():
    pending = [_solicitud(id=1), _solicitud(id=2)]
    invalid = _solicitud(id=None, desde="bad", hasta="10:00")
    decision = _resolver(solicitud=invalid, pending=pending)
    assert decision.reason_code == "target_key_invalid"
    assert decision.row_index is None


def test_precedence_key_not_marked_duplicated_over_match():
    pending = [_solicitud(id=1), _solicitud(id=2)]
    decision = _resolver(solicitud=_solicitud(id=None), pending=pending, duplicated_keys=set())
    assert decision.reason_code == "key_not_marked_duplicated"
    assert decision.row_index is None


def test_precedence_matched_duplicate_over_fallback():
    pending = [_solicitud(id=1), _solicitud(id=2)]
    keys = detectar_duplicados_en_pendientes(pending)
    decision = _resolver(solicitud=_solicitud(id=None), pending=pending, duplicated_keys=keys)
    assert decision.reason_code == "matched_duplicate_row"
    assert decision.row_index == 0


def test_precedence_fallback_first_row_when_key_marked_but_rows_invalid():
    pending = [_solicitud(id=1, desde="bad", hasta="10:00")]
    marked = {(1, "2026-01-10", "08:00", "10:00", "PARCIAL")}
    target = _solicitud(id=None, persona_id=1, desde="08:00", hasta="10:00")
    decision = _resolver(solicitud=target, pending=pending, duplicated_keys=marked)
    assert decision.reason_code == "fallback_first_row"
    assert decision.row_index == 0


def test_precedence_no_pending_rows_when_marked_key_and_empty_pending():
    marked = {(1, "2026-01-10", "08:00", "10:00", "PARCIAL")}
    decision = _resolver(solicitud=_solicitud(id=None), pending=[], duplicated_keys=marked)
    assert decision.reason_code == "no_pending_rows"
    assert decision.row_index is None
