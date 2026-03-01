from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.ui.copy_catalog import copy_text


_HEADER_STATE_PATH = Path(__file__).resolve().parents[2] / "app" / "ui" / "vistas" / "main_window" / "header_state.py"
_spec = importlib.util.spec_from_file_location("header_state_under_test", _HEADER_STATE_PATH)
assert _spec is not None and _spec.loader is not None
_header_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_header_state)
resolve_section_title = _header_state.resolve_section_title


@pytest.mark.headless_safe
def test_header_externo_resuelve_titulo_esperado_al_navegar_secciones() -> None:
    casos = {
        0: "Sincronización",
        1: copy_text("solicitudes.section_title"),
        2: copy_text("ui.historico.tab"),
        3: copy_text("ui.sync.configuracion"),
    }

    for seccion_idx, titulo_esperado in casos.items():
        assert resolve_section_title(seccion_idx) == titulo_esperado
