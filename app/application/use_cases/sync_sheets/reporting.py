from __future__ import annotations

import json

from app.domain.sync_models import SyncSummary


def build_sync_report(summary: SyncSummary) -> dict[str, int]:
    return {
        "inserted_local": summary.inserted_local,
        "updated_local": summary.updated_local,
        "inserted_remote": summary.inserted_remote,
        "updated_remote": summary.updated_remote,
        "duplicates_skipped": summary.duplicates_skipped,
        "conflicts_detected": summary.conflicts_detected,
        "omitted_by_delegada": summary.omitted_by_delegada,
        "errors": summary.errors,
    }


def render_report_json(summary: SyncSummary) -> str:
    return json.dumps(build_sync_report(summary), ensure_ascii=False, sort_keys=True)


def render_report_md(summary: SyncSummary) -> str:
    data = build_sync_report(summary)
    lines = ["# SyncReport", ""]
    lines.extend(f"- **{key}**: {value}" for key, value in data.items())
    return "\n".join(lines)
