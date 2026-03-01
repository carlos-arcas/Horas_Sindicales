from __future__ import annotations

import pytest

try:
    from app.ui.widgets.toast import GestorToasts, ToastManager
except ImportError as exc:  # pragma: no cover - entorno sin librerías Qt
    pytest.skip(f"Qt no disponible para test de compat toast: {exc}", allow_module_level=True)


def _assert_accepts_action_kwargs(manager: GestorToasts) -> None:
    called: list[dict[str, object]] = []

    def _fake_show(*args: object, **kwargs: object) -> None:
        called.append(kwargs)

    manager.show = _fake_show  # type: ignore[method-assign]

    manager.success("x", title="t", action_label="Abrir", action_callback=lambda: None)
    manager.error("x", action_label="Detalles", action_callback=lambda: None)

    assert len(called) == 2
    assert called[0]["action_label"] == "Abrir"
    assert callable(called[0]["action_callback"])
    assert called[1]["action_label"] == "Detalles"
    assert callable(called[1]["action_callback"])


def test_gestor_toasts_success_error_accept_action_kwargs() -> None:
    _assert_accepts_action_kwargs(GestorToasts())


def test_toast_manager_alias_success_error_accept_action_kwargs() -> None:
    _assert_accepts_action_kwargs(ToastManager())
