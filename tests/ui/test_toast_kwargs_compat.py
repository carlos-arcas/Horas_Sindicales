from __future__ import annotations

import pytest

from tests.ui.toast_test_helpers import crear_show_estricto_con_registro

try:
    from app.ui.widgets.toast import ToastManager
except ImportError as exc:  # pragma: no cover - entorno sin stack Qt completo
    pytest.skip(f"Qt no disponible para test de compat kwargs toast: {exc}", allow_module_level=True)


def test_toast_manager_success_accepta_action_kwargs_y_extras() -> None:
    manager = ToastManager()
    llamadas, show_estricto = crear_show_estricto_con_registro()

    manager.show = show_estricto  # type: ignore[method-assign]

    manager.success(
        "ok",
        title="titulo",
        action_text="Ver",
        action=lambda: None,
    )

    assert len(llamadas) == 1
    assert llamadas[0]["level"] == "success"
    assert llamadas[0]["action_label"] == "Ver"
    assert callable(llamadas[0]["action_callback"])


def test_toast_manager_error_accepta_action_kwargs_y_extras() -> None:
    manager = ToastManager()
    llamadas, show_estricto = crear_show_estricto_con_registro()

    manager.show = show_estricto  # type: ignore[method-assign]

    manager.error(
        "error",
        action_text="Detalles",
        action=lambda: None,
    )

    assert len(llamadas) == 1
    assert llamadas[0]["level"] == "error"
    assert llamadas[0]["action_label"] == "Detalles"
    assert callable(llamadas[0]["action_callback"])
