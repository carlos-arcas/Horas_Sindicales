from __future__ import annotations

from collections.abc import Callable
from typing import Any


def crear_show_estricto_con_registro() -> tuple[list[dict[str, object]], Callable[..., None]]:
    llamadas: list[dict[str, object]] = []

    def _show_estricto(
        *,
        message: str,
        level: str,
        title: str | None = None,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
        **_extras: object,
    ) -> None:
        llamadas.append(
            {
                "message": message,
                "level": level,
                "title": title,
                "action_label": action_label,
                "action_callback": action_callback,
            }
        )

    return llamadas, _show_estricto


def instrumentar_manager_con_registro(manager: Any) -> list[dict[str, object]]:
    llamadas, show_estricto = crear_show_estricto_con_registro()
    manager.show = show_estricto  # type: ignore[method-assign]
    return llamadas


def assert_toast_con_accion(
    carga: dict[str, object],
    *,
    nivel: str,
    etiqueta_accion: str,
) -> None:
    assert carga["level"] == nivel
    assert carga["action_label"] == etiqueta_accion
    assert callable(carga["action_callback"])
