from __future__ import annotations

import pytest

from app.entrypoints import main as entrypoint_main


@pytest.fixture
def _common_main_mocks(monkeypatch):
    stages: list[str] = []
    monkeypatch.setattr(entrypoint_main, "resolve_log_dir", lambda: "/tmp/logs")
    monkeypatch.setattr(
        entrypoint_main,
        "init_boot_diagnostics",
        lambda log_dir: stages.append(f"boot:{log_dir}"),
    )
    monkeypatch.setattr(
        entrypoint_main, "marcar_stage", lambda stage: stages.append(stage)
    )
    monkeypatch.setattr(
        entrypoint_main,
        "configure_logging",
        lambda log_dir: stages.append(f"configure:{log_dir}"),
    )
    monkeypatch.setattr(entrypoint_main, "manejar_excepcion_global", object())
    monkeypatch.setattr(entrypoint_main.os, "getenv", lambda _name: None)
    return stages


def test_main_ejecuta_flush_en_ruta_normal(monkeypatch, _common_main_mocks) -> None:
    flush_calls: list[str] = []
    monkeypatch.setattr(entrypoint_main, "run_ui", lambda: 7)
    monkeypatch.setattr(
        entrypoint_main, "flush_logging_handlers", lambda: flush_calls.append("flush")
    )

    result = entrypoint_main.main([])

    assert result == 7
    assert flush_calls == ["flush"]


def test_main_ejecuta_flush_en_finally_si_run_ui_falla(
    monkeypatch, _common_main_mocks
) -> None:
    flush_calls: list[str] = []

    def _raise() -> int:
        raise RuntimeError("fallo-ui")

    monkeypatch.setattr(entrypoint_main, "run_ui", _raise)
    monkeypatch.setattr(
        entrypoint_main, "flush_logging_handlers", lambda: flush_calls.append("flush")
    )

    with pytest.raises(RuntimeError, match="fallo-ui"):
        entrypoint_main.main([])

    assert flush_calls == ["flush"]
