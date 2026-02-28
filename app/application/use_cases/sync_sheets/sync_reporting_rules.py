from __future__ import annotations

from typing import Any

from app.domain.sync_models import SyncSummary


_REASON_TEXT = {
    "duplicate_with_uuid": "Solicitud remota omitida: uuid duplicado ya existente localmente.",
    "insert_new_uuid": "Solicitud remota nueva insertada por uuid.",
    "conflict_divergent": "Conflicto detectado: ambos lados cambiaron tras el último sync.",
    "remote_newer": "Solicitud local actualizada: versión remota más reciente.",
    "local_is_newer_or_equal": "Solicitud remota omitida: la local es más nueva o igual.",
    "duplicate_without_uuid": "Solicitud remota sin uuid omitida por duplicado compuesto.",
    "backfill_existing_uuid": "Solicitud remota sin uuid con backfill aplicado al uuid existente.",
    "insert_missing_uuid": "Solicitud remota sin uuid insertada generando identificador local.",
}


def reason_text(reason_code: str) -> str:
    return _REASON_TEXT.get(reason_code, f"reason_code_no_mapeado:{reason_code}")


def apply_stat_counter(stats: dict[str, Any], *, counter: str) -> dict[str, Any]:
    updated = dict(stats)
    if counter:
        updated[counter] = updated.get(counter, 0) + 1
    return updated


def accumulate_write_result(stats: dict[str, Any], result: tuple[bool, int, int], operation_counter: str) -> dict[str, Any]:
    written, omitted_delegada, operation_errors = result
    updated = dict(stats)
    updated["downloaded"] = updated.get("downloaded", 0) + (1 if written else 0)
    updated[operation_counter] = updated.get(operation_counter, 0) + (1 if written else 0)
    updated["omitted_by_delegada"] = updated.get("omitted_by_delegada", 0) + omitted_delegada
    updated["errors"] = updated.get("errors", 0) + operation_errors
    return updated


def pull_stats_tuple(stats: dict[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        int(stats.get("downloaded", 0)),
        int(stats.get("conflicts", 0)),
        int(stats.get("omitted_duplicates", 0)),
        int(stats.get("omitted_by_delegada", 0)),
        int(stats.get("errors", 0)),
    )


def combine_sync_summaries(pull_summary: SyncSummary, push_summary: SyncSummary) -> SyncSummary:
    return SyncSummary(
        inserted_local=pull_summary.inserted_local,
        updated_local=pull_summary.updated_local,
        inserted_remote=push_summary.inserted_remote,
        updated_remote=push_summary.updated_remote,
        duplicates_skipped=pull_summary.duplicates_skipped + push_summary.duplicates_skipped,
        conflicts_detected=pull_summary.conflicts_detected + push_summary.conflicts_detected,
        omitted_by_delegada=pull_summary.omitted_by_delegada + push_summary.omitted_by_delegada,
        errors=pull_summary.errors + push_summary.errors,
    )
