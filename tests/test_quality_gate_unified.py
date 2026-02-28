from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import quality_gate


class _Runner:
    def __call__(self, _args: list[str]) -> int:
        return 0


def _set_temp_reports(monkeypatch, tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    monkeypatch.setattr(quality_gate, "LOGS_DIR", logs)
    monkeypatch.setattr(quality_gate, "QUALITY_REPORT_JSON", logs / "quality_report.json")
    monkeypatch.setattr(quality_gate, "QUALITY_REPORT_MD", logs / "quality_report.md")


def test_quality_gate_unified_pass(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    monkeypatch.setattr(quality_gate, "load_config", lambda: {"coverage_fail_under_core": 80, "core_coverage_targets": ["app"]})
    monkeypatch.setattr(
        quality_gate,
        "run_pytest_coverage",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "coverage ok", "value": 86.5},
    )
    monkeypatch.setattr(
        quality_gate,
        "run_contractual_test",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "ok", "exit_code": 0},
    )
    monkeypatch.setattr(
        quality_gate,
        "run_naming_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "naming ok"},
    )

    results = quality_gate.build_report(pytest_runner=_Runner())

    assert results["global_status"] == "PASS"


def test_quality_gate_unified_fail_naming(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    monkeypatch.setattr(quality_gate, "load_config", lambda: {"coverage_fail_under_core": 80, "core_coverage_targets": ["app"]})
    monkeypatch.setattr(
        quality_gate,
        "run_pytest_coverage",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "coverage ok", "value": 90},
    )
    monkeypatch.setattr(
        quality_gate,
        "run_contractual_test",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "ok", "exit_code": 0},
    )
    monkeypatch.setattr(
        quality_gate,
        "run_naming_guard",
        lambda *_args, **_kwargs: {"status": "FAIL", "detail": "nuevos offenders"},
    )

    results = quality_gate.build_report(pytest_runner=_Runner())

    assert results["naming"]["status"] == "FAIL"
    assert results["global_status"] == "FAIL"


def test_quality_gate_unified_fail_coverage(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    monkeypatch.setattr(quality_gate, "load_config", lambda: {"coverage_fail_under_core": 80, "core_coverage_targets": ["app"]})
    monkeypatch.setattr(
        quality_gate,
        "run_pytest_coverage",
        lambda *_args, **_kwargs: {"status": "FAIL", "detail": "coverage bajo", "value": 70},
    )
    monkeypatch.setattr(
        quality_gate,
        "run_contractual_test",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "ok", "exit_code": 0},
    )
    monkeypatch.setattr(
        quality_gate,
        "run_naming_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "naming ok"},
    )

    results = quality_gate.build_report(pytest_runner=_Runner())

    assert results["coverage"]["status"] == "FAIL"
    assert results["global_status"] == "FAIL"


def test_quality_gate_unified_json_structure(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    monkeypatch.setattr(quality_gate, "load_config", lambda: {"coverage_fail_under_core": 80, "core_coverage_targets": ["app"]})
    monkeypatch.setattr(
        quality_gate,
        "run_pytest_coverage",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "coverage ok", "value": 90},
    )
    monkeypatch.setattr(
        quality_gate,
        "run_contractual_test",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "ok", "exit_code": 0},
    )
    monkeypatch.setattr(
        quality_gate,
        "run_naming_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "naming ok"},
    )

    quality_gate.build_report(pytest_runner=_Runner())

    payload = json.loads((tmp_path / "logs" / "quality_report.json").read_text(encoding="utf-8"))
    results = payload["results"]

    assert set(results) >= {
        "coverage",
        "cc_budget",
        "architecture",
        "naming",
        "secrets",
        "release_contract",
        "degraded_mode",
        "degraded_reason",
        "global_status",
    }


def test_sin_pytest_cov_y_sin_flag_hace_hard_fail(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(quality_gate.importlib.util, "find_spec", lambda _name: None)

    with pytest.raises(SystemExit) as exc:
        quality_gate.main([])

    assert exc.value.code == 2


def test_sin_pytest_cov_con_flag_modo_degradado(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(quality_gate.importlib.util, "find_spec", lambda _name: None)
    monkeypatch.setattr(quality_gate, "load_config", lambda: {"coverage_fail_under_core": 80, "core_coverage_targets": ["app"]})

    counters = {"contractual": 0, "naming": 0}

    def _fake_contractual(*_args, **_kwargs):
        counters["contractual"] += 1
        return {"status": "PASS", "detail": "ok", "exit_code": 0}

    def _fake_naming(*_args, **_kwargs):
        counters["naming"] += 1
        return {"status": "PASS", "detail": "naming ok"}

    def _should_not_run_coverage(*_args, **_kwargs):
        raise AssertionError("run_pytest_coverage no debe ejecutarse en modo degradado")

    monkeypatch.setattr(quality_gate, "run_contractual_test", _fake_contractual)
    monkeypatch.setattr(quality_gate, "run_naming_guard", _fake_naming)
    monkeypatch.setattr(quality_gate, "run_pytest_coverage", _should_not_run_coverage)

    exit_code = quality_gate.main(["--allow-missing-pytest-cov"])

    assert exit_code == 1
    payload = json.loads((tmp_path / "logs" / "quality_report.json").read_text(encoding="utf-8"))
    results = payload["results"]

    assert results["coverage"]["status"] == "SKIP"
    assert results["global_status"] == "FAIL"
    assert results["degraded_mode"] is True
    assert "pytest-cov no disponible" in results["degraded_reason"]
    assert counters["contractual"] == 4
    assert counters["naming"] == 1
