from __future__ import annotations

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
    monkeypatch.setattr(quality_gate, "QUALITY_REPORT_TXT", logs / "quality_report.txt")


def _set_checks_base(monkeypatch) -> None:
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
    monkeypatch.setattr(
        quality_gate,
        "run_i18n_hardcode_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "i18n ok"},
    )
    monkeypatch.setattr(
        quality_gate,
        "run_cc_targets_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "targets=1, failing=0"},
    )


def test_preflight_strict_falla_si_no_esta_mypy(monkeypatch, caplog) -> None:
    monkeypatch.setenv("QUALITY_GATE_STRICT", "1")
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        quality_gate.importlib.util,
        "find_spec",
        lambda name: None if name == "mypy" else object(),
    )

    with pytest.raises(SystemExit) as exc:
        quality_gate.preflight_pytest()

    assert exc.value.code == 2
    assert "Falta typecheck" in caplog.text


def test_preflight_non_strict_degrada_si_no_esta_mypy(monkeypatch) -> None:
    monkeypatch.setenv("QUALITY_GATE_STRICT", "0")
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        quality_gate.importlib.util,
        "find_spec",
        lambda name: None if name == "mypy" else object(),
    )

    data = quality_gate.preflight_pytest()

    assert data["degraded_mode"] is True
    assert "typecheck" in data["checks_omitidos"]


def test_typecheck_presente_con_errores_marca_fail(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    _set_checks_base(monkeypatch)

    resultado = quality_gate.build_report(
        pytest_runner=_Runner(),
        typecheck_runner=lambda: {
            "status": "FAIL",
            "errores": ["app/domain/modelo.py:1: error: detalle"],
            "comando": "python -m mypy --config-file .config/mypy.ini",
            "exit_code": 1,
        },
    )

    assert resultado["typecheck"]["status"] == "FAIL"
    assert resultado["global_status"] == "FAIL"


def test_typecheck_presente_sin_errores_marca_pass(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    _set_checks_base(monkeypatch)

    resultado = quality_gate.build_report(
        pytest_runner=_Runner(),
        typecheck_runner=lambda: {
            "status": "PASS",
            "errores": [],
            "comando": "python -m mypy --config-file .config/mypy.ini",
            "exit_code": 0,
        },
    )

    assert resultado["typecheck"]["status"] == "PASS"
    assert resultado["global_status"] == "PASS"
