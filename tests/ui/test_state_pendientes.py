from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace


def _load_state_pendientes_module():
    path = Path("app/ui/vistas/main_window/state_pendientes.py")
    spec = spec_from_file_location("state_pendientes_local", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_buscar_fila_pendiente_por_id_retorna_indice() -> None:
    module = _load_state_pendientes_module()
    pendientes = [SimpleNamespace(id=10), SimpleNamespace(id=20)]
    window = SimpleNamespace(_pending_solicitudes=pendientes)
    assert module.buscar_fila_pendiente_por_id(window, 20) == 1
