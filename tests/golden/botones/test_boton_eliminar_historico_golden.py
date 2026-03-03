from __future__ import annotations

import importlib.util
from pathlib import Path

from tests.utilidades.event_recorder import EventRecorder
from tests.golden.botones._helpers import FakeButton, FakeSolicitudUseCases, FakeTable, assert_matches_golden, install_pyside6_stubs


class _FakeWindow:
    def __init__(self, recorder: EventRecorder) -> None:
        self._historico_ids_seleccionados = {101, 102}
        self._solicitud_use_cases = FakeSolicitudUseCases(recorder)
        self.historico_table = FakeTable(recorder, "historico_table")
        self.eliminar_button = FakeButton(recorder, "eliminar_button")


def _load_eliminar_historico():
    module_path = Path(__file__).resolve().parents[3] / "app/ui/vistas/main_window/state_historico.py"
    spec = importlib.util.spec_from_file_location("state_historico_headless", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.eliminar_historico_seleccionado


def test_boton_eliminar_historico_golden_snapshot() -> None:
    install_pyside6_stubs()
    eliminar_historico_seleccionado = _load_eliminar_historico()

    recorder = EventRecorder()
    window = _FakeWindow(recorder)
    recorder.record("click_boton", {"nombre": "Eliminar histórico"})

    total = eliminar_historico_seleccionado(window)
    recorder.record("estado_ui_cambiado", {"clave": "historico_eliminados", "valor": total})

    assert_matches_golden(Path(__file__), "eliminar_historico", recorder.to_json())
