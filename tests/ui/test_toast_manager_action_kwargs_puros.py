from __future__ import annotations

import inspect
from typing import Any

from tests.ui.toast_module_loader import cargar_modulo_toast_con_stubs


def test_success_y_error_aceptan_action_kwargs_sin_typeerror() -> None:
    modulo_toast = cargar_modulo_toast_con_stubs()
    manager = modulo_toast.ToastManager()
    llamadas: list[dict[str, Any]] = []

    def _show_captura(**kwargs: Any) -> None:
        llamadas.append(kwargs)

    manager.show = _show_captura  # type: ignore[method-assign]

    manager.success("ok", action_label="Abrir", action_callback=lambda: None)
    manager.error("fallo", action_label="Detalles", action_callback=lambda: None)

    assert len(llamadas) == 2
    assert llamadas[0]["action_label"] == "Abrir"
    assert callable(llamadas[0]["action_callback"])
    assert llamadas[1]["action_label"] == "Detalles"
    assert callable(llamadas[1]["action_callback"])


def test_action_callback_no_callable_se_ignora_de_forma_segura() -> None:
    modulo_toast = cargar_modulo_toast_con_stubs()
    manager = modulo_toast.ToastManager()
    llamadas: list[dict[str, Any]] = []

    def _show_captura(**kwargs: Any) -> None:
        llamadas.append(kwargs)

    manager.show = _show_captura  # type: ignore[method-assign]

    manager.success("ok", action_label="Abrir", action_callback="invalido")

    assert len(llamadas) == 1
    assert llamadas[0]["action_label"] == "Abrir"
    assert llamadas[0]["action_callback"] is None


def test_firma_expone_parametros_opcionales_de_accion() -> None:
    modulo_toast = cargar_modulo_toast_con_stubs()

    firma_success = inspect.signature(modulo_toast.ToastManager.success)
    firma_error = inspect.signature(modulo_toast.ToastManager.error)

    for firma in (firma_success, firma_error):
        assert "action_label" in firma.parameters
        assert "action_callback" in firma.parameters
        assert firma.parameters["action_label"].default is None
        assert firma.parameters["action_callback"].default is None
