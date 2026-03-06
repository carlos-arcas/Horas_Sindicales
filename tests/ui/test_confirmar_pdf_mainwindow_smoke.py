from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from types import MethodType

import pytest

from tests.ui.conftest import require_qt

QApplication = require_qt()

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QFileDialog

from app.application.dto import SolicitudDTO
from app.bootstrap.container import build_container
from app.infrastructure.db import configure_sqlite_connection
from app.ui.main_window import MainWindow
from app.ui.vistas import confirmacion_actions


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


def _agregar_pendiente(container, persona_id: int, fecha: str) -> int:
    creada, _ = container.solicitud_use_cases.agregar_solicitud(
        SolicitudDTO(
            id=None,
            persona_id=persona_id,
            fecha_solicitud="2026-03-01",
            fecha_pedida=fecha,
            desde="09:00",
            hasta="10:00",
            completo=False,
            horas=1.0,
            observaciones="smoke ui real",
            pdf_path=None,
            pdf_hash=None,
            notas="smoke",
        ),
        correlation_id=f"corr-smoke-{fecha}",
    )
    assert creada.id is not None
    return int(creada.id)


def _seleccionar_filas_reales(window, rows: list[int]) -> list[int]:
    selection_model = window.pendientes_table.selectionModel()
    assert selection_model is not None
    selection_model.clearSelection()
    model = window.pendientes_table.model()
    assert model is not None

    for row in rows:
        index = model.index(row, 0)
        selection_model.select(index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)

    return [sid for sid in window._obtener_ids_seleccionados_pendientes() if sid is not None]


def _resolver_directorio_evidencia(tmp_path: Path) -> Path:
    override = os.getenv("HORAS_UI_SMOKE_EVIDENCE_DIR", "").strip()
    if not override:
        return tmp_path
    evidencia_dir = Path(override)
    evidencia_dir.mkdir(parents=True, exist_ok=True)
    return evidencia_dir


