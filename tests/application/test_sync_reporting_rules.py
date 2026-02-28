from __future__ import annotations

import pytest

from app.application.use_cases.sync_sheets.sync_reporting_rules import (
    accumulate_write_result,
    apply_stat_counter,
    combine_sync_summaries,
    pull_stats_tuple,
    reason_text,
)
from app.domain.sync_models import SyncSummary


@pytest.mark.parametrize(
    ("reason_code", "expected"),
    [
        ("duplicate_with_uuid", "Solicitud remota omitida: uuid duplicado ya existente localmente."),
        ("insert_new_uuid", "Solicitud remota nueva insertada por uuid."),
        ("conflict_divergent", "Conflicto detectado: ambos lados cambiaron tras el último sync."),
        ("remote_newer", "Solicitud local actualizada: versión remota más reciente."),
        ("local_is_newer_or_equal", "Solicitud remota omitida: la local es más nueva o igual."),
        ("duplicate_without_uuid", "Solicitud remota sin uuid omitida por duplicado compuesto."),
        ("backfill_existing_uuid", "Solicitud remota sin uuid con backfill aplicado al uuid existente."),
        ("insert_missing_uuid", "Solicitud remota sin uuid insertada generando identificador local."),
    ],
)
def test_reason_text_known_codes(reason_code: str, expected: str) -> None:
    assert reason_text(reason_code) == expected


@pytest.mark.parametrize("reason_code", ["", "otro", "CONFLICT", "x_y_z"])
def test_reason_text_unknown_code(reason_code: str) -> None:
    assert reason_text(reason_code).startswith("reason_code_no_mapeado:")


@pytest.mark.parametrize(
    ("stats", "counter", "expected"),
    [
        ({}, "omitted_duplicates", 1),
        ({"omitted_duplicates": 2}, "omitted_duplicates", 3),
        ({"downloaded": 1}, "inserted_ws", 1),
        ({"inserted_ws": 7}, "inserted_ws", 8),
    ],
)
def test_apply_stat_counter(stats: dict[str, int], counter: str, expected: int) -> None:
    updated = apply_stat_counter(stats, counter=counter)
    assert updated[counter] == expected


def test_apply_stat_counter_noop_if_counter_empty() -> None:
    stats = {"a": 1}
    assert apply_stat_counter(stats, counter="") == {"a": 1}


@pytest.mark.parametrize(
    ("result", "expected_downloaded", "expected_counter", "expected_omitted", "expected_errors"),
    [
        ((True, 0, 0), 1, 1, 0, 0),
        ((False, 1, 0), 0, 0, 1, 0),
        ((False, 0, 1), 0, 0, 0, 1),
        ((True, 2, 3), 1, 1, 2, 3),
    ],
)
def test_accumulate_write_result(result, expected_downloaded: int, expected_counter: int, expected_omitted: int, expected_errors: int) -> None:
    stats = {"downloaded": 0, "inserted_ws": 0, "omitted_by_delegada": 0, "errors": 0}
    updated = accumulate_write_result(stats, result, "inserted_ws")
    assert updated["downloaded"] == expected_downloaded
    assert updated["inserted_ws"] == expected_counter
    assert updated["omitted_by_delegada"] == expected_omitted
    assert updated["errors"] == expected_errors


@pytest.mark.parametrize(
    ("stats", "expected"),
    [
        ({}, (0, 0, 0, 0, 0)),
        ({"downloaded": 1}, (1, 0, 0, 0, 0)),
        ({"downloaded": 1, "conflicts": 2, "omitted_duplicates": 3, "omitted_by_delegada": 4, "errors": 5}, (1, 2, 3, 4, 5)),
    ],
)
def test_pull_stats_tuple(stats, expected) -> None:
    assert pull_stats_tuple(stats) == expected


@pytest.mark.parametrize(
    ("pull_vals", "push_vals", "expected"),
    [
        ((1, 2, 0, 0, 1, 1, 2, 3), (0, 0, 3, 4, 2, 3, 4, 5), (1, 2, 3, 4, 3, 4, 8, 6)),
        ((0, 0, 0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0, 0)),
    ],
)
def test_combine_sync_summaries_contract(pull_vals, push_vals, expected) -> None:
    pull = SyncSummary(
        inserted_local=pull_vals[0], updated_local=pull_vals[1], inserted_remote=pull_vals[2], updated_remote=pull_vals[3],
        duplicates_skipped=pull_vals[4], conflicts_detected=pull_vals[5], errors=pull_vals[6], omitted_by_delegada=pull_vals[7]
    )
    push = SyncSummary(
        inserted_local=push_vals[0], updated_local=push_vals[1], inserted_remote=push_vals[2], updated_remote=push_vals[3],
        duplicates_skipped=push_vals[4], conflicts_detected=push_vals[5], errors=push_vals[6], omitted_by_delegada=push_vals[7]
    )
    combined = combine_sync_summaries(pull, push)
    assert (
        combined.inserted_local,
        combined.updated_local,
        combined.inserted_remote,
        combined.updated_remote,
        combined.duplicates_skipped,
        combined.conflicts_detected,
        combined.omitted_by_delegada,
        combined.errors,
    ) == expected
