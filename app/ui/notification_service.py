from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.application.dto import SolicitudDTO
from app.application.dtos.contexto_operacion import ContextoOperacion
from app.ui.copy_catalog import copy_text
from app.ui.presentacion_confirmacion_notificaciones import construir_presentacion_confirmacion
from app.ui.presentador_feedback_notificaciones import (
    construir_detalles_feedback,
    construir_payload_toast_operacion,
    resolver_estado_confirmacion,
)
from app.ui.estilos.cargador_estilos_notificaciones import (
    construir_estilo_dialogo_confirmacion_resumen,
    construir_estilo_dialogo_operacion_feedback,
)
from app.ui.patterns import SPACING_BASE, apply_modal_behavior, build_modal_actions
from app.ui.toast_helpers import toast_success
from app.ui.widgets.toast import GestorToasts


@dataclass(slots=True)
class OperationFeedback:
    title: str
    happened: str
    affected_count: int
    incidents: str
    next_step: str
    status: str = "success"
    timestamp: str | None = None
    result_id: str | None = None
    details: list[str] | None = None


@dataclass(slots=True)
class ConfirmationSummaryPayload:
    count: int
    total_minutes: int
    delegadas: list[str]
    saldo_disponible: str
    errores: list[str]
    status: str
    timestamp: str
    result_id: str
    correlation_id: str | None = None
    on_view_history: Callable[[], None] | None = None
    on_sync_now: Callable[[], None] | None = None
    on_return_to_operativa: Callable[[], None] | None = None
    undo_seconds: int | None = None
    on_undo: Callable[[], None] | None = None


class OperationFeedbackDialog(QDialog):
    def __init__(
        self,
        title: str,
        lines: list[str],
        *,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setObjectName("dialogoOperacionFeedback")
        self.setMinimumWidth(520)
        self.setStyleSheet(construir_estilo_dialogo_operacion_feedback())

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_BASE)
        for text in lines:
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)

        action_button = None
        if action_label and action_callback:
            action_button = QPushButton(action_label)
            action_button.setProperty("variant", "secondary")
            action_button.clicked.connect(lambda: (action_callback(), self.accept()))
        close_button = QPushButton(copy_text("ui.preferencias.cerrar"))
        close_button.setProperty("variant", "ghost")
        close_button.clicked.connect(self.accept)
        actions = build_modal_actions(close_button, action_button if action_label and action_callback else None)
        layout.addLayout(actions)
        apply_modal_behavior(self, primary_button=action_button if action_label and action_callback else None)


