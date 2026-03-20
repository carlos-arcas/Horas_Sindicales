from __future__ import annotations

import traceback
import logging
from collections.abc import Set

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.bootstrap.logging import log_operational_error
from app.core.observability import OperationContext, log_event
from app.domain.sheets_errors import SheetsPermissionError
from app.ui.copy_catalog import copy_text
from app.ui.sync_permission_message import build_sync_permission_blocked_message
from app.ui.controllers.sync_button_state_rules import (
    EstadoBotonSyncEntrada,
    decidir_estado_botones_sync,
)
from app.ui.vistas.compat_i18n import resolver_texto_i18n
from app.ui.vistas.main_window.state_helpers import resolve_active_delegada_id


try:
    from presentacion.i18n import CATALOGO, I18nManager
except ImportError:  # pragma: no cover - fallback for headless/unit-test environments
    CATALOGO = {}
    I18nManager = None


logger = logging.getLogger(__name__)

if I18nManager is None:
    logger.warning(
        "I18N_FALLBACK_ACTIVE_SYNC_CONTROLLER",
        extra={"event": "I18N_FALLBACK_ACTIVE_SYNC_CONTROLLER"},
    )


class _SyncWorker(QObject):
    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, operation, correlation_id: str, operation_name: str) -> None:
        super().__init__()
        self._operation = operation
        self._correlation_id = correlation_id
        self._operation_name = operation_name

    @Slot()
    def run(self) -> None:
        try:
            log_event(
                logger,
                "sync_started",
                {"operation": self._operation_name},
                self._correlation_id,
            )
            result = self._operation()
            log_event(
                logger,
                "sync_succeeded",
                {"operation": self._operation_name},
                self._correlation_id,
            )
        except Exception as exc:  # pragma: no cover
            log_event(
                logger,
                "sync_failed",
                {"operation": self._operation_name, "error": str(exc)},
                self._correlation_id,
            )
            log_operational_error(
                logger,
                _fallback_texto("sync.error_operacion_log"),
                exc=exc,
                extra={
                    "operation": self._operation_name,
                    "correlation_id": self._correlation_id,
                },
            )
            self.failed.emit({"error": exc, "details": traceback.format_exc()})
            return
        self.finished.emit(result)


