from __future__ import annotations

import json
from pathlib import Path

from scripts.coverage_summary import _build_summary, _load_coverage_json


ROOT = Path(__file__).resolve().parents[2]


def test_detects_files_below_threshold_from_fixture() -> None:
    fixture = ROOT / "tests" / "fixtures" / "coverage_sample.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))

    summary_txt, summary_json = _build_summary(data, package="app", threshold=85.0, top_n=10)

    below = summary_json["below_threshold"]
    below_files = [entry["file"] for entry in below]

    assert "app/module_bad.py" in below_files
    assert "app/module_mid.py" in below_files
    assert "other/outside.py" not in below_files
    assert "FICHEROS BAJO UMBRAL" in summary_txt


def test_loads_existing_json_without_dot_coverage(tmp_path: Path) -> None:
    coverage_json = tmp_path / "coverage.json"
    coverage_json.write_text(
        json.dumps(
            {
                "files": {
                    "app/a.py": {
                        "summary": {
                            "covered_lines": 1,
                            "num_statements": 1,
                            "percent_covered": 100,
                            "missing_lines": 0,
                        }
                    }
                },
                "totals": {"percent_covered": 100},
            }
        ),
        encoding="utf-8",
    )

    loaded = _load_coverage_json(repo=tmp_path, out_json=coverage_json)
    assert loaded["totals"]["percent_covered"] == 100
