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


def _eventos_confirmar(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.getMessage().startswith("UI_CONFIRMAR_PDF_")]


def _contar_eventos(eventos: list[str], evento: str) -> int:
    return sum(1 for item in eventos if item == evento)


def _estado_conteos(window: MainWindow, container) -> dict[str, int]:
    return {
        "pendientes": len(window._pending_solicitudes),
        "historico": len(list(container.solicitud_use_cases.listar_historico())),
    }


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
    undo_calls: list[list[int]] = []
    closure_undo_callbacks = 0
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

    def _wrap_undo(self, solicitud_ids: list[int]):
        undo_calls.append(list(solicitud_ids))
        return original_undo(solicitud_ids)

    def _capturar_show_confirmation_closure(*_args, **kwargs):
        nonlocal closure_undo_callbacks
        on_undo = kwargs.get("on_undo")
        if callable(on_undo):
            closure_undo_callbacks += 1
        return original_show_confirmation_closure(*_args, **kwargs)

    puentes_obligatorios = (
        "_execute_confirmar_with_pdf",
        "_finalize_confirmar_with_pdf",
        "_show_confirmation_closure",
        "_show_pdf_actions_dialog",
        "_ask_push_after_pdf",
        "_undo_confirmation",
        "_set_config_incomplete_state",
    )

    for puente in puentes_obligatorios:
        assert callable(getattr(window, puente, None)), f"Falta bridge runtime obligatorio: {puente}"

    assert window.go_to_sync_config_button.isVisible()

    original_execute = window._execute_confirmar_with_pdf
    original_finalize = window._finalize_confirmar_with_pdf
    original_closure = window._show_confirmation_closure
    original_undo = window._undo_confirmation
    original_show_confirmation_closure = confirmacion_actions.show_confirmation_closure
    monkeypatch.setattr(window, "_execute_confirmar_with_pdf", MethodType(_wrap_execute, window))
    monkeypatch.setattr(window, "_finalize_confirmar_with_pdf", MethodType(_wrap_finalize, window))
    monkeypatch.setattr(window, "_show_confirmation_closure", MethodType(_wrap_closure, window))
    monkeypatch.setattr(window, "_show_pdf_actions_dialog", MethodType(_stub_show_pdf_actions_dialog, window))
    monkeypatch.setattr(window, "_ask_push_after_pdf", MethodType(_stub_ask_push_after_pdf, window))
    monkeypatch.setattr(window, "_undo_confirmation", MethodType(_wrap_undo, window))
    monkeypatch.setattr(confirmacion_actions, "show_confirmation_closure", _capturar_show_confirmation_closure)

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
        conteos_iniciales_s1 = _estado_conteos(window, container)
        window.pendientes_table.clearSelection()
        window._on_confirmar()
        app.processEvents()

        eventos_s1 = _eventos_confirmar(caplog)
        assert "UI_CONFIRMAR_PDF_START" in eventos_s1
        assert "UI_CONFIRMAR_PDF_SELECTED_ROWS" in eventos_s1
        assert "UI_CONFIRMAR_PDF_RETURN_EARLY" in eventos_s1
        assert "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN" not in eventos_s1
        assert "UI_CONFIRMAR_PDF_EXECUTE_OK" not in eventos_s1
        assert "UI_CONFIRMAR_PDF_EXECUTE_ERROR" not in eventos_s1
        assert "UI_CONFIRMAR_PDF_OPEN_OK" not in eventos_s1
        assert len(save_calls) == 0
        conteos_finales_s1 = _estado_conteos(window, container)
        assert conteos_finales_s1 == conteos_iniciales_s1

        historico_inicial = list(container.solicitud_use_cases.listar_historico())

        _guardar_evidencia(
            tmp_path,
            "escenario_1_sin_seleccion",
            {
                "escenario": "sin_seleccion",
                "ids_seleccionados": [],
                "ruta_pdf_elegida": None,
                "existe_pdf": False,
                "cabecera_pdf": "",
                "abrir_pdf_toggle": bool(window.abrir_pdf_check.isChecked()),
                "apertura_pdf_intentos": len(open_calls),
                "pendientes_antes": conteos_iniciales_s1["pendientes"],
                "pendientes_despues": conteos_finales_s1["pendientes"],
                "historico_antes": conteos_iniciales_s1["historico"],
                "historico_despues": conteos_finales_s1["historico"],
                "motivo_salida_temprana": "sin_seleccion",
                "bridges_runtime": {
                    "_execute_confirmar_with_pdf": execute_calls,
                    "_finalize_confirmar_with_pdf": finalize_calls,
                    "_show_confirmation_closure": closure_calls,
                    "_show_pdf_actions_dialog": len(called_show_pdf_actions_dialog),
                    "_ask_push_after_pdf": called_ask_push_after_pdf,
                    "_undo_confirmation": len(undo_calls),
                },
                "hitos": {evento: _contar_eventos(eventos_s1, evento) for evento in (
                    "UI_CONFIRMAR_PDF_START",
                    "UI_CONFIRMAR_PDF_SELECTED_ROWS",
                    "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
                    "UI_CONFIRMAR_PDF_EXECUTE_OK",
                    "UI_CONFIRMAR_PDF_EXECUTE_ERROR",
                    "UI_CONFIRMAR_PDF_OPEN_OK",
                    "UI_CONFIRMAR_PDF_RETURN_EARLY",
                )},
            },
        )

        # Escenario 2: selección válida + abrir PDF OFF.
        caplog.clear()
        open_calls.clear()
        conteos_iniciales_s2 = _estado_conteos(window, container)
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

        eventos_s2 = _eventos_confirmar(caplog)
        for evento in (
            "UI_CONFIRMAR_PDF_START",
            "UI_CONFIRMAR_PDF_SELECTED_ROWS",
            "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
            "UI_CONFIRMAR_PDF_EXECUTE_OK",
        ):
            assert evento in eventos_s2
        assert "UI_CONFIRMAR_PDF_EXECUTE_ERROR" not in eventos_s2
        assert "UI_CONFIRMAR_PDF_RETURN_EARLY" not in eventos_s2

        conteos_finales_s2 = _estado_conteos(window, container)

        _guardar_evidencia(
            tmp_path,
            "escenario_2_seleccion_valida_abrir_off",
            {
                "escenario": "seleccion_valida_abrir_off",
                "ids_seleccionados": selected_ids_s2,
                "ruta_pdf_elegida": str(pdf_path_s2),
                "existe_pdf": pdf_path_s2.exists(),
                "cabecera_pdf": pdf_path_s2.read_bytes()[:4].decode("latin1"),
                "abrir_pdf_toggle": False,
                "apertura_pdf_intentos": len(open_calls),
                "pendientes_antes": conteos_iniciales_s2["pendientes"],
                "pendientes_despues": conteos_finales_s2["pendientes"],
                "historico_antes": conteos_iniciales_s2["historico"],
                "historico_despues": conteos_finales_s2["historico"],
                "motivo_salida_temprana": None,
                "bridges_runtime": {
                    "_execute_confirmar_with_pdf": execute_calls,
                    "_finalize_confirmar_with_pdf": finalize_calls,
                    "_show_confirmation_closure": closure_calls,
                    "_show_pdf_actions_dialog": len(called_show_pdf_actions_dialog),
                    "_ask_push_after_pdf": called_ask_push_after_pdf,
                    "_undo_confirmation": len(undo_calls),
                },
                "hitos": {evento: _contar_eventos(eventos_s2, evento) for evento in (
                    "UI_CONFIRMAR_PDF_START",
                    "UI_CONFIRMAR_PDF_SELECTED_ROWS",
                    "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
                    "UI_CONFIRMAR_PDF_EXECUTE_OK",
                    "UI_CONFIRMAR_PDF_EXECUTE_ERROR",
                    "UI_CONFIRMAR_PDF_OPEN_OK",
                    "UI_CONFIRMAR_PDF_RETURN_EARLY",
                )},
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

        eventos_s3 = _eventos_confirmar(caplog)
        for evento in (
            "UI_CONFIRMAR_PDF_START",
            "UI_CONFIRMAR_PDF_SELECTED_ROWS",
            "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
            "UI_CONFIRMAR_PDF_EXECUTE_OK",
            "UI_CONFIRMAR_PDF_OPEN_OK",
        ):
            assert evento in eventos_s3
        assert "UI_CONFIRMAR_PDF_EXECUTE_ERROR" not in eventos_s3

        conteos_finales_s3 = _estado_conteos(window, container)

        _guardar_evidencia(
            tmp_path,
            "escenario_3_seleccion_valida_abrir_on",
            {
                "escenario": "seleccion_valida_abrir_on",
                "ids_seleccionados": selected_ids_s3,
                "ruta_pdf_elegida": str(pdf_path_s3),
                "existe_pdf": pdf_path_s3.exists(),
                "cabecera_pdf": pdf_path_s3.read_bytes()[:4].decode("latin1"),
                "abrir_pdf_toggle": True,
                "apertura_pdf_intentos": len(open_calls),
                "pendientes_antes": 1,
                "pendientes_despues": conteos_finales_s3["pendientes"],
                "historico_antes": len(historico_s2),
                "historico_despues": conteos_finales_s3["historico"],
                "motivo_salida_temprana": None,
                "bridges_runtime": {
                    "_execute_confirmar_with_pdf": execute_calls,
                    "_finalize_confirmar_with_pdf": finalize_calls,
                    "_show_confirmation_closure": closure_calls,
                    "_show_pdf_actions_dialog": len(called_show_pdf_actions_dialog),
                    "_ask_push_after_pdf": called_ask_push_after_pdf,
                    "_undo_confirmation": len(undo_calls),
                },
                "hitos": {evento: _contar_eventos(eventos_s3, evento) for evento in (
                    "UI_CONFIRMAR_PDF_START",
                    "UI_CONFIRMAR_PDF_SELECTED_ROWS",
                    "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
                    "UI_CONFIRMAR_PDF_EXECUTE_OK",
                    "UI_CONFIRMAR_PDF_EXECUTE_ERROR",
                    "UI_CONFIRMAR_PDF_OPEN_OK",
                    "UI_CONFIRMAR_PDF_RETURN_EARLY",
                )},
            },
        )

        resumen = {
            "escenarios": [
                {
                    "nombre": "sin_seleccion",
                    "estado_escenario": "PASS",
                    "paso_en_que_rompe": None,
                    "evidencia_principal": "UI_CONFIRMAR_PDF_RETURN_EARLY",
                    "mensaje_humano": "Sin selección se detecta salida temprana controlada sin cambios funcionales.",
                },
                {
                    "nombre": "seleccion_valida_abrir_off",
                    "estado_escenario": "PASS",
                    "paso_en_que_rompe": None,
                    "evidencia_principal": "UI_CONFIRMAR_PDF_EXECUTE_OK",
                    "mensaje_humano": "La selección se confirma y migra a histórico sin apertura automática de PDF.",
                },
                {
                    "nombre": "seleccion_valida_abrir_on",
                    "estado_escenario": "PASS",
                    "paso_en_que_rompe": None,
                    "evidencia_principal": "UI_CONFIRMAR_PDF_OPEN_OK",
                    "mensaje_humano": "La selección se confirma y abre el PDF exactamente una vez.",
                },
            ],
            "bridges_usados": {
                "_execute_confirmar_with_pdf": execute_calls,
                "_finalize_confirmar_with_pdf": finalize_calls,
                "_show_confirmation_closure": closure_calls,
                "_show_pdf_actions_dialog": len(called_show_pdf_actions_dialog),
                "_ask_push_after_pdf": called_ask_push_after_pdf,
                "_undo_confirmation": len(undo_calls),
                "_show_confirmation_closure_on_undo": closure_undo_callbacks,
            },
        }
        _guardar_evidencia(tmp_path, "resumen_mainwindow_confirmar_pdf", resumen)

        assert execute_calls >= 2
        assert finalize_calls >= 2
        assert closure_calls >= 2
        assert called_ask_push_after_pdf >= 2
        assert len(called_show_pdf_actions_dialog) >= 2
        assert closure_undo_callbacks >= 2
        assert len(undo_calls) == 0
    finally:
        window.close()
        app.processEvents()
