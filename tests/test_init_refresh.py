from __future__ import annotations

from app.ui.vistas.init_refresh import run_init_refresh


def test_run_init_refresh_calls_historico_and_logs_in_order() -> None:
    calls: list[str] = []

    run_init_refresh(
        refresh_resumen=lambda: calls.append("resumen"),
        refresh_pendientes=lambda: calls.append("pendientes"),
        refresh_historico=lambda: calls.append("historico"),
        emit_log=calls.append,
    )

    assert calls == [
        "UI_INIT_REFRESH_START",
        "resumen",
        "pendientes",
        "historico",
        "UI_INIT_REFRESH_DONE",
    ]