class NotificationService:
    def __init__(self, toast: GestorToasts, parent: QWidget) -> None:
        self._toast = toast
        self._parent = parent
        self._operation_counter = 0

    def _next_result_id(self) -> str:
        self._operation_counter += 1
        return f"{copy_text("ui.notificacion.resultado_prefijo")}{self._operation_counter:04d}"

    def build_operation_context(self, *, result_id: str | None = None) -> ContextoOperacion:
        resolved_result_id = result_id or self._next_result_id()
        return ContextoOperacion.nuevo(result_id=resolved_result_id)

    def _normalize_feedback(self, feedback: OperationFeedback) -> OperationFeedback:
        return OperationFeedback(
            title=feedback.title,
            happened=feedback.happened,
            affected_count=feedback.affected_count,
            incidents=feedback.incidents,
            next_step=feedback.next_step,
            status=feedback.status,
            timestamp=feedback.timestamp or datetime.now().strftime(copy_text("ui.toast.fecha_formato_default")),
            result_id=feedback.result_id or self._next_result_id(),
            details=feedback.details,
        )

    def notify_operation(self, feedback: OperationFeedback, *, show_details: bool = False) -> None:
        normalized = self._normalize_feedback(feedback)
        payload = construir_payload_toast_operacion(normalized)
        self._toast.show(
            payload.message,
            level=payload.level,
            title=normalized.title,
            details="\n".join(payload.details),
            duration_ms=7000,
        )
        if show_details:
            self.show_operation_details(normalized)

    def show_operation_details(self, feedback: OperationFeedback) -> None:
        normalized = self._normalize_feedback(feedback)
        dialog = OperationFeedbackDialog(
            normalized.title,
            construir_detalles_feedback(normalized),
            parent=self._parent,
        )
        dialog.exec()

    def notify_added_pending(self, solicitud: SolicitudDTO, *, on_undo: Callable[[], None]) -> None:
        _ = (solicitud, on_undo)
        toast_success(
            self._toast,
            copy_text("ui.notificacion.solicitud_anadida_ok"),
        )

    def notify_validation_error(self, *, what: str, why: str, how: str) -> None:
        self._toast.warning(f"{what} {why} {how}", title=copy_text("ui.notificacion.revisa_formulario"), duration_ms=7000)

    def show_confirmation_summary(self, *, count: int, total_minutes: int, errores: list[str] | None = None) -> None:
        issues = errores or []
        status = resolver_estado_confirmacion(count=count, errores=issues)
        payload = ConfirmationSummaryPayload(
            count=count,
            total_minutes=total_minutes,
            delegadas=[],
            saldo_disponible=copy_text("ui.toast.no_disponible"),
            errores=issues,
            status=status,
            timestamp=datetime.now().strftime(copy_text("ui.toast.fecha_formato_default")),
            result_id=self._next_result_id(),
            correlation_id=ContextoOperacion.nuevo().correlation_id,
        )
        self.show_confirmation_closure(payload)

    def show_confirmation_closure(self, payload: ConfirmationSummaryPayload) -> None:
        presentacion = construir_presentacion_confirmacion(
            status=payload.status,
            count=payload.count,
            total_minutes=payload.total_minutes,
            delegadas=payload.delegadas,
            saldo_disponible=payload.saldo_disponible,
            timestamp=payload.timestamp,
            result_id=payload.result_id,
            correlation_id=payload.correlation_id,
            errores=payload.errores,
        )
        dialog = QDialog(self._parent)
        dialog.setWindowTitle(presentacion.titulo)
        dialog.setModal(True)
        dialog.setObjectName("dialogoConfirmacionResumen")
        dialog.setStyleSheet(construir_estilo_dialogo_confirmacion_resumen(color_borde=presentacion.color_borde))

        layout = QVBoxLayout(dialog)
        layout.setSpacing(SPACING_BASE)
        for line in presentacion.lineas_resumen:
            label = QLabel(line)
            label.setWordWrap(True)
            layout.addWidget(label)

        if presentacion.avisos:
            warnings_title = QLabel(copy_text("ui.dialogo.avisos"))
            warnings_title.setProperty("role", "secondary")
            layout.addWidget(warnings_title)
            for error in presentacion.avisos:
                layout.addWidget(QLabel(f"• {error}"))

        actions = QHBoxLayout()
        actions.setSpacing(SPACING_BASE)

        if payload.on_view_history is not None:
            view_button = QPushButton(copy_text("ui.dialogo.ver_historico"))
            view_button.setProperty("variant", "secondary")
            view_button.clicked.connect(lambda: (payload.on_view_history(), dialog.accept()))
            actions.addWidget(view_button)
        if payload.on_sync_now is not None:
            sync_button = QPushButton(copy_text("ui.sync.sincronizar_ahora"))
            sync_button.setProperty("variant", "primary")
            sync_button.clicked.connect(lambda: (payload.on_sync_now(), dialog.accept()))
            actions.addWidget(sync_button)
        self._adjuntar_accion_deshacer(dialog=dialog, actions=actions, payload=payload)
        close_button = QPushButton(copy_text("ui.dialogo.volver_operativa"))
        close_button.setProperty("variant", "ghost")
        close_button.clicked.connect(lambda: (payload.on_return_to_operativa() if payload.on_return_to_operativa else None, dialog.accept()))
        actions.addWidget(close_button)
        layout.addLayout(actions)
        apply_modal_behavior(dialog)

        dialog.exec()

    def _adjuntar_accion_deshacer(
        self,
        *,
        dialog: QDialog,
        actions: QHBoxLayout,
        payload: ConfirmationSummaryPayload,
    ) -> None:
        if not payload.undo_seconds or payload.on_undo is None or payload.status == "error":
            return
        undo_button = QPushButton(copy_text("ui.dialogo.deshacer_segundos").format(segundos=payload.undo_seconds))
        countdown = {"value": payload.undo_seconds}

        def _tick_undo() -> None:
            countdown["value"] -= 1
            if countdown["value"] <= 0:
                undo_button.setText(copy_text("ui.dialogo.deshacer_no_disponible"))
                undo_button.setEnabled(False)
                timer.stop()
                return
            undo_button.setText(copy_text("ui.dialogo.deshacer_segundos").format(segundos=countdown["value"]))

        timer = QTimer(dialog)
        timer.setInterval(1000)
        timer.timeout.connect(_tick_undo)
        timer.start()
        undo_button.clicked.connect(lambda: (payload.on_undo(), dialog.accept()))
        actions.addWidget(undo_button)