class SyncController:
    def __init__(self, window) -> None:
        self.window = window

    def on_context_changed(self) -> None:
        w = self.window
        if getattr(w, '_pending_sync_plan', None) is not None:
            w._pending_sync_plan = None
        if hasattr(w, 'confirm_sync_button') and hasattr(w.confirm_sync_button, 'setEnabled'):
            w.confirm_sync_button.setEnabled(False)
        self.update_sync_button_state()

    def on_sync(self) -> None:
        self._run_background_operation(
            operation=lambda: self.window._sync_service.sync_bidirectional(),
            on_finished=getattr(self.window, "_on_sync_finished", lambda *_: None),
            operation_name="sync_bidirectional",
        )

    def on_simulate_sync(self) -> None:
        self._run_background_operation(
            operation=lambda: self.window._sync_service.simulate_sync_plan(),
            on_finished=getattr(
                self.window, "_on_sync_simulation_finished", lambda *_: None
            ),
            operation_name="simulate_sync",
        )

    def on_confirm_sync(self) -> None:
        w = self.window
        if w._pending_sync_plan is None:
            w.toast.warning(
                _tr(
                    w,
                    "sync.primero_simular_aviso",
                    _fallback_texto("sync.primero_simular_aviso"),
                ),
                title=_tr(
                    w, "sync.sin_plan_titulo", _fallback_texto("sync.sin_plan_titulo")
                ),
            )
            return
        if not w._pending_sync_plan.has_changes:
            w.toast.info(
                _tr(
                    w,
                    "sync.sin_cambios_aplicar",
                    _fallback_texto("sync.sin_cambios_aplicar"),
                ),
                title=_tr(w, "sync.titulo", _fallback_texto("sync.titulo")),
            )
            return
        self._run_background_operation(
            operation=lambda: w._sync_service.execute_sync_plan(w._pending_sync_plan),
            on_finished=getattr(w, "_on_sync_finished", lambda *_: None),
            operation_name="execute_sync_plan",
        )

    def _run_background_operation(
        self, *, operation, on_finished, operation_name: str
    ) -> None:
        w = self.window
        if w._sync_in_progress:
            return
        if not w._sync_service.is_configured():
            w._set_config_incomplete_state()
            w.toast.warning(
                _tr(
                    w,
                    "sync.configuracion_faltante_aviso",
                    _fallback_texto("sync.configuracion_faltante_aviso"),
                ),
                title=_tr(
                    w,
                    "sync.configuracion_faltante_titulo",
                    _fallback_texto("sync.configuracion_faltante_titulo"),
                ),
            )
            return
        w._set_sync_in_progress(True)
        w._sync_thread = QThread()
        operation_context = OperationContext("sync_ui")
        w._sync_operation_context = operation_context
        contexto_persona_id = self._contexto_persona_activo()
        w._sync_worker = _SyncWorker(
            operation, operation_context.correlation_id, operation_name
        )
        w._sync_worker.moveToThread(w._sync_thread)
        w._sync_thread.started.connect(w._sync_worker.run)
        w._sync_worker.finished.connect(
            lambda result, expected_persona_id=contexto_persona_id, callback=on_finished: self._handle_operation_finished(
                result,
                expected_persona_id=expected_persona_id,
                on_finished=callback,
                operation_name=operation_name,
            )
        )
        w._sync_worker.failed.connect(
            lambda payload, expected_persona_id=contexto_persona_id: self._handle_operation_failed(
                payload,
                expected_persona_id=expected_persona_id,
                operation_name=operation_name,
            )
        )
        w._sync_worker.finished.connect(w._sync_thread.quit)
        w._sync_worker.finished.connect(w._sync_worker.deleteLater)
        w._sync_thread.finished.connect(w._sync_thread.deleteLater)
        w._sync_thread.start()

    def update_sync_button_state(self) -> None:
        w = self.window
        pending_plan = getattr(w, "_pending_sync_plan", None)
        report = getattr(w, "_last_sync_report", None)
        conflictos_pendientes_total = _normalizar_conflictos_pendientes_total(
            w._conflicts_service.count_conflicts()
        )
        entrada = EstadoBotonSyncEntrada(
            sync_configurado=w._sync_service.is_configured(),
            sync_en_progreso=w._sync_in_progress,
            hay_plan_pendiente=pending_plan is not None,
            plan_tiene_cambios=bool(
                pending_plan is not None and pending_plan.has_changes
            ),
            plan_tiene_conflictos=bool(
                pending_plan is not None and pending_plan.conflicts
            ),
            ultimo_reporte_presente=report is not None,
            ultimo_reporte_tiene_fallos=bool(
                report and (report.errors or report.conflicts)
            ),
            conflictos_pendientes_total=conflictos_pendientes_total,
            texto_sync_actual=_leer_texto_boton(getattr(w, "sync_button", None)),
            tooltip_sync_actual=_leer_tooltip_boton(getattr(w, "sync_button", None)),
        )
        decision = decidir_estado_botones_sync(entrada)

        _aplicar_decision_boton(w.sync_button, decision.sync)
        if hasattr(w.review_conflicts_button, "setText"):
            w.review_conflicts_button.setText(
                _texto_review_conflictos(
                    reason_code=decision.review_conflicts.reason_code,
                    severity=decision.review_conflicts.severity,
                )
            )
        _aplicar_decision_boton(w.review_conflicts_button, decision.review_conflicts)

        if hasattr(w, "simulate_sync_button"):
            _aplicar_decision_boton(w.simulate_sync_button, decision.simulate_sync)
        if hasattr(w, "confirm_sync_button"):
            _aplicar_decision_boton(w.confirm_sync_button, decision.confirm_sync)
        if hasattr(w, "retry_failed_button"):
            _aplicar_decision_boton(w.retry_failed_button, decision.retry_failed)
        if hasattr(w, "_update_conflicts_reminder"):
            w._update_conflicts_reminder()
        if hasattr(w, "sync_details_button"):
            _aplicar_decision_boton(w.sync_details_button, decision.sync_details)
        if hasattr(w, "copy_sync_report_button"):
            _aplicar_decision_boton(
                w.copy_sync_report_button, decision.copy_sync_report
            )

    def on_open_opciones(self) -> None:
        w = self.window
        from app.ui.dialog_opciones import OpcionesDialog

        dialog = OpcionesDialog(w._sheets_service, w)
        dialog.exec()
        if w._sync_service.is_configured():
            w.go_to_sync_config_button.setVisible(False)
            w._set_sync_status_badge("IDLE")
            w.sync_panel_status.setText(
                _tr(
                    w, "sync.estado_pendiente", _fallback_texto("sync.estado_pendiente")
                )
            )
        self.update_sync_button_state()

    def _handle_operation_finished(
        self,
        result: object,
        *,
        expected_persona_id: int | None,
        on_finished,
        operation_name: str,
    ) -> None:
        if self._es_contexto_vigente(expected_persona_id):
            on_finished(result)
            return
        logger.info(
            "SYNC_CONTEXT_STALE_FINISHED_IGNORED",
            extra={
                "operation": operation_name,
                "expected_persona_id": expected_persona_id,
                "active_persona_id": self._contexto_persona_activo(),
            },
        )
        self._discard_stale_operation_result()

    def _handle_operation_failed(
        self,
        payload: object,
        *,
        expected_persona_id: int | None,
        operation_name: str,
    ) -> None:
        if self._es_contexto_vigente(expected_persona_id):
            self._on_sync_failed(payload)
            return
        logger.info(
            "SYNC_CONTEXT_STALE_FAILURE_IGNORED",
            extra={
                "operation": operation_name,
                "expected_persona_id": expected_persona_id,
                "active_persona_id": self._contexto_persona_activo(),
            },
        )
        self._discard_stale_operation_result()

    def _discard_stale_operation_result(self) -> None:
        w = self.window
        w._pending_sync_plan = None
        if hasattr(w, '_set_sync_in_progress'):
            w._set_sync_in_progress(False)
        self.update_sync_button_state()
        refrescar_pendientes = getattr(w, '_reload_pending_views', None)
        if callable(refrescar_pendientes):
            refrescar_pendientes()
        refrescar_historico = getattr(w, '_refresh_historico', None)
        if callable(refrescar_historico):
            refrescar_historico()
        refrescar_saldos = getattr(w, '_refresh_saldos', None)
        if callable(refrescar_saldos):
            refrescar_saldos()
        refrescar_contexto = getattr(w, '_update_global_context', None)
        if callable(refrescar_contexto):
            refrescar_contexto()

    def _es_contexto_vigente(self, expected_persona_id: int | None) -> bool:
        return expected_persona_id == self._contexto_persona_activo()

    def _contexto_persona_activo(self) -> int | None:
        return resolve_active_delegada_id(self.window)

    def _on_sync_failed(self, payload: object) -> None:
        error = _extract_error(payload)
        if isinstance(error, SheetsPermissionError):
            self._handle_permission_error(error)
        self.window._on_sync_failed(payload)

    def _handle_permission_error(self, error: SheetsPermissionError) -> None:
        service_email = error.service_account_email or _resolve_service_account_email(
            self.window
        )
        log_operational_error(
            logger,
            _fallback_texto("sync.permisos_bloqueados_log"),
            exc=error,
            extra={
                "operation": "sheets_permission_check",
                "spreadsheet_id": error.spreadsheet_id,
                "worksheet": error.worksheet,
                "service_email": service_email,
                "correlation_id": getattr(
                    getattr(self.window, "_sync_operation_context", None),
                    "correlation_id",
                    None,
                ),
            },
        )
        if hasattr(self.window, "toast"):
            self.window.toast.warning(
                build_sync_permission_blocked_message(
                    service_account_email=service_email
                ),
                title=_tr(
                    self.window,
                    "sync.permisos_google_sheets",
                    _fallback_texto("sync.permisos_google_sheets"),
                ),
                duration_ms=7000,
            )


