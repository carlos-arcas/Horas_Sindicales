from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Any


def cargar_modulo_toast_con_stubs() -> ModuleType:
    """Carga `app.ui.widgets.toast` con stubs mínimos para evitar runtime Qt."""

    modulo_dialogo = ModuleType("app.ui.widgets.dialogo_detalles_toast")
    modulo_dialogo.DialogoDetallesNotificacion = type("DialogoDetallesNotificacion", (), {})

    modulo_overlay = ModuleType("app.ui.widgets.overlay_toast")
    modulo_overlay.CapaToasts = type("CapaToasts", (), {})

    modulo_widget_toast = ModuleType("app.ui.widgets.widget_toast")
    modulo_widget_toast.NotificacionToast = type("NotificacionToast", (), {})
    modulo_widget_toast.TarjetaToast = type("TarjetaToast", (), {})

    class _GestorToastsBase:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.ultima_carga: dict[str, object] | None = None

        def show(self, **kwargs: Any) -> None:
            self.ultima_carga = kwargs

    modulo_gestor = ModuleType("app.ui.widgets.gestor_toasts")
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
