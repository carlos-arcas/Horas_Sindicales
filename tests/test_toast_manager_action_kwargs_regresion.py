from __future__ import annotations

import importlib
import logging
import sys
import types
from typing import Any


def _cargar_modulo_toast_sin_qt() -> types.ModuleType:
    modulo_dialogo = types.ModuleType("app.ui.widgets.dialogo_detalles_toast")
    modulo_dialogo.DialogoDetallesNotificacion = type("DialogoDetallesNotificacion", (), {})

    modulo_overlay = types.ModuleType("app.ui.widgets.overlay_toast")
    modulo_overlay.CapaToasts = type("CapaToasts", (), {})

    modulo_widget_toast = types.ModuleType("app.ui.widgets.widget_toast")
    modulo_widget_toast.NotificacionToast = type("NotificacionToast", (), {})
    modulo_widget_toast.TarjetaToast = type("TarjetaToast", (), {})

    class _GestorToastsBase:
        def show(self, **kwargs: Any) -> None:
            return None

    modulo_gestor = types.ModuleType("app.ui.widgets.gestor_toasts")
    modulo_gestor.GestorToasts = _GestorToastsBase

    for modulo in (modulo_dialogo, modulo_overlay, modulo_widget_toast, modulo_gestor):
        sys.modules[modulo.__name__] = modulo

    sys.modules.pop("app.ui.widgets.toast", None)
    return importlib.import_module("app.ui.widgets.toast")


def test_toast_manager_success_error_aceptan_action_kwargs() -> None:
    modulo_toast = _cargar_modulo_toast_sin_qt()
    manager = modulo_toast.ToastManager()

    manager.success("ok", action_label="Abrir", action_callback=lambda: None)
    manager.error("error", action_label="Reintentar", action_callback=lambda: None)


def test_toast_manager_action_incompleta_loggea_warning(caplog) -> None:
    modulo_toast = _cargar_modulo_toast_sin_qt()
    manager = modulo_toast.ToastManager()
    capturas: list[dict[str, Any]] = []

    def _show_captura(**kwargs: Any) -> None:
        capturas.append(kwargs)

    manager.show = _show_captura  # type: ignore[method-assign]

    with caplog.at_level(logging.WARNING):
        manager.success("ok", action_label="Abrir")

    assert "TOAST_ACTION_INCOMPLETE" in caplog.text
    assert capturas[0]["action_label"] is None
    assert capturas[0]["action_callback"] is None


def test_toast_manager_degrada_si_backend_no_soporta_acciones(caplog) -> None:
    modulo_toast = _cargar_modulo_toast_sin_qt()
    manager = modulo_toast.ToastManager()
    capturas: list[dict[str, Any]] = []

    def _show_legacy(**kwargs: Any) -> None:
        if "action_label" in kwargs or "action_callback" in kwargs:
            raise TypeError("legacy show")
        capturas.append(kwargs)

    manager.show = _show_legacy  # type: ignore[method-assign]

    with caplog.at_level(logging.WARNING):
        manager.error("error", action_label="Abrir", action_callback=lambda: None)

    assert "TOAST_ACTION_NOT_SUPPORTED" in caplog.text
    assert capturas[0]["level"] == "error"
    assert "action_label" not in capturas[0]
