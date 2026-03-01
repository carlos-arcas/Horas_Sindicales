from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel, QPushButton, QTextEdit, QVBoxLayout

from app.bootstrap.settings import resolve_log_dir
from app.ui.vistas.ui_helpers import abrir_archivo_local
from presentacion.i18n import I18nManager


class DialogoErrorArranque(QDialog):
    def __init__(
        self,
        i18n: I18nManager,
        *,
        titulo: str,
        mensaje_usuario: str,
        incident_id: str,
        detalles: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._incident_id = incident_id
        self.setWindowTitle(titulo)

        layout = QVBoxLayout(self)

        mensaje = QLabel(mensaje_usuario)
        mensaje.setWordWrap(True)
        layout.addWidget(mensaje)

        incident = QLabel(i18n.t("startup_error_incident_label", incident_id=incident_id))
        incident.setProperty("role", "caption")
        layout.addWidget(incident)

        self._detalles = QTextEdit()
        self._detalles.setReadOnly(True)
        self._detalles.setVisible(bool(detalles))
        self._detalles.setPlainText(detalles or "")
        layout.addWidget(self._detalles)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self._copiar_id_btn = QPushButton(i18n.t("startup_error_copy_id"))
        self._abrir_logs_btn = QPushButton(i18n.t("startup_error_open_logs"))
        buttons.addButton(self._copiar_id_btn, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(self._abrir_logs_btn, QDialogButtonBox.ButtonRole.ActionRole)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._copiar_id_btn.clicked.connect(self._copiar_incident_id)
        self._abrir_logs_btn.clicked.connect(self._abrir_logs)

    def _copiar_incident_id(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(self._incident_id)

    def _abrir_logs(self) -> None:
        log_dir = Path(resolve_log_dir())
        log_dir.mkdir(parents=True, exist_ok=True)
        abrir_archivo_local(log_dir)
