from __future__ import annotations

import sqlite3

import pytest
from tests.ui.conftest import require_qt

qt = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QApplication = require_qt()
QMessageBox = qt.QMessageBox

from app.application.dto import PersonaDTO
from app.bootstrap.container import build_container
from app.ui.vistas.main_window import MainWindow
from app.ui.vistas.main_window import acciones_personas


def _in_memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


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
        estado_modo_solo_lectura=container.estado_modo_solo_lectura,
    )


def test_cambiar_delegada_con_formulario_sucio_pide_confirmacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    p1 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Ana"))
    p2 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Bea"))
    window._load_personas(select_id=p1.id)
    window.notas_input.setPlainText("Borrador pendiente")

    llamadas: list[tuple[object, str, str]] = []

    def _fake_question(parent, title, text, *args, **kwargs):
        llamadas.append((parent, title, text))
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", _fake_question)

    window.persona_combo.setCurrentIndex(1)

    assert llamadas
    assert "descartará el formulario actual" in llamadas[0][2]
    assert window.persona_combo.currentData() == p1.id
    assert window.notas_input.toPlainText() == "Borrador pendiente"

    window.close()
    app.processEvents()


def test_cambiar_delegada_con_formulario_sucio_y_confirmacion_afirmativa_aplica_cambio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    p1 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Ana"))
    p2 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Bea"))
    window._load_personas(select_id=p1.id)
    window.notas_input.setPlainText("Borrador pendiente")

    llamadas: list[tuple[object, str, str]] = []

    def _fake_question(parent, title, text, *args, **kwargs):
        llamadas.append((parent, title, text))
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", _fake_question)

    window.persona_combo.setCurrentIndex(1)

    assert llamadas
    assert window.persona_combo.currentData() == p2.id
    assert window.notas_input.toPlainText() == ""

    window.close()
    app.processEvents()


def test_load_personas_sin_select_id_mantiene_carga_normal() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    p1 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Ana"))
    p2 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Bea"))

    window._load_personas()

    assert window.persona_combo.count() == 2
    assert window.persona_combo.currentData() == p1.id
    assert window.config_delegada_combo.currentData() == p1.id
    assert window._last_persona_id == p1.id

    window.close()
    app.processEvents()


def test_load_personas_con_select_id_reselecciona_y_sincroniza_contexto() -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    p1 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Ana"))
    p2 = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Bea"))

    window._load_personas(select_id=p1.id)
    window._load_personas(select_id=p2.id)

    assert window.persona_combo.currentData() == p2.id
    assert window.config_delegada_combo.currentData() == p2.id
    assert window.historico_delegada_combo.currentData() == p2.id
    assert window._last_persona_id == p2.id

    window.close()
    app.processEvents()


def test_editar_persona_y_recargar_reselecciona_la_persona_actualizada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    window = _build_window()

    persona = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Ana"))
    otra = window._persona_use_cases.crear_persona(PersonaDTO(nombre="Bea"))
    window._load_personas(select_id=otra.id)

    persona_editada = PersonaDTO(
        id=otra.id,
        nombre="Bea Editada",
        genero=otra.genero,
        horas_mes=otra.horas_mes,
        horas_ano=otra.horas_ano,
        is_active=otra.is_active,
        cuad_lun_man_min=otra.cuad_lun_man_min,
        cuad_lun_tar_min=otra.cuad_lun_tar_min,
        cuad_mar_man_min=otra.cuad_mar_man_min,
        cuad_mar_tar_min=otra.cuad_mar_tar_min,
        cuad_mie_man_min=otra.cuad_mie_man_min,
        cuad_mie_tar_min=otra.cuad_mie_tar_min,
        cuad_jue_man_min=otra.cuad_jue_man_min,
        cuad_jue_tar_min=otra.cuad_jue_tar_min,
        cuad_vie_man_min=otra.cuad_vie_man_min,
        cuad_vie_tar_min=otra.cuad_vie_tar_min,
        cuad_sab_man_min=otra.cuad_sab_man_min,
        cuad_sab_tar_min=otra.cuad_sab_tar_min,
        cuad_dom_man_min=otra.cuad_dom_man_min,
        cuad_dom_tar_min=otra.cuad_dom_tar_min,
    )

    monkeypatch.setattr(
        acciones_personas,
        "_crear_dialogo_persona",
        lambda *_args, **_kwargs: type(
            "_DialogoFalso",
            (),
            {"get_persona": staticmethod(lambda: persona_editada)},
        )(),
    )
    monkeypatch.setattr(
        acciones_personas.QMessageBox,
        "question",
        lambda *_args, **_kwargs: acciones_personas.QMessageBox.StandardButton.Yes,
    )

    window._on_edit_persona()

    assert window.persona_combo.currentData() == otra.id
    assert window.config_delegada_combo.currentData() == otra.id
    assert window.historico_delegada_combo.currentData() == otra.id
    assert window._last_persona_id == otra.id
    assert window.persona_combo.currentText() == "Bea Editada"
    assert persona.id != otra.id

    window.close()
    app.processEvents()
