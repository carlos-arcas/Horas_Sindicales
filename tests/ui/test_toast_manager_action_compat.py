from __future__ import annotations

import pytest

from tests.ui.toast_test_helpers import assert_toast_con_accion, instrumentar_manager_con_registro

try:
    from app.ui.widgets.toast import GestorToasts, ToastManager
except ImportError as exc:  # pragma: no cover - entorno sin librerías Qt
    pytest.skip(f"Qt no disponible para test de compat toast: {exc}", allow_module_level=True)


def _assert_accepts_action_kwargs(manager: GestorToasts) -> None:
    called = instrumentar_manager_con_registro(manager)

    manager.success("x", title="t", action_label="Abrir", action_callback=lambda: None)
    manager.error("x", action_label="Detalles", action_callback=lambda: None)

    assert len(called) == 2
    assert_toast_con_accion(called[0], nivel="success", etiqueta_accion="Abrir")
    assert_toast_con_accion(called[1], nivel="error", etiqueta_accion="Detalles")


def test_gestor_toasts_success_error_accept_action_kwargs() -> None:
    _assert_accepts_action_kwargs(GestorToasts())


def test_toast_manager_alias_success_error_accept_action_kwargs() -> None:
    _assert_accepts_action_kwargs(ToastManager())
