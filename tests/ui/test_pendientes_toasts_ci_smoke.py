from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path

import pytest

from tests.ui.conftest import require_qt

QApplication = require_qt()

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QFileDialog

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.modelos import SolicitudConfirmarPdfResultado
from app.ui.vistas.confirmacion_orquestacion import ResultadoConfirmacionFlujo
from app.bootstrap.container import build_container
from app.infrastructure.db import configure_sqlite_connection
from app.ui.main_window import MainWindow
from tests.ui.conftest import crear_persona_dto_valida


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


def _resolver_directorio_evidencia(tmp_path: Path) -> Path:
    override = os.getenv("HORAS_UI_SMOKE_EVIDENCE_DIR", "").strip()
    evidencia_dir = Path(override) if override else Path("artifacts/ui_smoke_evidencias")
    evidencia_dir.mkdir(parents=True, exist_ok=True)
    return evidencia_dir


def _guardar_evidencia(tmp_path: Path, nombre: str, payload: dict[str, object]) -> None:
    evidencia_dir = _resolver_directorio_evidencia(tmp_path)
    (evidencia_dir / nombre).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


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
            observaciones="smoke runtime pendientes/toast",
            pdf_path=None,
            pdf_hash=None,
            notas="smoke",
        ),
        correlation_id=f"corr-smoke-{fecha}",
    )
    assert creada.id is not None
    return int(creada.id)


def _crear_window(tmp_path: Path):
    app = QApplication.instance() or QApplication([])
    db_path = tmp_path / "runtime_ui_pendientes_toast.sqlite3"
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


def _ids_seleccionados(window: MainWindow) -> list[int]:
    return [sid for sid in window._obtener_ids_seleccionados_pendientes() if sid is not None]


def _seleccionar_filas(window: MainWindow, rows: list[int]) -> list[int]:
    selection_model = window.pendientes_table.selectionModel()
    model = window.pendientes_table.model()
    assert selection_model is not None and model is not None
    selection_model.clearSelection()
    for row in rows:
        idx = model.index(row, 0)
        selection_model.select(idx, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    return _ids_seleccionados(window)


def _eventos(caplog: pytest.LogCaptureFixture, prefijo: str) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith(prefijo)]


