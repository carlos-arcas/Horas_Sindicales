from __future__ import annotations

from app.domain.sync_models import SyncAttemptReport, SyncSummary
from app.ui.sync_reporting import build_sync_report, list_sync_history, load_sync_report, persist_report


def test_history_saves_multiple_attempts_same_sync_id(tmp_path) -> None:
    summary = SyncSummary(inserted_remote=1, errors=1)
    attempt_history = (
        SyncAttemptReport(attempt_number=1, status="ERROR", errors=1),
        SyncAttemptReport(attempt_number=2, status="OK", created=1),
    )
    report = build_sync_report(
        summary,
        status="OK",
        source="src",
        scope="all",
        actor="delegada",
        sync_id="sync-123",
        attempt_history=attempt_history,
    )

    persist_report(report, tmp_path)
    history_files = list_sync_history(tmp_path)

    assert history_files
    loaded = load_sync_report(history_files[0])
    assert loaded.sync_id == "sync-123"
    assert loaded.attempts == 2
    assert len(loaded.attempt_history) == 2
