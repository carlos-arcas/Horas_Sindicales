from __future__ import annotations

import pytest

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_conectar_signal():
    module_path = Path("app/ui/vistas/main_window/wiring_helpers.py")
    spec = spec_from_file_location("wiring_helpers", module_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.conectar_signal


conectar_signal = _load_conectar_signal()


class FakeSignal:
    def __init__(self) -> None:
        self.connected = None

    def connect(self, fn):
        self.connected = fn


class WindowWithHandler:
    def __init__(self) -> None:
        self._on_click = lambda: None


class WindowWithoutHandler:
    pass


class WindowWithNonCallable:
    _on_click = "not-callable"


def test_conectar_signal_ok_conecta_handler() -> None:
    window = WindowWithHandler()
    signal = FakeSignal()

    conectar_signal(window, signal, "_on_click", contexto="builder:test")

    assert signal.connected is window._on_click


def test_conectar_signal_missing_handler_raises_runtime_error() -> None:
    signal = FakeSignal()

    with pytest.raises(RuntimeError, match=r"_on_click.*builder:test"):
        conectar_signal(WindowWithoutHandler(), signal, "_on_click", contexto="builder:test")


def test_conectar_signal_non_callable_handler_raises_runtime_error() -> None:
    signal = FakeSignal()

    with pytest.raises(RuntimeError, match=r"_on_click.*builder:test"):
        conectar_signal(WindowWithNonCallable(), signal, "_on_click", contexto="builder:test")
