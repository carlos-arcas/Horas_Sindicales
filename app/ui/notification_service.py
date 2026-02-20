from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.application.dto import SolicitudDTO
from app.domain.time_utils import minutes_to_hhmm
from app.ui.widgets.toast import ToastManager


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
    action_label: str | None = None
    action_callback: Callable[[], None] | None = None


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

        layout = QVBoxLayout(self)
        for text in lines:
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)

        actions = QHBoxLayout()
        actions.addStretch(1)
        if action_label and action_callback:
            action_button = QPushButton(action_label)
            action_button.clicked.connect(lambda: (action_callback(), self.accept()))
            actions.addWidget(action_button)
        close_button = QPushButton("Cerrar")
        close_button.setProperty("variant", "primary")
        close_button.clicked.connect(self.accept)
        actions.addWidget(close_button)
        layout.addLayout(actions)

        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.reject)


class NotificationService:
    def __init__(self, toast: ToastManager, parent: QWidget) -> None:
        self._toast = toast
        self._parent = parent
        self._operation_counter = 0

    def _next_result_id(self) -> str:
        self._operation_counter += 1
        return f"OP-{self._operation_counter:04d}"

    def _normalize_feedback(self, feedback: OperationFeedback) -> OperationFeedback:
        return OperationFeedback(
            title=feedback.title,
            happened=feedback.happened,
            affected_count=feedback.affected_count,
            incidents=feedback.incidents,
            next_step=feedback.next_step,
            status=feedback.status,
            timestamp=feedback.timestamp or datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            result_id=feedback.result_id or self._next_result_id(),
            details=feedback.details,
            action_label=feedback.action_label,
            action_callback=feedback.action_callback,
        )

    def _status_to_toast_level(self, status: str) -> str:
        if status == "error":
            return "error"
        if status == "partial":
            return "warning"
        return "success"

    def notify_operation(self, feedback: OperationFeedback, *, show_details: bool = False) -> None:
        normalized = self._normalize_feedback(feedback)
        lines = [
            f"- {normalized.happened}",
            f"- Elementos afectados: {normalized.affected_count}",
            f"- Incidencias: {normalized.incidents}",
            f"- Ahora puedes: {normalized.next_step}",
            f"- {normalized.timestamp} · {normalized.result_id}",
        ]
        self._toast.show(
            "\n".join(lines),
            level=self._status_to_toast_level(normalized.status),
            title=normalized.title,
            duration_ms=7000,
            action_label="Ver detalle",
            action_callback=lambda: self.show_operation_details(normalized),
        )
        if show_details:
            self.show_operation_details(normalized)

    def show_operation_details(self, feedback: OperationFeedback) -> None:
        normalized = self._normalize_feedback(feedback)
        detail_lines = [
            normalized.happened,
            f"Elementos afectados: {normalized.affected_count}",
            f"Incidencias: {normalized.incidents}",
            f"Siguiente paso: {normalized.next_step}",
            f"Fecha y hora: {normalized.timestamp}",
            f"Identificador: {normalized.result_id}",
        ]
        if normalized.details:
            detail_lines.extend(normalized.details)
        dialog = OperationFeedbackDialog(
            normalized.title,
            detail_lines,
            action_label=normalized.action_label,
            action_callback=normalized.action_callback,
            parent=self._parent,
        )
        dialog.exec()

    def notify_added_pending(self, solicitud: SolicitudDTO, *, on_undo: Callable[[], None]) -> None:
        duration_minutes = int(round(solicitud.horas * 60))
        tramo = "completo" if solicitud.completo else f"{solicitud.desde}-{solicitud.hasta}"
        self.notify_operation(
            OperationFeedback(
                title="Solicitud añadida a pendientes",
                happened=(
                    f"Se guardó la solicitud del {solicitud.fecha_pedida} ({tramo}, "
                    f"{minutes_to_hhmm(duration_minutes)})."
                ),
                affected_count=1,
                incidents="Sin incidencias.",
                next_step="Revisar pendientes o continuar cargando solicitudes.",
                action_label="Deshacer",
                action_callback=on_undo,
            )
        )

    def notify_validation_error(self, *, what: str, why: str, how: str) -> None:
        self._toast.warning(f"{what} {why} {how}", title="Revisa el formulario", duration_ms=7000)

    def show_confirmation_summary(self, *, count: int, total_minutes: int, errores: list[str] | None = None) -> None:
        issues = errores or []
        status = "partial" if issues else "success"
        incidents = (
            f"{len(issues)} con advertencia." if issues else "Sin incidencias."
        )
        details = [f"Total confirmado: {minutes_to_hhmm(total_minutes)}."]
        if issues:
            details.extend([f"- {error}" for error in issues])
        self.notify_operation(
            OperationFeedback(
                title="Solicitudes confirmadas",
                happened=f"{count} solicitudes registradas correctamente.",
                affected_count=count,
                incidents=incidents,
                next_step="Puedes revisar el detalle o continuar.",
                status=status,
                details=details,
            ),
            show_details=bool(issues),
        )
