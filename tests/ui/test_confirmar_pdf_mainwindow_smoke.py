from __future__ import annotations

import json
import logging
import os
import signal
import sqlite3
import traceback
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
        selection_model.select(
            index,
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )

    return [
        sid for sid in window._obtener_ids_seleccionados_pendientes() if sid is not None
    ]


def _resolver_directorio_evidencia(tmp_path: Path) -> Path:
    override = os.getenv("HORAS_UI_SMOKE_EVIDENCE_DIR", "").strip()
    if not override:
        evidencia_dir = Path("artifacts/ui_smoke_evidencias")
        evidencia_dir.mkdir(parents=True, exist_ok=True)
        return evidencia_dir
    evidencia_dir = Path(override)
    evidencia_dir.mkdir(parents=True, exist_ok=True)
    return evidencia_dir


class _WatchdogEscenario:
    def __init__(self, app: QApplication, tmp_path: Path, timeout_s: int = 45) -> None:
        self._app = app
        self._tmp_path = tmp_path
        self._timeout_s = timeout_s
        self._escenario = "init"
        self._ultimo_paso = "sin_paso"
        self._previous = None

    def paso(self, escenario: str, paso: str) -> None:
        self._escenario = escenario
        self._ultimo_paso = paso

    def activar(self) -> None:
        self._previous = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, self._on_timeout)
        signal.setitimer(signal.ITIMER_REAL, self._timeout_s)

    def desactivar(self) -> None:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if self._previous is not None:
            signal.signal(signal.SIGALRM, self._previous)

    def _on_timeout(self, _signum, frame) -> None:
        widgets = []
        for widget in self._app.topLevelWidgets():
            widgets.append(
                {
                    "clase": widget.__class__.__name__,
                    "titulo": widget.windowTitle(),
                    "visible": bool(widget.isVisible()),
                    "oculto": bool(widget.isHidden()),
                }
            )
        evidencia = {
            "escenario": self._escenario,
            "ultimo_paso": self._ultimo_paso,
            "timeout_segundos": self._timeout_s,
            "widgets_top_level": widgets,
            "stacktrace": traceback.format_stack(frame),
        }
        _guardar_evidencia(self._tmp_path, "watchdog_timeout", evidencia)
        raise TimeoutError(
            f"Watchdog UI smoke agotado en escenario={self._escenario} paso={self._ultimo_paso}"
        )