def _guardar_evidencia(tmp_path: Path, escenario: str, payload: dict[str, object]) -> None:
    evidencia_dir = _resolver_directorio_evidencia(tmp_path)
    (evidencia_dir / f"evidencia_{escenario}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def test_confirmar_pdf_mainwindow_smoke_real(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "runtime_ui_smoke.sqlite3"
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

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

    called_show_pdf_actions_dialog: list[str] = []
    called_ask_push_after_pdf = 0
    finalize_calls = 0
    execute_calls = 0
    closure_calls = 0

    def _stub_show_pdf_actions_dialog(self, generated_path):
        called_show_pdf_actions_dialog.append(str(generated_path))

    def _stub_ask_push_after_pdf(self):
        nonlocal called_ask_push_after_pdf
        called_ask_push_after_pdf += 1

    def _wrap_finalize(self, *args, **kwargs):
        nonlocal finalize_calls
        finalize_calls += 1
        return original_finalize(*args, **kwargs)

    def _wrap_execute(self, *args, **kwargs):
        nonlocal execute_calls
        execute_calls += 1
        return original_execute(*args, **kwargs)

    def _wrap_closure(self, *args, **kwargs):
        nonlocal closure_calls
        closure_calls += 1
        return original_closure(*args, **kwargs)

    puentes_obligatorios = (
        "_execute_confirmar_with_pdf",
        "_finalize_confirmar_with_pdf",
        "_show_confirmation_closure",
        "_show_pdf_actions_dialog",
        "_ask_push_after_pdf",
        "_undo_confirmation",
    )

    for puente in puentes_obligatorios:
        assert callable(getattr(window, puente, None)), f"Falta bridge runtime obligatorio: {puente}"

    original_execute = window._execute_confirmar_with_pdf
    original_finalize = window._finalize_confirmar_with_pdf
    original_closure = window._show_confirmation_closure
    monkeypatch.setattr(window, "_execute_confirmar_with_pdf", MethodType(_wrap_execute, window))
    monkeypatch.setattr(window, "_finalize_confirmar_with_pdf", MethodType(_wrap_finalize, window))
    monkeypatch.setattr(window, "_show_confirmation_closure", MethodType(_wrap_closure, window))
    monkeypatch.setattr(window, "_show_pdf_actions_dialog", MethodType(_stub_show_pdf_actions_dialog, window))
    monkeypatch.setattr(window, "_ask_push_after_pdf", MethodType(_stub_ask_push_after_pdf, window))

    try:
        caplog.set_level(logging.INFO)
        window._reload_pending_views()
        app.processEvents()
        persona = window._current_persona()
        assert persona is not None and persona.id is not None

        _agregar_pendiente(container, int(persona.id), "2026-03-10")
        _agregar_pendiente(container, int(persona.id), "2026-03-11")
        window._reload_pending_views()
        app.processEvents()

        # Escenario 1: sin selección.
        caplog.clear()
        historico_inicial = list(container.solicitud_use_cases.listar_historico())
        pendientes_antes_s1 = list(window._pending_solicitudes)
        window.pendientes_table.clearSelection()
        window._on_confirmar()
        app.processEvents()

        logs_s1 = [record.getMessage() for record in caplog.records]
        assert "UI_CONFIRMAR_PDF_RETURN_EARLY" in logs_s1
        assert len(save_calls) == 0
        assert list(window._pending_solicitudes) == pendientes_antes_s1
        assert list(container.solicitud_use_cases.listar_historico()) == historico_inicial

        _guardar_evidencia(
            tmp_path,
            "escenario_1_sin_seleccion",
            {
                "escenario": "sin_seleccion",
                "ids_seleccionados": [],
                "ruta_pdf": None,
                "existe_pdf": False,
                "bytes_iniciales_pdf": "",
                "abrir_pdf_toggle": bool(window.abrir_pdf_check.isChecked()),
                "apertura_pdf_invocada": False,
                "pendientes_antes": len(pendientes_antes_s1),
                "pendientes_despues": len(window._pending_solicitudes),
                "historico_encontrado": len(list(container.solicitud_use_cases.listar_historico())),
                "logs_clave_si_aplica": [log for log in logs_s1 if log in {"UI_CONFIRMAR_PDF_START", "UI_CONFIRMAR_PDF_SELECTED_ROWS", "UI_CONFIRMAR_PDF_RETURN_EARLY"}],
            },
        )

        # Escenario 2: selección válida + abrir PDF OFF.
        caplog.clear()
        open_calls.clear()
        pendientes_antes_s2 = len(window._pending_solicitudes)
        selected_ids_s2 = _seleccionar_filas_reales(window, [0, 1])
        assert selected_ids_s2
        window.abrir_pdf_check.setChecked(False)
        window.confirmar_button.click()
        app.processEvents()

        assert save_calls
        pdf_path_s2 = Path(save_calls[-1])
        historico_s2 = list(container.solicitud_use_cases.listar_historico())
        assert pdf_path_s2.exists()
        assert pdf_path_s2.stat().st_size > 0
        assert pdf_path_s2.read_bytes()[:4] == b"%PDF"
        assert len(window._pending_solicitudes) == 0
        assert len(historico_s2) >= len(historico_inicial) + len(selected_ids_s2)
        assert open_calls == []

        logs_s2 = [record.getMessage() for record in caplog.records]
        for evento in (
            "UI_CONFIRMAR_PDF_START",
            "UI_CONFIRMAR_PDF_SELECTED_ROWS",
            "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
            "UI_CONFIRMAR_PDF_EXECUTE_OK",
        ):
            assert evento in logs_s2

        _guardar_evidencia(
            tmp_path,
            "escenario_2_seleccion_valida_abrir_off",
            {
                "escenario": "seleccion_valida_abrir_off",
                "ids_seleccionados": selected_ids_s2,
                "ruta_pdf": str(pdf_path_s2),
                "existe_pdf": pdf_path_s2.exists(),
                "bytes_iniciales_pdf": pdf_path_s2.read_bytes()[:4].decode("latin1"),
                "abrir_pdf_toggle": False,
                "apertura_pdf_invocada": False,
                "pendientes_antes": pendientes_antes_s2,
                "pendientes_despues": len(window._pending_solicitudes),
                "historico_encontrado": len(historico_s2),
                "logs_clave_si_aplica": [
                    log
                    for log in logs_s2
                    if log
                    in {
                        "UI_CONFIRMAR_PDF_START",
                        "UI_CONFIRMAR_PDF_SELECTED_ROWS",
                        "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
                        "UI_CONFIRMAR_PDF_EXECUTE_OK",
                    }
                ],
            },
        )

        # Escenario 3: selección válida + abrir PDF ON.
        caplog.clear()
        _agregar_pendiente(container, int(persona.id), "2026-03-12")
        window._reload_pending_views()
        app.processEvents()

        selected_ids_s3 = _seleccionar_filas_reales(window, [0])
        assert len(selected_ids_s3) == 1
        window.abrir_pdf_check.setChecked(True)
        window.confirmar_button.click()
        app.processEvents()

        pdf_path_s3 = Path(save_calls[-1])
        historico_s3 = list(container.solicitud_use_cases.listar_historico())
        assert pdf_path_s3.exists()
        assert pdf_path_s3.read_bytes()[:4] == b"%PDF"
        assert len(historico_s3) >= len(historico_s2) + len(selected_ids_s3)
        assert open_calls == [str(pdf_path_s3)]

        logs_s3 = [record.getMessage() for record in caplog.records]
        for evento in (
            "UI_CONFIRMAR_PDF_START",
            "UI_CONFIRMAR_PDF_SELECTED_ROWS",
            "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
            "UI_CONFIRMAR_PDF_EXECUTE_OK",
            "UI_CONFIRMAR_PDF_OPEN_OK",
        ):
            assert evento in logs_s3

        _guardar_evidencia(
            tmp_path,
            "escenario_3_seleccion_valida_abrir_on",
            {
                "escenario": "seleccion_valida_abrir_on",
                "ids_seleccionados": selected_ids_s3,
                "ruta_pdf": str(pdf_path_s3),
                "existe_pdf": pdf_path_s3.exists(),
                "bytes_iniciales_pdf": pdf_path_s3.read_bytes()[:4].decode("latin1"),
                "abrir_pdf_toggle": True,
                "apertura_pdf_invocada": True,
                "pendientes_antes": 1,
                "pendientes_despues": len(window._pending_solicitudes),
                "historico_encontrado": len(historico_s3),
                "logs_clave_si_aplica": [log for log in logs_s3 if log in {"UI_CONFIRMAR_PDF_OPEN_OK", "UI_CONFIRMAR_PDF_EXECUTE_OK"}],
            },
        )

        assert execute_calls >= 2
        assert finalize_calls >= 2
        assert closure_calls >= 2
        assert called_ask_push_after_pdf >= 2
        assert len(called_show_pdf_actions_dialog) >= 2
    finally:
        window.close()
        app.processEvents()
