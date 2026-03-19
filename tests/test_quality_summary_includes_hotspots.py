from __future__ import annotations

import json
from pathlib import Path

from scripts import quality_summary


def test_quality_summary_includes_hotspots_sections(
    monkeypatch, tmp_path: Path
) -> None:
    logs_dir = tmp_path / "logs"
    report_json = logs_dir / "quality_report.json"
    quality_md = logs_dir / "quality_report.md"
    summary_md = logs_dir / "quality_summary.md"

    payload = {
        "results": {
            "global_status": "PASS",
            "coverage": {"status": "PASS", "value": 90, "threshold": 85},
            "cc_budget": {"status": "PASS", "detail": "ok"},
            "cc_targets": {"status": "PASS", "detail": "targets=1, failing=0"},
            "architecture": {"status": "PASS", "detail": "ok"},
            "secrets": {"status": "PASS", "detail": "ok"},
            "naming": {
                "status": "PASS",
                "total_offenders": 0,
                "nuevos_archivos": [],
                "nuevos_simbolos": [],
            },
            "release_contract": {"status": "PASS", "detail": "ok"},
        }
    }

    logs_dir.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload), encoding="utf-8")
    quality_md.write_text("# Quality Gate Unificado\n", encoding="utf-8")

    monkeypatch.setattr(quality_summary, "REPORT_JSON_PATH", report_json)
    monkeypatch.setattr(quality_summary, "QUALITY_REPORT_MD_PATH", quality_md)
    monkeypatch.setattr(quality_summary, "SUMMARY_MD_PATH", summary_md)

    exit_code = quality_summary.main()

    assert exit_code == 0
    generated_markdown = quality_md.read_text(encoding="utf-8")
    assert "Top 10 archivos por LOC" in generated_markdown
    assert "Top 10 por complejidad" in generated_markdown
