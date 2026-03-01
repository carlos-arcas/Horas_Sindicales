from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[2] / "app/ui/vistas/main_window/state_bindings.py"
SPEC = importlib.util.spec_from_file_location("state_bindings_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
state_bindings = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(state_bindings)
_invocar_handler_compatible = state_bindings._invocar_handler_compatible


class Dummy:
    pass


def test_invocador_recorta_args_si_handler_no_acepta_senal_extra() -> None:
    recibido: list[object] = []

    def f0(self):
        recibido.append((self,))
        return "ok0"

    self_obj = Dummy()
    resultado = _invocar_handler_compatible(f0, self_obj, (True, 123), {})

    assert resultado == "ok0"
    assert recibido == [(self_obj,)]


def test_invocador_respeta_handlers_con_uno_o_dos_argumentos() -> None:
    llamadas: list[tuple[object, ...]] = []

    def f1(self, x):
        llamadas.append((self, x))
        return "ok1"

    def f2(self, x, y):
        llamadas.append((self, x, y))
        return "ok2"

    self_obj = Dummy()
    assert _invocar_handler_compatible(f1, self_obj, ("a", "b"), {}) == "ok1"
    assert _invocar_handler_compatible(f2, self_obj, ("a", "b", "c"), {}) == "ok2"
    assert llamadas == [(self_obj, "a"), (self_obj, "a", "b")]


def test_invocador_no_recorta_si_handler_tiene_varargs() -> None:
    recibido: list[tuple[object, ...]] = []

    def fv(self, *args):
        recibido.append((self, *args))
        return "okv"

    self_obj = Dummy()
    resultado = _invocar_handler_compatible(fv, self_obj, (1, 2, 3), {})

    assert resultado == "okv"
    assert recibido == [(self_obj, 1, 2, 3)]


def test_invocador_relanza_type_error_real() -> None:
    def fboom(self):
        raise TypeError("boom")

    with pytest.raises(TypeError, match="boom"):
        _invocar_handler_compatible(fboom, Dummy(), (), {})


def test_invocador_no_oculta_type_error_interno_que_parece_de_firma() -> None:
    def fboom(self, valor):
        raise TypeError("required positional argument")

    with pytest.raises(TypeError, match="required positional argument"):
        _invocar_handler_compatible(fboom, Dummy(), ("dato",), {})
