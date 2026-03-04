from __future__ import annotations

import pytest

from scripts import quality_gate


def test_preflight_falla_si_no_esta_pytest(monkeypatch, caplog) -> None:
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 1)

    with pytest.raises(SystemExit) as exc:
        quality_gate.preflight_pytest()

    assert exc.value.code == 2
    assert "Falta pytest" in caplog.text


def test_preflight_strict_falla_si_no_esta_pytest_cov(monkeypatch, caplog) -> None:
    monkeypatch.setenv("QUALITY_GATE_STRICT", "1")
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        quality_gate.importlib.util,
        "find_spec",
        lambda name: None if name == "pytest_cov" else object(),
    )

    with pytest.raises(SystemExit) as exc:
        quality_gate.preflight_pytest()

    assert exc.value.code == 2
    assert "Falta pytest-cov" in caplog.text


def test_preflight_ok_con_pytest_dependencias(monkeypatch) -> None:
    monkeypatch.setenv("QUALITY_GATE_STRICT", "1")
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(quality_gate.importlib.util, "find_spec", lambda _name: object())

    data = quality_gate.preflight_pytest()

    assert data["degraded_mode"] is False
    assert data["checks_omitidos"] == []


def test_preflight_falla_si_no_esta_radon(monkeypatch, caplog) -> None:
    monkeypatch.setenv("QUALITY_GATE_STRICT", "1")
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        quality_gate.importlib.util,
        "find_spec",
        lambda name: None if name == "radon" else object(),
    )

    with pytest.raises(SystemExit) as exc:
        quality_gate.preflight_pytest()

    assert exc.value.code == 2
    assert "Falta radon" in caplog.text


def test_preflight_falla_si_no_esta_pip_audit(monkeypatch, caplog) -> None:
    monkeypatch.setenv("QUALITY_GATE_STRICT", "1")
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        quality_gate.importlib.util,
        "find_spec",
        lambda name: None if name == "pip_audit" else object(),
    )

    with pytest.raises(SystemExit) as exc:
        quality_gate.preflight_pytest()

    assert exc.value.code == 2
    assert "Falta pip-audit" in caplog.text
