from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.ui.widgets.toast_models import ToastDTO


class DialogoDetallesToast(QDialog):
    def __init__(self, dto: ToastDTO, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dto = dto
        self.setWindowTitle("Detalles de notificación")
        self.setModal(True)
        self.resize(560, 420)

        root = QVBoxLayout(self)
        for line in self._summary_lines():
            label = QLabel(line)
            label.setWordWrap(True)
            root.addWidget(label)

        self._detalles = QTextEdit()
        self._detalles.setReadOnly(True)
        self._detalles.setPlainText(self._build_copy_text())
        root.addWidget(self._detalles, 1)

        actions = QHBoxLayout()
        self._btn_copiar = QPushButton("Copiar")
        self._btn_cerrar = QPushButton("Cerrar")
        self._btn_copiar.clicked.connect(self._copiar_al_portapapeles)
        self._btn_cerrar.clicked.connect(self.accept)
        actions.addStretch(1)
        actions.addWidget(self._btn_copiar)
        actions.addWidget(self._btn_cerrar)
        root.addLayout(actions)

    def _summary_lines(self) -> list[str]:
        return [
            f"Título: {self._dto.titulo}",
            f"Mensaje: {self._dto.mensaje}",
            f"Código: {self._dto.codigo or 'No disponible'}",
            f"Correlación: {self._dto.correlacion_id or 'No disponible'}",
            f"Fecha y hora: {self._dto.timestamp}",
        ]

    def _build_copy_text(self) -> str:
        bloques = [
            f"Título: {self._dto.titulo}",
            f"Mensaje: {self._dto.mensaje}",
            f"Detalles: {self._dto.detalles or 'No disponible'}",
            f"Código: {self._dto.codigo or 'No disponible'}",
            f"Correlación: {self._dto.correlacion_id or 'No disponible'}",
            f"Timestamp: {self._dto.timestamp}",
        ]
        return "\n".join(bloques)

    def _copiar_al_portapapeles(self) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self._build_copy_text())
