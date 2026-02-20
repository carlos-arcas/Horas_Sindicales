from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.application.dto import SolicitudDTO
from app.domain.time_utils import minutes_to_hhmm
from app.ui.widgets.toast import ToastManager


class ConfirmationSummaryDialog(QDialog):
    def __init__(self, title: str, lines: list[str], parent: QWidget | None = None) -> None:
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

    def notify_added_pending(self, solicitud: SolicitudDTO, *, on_undo: Callable[[], None]) -> None:
        duration_minutes = int(round(solicitud.horas * 60))
        tramo = "completo" if solicitud.completo else f"{solicitud.desde}-{solicitud.hasta}"
        message = (
            f"Añadido a pendientes: {solicitud.fecha_pedida} {tramo} "
            f"({minutes_to_hhmm(duration_minutes)})."
        )
        self._toast.show(
            message,
            level="success",
            duration_ms=9000,
            action_label="Deshacer",
            action_callback=on_undo,
            title="Solicitud en pendientes",
        )

    def notify_validation_error(self, *, what: str, why: str, how: str) -> None:
        self._toast.warning(f"{what} {why} {how}", title="Revisa el formulario", duration_ms=7000)

    def show_confirmation_summary(self, *, count: int, total_minutes: int) -> None:
        dialog = ConfirmationSummaryDialog(
            "Confirmación completada",
            [
                f"Confirmadas {count} solicitudes.",
                f"Total confirmado: {minutes_to_hhmm(total_minutes)}.",
                "Próximo paso: Abrir PDF / Ver histórico / Sincronizar.",
            ],
            self._parent,
        )
        dialog.exec()