def _aplicar_decision_boton(widget, decision) -> None:
    """Aplica una decisión de estado a un botón Qt sin acoplar reglas al controlador."""

    if widget is None:
        return
    if hasattr(widget, "setEnabled"):
        widget.setEnabled(decision.enabled)
    if decision.text and hasattr(widget, "setText"):
        widget.setText(decision.text)
    if decision.tooltip is not None and hasattr(widget, "setToolTip"):
        widget.setToolTip(decision.tooltip)


def _texto_review_conflictos(reason_code: str, severity: str | None) -> str:
    """Resuelve el texto i18n del botón de conflictos a partir del contrato de decisión."""

    if reason_code == "review_conflictos_pendientes" or severity == "warning":
        return copy_text("ui.sync.revisar_conflictos")
    return copy_text("ui.sync.revisar_conflictos_sin_pendientes")


def _leer_texto_boton(widget) -> str:
    if widget is None or not hasattr(widget, "text"):
        return ""
    try:
        texto = widget.text()
    except TypeError:
        return ""
    return str(texto)


def _leer_tooltip_boton(widget) -> str:
    if widget is None or not hasattr(widget, "toolTip"):
        return ""
    try:
        tooltip = widget.toolTip()
    except TypeError:
        return ""
    return str(tooltip)


def _extract_error(payload: object) -> Exception | None:
    if isinstance(payload, dict):
        error = payload.get("error")
        return error if isinstance(error, Exception) else None
    if isinstance(payload, Exception):
        return payload
    return None


def _normalizar_conflictos_pendientes_total(conflictos_pendientes: object) -> int:
    """Normaliza entradas legacy para entregar siempre un contador entero."""

    if isinstance(conflictos_pendientes, int):
        return conflictos_pendientes
    if conflictos_pendientes is None:
        return 0
    if isinstance(conflictos_pendientes, (list, tuple, set, frozenset, Set)):
        return len(conflictos_pendientes)
    return 0


def _resolve_service_account_email(window) -> str:
    sync_service = getattr(window, "_sync_service", None)
    if sync_service is not None and hasattr(sync_service, "get_service_account_email"):
        account_email = sync_service.get_service_account_email()
        if isinstance(account_email, str) and account_email.strip():
            return account_email.strip()
    logger.warning(
        "SHEETS_SERVICE_EMAIL_MISSING", extra={"event": "SHEETS_SERVICE_EMAIL_MISSING"}
    )
    return _tr(
        window, "sync.email_no_disponible", _fallback_texto("sync.email_no_disponible")
    )


def _fallback_texto(key: str) -> str:
    catalogo_es = CATALOGO.get("es", {}) if isinstance(CATALOGO, dict) else {}
    if isinstance(catalogo_es, dict):
        texto = catalogo_es.get(key)
        if isinstance(texto, str) and texto.strip():
            return texto
    return key


def _tr(window, key: str, fallback: str, **params: object) -> str:
    """Resuelve textos i18n con fallback estático para pruebas unitarias/headless."""

    i18n = getattr(window, "i18n", None)
    return resolver_texto_i18n(
        i18n=i18n, key=key, fallback=fallback, catalogo=CATALOGO, **params
    )
