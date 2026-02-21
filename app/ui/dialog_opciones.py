from __future__ import annotations

import logging
import json
from pathlib import Path

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
from app.domain.sheets_errors import (
    SheetsApiDisabledError,
    SheetsCredentialsError,
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsRateLimitError,
)
from app.ui.error_mapping import map_error_to_ui_message
from app.ui.patterns import SPACING_BASE, apply_modal_behavior, build_modal_actions, status_badge

logger = logging.getLogger(__name__)


class OpcionesDialog(QDialog):
    def __init__(self, sheets_service: SheetsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sheets_service = sheets_service
        self._last_status_key: tuple[str, str] | None = None
        self.setWindowTitle("Opciones")
        self._build_ui()
        self._load_config()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_BASE * 2, SPACING_BASE * 2, SPACING_BASE * 2, SPACING_BASE * 2)
        layout.setSpacing(SPACING_BASE + 4)

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

        status_container = QVBoxLayout()
        status_title = QLabel("Estado")
        status_title.setProperty("role", "subtitle")
        status_container.addWidget(status_title)
        self.credentials_status_label = QLabel()
        self.spreadsheet_status_label = QLabel()
        self.connection_status_label = QLabel()
        status_container.addWidget(self.credentials_status_label)
        status_container.addWidget(self.spreadsheet_status_label)
        status_container.addWidget(self.connection_status_label)
        layout.addLayout(status_container)

        self.test_button = QPushButton("Probar conexión")
        self.test_button.setProperty("variant", "secondary")
        self.test_button.clicked.connect(self._on_test_connection)

        self.cancel_button = QPushButton("Cerrar")
        self.cancel_button.setProperty("variant", "ghost")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("Guardar")
        self.save_button.setProperty("variant", "primary")
        self.save_button.clicked.connect(self._on_save)

        actions_layout = build_modal_actions(self.cancel_button, self.save_button)
        actions_layout.insertWidget(0, self.test_button)
        layout.addLayout(actions_layout)
        apply_modal_behavior(self, primary_button=self.save_button)

        self.spreadsheet_input.textChanged.connect(self._update_status)
        self.credentials_input.textChanged.connect(self._update_status)

    def _load_config(self) -> None:
        config = self._sheets_service.get_config()
        if config:
            self.spreadsheet_input.setText(config.spreadsheet_id)
            self.credentials_input.setText(config.credentials_path)
        self._update_status()

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
            self._show_unknown_error(exc)
            return
        self.credentials_input.setText(str(destination))
        self._update_status()

    def _on_save(self) -> None:
        try:
            self._sheets_service.save_config(
                self.spreadsheet_input.text().strip(),
                self.credentials_input.text().strip(),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", f"{str(exc)}\nCausa probable: Falta un dato requerido.\nAcción recomendada: Indica el dato faltante y vuelve a probar.")
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error guardando configuración de Sheets")
            self._show_unknown_error(exc)
            return
        QMessageBox.information(self, "Opciones", "Configuración guardada.")
        self._update_status()

    def _on_test_connection(self) -> None:
        try:
            result = self._sheets_service.test_connection(
                self.spreadsheet_input.text().strip(),
                self.credentials_input.text().strip(),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", f"{str(exc)}\nCausa probable: Falta un dato requerido.\nAcción recomendada: Indica el dato faltante y vuelve a probar.")
            return
        except SheetsApiDisabledError:
            self._set_connection_error(
                "La API de Google Sheets no está habilitada en tu proyecto de Google Cloud."
            )
            QMessageBox.critical(
                self,
                "No se pudo validar la conexión",
                "No se pudo validar la conexión.\n"
                "Causa probable: La API de Google Sheets no está habilitada en Google Cloud.\n"
                "Acción recomendada: Activa Google Sheets API y reintenta en 2-5 minutos.",
            )
            return
        except SheetsPermissionError:
            email = self._service_account_email()
            email_hint = f"{email}" if email else "la cuenta de servicio"
            self._set_connection_error("Permisos insuficientes para acceder a la hoja.")
            QMessageBox.critical(
                self,
                "No se pudo validar la conexión",
                "No se pudo validar la conexión.\n"
                f"Causa probable: La hoja no está compartida con {email_hint}.\n"
                "Acción recomendada: Comparte la hoja con ese email como Editor.",
            )
            return
        except SheetsNotFoundError:
            self._set_connection_error("Hoja no encontrada.")
            QMessageBox.critical(
                self,
                "No se pudo validar la conexión",
                "No se pudo validar la conexión.\n"
                "Causa probable: El Spreadsheet ID/URL es inválido o la hoja no existe.\n"
                "Acción recomendada: Revisa el ID/URL y vuelve a probar.",
            )
            return
        except SheetsCredentialsError:
            self._set_connection_error("Credenciales inválidas.")
            QMessageBox.critical(
                self,
                "No se pudo validar la conexión",
                "No se pudo validar la conexión.\n"
                "Causa probable: El archivo de credenciales JSON no es válido o no se puede leer.\n"
                "Acción recomendada: Selecciona de nuevo las credenciales y reintenta.",
            )
            return
        except SheetsRateLimitError:
            self._set_connection_error("Límite temporal alcanzado.")
            QMessageBox.warning(
                self,
                "Sincronización pausada",
                "Sincronización pausada temporalmente.\n"
                "Causa probable: Google Sheets aplicó un límite de peticiones.\n"
                "Acción recomendada: Espera 1 minuto y vuelve a intentar la prueba.",
            )
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error probando conexión a Sheets")
            self._show_unknown_error(exc)
            return
        extra = ""
        if result.schema_actions:
            extra = "\n\n" + "\n".join(result.schema_actions)
        QMessageBox.information(
            self,
            "Conexión OK",
            f"Spreadsheet: {result.spreadsheet_title}\nID: {result.spreadsheet_id}{extra}",
        )
        self._set_connection_ok()

    def _update_status(self) -> None:
        credentials_value = self.credentials_input.text().strip()
        spreadsheet_value = self.spreadsheet_input.text().strip()
        credentials_set = bool(credentials_value)
        spreadsheet_set = bool(spreadsheet_value)
        self.credentials_status_label.setText(
            status_badge("CONFIRMED") + " Credenciales seleccionadas" if credentials_set else status_badge("ERROR") + " Credenciales sin seleccionar"
        )
        self.spreadsheet_status_label.setText(
            status_badge("CONFIRMED") + " Hoja configurada" if spreadsheet_set else status_badge("ERROR") + " Hoja sin configurar"
        )
        status_key = (credentials_value, spreadsheet_value)
        if status_key != self._last_status_key:
            self.connection_status_label.setText(status_badge("PENDING") + " Pendiente de comprobación")
            self._last_status_key = status_key

    def _set_connection_ok(self) -> None:
        self.connection_status_label.setText(status_badge("CONFIRMED") + " Confirmada")

    def _set_connection_error(self, message: str) -> None:
        self.connection_status_label.setText(f"{status_badge('ERROR')} Error: {message}")


    def _show_unknown_error(self, exc: Exception) -> None:
        logger.exception("Error técnico en configuración de Sheets", exc_info=exc)
        mapped = map_error_to_ui_message(exc)
        QMessageBox.critical(self, mapped.title, mapped.as_text())

    def _service_account_email(self) -> str | None:
        path = self.credentials_input.text().strip()
        if not path:
            return None
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return str(payload.get("client_email", "")).strip() or None
