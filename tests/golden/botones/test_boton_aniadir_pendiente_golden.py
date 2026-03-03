from __future__ import annotations

import importlib.util
from pathlib import Path

from tests.utilidades.event_recorder import EventRecorder
from tests.golden.botones._helpers import assert_matches_golden, install_pyside6_stubs


class _FakeController:
    def __init__(self, recorder: EventRecorder) -> None:
        self._recorder = recorder

    def on_add_pendiente(self) -> None:
        self._recorder.record("use_case_llamado", {"nombre": "on_add_pendiente", "payload_minimo": {"origen": "solicitudes_controller"}})


class _FakeWindow:
    def __init__(self, recorder: EventRecorder) -> None:
        self._solicitudes_controller = _FakeController(recorder)


def _load_on_add_pendiente():
    module_path = Path(__file__).resolve().parents[3] / "app/ui/vistas/main_window/acciones_pendientes.py"
    spec = importlib.util.spec_from_file_location("acciones_pendientes_headless", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.on_add_pendiente


def test_boton_aniadir_pendiente_golden_snapshot() -> None:
    install_pyside6_stubs()
    on_add_pendiente = _load_on_add_pendiente()

    recorder = EventRecorder()
    window = _FakeWindow(recorder)
    recorder.record("click_boton", {"nombre": "Añadir pendiente"})

    on_add_pendiente(window)

    assert_matches_golden(Path(__file__), "aniadir_pendiente", recorder.to_json())