def test_ui_smoke_pendientes_y_toasts_con_evidencias_ci(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app, container, window = _crear_window(tmp_path)

    scenario_status: list[dict[str, str]] = []
    save_calls: list[str] = []
    cierre_payloads: list[dict[str, bool]] = []
    original_execute = window._execute_confirmar_with_pdf
    original_finalize = window._finalize_confirmar_with_pdf

    def _fake_save(*_args, **_kwargs):
        path = tmp_path / f"confirmacion_{len(save_calls) + 1}.pdf"
        save_calls.append(str(path))
        return str(path), "pdf"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", _fake_save)
    monkeypatch.setattr(window, "_ask_push_after_pdf", lambda: None)
    monkeypatch.setattr(window, "_show_pdf_actions_dialog", lambda _path: None)

    def _capturar_cierre(payload):
        cierre_payloads.append(
            {
                "on_undo": callable(payload.on_undo),
                "on_sync_now": callable(payload.on_sync_now),
                "on_view_history": callable(payload.on_view_history),
            }
        )

    monkeypatch.setattr(window.notifications, "show_confirmation_closure", _capturar_cierre)

    try:
        caplog.set_level(logging.INFO)

        persona_1 = window._persona_use_cases.crear_persona(crear_persona_dto_valida("Delegada Smoke Uno"))
        persona_2 = window._persona_use_cases.crear_persona(crear_persona_dto_valida("Delegada Smoke Dos"))
        assert persona_1.id is not None and persona_2.id is not None
        window._load_personas(select_id=persona_1.id)
        app.processEvents()

        id_p1 = _agregar_pendiente(container, int(persona_1.id), "2026-03-10")
        id_p2 = _agregar_pendiente(container, int(persona_2.id), "2026-03-11")
        window._reload_pending_views()
        app.processEvents()

        # Escenario 1
        before_hidden = len(window._hidden_pendientes)
        before_visible = len(window._pending_solicitudes)
        before_total = len(window._pending_all_solicitudes)
        window.ver_todas_pendientes_button.setChecked(True)
        app.processEvents()
        after_hidden = len(window._hidden_pendientes)
        after_visible = len(window._pending_solicitudes)
        after_total = len(window._pending_all_solicitudes)
        model_rows = window.pendientes_model.rowCount()

        pass_s1 = after_hidden == 0 and after_visible == after_total == model_rows
        _guardar_evidencia(
            tmp_path,
            "evidencia_ver_todas_delegadas.json",
            {
                "escenario": "ver_todas_delegadas_limpia_ocultas",
                "estado": "PASS" if pass_s1 else "FAIL",
                "conteos_antes": {"hidden": before_hidden, "visible": before_visible, "total": before_total},
                "conteos_despues": {"hidden": after_hidden, "visible": after_visible, "total": after_total, "row_count": model_rows},
                "ids_relevantes": {"persona_1": persona_1.id, "persona_2": persona_2.id, "pendiente_persona_1": id_p1, "pendiente_persona_2": id_p2},
                "hitos": ["click_ver_todas_delegadas", "recarga_pendientes", "alineacion_visible_logico"],
                "callbacks_detectados": {},
                "razon_fallo": None if pass_s1 else "Quedaron ocultas o los conteos no alinean.",
                "mensaje_humano": "Ver todas delegadas limpia ocultas y alinea tabla con el estado lógico." if pass_s1 else "Persisten ocultas o desalineación de conteos.",
            },
        )
        assert pass_s1
        scenario_status.append({"escenario": "ver_todas", "estado": "PASS"})

        # Escenario 2
        seleccion_toggle = _seleccionar_filas(window, [0, 1])
        window._on_pending_select_all_visible_toggled(False)
        app.processEvents()
        seleccion_limpia = _ids_seleccionados(window)
        window._on_pending_select_all_visible_toggled(True)
        app.processEvents()
        seleccion_toggle_2 = _ids_seleccionados(window)

        window._on_pending_row_clicked(window.pendientes_model.index(0, 0))
        selection_model = window.pendientes_table.selectionModel()
        assert selection_model is not None
        selection_model.select(
            window.pendientes_model.index(1, 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )
        selected_real = _ids_seleccionados(window)

        capturado: dict[str, list[int]] = {}

        def _capturar_execute(_persona, selected, _pdf_path):
            capturado["ids"] = [sol.id for sol in selected if sol.id is not None]
            return ResultadoConfirmacionFlujo(
                correlation_id="corr-test",
                resultado=SolicitudConfirmarPdfResultado(
                    estado="OK_CON_PDF",
                    confirmadas=len(capturado["ids"]),
                    confirmadas_ids=capturado["ids"],
                    errores=[],
                    pdf_generado=tmp_path / "fake.pdf",
                    sync_permitido=True,
                    pendientes_restantes=[sol.id for sol in window._pending_solicitudes if sol.id is not None],
                ),
                creadas=selected,
                pendientes_restantes=window._pending_solicitudes,
            )

        monkeypatch.setattr(window, "_execute_confirmar_with_pdf", _capturar_execute)
        monkeypatch.setattr(window, "_finalize_confirmar_with_pdf", lambda *_args, **_kwargs: None)
        window._on_confirmar()
        app.processEvents()

        pass_s2 = sorted(capturado.get("ids", [])) == sorted(selected_real)
        _guardar_evidencia(
            tmp_path,
            "evidencia_seleccion_pendientes_post_ver_todas.json",
            {
                "escenario": "seleccion_integra_post_ver_todas",
                "estado": "PASS" if pass_s2 else "FAIL",
                "conteos_antes": {"seleccion_toggle": len(seleccion_toggle)},
                "conteos_despues": {"seleccion_limpia": len(seleccion_limpia), "seleccion_toggle_2": len(seleccion_toggle_2), "seleccion_real_confirmar": len(selected_real)},
                "ids_relevantes": {"selection_model_ids": selected_real, "ids_consumidos_confirmar": capturado.get("ids", [])},
                "hitos": ["toggle_visible_on_off", "seleccion_real_selection_model", "confirmar_usa_seleccion_real"],
                "callbacks_detectados": {},
                "razon_fallo": None if pass_s2 else "Confirmar/PDF no consumió la misma selección real.",
                "mensaje_humano": "La selección visible/rango se conserva y confirmar consume los IDs reales." if pass_s2 else "Desalineación entre selección visible y payload de confirmar.",
            },
        )
        assert pass_s2
        scenario_status.append({"escenario": "seleccion_post_ver_todas", "estado": "PASS"})

        monkeypatch.setattr(window, "_execute_confirmar_with_pdf", original_execute)
        monkeypatch.setattr(window, "_finalize_confirmar_with_pdf", original_finalize)

        # Escenario 3
        window._reload_pending_views()
        app.processEvents()
        _seleccionar_filas(window, [0])
        caplog.clear()
        window._on_confirmar()
        app.processEvents()
        mensajes_confirmar = [r.getMessage() for r in caplog.records]
        eventos_confirmar = _eventos(caplog, "UI_CONFIRMAR_PDF_")
        success_present = any(r.nivel == "success" for r in window.toast._cache.values())
        callbacks = cierre_payloads[-1] if cierre_payloads else {}
        pass_s3 = (
            success_present
            and "UI_CONFIRMAR_PDF_EXECUTE_OK" in eventos_confirmar
            and "UI_CONFIRMAR_PDF_EXCEPTION" not in mensajes_confirmar
            and "UI_CONFIRMAR_HANDLER_FALLO" not in mensajes_confirmar
            and callbacks.get("on_undo", False)
            and not callbacks.get("on_sync_now", False)
            and callbacks.get("on_view_history", False)
        )
        _guardar_evidencia(
            tmp_path,
            "evidencia_toast_success_real.json",
            {
                "escenario": "toast_success_real",
                "estado": "PASS" if pass_s3 else "FAIL",
                "conteos_antes": {"toasts_cache": 0},
                "conteos_despues": {"toasts_cache": len(window.toast._cache), "eventos_confirmar": len(eventos_confirmar)},
                "ids_relevantes": {"ids_seleccionados": _ids_seleccionados(window), "pdf_guardados": save_calls},
                "hitos": ["flujo_confirmar_valido", "ui_confirmar_pdf_execute_ok", "toast_success_emitido"],
                "callbacks_detectados": callbacks,
                "razon_fallo": None if pass_s3 else "Falta toast success real, callback o apareció error contradictorio.",
                "mensaje_humano": "Flujo válido muestra success coherente sin excepciones de confirmar." if pass_s3 else "Contrato de success no cumplido en flujo válido.",
            },
        )
        assert pass_s3
        scenario_status.append({"escenario": "toast_success", "estado": "PASS"})

        # Escenario 4
        for toast_id in list(window.toast._visibles.keys()):
            window.toast._cerrar_toast(toast_id)
        app.processEvents()

        caplog.clear()

        def _fallar_execute(_persona, _selected, _pdf_path):
            raise RuntimeError("fallo_controlado_smoke")

        monkeypatch.setattr(window, "_finalize_confirmar_with_pdf", original_finalize)
        monkeypatch.setattr(window, "_execute_confirmar_with_pdf", _fallar_execute)
        _agregar_pendiente(container, int(persona_1.id), "2026-03-15")
        window._reload_pending_views()
        app.processEvents()
        _seleccionar_filas(window, [0])
        window._on_confirmar()
        app.processEvents()

        eventos_error = _eventos(caplog, "UI_CONFIRMAR_PDF_")
        success_toasts = [t.id for t in window.toast._cache.values() if t.nivel == "success"]
        error_toasts = [t.id for t in window.toast._cache.values() if t.nivel == "error"]
        pass_s4 = "UI_CONFIRMAR_PDF_EXECUTE_ERROR" in eventos_error and not success_toasts and bool(error_toasts)
        _guardar_evidencia(
            tmp_path,
            "evidencia_toast_error_real.json",
            {
                "escenario": "toast_error_sin_falso_success",
                "estado": "PASS" if pass_s4 else "FAIL",
                "conteos_antes": {"toasts_cache": 0},
                "conteos_despues": {"toasts_cache": len(window.toast._cache), "toasts_error": len(error_toasts), "toasts_success": len(success_toasts)},
                "ids_relevantes": {"toast_error_ids": error_toasts, "toast_success_ids": success_toasts},
                "hitos": ["error_controlado_execute", "ui_confirmar_pdf_execute_error", "sin_false_success"],
                "callbacks_detectados": {},
                "razon_fallo": None if pass_s4 else "Hubo success indebido o faltó toast de error.",
                "mensaje_humano": "Ante fallo real, solo se muestra error coherente y sin éxito falso." if pass_s4 else "Se detectó mensaje contradictorio de success/error.",
            },
        )
        assert pass_s4
        scenario_status.append({"escenario": "toast_error", "estado": "PASS"})

        # Escenario 5
        cierre_manual_hit = False
        target_id = None
        for toast in window.toast._cache.values():
            if toast.nivel == "error":
                target_id = toast.id
                break
        assert target_id is not None
        tarjeta = window.toast._visibles[target_id]
        tarjeta._btn_cerrar.click()
        app.processEvents()
        cierre_manual_hit = target_id not in window.toast._cache and target_id not in window.toast._visibles
        pass_s5 = cierre_manual_hit and not window.toast._modelo.listar()
        _guardar_evidencia(
            tmp_path,
            "evidencia_toast_cierre_manual.json",
            {
                "escenario": "toast_cierre_manual",
                "estado": "PASS" if pass_s5 else "FAIL",
                "conteos_antes": {"toasts_cache": 1},
                "conteos_despues": {
                    "toasts_cache": len(window.toast._cache),
                    "toasts_visibles": len(window.toast._visibles),
                    "toasts_modelo": len(window.toast._modelo.listar()),
                },
                "ids_relevantes": {"toast_cerrado": target_id},
                "hitos": ["click_cerrar_manual", "limpieza_cache", "limpieza_modelo", "sin_zombie_ui"],
                "callbacks_detectados": {},
                "razon_fallo": None if pass_s5 else "No se limpiaron cache/modelo/visibles tras cierre manual.",
                "mensaje_humano": "El cierre manual elimina el toast y evita zombis de UI." if pass_s5 else "Cierre manual dejó estado zombi o inconsistente.",
            },
        )
        assert pass_s5
        scenario_status.append({"escenario": "toast_cierre_manual", "estado": "PASS"})

        _guardar_evidencia(
            tmp_path,
            "resumen_ui_pendientes_toasts.json",
            {
                "escenarios": scenario_status,
                "estado_global": "PASS" if all(s["estado"] == "PASS" for s in scenario_status) else "FAIL",
                "mensaje_humano": "Todos los contratos runtime de pendientes/toasts pasan en smoke UI headless." if all(s["estado"] == "PASS" for s in scenario_status) else "Hay contratos runtime sin cerrar.",
            },
        )
    finally:
        window.close()
        app.processEvents()
