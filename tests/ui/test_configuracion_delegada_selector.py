from __future__ import annotations

import sqlite3

import pytest
from tests.ui.conftest import require_qt

qt = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = require_qt()

from app.application.dto import PersonaDTO
from app.bootstrap.container import build_container
from app.ui.main_window import MainWindow
from app.ui.vistas.main_window_vista import resolve_active_delegada_id


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection




def _persona(nombre: str) -> PersonaDTO:
    return PersonaDTO(
        id=None,
        nombre=nombre,
        genero="F",
        horas_mes=0,
        horas_ano=0,
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


def _build_window() -> MainWindow:
    container = build_container(connection_factory=_in_memory_connection)
    return MainWindow(
        container.persona_use_cases,
        container.solicitud_use_cases,
        container.grupo_use_cases,
        container.sheets_service,
        container.sync_service,
        container.conflicts_service,
        health_check_use_case=None,
        alert_engine=container.alert_engine,
    )


def test_resolve_active_delegada_id_usa_preferida_si_existe() -> None:
    assert resolve_active_delegada_id([4, 8, 15], 8) == 8


def test_resolve_active_delegada_id_hace_fallback_a_primera() -> None:
    assert resolve_active_delegada_id([4, 8, 15], 99) == 4
    assert resolve_active_delegada_id([], 99) is None


def test_configuracion_combo_tiene_items_y_botones_dependen_de_current_data() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    assert window.config_delegada_combo.count() == 0
    assert window.edit_persona_button.isEnabled() is False
    assert window.delete_persona_button.isEnabled() is False

    p1 = window._persona_use_cases.crear_persona(_persona("Ana Díaz"))
    p2 = window._persona_use_cases.crear_persona(_persona("Ana Díaz"))
    window._load_personas(select_id=p2.id)

    assert window.config_delegada_combo.count() == 2
    assert window.config_delegada_combo.currentData() == p2.id
    assert window.edit_persona_button.isEnabled() is True
    assert window.delete_persona_button.isEnabled() is True

    window.config_delegada_combo.setCurrentIndex(-1)
    window._sync_config_persona_actions()
    assert window.config_delegada_combo.currentData() is None
    assert window.edit_persona_button.isEnabled() is False
    assert window.delete_persona_button.isEnabled() is False

    window.close()
    app.processEvents()
