from __future__ import annotations

import pytest

try:
    from app.ui.widgets.toast import ToastManager
except ImportError as exc:  # pragma: no cover - entorno sin stack Qt completo
    pytest.skip(f"Qt no disponible para test de compat kwargs toast: {exc}", allow_module_level=True)


def test_toast_manager_success_accepta_action_kwargs_y_extras() -> None:
    manager = ToastManager()
    llamadas: list[dict[str, object]] = []

    def _show_estricto(*, message: str, level: str, title: str | None = None, action_label: str | None = None, action_callback=None) -> None:
        llamadas.append(
            {
                "message": message,
                "level": level,
                "title": title,
                "action_label": action_label,
                "action_callback": action_callback,
            }
        )

    manager.show = _show_estricto  # type: ignore[method-assign]

    manager.success(
        "ok",
        title="titulo",
        action_label="Ver",
        action_callback=lambda: None,
        kwargs_desconocido=True,
    )

    assert len(llamadas) == 1
    assert llamadas[0]["level"] == "success"
    assert llamadas[0]["action_label"] == "Ver"
    assert callable(llamadas[0]["action_callback"])


def test_toast_manager_error_accepta_action_kwargs_y_extras() -> None:
    manager = ToastManager()
    llamadas: list[dict[str, object]] = []

    def _show_estricto(*, message: str, level: str, title: str | None = None, action_label: str | None = None, action_callback=None) -> None:
        llamadas.append(
            {
                "message": message,
                "level": level,
                "title": title,
                "action_label": action_label,
                "action_callback": action_callback,
            }
        )

    manager.show = _show_estricto  # type: ignore[method-assign]

    manager.error(
        "error",
        action_label="Detalles",
        action_callback=lambda: None,
        action_style="primario",
    )

    assert len(llamadas) == 1
    assert llamadas[0]["level"] == "error"
    assert llamadas[0]["action_label"] == "Detalles"
    assert callable(llamadas[0]["action_callback"])
