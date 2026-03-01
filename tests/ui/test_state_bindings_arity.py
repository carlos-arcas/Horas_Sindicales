from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_MODULE_PATH = Path(__file__).resolve().parents[2] / "app" / "ui" / "vistas" / "main_window" / "state_bindings.py"
_spec = importlib.util.spec_from_file_location("state_bindings_under_test", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
_state_bindings = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_state_bindings)
_adaptar_slot_a_senal = _state_bindings._adaptar_slot_a_senal


class _Dummy:
    def __init__(self) -> None:
        self.invocado = False
        self.indice: int | None = None


@pytest.mark.headless_safe
def test_slot_compatible_tolera_args_extra_si_handler_no_acepta_payload() -> None:
    def handler(self) -> None:
        self.invocado = True

    dummy = _Dummy()

    _adaptar_slot_a_senal(handler)(dummy, True, 99)

    assert dummy.invocado is True


@pytest.mark.headless_safe
def test_slot_compatible_propaga_indice_si_handler_acepta_un_argumento() -> None:
    def handler(self, idx: int) -> None:
        self.indice = idx

    dummy = _Dummy()

    _adaptar_slot_a_senal(handler)(dummy, 3, "ignorado")

    assert dummy.indice == 3
