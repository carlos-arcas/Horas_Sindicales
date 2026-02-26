from __future__ import annotations

from collections.abc import Callable


def run_init_refresh(
    refresh_resumen: Callable[[], None],
    refresh_pendientes: Callable[[], None],
    refresh_historico: Callable[[], None],
    emit_log: Callable[[str], None],
) -> None:
    emit_log("UI_INIT_REFRESH_START")
    refresh_resumen()
    refresh_pendientes()
    refresh_historico()
    emit_log("UI_INIT_REFRESH_DONE")

