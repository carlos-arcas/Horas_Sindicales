from __future__ import annotations

import logging
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_modulo_wiring_helpers():
    module_path = Path("app/ui/vistas/main_window/wiring_helpers.py")
    spec = spec_from_file_location("wiring_helpers_modes", module_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wiring_helpers = _load_modulo_wiring_helpers()
conectar_signal = wiring_helpers.conectar_signal


class SignalFalso:
    def __init__(self) -> None:
        self.conexiones = 0

    def connect(self, fn) -> None:
        self.conexiones += 1


class VentanaConHandler:
    def __init__(self) -> None:
        self._on_confirmar = lambda: None


class VentanaSinHandler:
    pass


def test_conectar_signal_modo_estricto_lanza_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WIRING_STRICT", "true")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(wiring_helpers, "es_hilo_ui", lambda: True)

    with pytest.raises(RuntimeError, match=r"_on_confirmar.*builder:confirmar"):
        conectar_signal(
            VentanaSinHandler(),
            SignalFalso(),
            "_on_confirmar",
            contexto="builder:confirmar",
        )


def test_conectar_signal_modo_runtime_no_lanza_y_loguea(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("WIRING_STRICT", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(wiring_helpers, "es_hilo_ui", lambda: True)

    with caplog.at_level(logging.ERROR):
        conectar_signal(
            VentanaSinHandler(),
            SignalFalso(),
            "_on_confirmar",
            contexto="builder:confirmar",
        )

    assert "wiring_handler_missing" in caplog.text
    registro = caplog.records[-1]
    assert registro.reason_code == "WIRING_HANDLER_MISSING"
    assert registro.contexto == "builder:confirmar"
    assert registro.handler_name == "_on_confirmar"


def test_conectar_signal_es_idempotente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WIRING_STRICT", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(wiring_helpers, "es_hilo_ui", lambda: True)
    ventana = VentanaConHandler()
    signal = SignalFalso()

    conectar_signal(ventana, signal, "_on_confirmar", contexto="builder:confirmar")
    conectar_signal(ventana, signal, "_on_confirmar", contexto="builder:confirmar")

    assert signal.conexiones == 1
