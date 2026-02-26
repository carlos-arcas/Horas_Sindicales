from __future__ import annotations

import scripts.preflight_tests as preflight


def test_preflight_script_exists() -> None:
    assert preflight.__file__, "Debe existir scripts/preflight_tests.py"


def test_preflight_exposes_main() -> None:
    assert hasattr(preflight, "main")
    assert callable(preflight.main)


def test_preflight_returns_missing_deps_when_pytest_cov_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(preflight, "_has_module", lambda name: name == "pytest")
    monkeypatch.setattr(preflight, "_pytest_cov_available", lambda: False)

    code = preflight.main([])
    assert code == preflight.EXIT_MISSING_DEPS


def test_preflight_returns_ok_with_optional_radon_missing(monkeypatch) -> None:
    monkeypatch.setattr(preflight, "_pytest_cov_available", lambda: True)

    def fake_has_module(name: str) -> bool:
        return name in {"pytest"}

    monkeypatch.setattr(preflight, "_has_module", fake_has_module)

    code = preflight.main([])
    assert code == preflight.EXIT_OK


def test_pytest_cov_available_requiere_import_y_flag_cov(monkeypatch) -> None:
    class DummyResult:
        returncode = 0
        stdout = "usage: pytest [options] --cov"

    monkeypatch.setattr(preflight.subprocess, "run", lambda *args, **kwargs: DummyResult())
    monkeypatch.setattr(preflight, "_has_module", lambda name: name in {"pytest_cov"})

    assert preflight._pytest_cov_available() is True


def test_pytest_cov_available_falla_si_help_no_expone_cov(monkeypatch) -> None:
    class DummyResult:
        returncode = 0
        stdout = "usage: pytest [options]"

    monkeypatch.setattr(preflight.subprocess, "run", lambda *args, **kwargs: DummyResult())
    monkeypatch.setattr(preflight, "_has_module", lambda name: name in {"pytest_cov"})

    assert preflight._pytest_cov_available() is False
