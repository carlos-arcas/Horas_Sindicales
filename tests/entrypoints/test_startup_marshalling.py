from __future__ import annotations

import json
import subprocess
import sys


def test_on_finished_signal_received_solo_encola_en_subprocess() -> None:
    codigo = r'''
import importlib
import json
import sys
import types

qtcore = types.ModuleType("PySide6.QtCore")

class _SignalDescriptor:
    def __init__(self, *_args, **_kwargs):
        self._nombre = None

    def __set_name__(self, owner, name):
        self._nombre = "_signal_" + name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        signal = instance.__dict__.get(self._nombre)
        if signal is None:
            signal = _SignalInstance()
            instance.__dict__[self._nombre] = signal
        return signal

class _SignalInstance:
    def __init__(self):
        self.payloads = []
        self.callbacks = []

    def connect(self, callback, *_args, **_kwargs):
        self.callbacks.append(callback)

    def emit(self, payload):
        self.payloads.append(payload)

class _QObject:
    def __init__(self, *args, **kwargs):
        pass

class _Qt:
    class ConnectionType:
        QueuedConnection = object()


def _slot(*_args, **_kwargs):
    def _decorador(fn):
        return fn
    return _decorador

qtcore.QObject = _QObject
qtcore.Signal = _SignalDescriptor
qtcore.Qt = _Qt
qtcore.Slot = _slot

pyside6 = types.ModuleType("PySide6")
pyside6.QtCore = qtcore

sys.modules["PySide6"] = pyside6
sys.modules["PySide6.QtCore"] = qtcore

modulo = importlib.import_module("app.entrypoints.coordinador_arranque")
coordinador = object.__new__(modulo.CoordinadorArranque)
coordinador._boot_timeout_disparado = False
coordinador.terminado = False
etapas = []
coordinador._marcar_boot_stage = etapas.append
coordinador.senal_arranque_ok = _SignalInstance()

payload = object()
coordinador.on_finished(payload)

print(json.dumps({
    "terminado": coordinador.terminado,
    "etapas": etapas,
    "payload_count": len(coordinador.senal_arranque_ok.payloads),
}))
'''
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, check=False)
    assert resultado.returncode == 0, resultado.stderr
    payload = json.loads(resultado.stdout.strip())
    assert payload == {
        "terminado": True,
        "etapas": ["on_finished_signal_received"],
        "payload_count": 1,
    }