def _guardar_evidencia(
    tmp_path: Path, escenario: str, payload: dict[str, object]
) -> None:
    evidencia_dir = _resolver_directorio_evidencia(tmp_path)
    (evidencia_dir / f"evidencia_{escenario}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _eventos_confirmar(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.getMessage().startswith("UI_CONFIRMAR_PDF_")
    ]


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
        proveedor_ui_solo_lectura=container.proveedor_ui_solo_lectura,
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
    closure_sync_callbacks = 0
    closure_focus_callbacks = 0
    called_ask_push_after_pdf = 0
    finalize_calls = 0
    execute_calls = 0
    closure_calls = 0
    payloads_cierre: list[dict[str, bool]] = []

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

    def _stub_renderer_final(payload):
        nonlocal closure_undo_callbacks, closure_sync_callbacks, closure_focus_callbacks
        callbacks = {
            "on_undo": callable(payload.on_undo),
            "on_sync_now": callable(payload.on_sync_now),
            "on_view_history": callable(payload.on_view_history),
        }
        if callbacks["on_undo"]:
            closure_undo_callbacks += 1
        if callbacks["on_sync_now"]:
            closure_sync_callbacks += 1
        if callbacks["on_view_history"]:
            closure_focus_callbacks += 1
        payloads_cierre.append(callbacks)

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
        assert callable(getattr(window, puente, None)), (
            f"Falta bridge runtime obligatorio: {puente}"
        )

    # Contrato estable: al iniciar sin configuración de sync, el estado debe
    # marcarse como CONFIG_INCOMPLETE y el CTA no debe quedar oculto de forma
    # explícita. No usamos isVisible() aquí porque depende de que la pestaña
    # contenedora esté activa/mostrada en ese instante.
    assert window._last_sync_report is not None
    assert window._last_sync_report.status == "CONFIG_INCOMPLETE"
    assert not window.go_to_sync_config_button.isHidden()

    original_execute = window._execute_confirmar_with_pdf
    original_finalize = window._finalize_confirmar_with_pdf
    original_closure = window._show_confirmation_closure
    original_undo = window._undo_confirmation
    monkeypatch.setattr(
        window, "_execute_confirmar_with_pdf", MethodType(_wrap_execute, window)
    )
    monkeypatch.setattr(
        window, "_finalize_confirmar_with_pdf", MethodType(_wrap_finalize, window)
    )
    monkeypatch.setattr(
        window, "_show_confirmation_closure", MethodType(_wrap_closure, window)
    )
    monkeypatch.setattr(
        window,
        "_show_pdf_actions_dialog",
        MethodType(_stub_show_pdf_actions_dialog, window),
    )
    monkeypatch.setattr(
        window, "_ask_push_after_pdf", MethodType(_stub_ask_push_after_pdf, window)
    )
    monkeypatch.setattr(window, "_undo_confirmation", MethodType(_wrap_undo, window))
    monkeypatch.setattr(
        window.notifications, "show_confirmation_closure", _stub_renderer_final
    )

    watchdog = _WatchdogEscenario(app, tmp_path)
    watchdog.activar()

    try:
        caplog.set_level(logging.INFO)
        watchdog.paso("setup", "reload_inicial")
        window._reload_pending_views()
        app.processEvents()
        persona = window._current_persona()
        assert persona is not None and persona.id is not None

        watchdog.paso("setup", "crear_pendientes_base")
        _agregar_pendiente(container, int(persona.id), "2026-03-10")
        _agregar_pendiente(container, int(persona.id), "2026-03-11")
        window._reload_pending_views()
        app.processEvents()

        # Escenario 1: sin selección.
        caplog.clear()
        conteos_iniciales_s1 = _estado_conteos(window, container)
        window.pendientes_table.clearSelection()
        watchdog.paso("escenario_1_sin_seleccion", "click_confirmar")
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
                "hitos": {
                    evento: _contar_eventos(eventos_s1, evento)
                    for evento in (
                        "UI_CONFIRMAR_PDF_START",
                        "UI_CONFIRMAR_PDF_SELECTED_ROWS",
                        "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
                        "UI_CONFIRMAR_PDF_EXECUTE_OK",
                        "UI_CONFIRMAR_PDF_EXECUTE_ERROR",
                        "UI_CONFIRMAR_PDF_OPEN_OK",
                        "UI_CONFIRMAR_PDF_RETURN_EARLY",
                    )
                },
            },
        )

        # Escenario 2: selección válida + abrir PDF OFF.
        caplog.clear()
        open_calls.clear()
        conteos_iniciales_s2 = _estado_conteos(window, container)
        watchdog.paso("escenario_2_seleccion_valida_abrir_off", "seleccionar_filas")
        selected_ids_s2 = _seleccionar_filas_reales(window, [0, 1])
        assert selected_ids_s2
        window.abrir_pdf_check.setChecked(False)
        watchdog.paso("escenario_2_seleccion_valida_abrir_off", "click_confirmar")
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
        mensajes_s2 = [record.getMessage() for record in caplog.records]
        assert "UI_CONFIRMAR_PDF_EXCEPTION" not in mensajes_s2
        assert "UI_CONFIRMAR_HANDLER_FALLO" not in mensajes_s2
        assert payloads_cierre[-1]["on_undo"]
        assert not payloads_cierre[-1]["on_sync_now"]
        assert payloads_cierre[-1]["on_view_history"]

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
                "hitos": {
                    evento: _contar_eventos(eventos_s2, evento)
                    for evento in (
                        "UI_CONFIRMAR_PDF_START",
                        "UI_CONFIRMAR_PDF_SELECTED_ROWS",
                        "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
                        "UI_CONFIRMAR_PDF_EXECUTE_OK",
                        "UI_CONFIRMAR_PDF_EXECUTE_ERROR",
                        "UI_CONFIRMAR_PDF_OPEN_OK",
                        "UI_CONFIRMAR_PDF_RETURN_EARLY",
                    )
                },
            },
        )

        # Escenario 3: selección válida + abrir PDF ON.
        caplog.clear()
        watchdog.paso("escenario_3_seleccion_valida_abrir_on", "agregar_pendiente")
        _agregar_pendiente(container, int(persona.id), "2026-03-12")
        window._reload_pending_views()
        app.processEvents()

        watchdog.paso("escenario_3_seleccion_valida_abrir_on", "seleccionar_filas")
        selected_ids_s3 = _seleccionar_filas_reales(window, [0])
        assert len(selected_ids_s3) == 1
        window.abrir_pdf_check.setChecked(True)
        watchdog.paso("escenario_3_seleccion_valida_abrir_on", "click_confirmar")
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
        mensajes_s3 = [record.getMessage() for record in caplog.records]
        assert "UI_CONFIRMAR_PDF_EXCEPTION" not in mensajes_s3
        assert "UI_CONFIRMAR_HANDLER_FALLO" not in mensajes_s3
        assert payloads_cierre[-1]["on_undo"]
        assert not payloads_cierre[-1]["on_sync_now"]
        assert payloads_cierre[-1]["on_view_history"]

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
                "hitos": {
                    evento: _contar_eventos(eventos_s3, evento)
                    for evento in (
                        "UI_CONFIRMAR_PDF_START",
                        "UI_CONFIRMAR_PDF_SELECTED_ROWS",
                        "UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN",
                        "UI_CONFIRMAR_PDF_EXECUTE_OK",
                        "UI_CONFIRMAR_PDF_EXECUTE_ERROR",
                        "UI_CONFIRMAR_PDF_OPEN_OK",
                        "UI_CONFIRMAR_PDF_RETURN_EARLY",
                    )
                },
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
                "_show_confirmation_closure_on_sync_now": closure_sync_callbacks,
                "_show_confirmation_closure_on_view_history": closure_focus_callbacks,
            },
        }
        _guardar_evidencia(tmp_path, "resumen_mainwindow_confirmar_pdf", resumen)

        assert execute_calls >= 2
        assert finalize_calls >= 2
        assert closure_calls >= 2
        assert called_ask_push_after_pdf >= 2
        assert len(called_show_pdf_actions_dialog) >= 2
        assert closure_undo_callbacks >= 2
        assert closure_sync_callbacks == 0
        assert closure_focus_callbacks >= 2
        assert len(undo_calls) == 0
    finally:
        watchdog.desactivar()
        window.close()
        app.processEvents()
