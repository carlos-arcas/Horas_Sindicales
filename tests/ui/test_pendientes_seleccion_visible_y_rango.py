from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.ui.conftest import require_qt

QApplication = require_qt()

from PySide6.QtCore import QItemSelectionModel, QModelIndex, Qt

from app.application.dto import SolicitudDTO
from app.bootstrap.container import build_container
from app.infrastructure.db import configure_sqlite_connection
from app.ui.main_window import MainWindow
from app.ui.vistas import confirmacion_orquestacion
from app.ui.vistas.main_window import state_pendientes


class _ServicioSheetsSinRed:
    def is_configured(self) -> bool:
        return False

    def __getattr__(self, _name: str):
        return lambda *args, **kwargs: None


def _connection_factory(db_path: Path):
    def _build() -> sqlite3.Connection:
        connection = sqlite3.connect(db_path)
        configure_sqlite_connection(connection)
        return connection

    return _build


def _agregar_pendiente(container, persona_id: int, fecha: str, horas: float = 1.0) -> int:
    creada, _ = container.solicitud_use_cases.agregar_solicitud(
        SolicitudDTO(
            id=None,
            persona_id=persona_id,
            fecha_solicitud="2026-02-01",
            fecha_pedida=fecha,
            desde="09:00",
            hasta="10:00",
            completo=False,
            horas=horas,
            observaciones="seleccion pendientes",
            pdf_path=None,
            pdf_hash=None,
            notas="prueba",
        ),
        correlation_id=f"corr-seleccion-{fecha}",
    )
    assert creada.id is not None
    return int(creada.id)


def _crear_window(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "runtime_ui_select.sqlite3"
    container = build_container(connection_factory=_connection_factory(db_path))
    container.sheets_service = _ServicioSheetsSinRed()
    window = MainWindow(
        container.persona_use_cases,
        container.solicitud_use_cases,
        container.grupo_use_cases,
        container.sheets_service,
        container.sync_service,
        container.conflicts_service,
        health_check_use_case=container.health_check_use_case,
        alert_engine=container.alert_engine,
        validacion_preventiva_lock_use_case=container.validacion_preventiva_lock_use_case,
        confirmar_pendientes_pdf_caso_uso=container.confirmar_pendientes_pdf_caso_uso,
        crear_pendiente_caso_uso=container.crear_pendiente_caso_uso,
        servicio_i18n=container.servicio_i18n,
    )
    return app, container, window


def _seleccion_rows(window: MainWindow) -> list[int]:
    selection_model = window.pendientes_table.selectionModel()
    assert selection_model is not None
    return sorted(index.row() for index in selection_model.selectedRows())


def test_toggle_visible_y_shift_rango_integran_seleccion_real(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, container, window = _crear_window(tmp_path)
    try:
        window._reload_pending_views()
        app.processEvents()
        persona = window._current_persona()
        assert persona is not None and persona.id is not None

        for fecha in ("2026-02-10", "2026-02-11", "2026-02-12", "2026-02-13"):
            _agregar_pendiente(container, int(persona.id), fecha)
        window._reload_pending_views()
        app.processEvents()

        assert window.pendientes_model.rowCount() == 4
        assert window.pending_select_all_visible_check.isEnabled() is True

        # No marcable (deshabilitada) + oculta: deben quedar fuera del toggle visible.
        window.pendientes_table.setRowHidden(3, True)
        idx_no_marcable = window.pendientes_model.index(1, 0)
        flags_originales = window.pendientes_model.flags

        def _flags_con_no_marcable(index: QModelIndex):
            base = flags_originales(index)
            if index.row() == 1:
                return base & ~Qt.ItemFlag.ItemIsSelectable
            return base

        monkeypatch.setattr(window.pendientes_model, "flags", _flags_con_no_marcable)

        window._on_pending_select_all_visible_toggled(True)
        app.processEvents()
        assert _seleccion_rows(window) == [0, 2]
        assert window.pending_select_all_visible_check.checkState() == Qt.CheckState.Checked

        window._on_pending_select_all_visible_toggled(False)
        app.processEvents()
        assert _seleccion_rows(window) == []
        assert window.pending_select_all_visible_check.checkState() == Qt.CheckState.Unchecked

        # Shift + click: ancla en fila 0; destino fila 2 marca rango contiguo visible [0,2].
        monkeypatch.setattr(state_pendientes.QApplication, "keyboardModifiers", lambda: Qt.KeyboardModifier.NoModifier)
        window._on_pending_row_clicked(window.pendientes_model.index(0, 0))

        selection_model = window.pendientes_table.selectionModel()
        assert selection_model is not None
        selection_model.select(
            window.pendientes_model.index(2, 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )
        monkeypatch.setattr(state_pendientes.QApplication, "keyboardModifiers", lambda: Qt.KeyboardModifier.ShiftModifier)
        window._on_pending_row_clicked(window.pendientes_model.index(2, 0))
        app.processEvents()
        assert _seleccion_rows(window) == [0, 2]

        # Shift + click desmarca rango al clicar destino ya desmarcado.
        selection_model.select(
            window.pendientes_model.index(2, 0),
            QItemSelectionModel.SelectionFlag.Deselect | QItemSelectionModel.SelectionFlag.Rows,
        )
        window._on_pending_row_clicked(window.pendientes_model.index(2, 0))
        app.processEvents()
        assert _seleccion_rows(window) == []
        assert window.pending_select_all_visible_check.checkState() == Qt.CheckState.Unchecked

        # Confirmar usa exactamente selección real.
        selection_model.select(
            window.pendientes_model.index(0, 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )
        ids_esperados = window._obtener_ids_seleccionados_pendientes()
        assert len(ids_esperados) == 1

        capturado: dict[str, list[int]] = {}

        def _capturar_confirmar(_window, _persona, selected, _pdf_path):
            capturado["ids"] = [sol.id for sol in selected if sol.id is not None]
            return None

        monkeypatch.setattr(confirmacion_orquestacion, "execute_confirmar_with_pdf", _capturar_confirmar)
        monkeypatch.setattr(window, "_prompt_confirm_pdf_path", lambda _selected: str(tmp_path / "salida.pdf"))
        window._on_confirmar()
        app.processEvents()

        assert capturado["ids"] == ids_esperados
    finally:
        window.close()
        app.processEvents()


def test_toggle_sin_filas_visibles_se_deshabilita(tmp_path: Path) -> None:
    app, _container, window = _crear_window(tmp_path)
    try:
        window._reload_pending_views()
        app.processEvents()
        assert window.pendientes_model.rowCount() == 0
        assert window.pending_select_all_visible_check.isEnabled() is False
        assert window.pending_select_all_visible_check.checkState() == Qt.CheckState.Unchecked
    finally:
        window.close()
        app.processEvents()


def test_toggle_con_una_sola_fila_funciona(tmp_path: Path) -> None:
    app, container, window = _crear_window(tmp_path)
    try:
        persona = window._current_persona()
        assert persona is not None and persona.id is not None
        _agregar_pendiente(container, int(persona.id), "2026-02-15")
        window._reload_pending_views()
        app.processEvents()

        assert window.pendientes_model.rowCount() == 1
        window._on_pending_select_all_visible_toggled(True)
        app.processEvents()
        assert _seleccion_rows(window) == [0]

        window._on_pending_select_all_visible_toggled(False)
        app.processEvents()
        assert _seleccion_rows(window) == []
    finally:
        window.close()
        app.processEvents()
