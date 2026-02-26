from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.application.dto import PersonaDTO, SolicitudDTO
from app.ui.vistas.historico_refresh_logic import build_historico_rows

pytestmark = pytest.mark.headless_safe

VISTA_PATH = Path("app/ui/vistas/main_window_vista.py")


def _persona(persona_id: int | None, nombre: str) -> PersonaDTO:
    return PersonaDTO(
        id=persona_id,
        nombre=nombre,
        genero="F",
        horas_mes=600,
        horas_ano=7200,
        is_active=True,
        cuad_lun_man_min=0,
        cuad_lun_tar_min=0,
        cuad_mar_man_min=0,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=0,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=0,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=0,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )



def _solicitud(solicitud_id: int, persona_id: int, fecha: str, desde: str, hasta: str) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=persona_id,
        fecha_solicitud=fecha,
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=False,
        horas=1.0,
        observaciones="",
        pdf_path=None,
        pdf_hash=None,
        notas="",
    )

def _class_and_methods() -> tuple[ast.ClassDef, dict[str, ast.FunctionDef]]:
    module = ast.parse(VISTA_PATH.read_text(encoding="utf-8"))
    main_window = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )
    methods = {
        node.name: node
        for node in main_window.body
        if isinstance(node, ast.FunctionDef)
    }
    return main_window, methods


def _contains_refresh_call(method: ast.FunctionDef, force_value: bool) -> bool:
    for node in ast.walk(method):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "_refresh_historico":
            continue
        for keyword in node.keywords:
            if keyword.arg == "force" and isinstance(keyword.value, ast.Constant):
                return keyword.value.value is force_value
    return False


def test_post_init_load_wires_historico_refresh() -> None:
    _, methods = _class_and_methods()
    assert "_post_init_load" in methods
    assert _contains_refresh_call(methods["_post_init_load"], force_value=True)


def test_tab_changed_wires_historico_refresh() -> None:
    _, methods = _class_and_methods()
    assert "_on_main_tab_changed" in methods
    assert _contains_refresh_call(methods["_on_main_tab_changed"], force_value=False)


def test_build_historico_rows_collects_all_persona_rows() -> None:
    personas = [
        _persona(1, "Ana"),
        _persona(None, "Sin id"),
        _persona(2, "Bea"),
    ]
    solicitud_a = _solicitud(11, 1, "2026-01-10", "09:00", "10:00")
    solicitud_b = _solicitud(22, 2, "2026-01-11", "10:00", "11:00")

    def fake_listar(persona_id: int) -> list[SolicitudDTO]:
        if persona_id == 1:
            return [solicitud_a]
        if persona_id == 2:
            return [solicitud_b]
        return []

    rows = build_historico_rows(personas, fake_listar)

    assert rows == [solicitud_a, solicitud_b]
