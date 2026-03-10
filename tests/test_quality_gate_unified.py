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
    monkeypatch.setattr(quality_gate, "QUALITY_REPORT_TXT", logs / "quality_report.txt")


def _mock_i18n_guard_pass(monkeypatch) -> None:
    monkeypatch.setattr(
        quality_gate,
        "run_i18n_hardcode_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "i18n ok", "total_hallazgos": 0},
    )


def test_quality_gate_unified_pass(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    _mock_i18n_guard_pass(monkeypatch)
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
    monkeypatch.setattr(
        quality_gate,
        "run_cc_targets_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "targets=1, failing=0"},
    )

    results = quality_gate.build_report(pytest_runner=_Runner())

    assert results["global_status"] == "PASS"


def test_quality_gate_unified_fail_naming(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    _mock_i18n_guard_pass(monkeypatch)
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
    monkeypatch.setattr(
        quality_gate,
        "run_cc_targets_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "targets=1, failing=0"},
    )

    results = quality_gate.build_report(pytest_runner=_Runner())

    assert results["naming"]["status"] == "FAIL"
    assert results["global_status"] == "FAIL"


def test_quality_gate_unified_fail_coverage(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    _mock_i18n_guard_pass(monkeypatch)
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
    monkeypatch.setattr(
        quality_gate,
        "run_cc_targets_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "targets=1, failing=0"},
    )

    results = quality_gate.build_report(pytest_runner=_Runner())

    assert results["coverage"]["status"] == "FAIL"
    assert results["global_status"] == "FAIL"


def test_quality_gate_unified_json_structure(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    _mock_i18n_guard_pass(monkeypatch)
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
        "run_cc_targets_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "targets=1, failing=0"},
    )

    quality_gate.build_report(pytest_runner=_Runner())

    payload = json.loads((tmp_path / "logs" / "quality_report.json").read_text(encoding="utf-8"))
    results = payload["results"]

    assert set(results) >= {
        "coverage",
        "cc_budget",
        "cc_targets",
        "architecture",
        "naming",
        "secrets",
        "release_contract",
        "degraded_mode",
        "degraded_reason",
        "checks_omitidos",
        "reason_code",
        "strict_mode",
        "global_status",
    }


def test_sin_pytest_cov_modo_strict_hace_hard_fail(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    monkeypatch.setenv("QUALITY_GATE_STRICT", "1")
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(quality_gate.importlib.util, "find_spec", lambda _name: None)

    with pytest.raises(SystemExit) as exc:
        quality_gate.main([])

    assert exc.value.code == 2


def test_sin_pytest_cov_non_strict_modo_degradado(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    _mock_i18n_guard_pass(monkeypatch)
    monkeypatch.setenv("QUALITY_GATE_STRICT", "0")
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
    monkeypatch.setattr(
        quality_gate,
        "run_cc_targets_guard",
        lambda *_args, **_kwargs: {"status": "PASS", "detail": "targets=1, failing=0"},
    )
    monkeypatch.setattr(quality_gate, "run_pytest_coverage", _should_not_run_coverage)

    exit_code = quality_gate.main([])

    assert exit_code == 0
    payload = json.loads((tmp_path / "logs" / "quality_report.json").read_text(encoding="utf-8"))
    results = payload["results"]

    assert results["coverage"]["status"] == "SKIP"
    assert results["global_status"] == "DEGRADED"
    assert results["degraded_mode"] is True
    assert results["checks_omitidos"] == ["pytest-cov", "radon", "pip-audit"]
    assert results["reason_code"] == "QUALITY_GATE_DEGRADED_MISSING_DEPS"
    report_md = (tmp_path / "logs" / "quality_report.md").read_text(encoding="utf-8")
    report_txt = (tmp_path / "logs" / "quality_report.txt").read_text(encoding="utf-8")
    assert "## checks_omitidos" in report_md
    assert "pytest-cov" in report_md
    assert "checks_omitidos=pytest-cov, radon, pip-audit" in report_txt
    assert counters["contractual"] == 4
    assert counters["naming"] == 1


def test_build_report_fuerza_no_cargar_pytestqt_en_runner_core(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    _mock_i18n_guard_pass(monkeypatch)
    monkeypatch.setattr(quality_gate, "load_config", lambda: {"coverage_fail_under_core": 80, "core_coverage_targets": ["app"]})

    llamadas: list[list[str]] = []

    class _RunnerSpy:
        def __call__(self, args: list[str]) -> int:
            llamadas.append(args)
            return 0

    def _fake_coverage(_threshold, _targets, _records, pytest_runner):
        exit_code = pytest_runner(["-q", "-m", "not ui"])
        assert exit_code == 0
        return {"status": "PASS", "detail": "coverage ok", "value": 88.0}

    monkeypatch.setattr(quality_gate, "run_pytest_coverage", _fake_coverage)
    monkeypatch.setattr(quality_gate, "run_contractual_test", lambda *_a, **_k: {"status": "PASS", "detail": "ok", "exit_code": 0})
    monkeypatch.setattr(quality_gate, "run_naming_guard", lambda *_a, **_k: {"status": "PASS", "detail": "naming ok"})
    monkeypatch.setattr(quality_gate, "run_cc_targets_guard", lambda *_a, **_k: {"status": "PASS", "detail": "targets=1, failing=0"})

    resultado = quality_gate.build_report(pytest_runner=_RunnerSpy())

    assert resultado["global_status"] == "PASS"
    assert llamadas
    assert llamadas[0][:6] == ["-p", "pytest_cov", "-p", "no:pytestqt", "-p", "no:pytestqt.plugin"]
    assert llamadas[0][6:] == ["-q", "-m", "not ui"]


def test_build_report_aplica_entorno_core_no_ui_en_todos_los_subruns(monkeypatch, tmp_path: Path) -> None:
    _set_temp_reports(monkeypatch, tmp_path)
    _mock_i18n_guard_pass(monkeypatch)
    monkeypatch.setattr(quality_gate, "load_config", lambda: {"coverage_fail_under_core": 80, "core_coverage_targets": ["app"]})

    trazas_entorno: list[dict[str, str | None]] = []

    class _RunnerSpy:
        def __call__(self, _args: list[str]) -> int:
            trazas_entorno.append(
                {
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": quality_gate.os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD"),
                    "PYTEST_CORE_SIN_QT": quality_gate.os.environ.get("PYTEST_CORE_SIN_QT"),
                }
            )
            return 0

    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)
    monkeypatch.setenv("PYTEST_CORE_SIN_QT", "0")
    monkeypatch.setattr(
        quality_gate,
        "run_pytest_coverage",
        lambda _threshold, _targets, _records, pytest_runner: (
            pytest_runner(["-q", "-m", "not ui"]),
            {"status": "PASS", "detail": "coverage ok", "value": 88.0},
        )[1],
    )
    monkeypatch.setattr(quality_gate, "run_contractual_test", lambda *_a, **_k: {"status": "PASS", "detail": "ok", "exit_code": 0})
    monkeypatch.setattr(quality_gate, "run_naming_guard", lambda *_a, **_k: {"status": "PASS", "detail": "naming ok"})
    monkeypatch.setattr(quality_gate, "run_cc_targets_guard", lambda *_a, **_k: {"status": "PASS", "detail": "targets=1, failing=0"})

    resultado = quality_gate.build_report(pytest_runner=_RunnerSpy())

    assert resultado["global_status"] == "PASS"
    assert len(trazas_entorno) == 1
    assert trazas_entorno[0] == {
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_CORE_SIN_QT": "1",
    }
    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD" not in quality_gate.os.environ
    assert quality_gate.os.environ["PYTEST_CORE_SIN_QT"] == "0"


def test_preflight_pytest_ejecuta_version_con_entorno_core_no_ui(monkeypatch) -> None:
    trazas: list[dict[str, object]] = []

    def _pytest_main_spy(args: list[str]) -> int:
        trazas.append(
            {
                "args": args,
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": quality_gate.os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD"),
                "PYTEST_CORE_SIN_QT": quality_gate.os.environ.get("PYTEST_CORE_SIN_QT"),
            }
        )
        return 0

    monkeypatch.setattr(quality_gate.pytest, "main", _pytest_main_spy)
    monkeypatch.setattr(quality_gate.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)
    monkeypatch.setenv("PYTEST_CORE_SIN_QT", "0")

    resultado = quality_gate.preflight_pytest()

    assert resultado["degraded_mode"] is False
    assert trazas == [
        {
            "args": ["-p", "no:pytestqt", "-p", "no:pytestqt.plugin", "--version"],
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTEST_CORE_SIN_QT": "1",
        }
    ]
    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD" not in quality_gate.os.environ
    assert quality_gate.os.environ["PYTEST_CORE_SIN_QT"] == "0"
