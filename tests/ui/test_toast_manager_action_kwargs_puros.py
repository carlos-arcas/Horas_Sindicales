from __future__ import annotations

import importlib
import inspect
import sys
import types
from typing import Any


def _cargar_modulo_toast_sin_qt() -> types.ModuleType:
    """Carga `app.ui.widgets.toast` con stubs mínimos para evitar runtime Qt."""

    modulo_dialogo = types.ModuleType("app.ui.widgets.dialogo_detalles_toast")
    modulo_dialogo.DialogoDetallesNotificacion = type("DialogoDetallesNotificacion", (), {})

    modulo_overlay = types.ModuleType("app.ui.widgets.overlay_toast")
    modulo_overlay.CapaToasts = type("CapaToasts", (), {})

    modulo_widget_toast = types.ModuleType("app.ui.widgets.widget_toast")
    modulo_widget_toast.NotificacionToast = type("NotificacionToast", (), {})
    modulo_widget_toast.TarjetaToast = type("TarjetaToast", (), {})

    class _GestorToastsBase:
        def show(self, **kwargs: Any) -> None:  # pragma: no cover - verificado vía monkeypatch en tests
            return None

    modulo_gestor = types.ModuleType("app.ui.widgets.gestor_toasts")
    modulo_gestor.GestorToasts = _GestorToastsBase

    stubs = {
        modulo_dialogo.__name__: modulo_dialogo,
        modulo_overlay.__name__: modulo_overlay,
        modulo_widget_toast.__name__: modulo_widget_toast,
        modulo_gestor.__name__: modulo_gestor,
    }

    for nombre, modulo in stubs.items():
        sys.modules[nombre] = modulo

    sys.modules.pop("app.ui.widgets.toast", None)
    return importlib.import_module("app.ui.widgets.toast")


def test_success_y_error_aceptan_action_kwargs_sin_typeerror() -> None:
    modulo_toast = _cargar_modulo_toast_sin_qt()
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
    modulo_toast = _cargar_modulo_toast_sin_qt()
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
    modulo_toast = _cargar_modulo_toast_sin_qt()

    firma_success = inspect.signature(modulo_toast.ToastManager.success)
    firma_error = inspect.signature(modulo_toast.ToastManager.error)

    for firma in (firma_success, firma_error):
        assert "action_label" in firma.parameters
        assert "action_callback" in firma.parameters
        assert firma.parameters["action_label"].default is None
        assert firma.parameters["action_callback"].default is None
