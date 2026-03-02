from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_modulo_wiring_helpers():
    module_path = Path("app/ui/vistas/main_window/wiring_helpers.py")
    spec = spec_from_file_location("wiring_helpers", module_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wiring_helpers = _load_modulo_wiring_helpers()
conectar_signal = wiring_helpers.conectar_signal


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


def test_conectar_signal_ok_conecta_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("WIRING_STRICT", raising=False)
    monkeypatch.setattr(wiring_helpers, "es_hilo_ui", lambda: True)
    window = WindowWithHandler()
    signal = FakeSignal()

    conectar_signal(window, signal, "_on_click", contexto="builder:test")

    assert signal.connected is window._on_click


def test_conectar_signal_missing_handler_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WIRING_STRICT", "true")
    monkeypatch.setattr(wiring_helpers, "es_hilo_ui", lambda: True)
    signal = FakeSignal()

    with pytest.raises(RuntimeError, match=r"_on_click.*builder:test"):
        conectar_signal(
            WindowWithoutHandler(), signal, "_on_click", contexto="builder:test"
        )


def test_conectar_signal_non_callable_handler_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WIRING_STRICT", "true")
    monkeypatch.setattr(wiring_helpers, "es_hilo_ui", lambda: True)
    signal = FakeSignal()

    with pytest.raises(RuntimeError, match=r"_on_click.*builder:test"):
        conectar_signal(
            WindowWithNonCallable(), signal, "_on_click", contexto="builder:test"
        )


def test_conectar_signal_fuera_hilo_gui_loguea_y_lanza(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(wiring_helpers, "es_hilo_ui", lambda: False)

    with caplog.at_level("ERROR"):
        with pytest.raises(RuntimeError, match="hilo GUI"):
            conectar_signal(
                WindowWithHandler(), FakeSignal(), "_on_click", contexto="builder:test"
            )

    registro = caplog.records[-1]
    assert registro.reason_code == "WIRING_UI_THREAD_REQUIRED"
    assert registro.contexto == "builder:test"
    assert registro.handler_name == "_on_click"


def test_conectar_signal_valida_firma_si_signal_pasa_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wiring_helpers, "es_hilo_ui", lambda: True)

    class VentanaFirmaInvalida:
        @staticmethod
        def _on_click() -> None:
            return None

    with pytest.raises(RuntimeError, match="firma_invalida"):
        conectar_signal(
            VentanaFirmaInvalida(),
            FakeSignal(),
            "_on_click",
            contexto="builder:test",
            signal_pasa_args=True,
        )
