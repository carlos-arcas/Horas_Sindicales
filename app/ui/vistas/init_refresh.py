from __future__ import annotations

from collections.abc import Callable


def run_init_refresh(
    refresh_resumen: Callable[[], None],
    refresh_pendientes: Callable[[], None],
    refresh_historico: Callable[[], None],
    emit_log: Callable[[str, dict[str, object] | None], None] | None = None,
) -> None:
    def emit_log_noop(_msg: str, _extra: dict[str, object] | None = None) -> None:
        return None

    emit_log_safe = emit_log_noop if emit_log is None else emit_log
    emit_log_safe("UI_INIT_REFRESH_START")
    refresh_resumen()
    refresh_pendientes()
    refresh_historico()
    emit_log_safe("UI_INIT_REFRESH_DONE")
