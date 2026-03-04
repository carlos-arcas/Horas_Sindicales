from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.domain.sync_models import SyncAttemptReport, SyncLogEntry, SyncReport
from app.ui.sync_reporting_formatters import to_markdown, txt


def persist_report(report: SyncReport, root: Path) -> tuple[Path, Path]:
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    json_path = logs_dir / "sync_last.json"
    md_path = logs_dir / "sync_last.md"
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(to_markdown(report), encoding="utf-8")

    history_dir = logs_dir / "sync_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime(txt("ui.sync_report.timestamp_format"))
    sync_id = report.sync_id or "no-sync-id"
    history_json = history_dir / f"{stamp}_{sync_id}.json"
    history_md = history_dir / f"{stamp}_{sync_id}.md"
    history_json.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    history_md.write_text(to_markdown(report), encoding="utf-8")
    _trim_history(history_dir)
    return json_path, md_path


def list_sync_history(root: Path) -> list[Path]:
    history_dir = root / "logs" / "sync_history"
    if not history_dir.exists():
        return []
    return sorted(
        history_dir.glob(txt("ui.sync_report.glob_json")),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def load_sync_report(path: Path) -> SyncReport:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = [SyncLogEntry(**entry) for entry in data.get("entries", [])]
    attempts = [
        SyncAttemptReport(**attempt) for attempt in data.get("attempt_history", [])
    ]
    return SyncReport(
        sync_id=data.get("sync_id", ""),
        started_at=data["started_at"],
        finished_at=data["finished_at"],
        attempts=int(data.get("attempts", 1)),
        final_status=data.get("final_status", data.get("status", "IDLE")),
        status=data.get("status", "IDLE"),
        source=data.get("source", ""),
        scope=data.get("scope", ""),
        idempotency_criteria=data.get("idempotency_criteria", ""),
        actor=data.get("actor", txt("ui.sync_report.no_disponible_abrev")),
        counts=data.get("counts", {}),
        warnings=data.get("warnings", []),
        errors=data.get("errors", []),
        conflicts=data.get("conflicts", []),
        items_changed=data.get("items_changed", []),
        entries=entries,
        duration_ms=int(data.get("duration_ms", 0)),
        rows_total_local=int(data.get("rows_total_local", 0)),
        rows_scanned_remote=int(data.get("rows_scanned_remote", 0)),
        api_calls_count=int(data.get("api_calls_count", 0)),
        retry_count=int(data.get("retry_count", 0)),
        conflicts_count=int(data.get("conflicts_count", 0)),
        error_count=int(data.get("error_count", 0)),
        success_rate=float(data.get("success_rate", 1.0)),
        attempt_history=tuple(attempts),
    )


def _trim_history(history_dir: Path, max_entries: int = 20) -> None:
    files = sorted(
        history_dir.glob(txt("ui.sync_report.glob_json")),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    companion_md = {path.with_suffix(".md") for path in files}
    all_files = files + [path for path in companion_md if path.exists()]
    for old in all_files[max_entries * 2 :]:
        old.unlink(missing_ok=True)
