from __future__ import annotations

import json
import subprocess
import sys

import pytest


def test_on_startup_timeout_funciona_con_stub_qt_en_subprocess() -> None:
    codigo = r'''
import importlib
import json
import sys
import types

qtcore = types.ModuleType("PySide6.QtCore")

class _QObject:
    def __init__(self, *args, **kwargs):
        pass

class _QTimer:
    @staticmethod
    def singleShot(_ms, callback):
        callback()

def _slot(*_args, **_kwargs):
    def _decorador(fn):
        return fn
    return _decorador

qtcore.QObject = _QObject
qtcore.QTimer = _QTimer
qtcore.Slot = _slot

pyside6 = types.ModuleType("PySide6")
pyside6.QtCore = qtcore

sys.modules["PySide6"] = pyside6
sys.modules["PySide6.QtCore"] = qtcore

modulo = importlib.import_module("app.entrypoints.coordinador_arranque")
setattr(modulo, "es_objeto_qt_valido", lambda _obj: True)

class _I18nDummy:
    def t(self, key: str, **kwargs) -> str:
        if kwargs:
            return f"{key}:{kwargs}"
        return key

class _TimerDummy:
    def stop(self) -> None:
        return

class _SplashDummy:
    def set_status(self, _etapa: str) -> None:
        return
    def hide(self) -> None:
        return

class _ThreadDummy:
    def quit(self) -> None:
        return

eventos = []

def _fallo_arranque_handler(**kwargs):
    eventos.append(kwargs)
    return "INC"

coordinador = modulo.CoordinadorArranque(
    app=object(),
    i18n=_I18nDummy(),
    splash=_SplashDummy(),
    startup_timeout_ms=10,
    startup_thread=_ThreadDummy(),
    startup_worker=object(),
    watchdog_timer=_TimerDummy(),
    main_window_factory=lambda *_a, **_k: object(),
    orquestador_factory=lambda *_a, **_k: object(),
    instalar_menu_ayuda=lambda *_a, **_k: None,
    fallo_arranque_handler=_fallo_arranque_handler,
)
coordinador._on_startup_timeout()
print(json.dumps({
    "boot_timeout": coordinador._boot_timeout_disparado,
    "etapa": coordinador.ultima_etapa,
    "mensaje_usuario": eventos[0]["mensaje_usuario"],
}))
'''
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0 and "Problem importing shibokensupport" in resultado.stderr:
        pytest.skip("Entorno no permite stub PySide6/shiboken en subprocess")
    assert resultado.returncode == 0, resultado.stderr
    payload = json.loads(resultado.stdout.strip())
    assert payload == {
        "boot_timeout": True,
        "etapa": "startup_timeout",
        "mensaje_usuario": "startup_timeout_title",
    }
