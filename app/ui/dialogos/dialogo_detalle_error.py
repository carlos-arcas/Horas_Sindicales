from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.ui.copy_catalog import copy_text


class DialogoDetalleError(QDialog):
    def __init__(
        self,
        titulo: str,
        resumen: str,
        detalle: str,
        incident_id: str | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._detalle = detalle
        self._incident_id = incident_id
        self._logs_dir = Path.cwd() / "logs"
        self.setWindowTitle(titulo)
        self.setModal(False)
        self.resize(680, 460)

        root = QVBoxLayout(self)
        self._label_resumen = QLabel(resumen)
        self._label_resumen.setWordWrap(True)
        root.addWidget(self._label_resumen)

        self._label_incidente = QLabel(
            copy_text("ui.error_details.incident_value").format(
                incident_id=incident_id or copy_text("ui.toast.no_disponible")
            )
        )
        self._label_incidente.setWordWrap(True)
        root.addWidget(self._label_incidente)

        self._label_logs = QLabel(
            copy_text("ui.error_details.logs_path").format(logs_path=str(self._logs_dir))
        )
        self._label_logs.setWordWrap(True)
        root.addWidget(self._label_logs)

        self._detalle_tecnico = QTextEdit()
        self._detalle_tecnico.setReadOnly(True)
        self._detalle_tecnico.setPlainText(detalle)
        root.addWidget(self._detalle_tecnico, 1)

        acciones = QHBoxLayout()
        acciones.addStretch(1)
        self._btn_copiar = QPushButton(copy_text("ui.toast.copiar"))
        self._btn_logs = QPushButton(copy_text("ui.error_details.open_logs"))
        self._btn_cerrar = QPushButton(copy_text("ui.toast.cerrar"))
        self._btn_copiar.clicked.connect(self._copiar_detalle)
        self._btn_logs.clicked.connect(self._abrir_logs)
        self._btn_cerrar.clicked.connect(self.close)
        acciones.addWidget(self._btn_copiar)
        acciones.addWidget(self._btn_logs)
        acciones.addWidget(self._btn_cerrar)
        root.addLayout(acciones)

    def _copiar_detalle(self) -> None:
        QGuiApplication.clipboard().setText(self._detalle)

    def _abrir_logs(self) -> None:
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._logs_dir)))


__all__ = [DialogoDetalleError.__name__]
