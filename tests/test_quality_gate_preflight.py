from __future__ import annotations

import pytest

from scripts import quality_gate


def test_preflight_falla_si_no_esta_pytest(monkeypatch, caplog) -> None:
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 1)

    with pytest.raises(SystemExit) as exc:
        quality_gate.preflight_pytest()

    assert exc.value.code == 2
    assert "Falta pytest" in caplog.text


def test_preflight_falla_si_no_esta_pytest_cov(monkeypatch, caplog) -> None:
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(quality_gate.importlib.util, "find_spec", lambda _name: None)

    with pytest.raises(SystemExit) as exc:
        quality_gate.preflight_pytest()

    assert exc.value.code == 2
    assert "Falta pytest-cov" in caplog.text


def test_preflight_ok_con_pytest_y_pytest_cov(monkeypatch) -> None:
    monkeypatch.setattr(quality_gate.pytest, "main", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(quality_gate.importlib.util, "find_spec", lambda _name: object())

    quality_gate.preflight_pytest()
