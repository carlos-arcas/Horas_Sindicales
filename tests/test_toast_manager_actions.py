from __future__ import annotations

import ast
import logging
from pathlib import Path

from app.ui.toasts.ejecutar_callback_seguro import ejecutar_callback_seguro


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module_ast(relative_path: str) -> ast.Module:
    source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    return ast.parse(source)


def _get_class_method(module: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return item
    raise AssertionError(f"No se encontró {class_name}.{method_name}")


def test_success_and_error_signature_support_action_params() -> None:
    module = _load_module_ast("app/ui/widgets/toast.py")

    for method_name in ("success", "error"):
        method = _get_class_method(module, "GestorToasts", method_name)
        kwonly = {arg.arg for arg in method.args.kwonlyargs}
        assert "action_label" in kwonly
        assert "action_callback" in kwonly


def test_payload_internal_contains_action_fields() -> None:
    module = _load_module_ast("app/ui/widgets/gestor_toasts.py")
    method = _get_class_method(module, "GestorToasts", "_crear_notificacion")

    notificacion_calls = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "NotificacionToast"
    ]
    assert notificacion_calls, "No se encontró construcción de NotificacionToast"

    keywords = {kw.arg for kw in notificacion_calls[0].keywords}
    assert "action_label" in keywords
    assert "action_callback" in keywords


def test_safe_wrapper_swallows_callback_exception_and_logs(caplog) -> None:
    caplog.set_level(logging.ERROR)

    def _boom() -> None:
        raise RuntimeError("boom")

    result = ejecutar_callback_seguro(
        _boom,
        logger=logging.getLogger("tests.toast"),
        contexto="toast:error:Reintentar",
        correlation_id="abc-123",
    )

    assert result is False
    assert "TOAST_ACTION_FAILED" in caplog.text


class _TimerStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None]] = []

    def stop(self) -> None:
        self.calls.append(("stop", None))

    def start(self, value: int) -> None:
        self.calls.append(("start", value))


class _TarjetaStub:
    def __init__(self) -> None:
        self.recibidas = []

    def actualizar_notificacion(self, notificacion) -> None:
        self.recibidas.append(notificacion)


def test_dedupe_update_reinicia_timer_y_callback_visible() -> None:
    module = _cargar_gestor_toasts_sin_qt()
    GestorToasts = module.GestorToasts
    NotificacionToast = module.NotificacionToast

    timer = _TimerStub()
    tarjeta = _TarjetaStub()
    def callback() -> None:
        return None
    gestor = type('GestorStub', (), {
        '_cache': {},
        '_visibles': {'toast-1': tarjeta},
        '_timers': {'toast-1': timer},
    })()
    notificacion = NotificacionToast(
        id='temp',
        titulo='Nuevo',
        mensaje='Actualizado',
        nivel='warning',
        action_label='Reintentar',
        action_callback=callback,
        dedupe_key='sync:error:sin_excepcion',
        duracion_ms=3210,
    )

    GestorToasts._actualizar_toast_dedupe(gestor, notificacion=notificacion, toast_id='toast-1')

    assert gestor._cache['toast-1'].action_callback is callback
    assert tarjeta.recibidas[0].action_callback is callback
    assert timer.calls == [('stop', None), ('start', 3210)]


def test_abrir_detalles_retiene_referencia_hasta_cerrar(monkeypatch) -> None:
    module = _cargar_gestor_toasts_sin_qt()
    NotificacionToast = module.NotificacionToast

    class _SignalStub:
        def __init__(self) -> None:
            self.callback = None

        def connect(self, callback) -> None:
            self.callback = callback

    class _DialogoStub:
        def __init__(self, notificacion, parent=None) -> None:
            self.notificacion = notificacion
            self.parent = parent
            self.finished = _SignalStub()
            self.exec_called = False

        def exec(self) -> None:
            self.exec_called = True
            assert gestor._dialogos_detalle['toast-1'] is self
            self.finished.callback(0)

    monkeypatch.setattr(module, 'DialogoDetallesNotificacion', _DialogoStub)
    gestor = type('GestorStub', (), {
        '_cache': {'toast-1': NotificacionToast(id='toast-1', titulo='t', mensaje='m', detalles='detalle')},
        '_host': object(),
        '_dialogos_detalle': {},
    })()

    module.GestorToasts._abrir_detalles(gestor, 'toast-1')

    assert gestor._dialogos_detalle == {}


def _cargar_gestor_toasts_sin_qt():
    import importlib
    import sys
    import types

    qtcore = types.ModuleType('PySide6.QtCore')
    qtcore.QEvent = type('QEvent', (), {'Resize': 1, 'Move': 2})
    qtcore.QObject = type('QObject', (), {'__init__': lambda self, parent=None: None})
    qtcore.QTimer = type('QTimer', (), {})
    qtcore.Qt = type('Qt', (), {'AlignmentFlag': type('AlignmentFlag', (), {'AlignHCenter': 0})})
    qtwidgets = types.ModuleType('PySide6.QtWidgets')
    qtwidgets.QWidget = type('QWidget', (), {})

    dialogo = types.ModuleType('app.ui.widgets.dialogo_detalles_toast')
    dialogo.DialogoDetallesNotificacion = type('DialogoDetallesNotificacion', (), {})
    overlay = types.ModuleType('app.ui.widgets.overlay_toast')
    overlay.CapaToasts = type('CapaToasts', (), {})

    from dataclasses import dataclass

    @dataclass
    class _NotificacionToast:
        id: str
        titulo: str
        mensaje: str
        nivel: str = 'info'
        detalles: str | None = None
        codigo: str | None = None
        correlacion_id: str | None = None
        origen: str | None = None
        action_label: str | None = None
        action_callback: object | None = None
        dedupe_key: str | None = None
        duracion_ms: int = 8000

    widget = types.ModuleType('app.ui.widgets.widget_toast')
    widget.NotificacionToast = _NotificacionToast
    widget.TarjetaToast = type('TarjetaToast', (), {})

    modulos_temporales = {
        'PySide6.QtCore': qtcore,
        'PySide6.QtWidgets': qtwidgets,
        'app.ui.widgets.dialogo_detalles_toast': dialogo,
        'app.ui.widgets.overlay_toast': overlay,
        'app.ui.widgets.widget_toast': widget,
    }
    nombres_restaurables = (
        *modulos_temporales.keys(),
        'app.ui.widgets.gestor_toasts',
    )
    modulos_previos = {nombre: sys.modules.get(nombre) for nombre in nombres_restaurables}

    try:
        for nombre, modulo in modulos_temporales.items():
            sys.modules[nombre] = modulo
        sys.modules.pop('app.ui.widgets.gestor_toasts', None)
        return importlib.import_module('app.ui.widgets.gestor_toasts')
    finally:
        for nombre, modulo_previo in modulos_previos.items():
            if modulo_previo is None:
                sys.modules.pop(nombre, None)
            else:
                sys.modules[nombre] = modulo_previo
