from __future__ import annotations

import argparse
from pathlib import Path

import scripts.product_audit as pa


def test_parse_bool_float_int() -> None:
    assert pa.parse_bool("true") is True
    assert pa.parse_bool("No") is False
    assert pa.parse_int("42") == 42
    assert pa.parse_float("63.5") == 63.5

    try:
        pa.parse_bool("maybe")
    except argparse.ArgumentTypeError:
        pass
    else:
        raise AssertionError("parse_bool should fail for invalid value")


def test_scoring_with_rules() -> None:
    rules = pa.default_rules()
    metrics = {
        "coverage": 70.0,
        "coverage_threshold": 63,
        "max_file_lines": 600,
        "main_window_lines": 0,
        "use_cases_lines": 0,
        "architecture_violations": 0,
        "ci_green": True,
        "release_automated": True,
        "whitelist_active": False,
        "tests_count": 120,
        "critical_modules_over_500": 1,
        "modules_over_800": 0,
        "coverage_thresholds_aligned": True,
        "correlation_id_implemented": True,
        "structured_logs": True,
        "secrets_outside_repo": True,
        "db_in_repo_root": True,
        "has_env_example": True,
        "has_contributing": True,
        "has_changelog": True,
        "has_dod": True,
        "has_roadmap": False,
    }
    areas, _, global_score = pa.score_areas(metrics, rules)
    by_name = {a.name: a.score for a in areas}
    assert by_name["Observabilidad y resiliencia"] >= 95
    assert by_name["DevEx / CI / Governance"] >= 90
    assert by_name["Configuración & seguridad"] >= 80
    assert global_score > 70


def test_should_ignore_dirs() -> None:
    assert pa.should_ignore(Path(".venv/lib/python3.12/site.py")) is True
    assert pa.should_ignore(Path("app/application/use_case.py")) is False


def test_detect_db_in_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pa, "ROOT", tmp_path)
    (tmp_path / "horas.db").write_text("x", encoding="utf-8")
    (tmp_path / "other.txt").write_text("x", encoding="utf-8")

    assert pa.find_db_files_in_root() == ["horas.db"]


def test_render_markdown_contains_sections() -> None:
    snapshot = {
        "timestamp": "2026-01-01 00:00:00",
        "commit": "abc123",
        "metrics": {
            "coverage": 70,
            "tests_count": 120,
            "top_10_files": [{"path": "app/x.py", "lines": 600}],
            "warnings": [],
            "evidences": {
                "architecture": ["arch evidence"],
                "complexity": ["complexity evidence"],
                "security": ["security evidence"],
                "coverage": ["coverage evidence"],
            },
        },
        "areas": [
            {"name": "Arquitectura estructural", "weight": 20, "score": 90, "formula": "f"},
        ],
        "improvements": [{"area": "Arquitectura estructural", "action": "x", "area_gain": 10, "weighted_gain": 2.0}],
        "global_score": 85.0,
    }
    trend = {"message": "ok", "delta": 1.0, "improvements": [], "regressions": []}

    md = pa.render_markdown(snapshot, trend)
    assert "## Evidencias" in md
    assert "### Arquitectura" in md
    assert "## Tendencia" in md
    assert "## Score global ponderado" in md
