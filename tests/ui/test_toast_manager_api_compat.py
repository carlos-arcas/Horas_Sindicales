from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import pytest


@dataclass
class _NotificacionToast:
    mensaje: str = ""


class _GestorToastsBase:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.ultima_carga: dict[str, object] | None = None

    def show(self, **kwargs: object) -> None:
        self.ultima_carga = kwargs


class _TarjetaToast:
    pass


class _CapaToasts:
    pass


class _DialogoDetallesNotificacion:
    pass


def _cargar_modulo_toast() -> ModuleType:
    modulo_dialogo = ModuleType("app.ui.widgets.dialogo_detalles_toast")
    modulo_dialogo.DialogoDetallesNotificacion = _DialogoDetallesNotificacion

    modulo_base = ModuleType("app.ui.widgets.gestor_toasts")
    modulo_base.GestorToasts = _GestorToastsBase

    modulo_overlay = ModuleType("app.ui.widgets.overlay_toast")
    modulo_overlay.CapaToasts = _CapaToasts

    modulo_widget = ModuleType("app.ui.widgets.widget_toast")
    modulo_widget.NotificacionToast = _NotificacionToast
    modulo_widget.TarjetaToast = _TarjetaToast

    sys.modules[modulo_dialogo.__name__] = modulo_dialogo
    sys.modules[modulo_base.__name__] = modulo_base
    sys.modules[modulo_overlay.__name__] = modulo_overlay
    sys.modules[modulo_widget.__name__] = modulo_widget

    ruta = Path("app/ui/widgets/toast.py")
    spec = importlib.util.spec_from_file_location("tests.toast_module", ruta)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_success_acepta_action_label_action_callback() -> None:
    modulo = _cargar_modulo_toast()
    gestor = modulo.ToastManager()

    gestor.success("ok", action_label="Abrir", action_callback=lambda: None)

    assert gestor.ultima_carga is not None
    assert gestor.ultima_carga["action_label"] == "Abrir"
    assert callable(gestor.ultima_carga["action_callback"])


def test_error_acepta_action_label_action_callback() -> None:
    modulo = _cargar_modulo_toast()
    gestor = modulo.ToastManager()

    gestor.error("fallo", action_label="Ver", action_callback=lambda: None)

    assert gestor.ultima_carga is not None
    assert gestor.ultima_carga["action_label"] == "Ver"
    assert callable(gestor.ultima_carga["action_callback"])


def test_success_rechaza_kwargs_desconocidos_con_value_error() -> None:
    modulo = _cargar_modulo_toast()
    gestor = modulo.ToastManager()

    with pytest.raises(ValueError):
        gestor.success("ok", desconocido="x")


def test_error_rechaza_kwargs_desconocidos_con_value_error() -> None:
    modulo = _cargar_modulo_toast()
    gestor = modulo.ToastManager()

    with pytest.raises(ValueError):
        gestor.error("boom", inesperado=123)


def test_success_mapea_alias_action_text_y_action() -> None:
    modulo = _cargar_modulo_toast()
    gestor = modulo.ToastManager()

    def callback() -> None:
        return None

    gestor.success("ok", action_text="Detalle", action=callback)

    assert gestor.ultima_carga is not None
    assert gestor.ultima_carga["action_label"] == "Detalle"
    assert gestor.ultima_carga["action_callback"] is callback
