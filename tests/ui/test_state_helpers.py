from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_state_helpers_module():
    path = Path("app/ui/vistas/main_window/state_helpers.py")
    spec = spec_from_file_location("state_helpers_local", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_active_delegada_id_prioriza_preferido_valido() -> None:
    module = _load_state_helpers_module()
    assert module.resolve_active_delegada_id([10, 20, 30], "20") == 20


def test_resolve_active_delegada_id_usa_primera_si_preferido_no_valido() -> None:
    module = _load_state_helpers_module()
    assert module.resolve_active_delegada_id([10, 20, 30], "999") == 10


def test_resolve_active_delegada_id_none_si_no_hay_ids() -> None:
    module = _load_state_helpers_module()
    assert module.resolve_active_delegada_id([], "20") is None
