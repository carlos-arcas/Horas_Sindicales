from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.sheets_service import SheetsService
from app.domain.services import BusinessRuleError

logger = logging.getLogger(__name__)


class OpcionesDialog(QDialog):
    def __init__(self, sheets_service: SheetsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sheets_service = sheets_service
        self.setWindowTitle("Opciones")
        self._build_ui()
        self._load_config()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Google Sheets (Service Account)")
        title.setProperty("role", "subtitle")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignLeft)

        self.spreadsheet_input = QLineEdit()
        self.spreadsheet_input.setPlaceholderText("URL o ID de la spreadsheet")
        form_layout.addRow("Spreadsheet URL/ID", self.spreadsheet_input)

        credentials_row = QHBoxLayout()
        self.credentials_input = QLineEdit()
        self.credentials_input.setReadOnly(True)
        credentials_row.addWidget(self.credentials_input, 1)
        self.credentials_button = QPushButton("Seleccionar credenciales JSON…")
        self.credentials_button.setProperty("variant", "secondary")
        self.credentials_button.clicked.connect(self._on_select_credentials)
        credentials_row.addWidget(self.credentials_button)

        credentials_container = QWidget()
        credentials_container.setLayout(credentials_row)
        form_layout.addRow("Credenciales", credentials_container)

        layout.addLayout(form_layout)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch(1)

        self.test_button = QPushButton("Probar conexión")
        self.test_button.setProperty("variant", "secondary")
        self.test_button.clicked.connect(self._on_test_connection)
        actions_layout.addWidget(self.test_button)

        self.cancel_button = QPushButton("Cerrar")
        self.cancel_button.setProperty("variant", "secondary")
        self.cancel_button.clicked.connect(self.reject)
        actions_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("Guardar")
        self.save_button.setProperty("variant", "primary")
        self.save_button.clicked.connect(self._on_save)
        actions_layout.addWidget(self.save_button)

        layout.addLayout(actions_layout)

    def _load_config(self) -> None:
        config = self._sheets_service.get_config()
        if config:
            self.spreadsheet_input.setText(config.spreadsheet_id)
            self.credentials_input.setText(config.credentials_path)

    def _on_select_credentials(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar credenciales JSON",
            "",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            destination = self._sheets_service.store_credentials(path)
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error copiando credenciales")
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.credentials_input.setText(str(destination))

    def _on_save(self) -> None:
        try:
            self._sheets_service.save_config(
                self.spreadsheet_input.text().strip(),
                self.credentials_input.text().strip(),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error guardando configuración de Sheets")
            QMessageBox.critical(self, "Error", str(exc))
            return
        QMessageBox.information(self, "Opciones", "Configuración guardada correctamente.")

    def _on_test_connection(self) -> None:
        try:
            result = self._sheets_service.test_connection(
                self.spreadsheet_input.text().strip(),
                self.credentials_input.text().strip(),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error probando conexión a Sheets")
            QMessageBox.critical(self, "Error", str(exc))
            return
        extra = ""
        if result.schema_actions:
            extra = "\n\n" + "\n".join(result.schema_actions)
        QMessageBox.information(
            self,
            "Conexión OK",
            f"Spreadsheet: {result.spreadsheet_title}\nID: {result.spreadsheet_id}{extra}",
        )
