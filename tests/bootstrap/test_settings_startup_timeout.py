from __future__ import annotations

from app.configuracion.settings import STARTUP_TIMEOUT_MS_POR_DEFECTO, resolver_startup_timeout_ms


def test_resolver_startup_timeout_ms_con_env_nuevo(monkeypatch) -> None:
    monkeypatch.setenv("HORAS_SINDICALES_STARTUP_TIMEOUT_MS", "1234")
    assert resolver_startup_timeout_ms() == 1234


def test_resolver_startup_timeout_ms_fallback_default(monkeypatch) -> None:
    monkeypatch.delenv("HORAS_SINDICALES_STARTUP_TIMEOUT_MS", raising=False)
    monkeypatch.setenv("HORAS_STARTUP_TIMEOUT_MS", "invalido")
    assert resolver_startup_timeout_ms() == STARTUP_TIMEOUT_MS_POR_DEFECTO
