from pathlib import Path

from app.domain.sync_models import SyncSummary
from app.ui.sync_reporting import build_config_incomplete_report, build_sync_report, persist_report


def test_config_incomplete_report_sets_expected_status() -> None:
    report = build_config_incomplete_report("source", "scope", "actor")

    assert report.status == "CONFIG_INCOMPLETE"
    assert report.counts["errors"] == 1
    assert report.entries[0].entity == "Config"


def test_sync_ok_report_includes_counts() -> None:
    summary = SyncSummary(inserted_local=1, updated_local=2, inserted_remote=3, updated_remote=1)

    report = build_sync_report(summary, status="OK", source="src", scope="all", actor="delegada")

    assert report.status == "OK"
    assert report.counts["created"] == 4
    assert report.counts["updated"] == 3


def test_sync_report_persist_creates_last_files(tmp_path: Path) -> None:
    summary = SyncSummary(errors=1)
    report = build_sync_report(summary, status="ERROR", source="src", scope="all", actor="delegada")

    json_path, md_path = persist_report(report, tmp_path)

    assert json_path.exists()
    assert md_path.exists()
    assert (tmp_path / "logs" / "sync_history").exists()
