from __future__ import annotations

import json
import logging
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
from app.application.sync_diagnostics import resolve_sync_diagnostic
from app.domain.services import BusinessRuleError
from app.domain.sheets_errors import (
    SheetsApiDisabledError,
    SheetsCredentialsError,
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsRateLimitError,
)
from app.ui.copy_catalog import copy_text
from app.ui.patterns import SPACING_BASE, apply_modal_behavior, build_modal_actions, status_badge

logger = logging.getLogger(__name__)


class OpcionesDialog(QDialog):
    def __init__(self, sheets_service: SheetsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sheets_service = sheets_service
        self._last_status_key: tuple[str, str] | None = None
        self.setWindowTitle(copy_text("sync_credenciales.title"))
        self._build_ui()
        self._load_config()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_BASE * 2, SPACING_BASE * 2, SPACING_BASE * 2, SPACING_BASE * 2)
        layout.setSpacing(SPACING_BASE + 4)

        title = QLabel(copy_text("sync_credenciales.title"))
        title.setProperty("role", "subtitle")
        layout.addWidget(title)

        step_1 = QLabel(f"<b>{copy_text('sync_credenciales.step_1')}</b><br>{copy_text('sync_credenciales.step_1_body')}")
        step_1.setWordWrap(True)
        layout.addWidget(step_1)

        step_2 = QLabel(f"<b>{copy_text('sync_credenciales.step_2')}</b>")
        step_2.setProperty("role", "subtitle")
        layout.addWidget(step_2)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignLeft)

        self.spreadsheet_input = QLineEdit()
        self.spreadsheet_input.setPlaceholderText(copy_text("sync_credenciales.spreadsheet_placeholder"))
        form_layout.addRow("Spreadsheet URL/ID", self.spreadsheet_input)

        credentials_row = QHBoxLayout()
        self.credentials_input = QLineEdit()
        self.credentials_input.setReadOnly(True)
        credentials_row.addWidget(self.credentials_input, 1)
        self.credentials_button = QPushButton(copy_text("sync_credenciales.credentials_button"))
        self.credentials_button.setProperty("variant", "secondary")
        self.credentials_button.clicked.connect(self._on_select_credentials)
        credentials_row.addWidget(self.credentials_button)

        credentials_container = QWidget()
        credentials_container.setLayout(credentials_row)
        form_layout.addRow("Credenciales", credentials_container)
        layout.addLayout(form_layout)

        step_3 = QLabel(f"<b>{copy_text('sync_credenciales.step_3')}</b>")
        step_3.setProperty("role", "subtitle")
        layout.addWidget(step_3)

        status_container = QVBoxLayout()
        self.credentials_status_label = QLabel()
        self.spreadsheet_status_label = QLabel()
        self.connection_status_label = QLabel()
        status_container.addWidget(self.credentials_status_label)
        status_container.addWidget(self.spreadsheet_status_label)
        status_container.addWidget(self.connection_status_label)
        layout.addLayout(status_container)

        self.test_button = QPushButton(copy_text("sync_credenciales.test_connection"))
        self.test_button.setProperty("variant", "secondary")
        self.test_button.clicked.connect(self._on_test_connection)

        self.cancel_button = QPushButton("Cerrar")
        self.cancel_button.setProperty("variant", "ghost")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton(copy_text("sync_credenciales.save"))
        self.save_button.setProperty("variant", "primary")
        self.save_button.clicked.connect(self._on_save)

        actions_layout = build_modal_actions(self.cancel_button, self.save_button)
        actions_layout.insertWidget(0, self.test_button)
        layout.addWidget(QLabel(f"<b>{copy_text('sync_credenciales.step_4')}</b>"))
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
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar credenciales JSON", "", "JSON (*.json)")
        if not path:
            return
        try:
            destination = self._sheets_service.store_credentials(path)
        except Exception as exc:  # pragma: no cover
            logger.exception("Error copiando credenciales", exc_info=exc)
            self._show_diagnostic("unknown")
            return
        self.credentials_input.setText(str(destination))
        self._update_status()

    def _on_save(self) -> None:
        try:
            self._sheets_service.save_config(
                self.spreadsheet_input.text().strip(),
                self.credentials_input.text().strip(),
            )
        except BusinessRuleError:
            self._show_diagnostic("missing_input")
            return
        except Exception as exc:  # pragma: no cover
            logger.exception("Error guardando configuración de Sheets", exc_info=exc)
            self._show_diagnostic("unknown")
            return
        QMessageBox.information(self, "Configuración", copy_text("sync_credenciales.saved_ok"))
        self._update_status()

    def _on_test_connection(self) -> None:
        spreadsheet = self.spreadsheet_input.text().strip()
        credentials = self.credentials_input.text().strip()
        try:
            result = self._sheets_service.test_connection(spreadsheet, credentials)
        except BusinessRuleError:
            self._show_diagnostic("missing_input")
            return
        except SheetsApiDisabledError as exc:
            logger.exception("sync_test_error api_disabled", exc_info=exc)
            self._show_diagnostic("api_disabled")
            return
        except SheetsPermissionError as exc:
            logger.exception("sync_test_error sheet_access_denied", exc_info=exc)
            self._show_diagnostic("sheet_access_denied")
            return
        except SheetsNotFoundError as exc:
            logger.exception("sync_test_error sheet_not_found", exc_info=exc)
            self._show_diagnostic("sheet_not_found")
            return
        except SheetsCredentialsError as exc:
            logger.exception("sync_test_error invalid_credentials", exc_info=exc)
            self._show_diagnostic("invalid_credentials")
            return
        except SheetsRateLimitError as exc:
            logger.exception("sync_test_error rate_limit", exc_info=exc)
            self._show_diagnostic("rate_limit")
            return
        except FileNotFoundError as exc:
            logger.exception("sync_test_error file_not_found", exc_info=exc)
            self._show_diagnostic("file_not_found")
            return
        except PermissionError as exc:
            logger.exception("sync_test_error permission_denied", exc_info=exc)
            self._show_diagnostic("permission_denied")
            return
        except Exception as exc:  # pragma: no cover
            logger.exception("Error probando conexión a Sheets", exc_info=exc)
            self._show_diagnostic("unknown")
            return

        extra = ""
        if result.schema_actions:
            extra = "\n\n" + "\n".join(result.schema_actions)
        QMessageBox.information(self, "Conexión OK", f"Spreadsheet: {result.spreadsheet_title}\nID: {result.spreadsheet_id}{extra}")
        self._set_connection_ok()

    def _show_diagnostic(self, reason_code: str) -> None:
        diagnostic = resolve_sync_diagnostic(reason_code)
        self._set_connection_error(diagnostic.message)
        QMessageBox.warning(
            self,
            diagnostic.title,
            f"{diagnostic.message}\n\nQué hacer ahora: {diagnostic.suggested_action}",
        )

    def _update_status(self) -> None:
        credentials_value = self.credentials_input.text().strip()
        spreadsheet_value = self.spreadsheet_input.text().strip()
        credentials_set = bool(credentials_value)
        spreadsheet_set = bool(spreadsheet_value)
        self.credentials_status_label.setText(
            status_badge("CONFIRMED") + " " + copy_text("sync_credenciales.status_credentials_ok")
            if credentials_set
            else status_badge("ERROR") + " " + copy_text("sync_credenciales.status_credentials_missing")
        )
        self.spreadsheet_status_label.setText(
            status_badge("CONFIRMED") + " " + copy_text("sync_credenciales.status_sheet_ok")
            if spreadsheet_set
            else status_badge("ERROR") + " " + copy_text("sync_credenciales.status_sheet_missing")
        )
        status_key = (credentials_value, spreadsheet_value)
        if status_key != self._last_status_key:
            self.connection_status_label.setText(status_badge("PENDING") + " " + copy_text("sync_credenciales.status_pending"))
            self._last_status_key = status_key

    def _set_connection_ok(self) -> None:
        self.connection_status_label.setText(status_badge("CONFIRMED") + " " + copy_text("sync_credenciales.status_ok"))

    def _set_connection_error(self, message: str) -> None:
        self.connection_status_label.setText(f"{status_badge('ERROR')} {message}")

    def _service_account_email(self) -> str | None:
        path = self.credentials_input.text().strip()
        if not path:
            return None
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return str(payload.get("client_email", "")).strip() or None
