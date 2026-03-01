from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "app/ui/vistas/main_window/state_bindings.py"
SPEC = importlib.util.spec_from_file_location("state_bindings_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
state_bindings = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(state_bindings)
_adaptar_slot_a_senal = state_bindings._adaptar_slot_a_senal


class Dummy:
    pass


def test_adaptador_slot_tolera_payload_de_senal() -> None:
    llamadas: list[object] = []

    def slot_sin_payload(self):
        llamadas.append(self)

    slot_compatible = _adaptar_slot_a_senal(slot_sin_payload)
    self_obj = Dummy()

    slot_compatible(self_obj)
    slot_compatible(self_obj, True)

    assert llamadas == [self_obj, self_obj]
