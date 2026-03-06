from __future__ import annotations

import json
import logging
import os
import sqlite3
from importlib import import_module
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")

try:
    qt_widgets = import_module("PySide6.QtWidgets")
    qt_core = import_module("PySide6.QtCore")
except ImportError as exc:
    pytest.skip(f"PySide6 no importable: {exc}", allow_module_level=True)

QApplication = qt_widgets.QApplication
QFileDialog = qt_widgets.QFileDialog
QItemSelectionModel = qt_core.QItemSelectionModel

from app.application.dto import SolicitudDTO
from app.bootstrap.container import build_container
from app.infrastructure.db import configure_sqlite_connection
from app.ui.main_window import MainWindow
from app.ui.vistas import confirmacion_actions


class _SinRedSheetsService:
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


def _agregar_pendiente(container, persona_id: int, fecha: str) -> int:
    creada, _ = container.solicitud_use_cases.agregar_solicitud(
        SolicitudDTO(
            id=None,
            persona_id=persona_id,
            fecha_solicitud="2026-02-01",
            fecha_pedida=fecha,
            desde="09:00",
            hasta="10:00",
            completo=False,
            horas=1.0,
            observaciones="contrato ui real",
            pdf_path=None,
            pdf_hash=None,
            notas="prioridad 1",
        ),
        correlation_id=f"corr-ui-real-{fecha}",
    )
    assert creada.id is not None
    return int(creada.id)


def _seleccionar_filas(window, rows: list[int]) -> list[int]:
    selection_model = window.pendientes_table.selectionModel()
    assert selection_model is not None
    selection_model.clearSelection()
    model = window.pendientes_table.model()
    assert model is not None

    for row in rows:
        index = model.index(row, 0)
        selection_model.select(index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    return window._obtener_ids_seleccionados_pendientes()


def test_confirmar_pdf_ui_real_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "runtime_ui_real.sqlite3"
    pdf_dir = tmp_path / "salida_pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    container = build_container(connection_factory=_connection_factory(db_path))
    container.sheets_service = _SinRedSheetsService()

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

    save_calls: list[str] = []
    open_calls: list[str] = []

    def _fake_save(*_args, **_kwargs):
        path = pdf_dir / f"confirmacion_{len(save_calls) + 1}.pdf"
        save_calls.append(str(path))
        return str(path), "pdf"

    def _fake_open(path: Path) -> None:
        open_calls.append(str(path))

    monkeypatch.setattr(QFileDialog, "getSaveFileName", _fake_save)
    monkeypatch.setattr(confirmacion_actions, "abrir_archivo_local", _fake_open)
    monkeypatch.setattr(window, "_ask_push_after_pdf", lambda: None)
    monkeypatch.setattr(window, "_show_pdf_actions_dialog", lambda _path: None)

    metodos_bridge = [
        "_execute_confirmar_with_pdf",
        "_finalize_confirmar_with_pdf",
        "_show_confirmation_closure",
        "_show_pdf_actions_dialog",
        "_ask_push_after_pdf",
        "_undo_confirmation",
    ]

    try:
        for metodo in metodos_bridge:
            assert hasattr(window, metodo), f"MainWindow sin bridge obligatorio: {metodo}"

        window._reload_pending_views()
        app.processEvents()
        persona = window._current_persona()
        assert persona is not None and persona.id is not None

        # Datos reales para escenarios 1 y 2.
        _agregar_pendiente(container, int(persona.id), "2026-02-10")
        _agregar_pendiente(container, int(persona.id), "2026-02-11")
        window._reload_pending_views()
        app.processEvents()

        historico_inicial = len(list(container.solicitud_use_cases.listar_historico()))
        pendientes_inicial = len(window._pending_solicitudes)
        assert pendientes_inicial >= 2

        evidencia: list[dict[str, object]] = []

        # ESCENARIO 1: sin selección.
        caplog.clear()
        caplog.set_level(logging.INFO)
        window.pendientes_table.clearSelection()
        window._on_confirmar()
        app.processEvents()

        assert len(save_calls) == 0
        assert len(open_calls) == 0
        assert len(window._pending_solicitudes) == pendientes_inicial
        assert len(list(container.solicitud_use_cases.listar_historico())) == historico_inicial
        assert any(
            registro.message == "UI_CONFIRMAR_PDF_RETURN_EARLY" and getattr(registro, "reason", "") == "no_pending_rows"
            for registro in caplog.records
        )
        evidencia.append(
            {
                "escenario": "sin_seleccion",
                "ids_seleccionados": [],
                "ruta_pdf": None,
                "existe_pdf": False,
                "bytes_pdf": None,
                "pendientes_restantes": len(window._pending_solicitudes),
                "historico_encontrado": len(list(container.solicitud_use_cases.listar_historico())),
                "apertura_pdf_invocada": 0,
            }
        )

        # ESCENARIO 2: selección válida con toggle desactivado.
        selected_ids_s2 = _seleccionar_filas(window, [0, 1])
        window.abrir_pdf_check.setChecked(False)
        window._on_confirmar()
        app.processEvents()

        pdf_path_s2 = Path(save_calls[-1])
        pdf_bytes_s2 = pdf_path_s2.read_bytes()
        assert pdf_path_s2.exists()
        assert pdf_path_s2.stat().st_size > 0
        assert pdf_bytes_s2[:4] == b"%PDF"
        assert len(window._pending_solicitudes) == 0
        historico_s2 = len(list(container.solicitud_use_cases.listar_historico()))
        assert historico_s2 >= historico_inicial + len(selected_ids_s2)
        assert len(open_calls) == 0
        evidencia.append(
            {
                "escenario": "seleccion_valida_abrir_pdf_off",
                "ids_seleccionados": selected_ids_s2,
                "ruta_pdf": str(pdf_path_s2),
                "existe_pdf": pdf_path_s2.exists(),
                "bytes_pdf": list(pdf_bytes_s2[:4]),
                "pendientes_restantes": len(window._pending_solicitudes),
                "historico_encontrado": historico_s2,
                "apertura_pdf_invocada": len(open_calls),
            }
        )

        # ESCENARIO 3: selección válida con toggle activado.
        _agregar_pendiente(container, int(persona.id), "2026-02-12")
        window._reload_pending_views()
        app.processEvents()

        selected_ids_s3 = _seleccionar_filas(window, [0])
        window.abrir_pdf_check.setChecked(True)
        window._on_confirmar()
        app.processEvents()

        pdf_path_s3 = Path(save_calls[-1])
        pdf_bytes_s3 = pdf_path_s3.read_bytes()
        historico_s3 = len(list(container.solicitud_use_cases.listar_historico()))
        assert pdf_path_s3.exists()
        assert pdf_bytes_s3[:4] == b"%PDF"
        assert historico_s3 >= historico_s2 + len(selected_ids_s3)
        assert open_calls == [str(pdf_path_s3)]
        evidencia.append(
            {
                "escenario": "seleccion_valida_abrir_pdf_on",
                "ids_seleccionados": selected_ids_s3,
                "ruta_pdf": str(pdf_path_s3),
                "existe_pdf": pdf_path_s3.exists(),
                "bytes_pdf": list(pdf_bytes_s3[:4]),
                "pendientes_restantes": len(window._pending_solicitudes),
                "historico_encontrado": historico_s3,
                "apertura_pdf_invocada": len(open_calls),
            }
        )

        (tmp_path / "evidencia_confirmar_pdf_ui_real.json").write_text(
            json.dumps(evidencia, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    finally:
        window.close()
        app.processEvents()
