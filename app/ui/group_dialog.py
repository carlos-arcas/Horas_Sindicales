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
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.application.dto import GrupoConfigDTO
from app.application.use_cases import GrupoConfigUseCases
from app.domain.services import BusinessRuleError

logger = logging.getLogger(__name__)


class GrupoConfigDialog(QDialog):
    def __init__(self, use_cases: GrupoConfigUseCases, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._use_cases = use_cases
        self._config: GrupoConfigDTO | None = None
        self._include_hours: bool | None = None
        self.setWindowTitle("Editar grupo")
        self._build_ui()
        self._load_config()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignLeft)

        hours_container = QWidget()
        hours_layout = QHBoxLayout(hours_container)
        hours_layout.setContentsMargins(0, 0, 0, 0)
        hours_layout.setSpacing(8)

        self.group_hours_input = QSpinBox()
        self.group_hours_input.setRange(0, 9999)
        self.group_hours_input.setSuffix(" h")
        hours_layout.addWidget(self.group_hours_input)

        self.group_minutes_input = QSpinBox()
        self.group_minutes_input.setRange(0, 59)
        self.group_minutes_input.setSuffix(" min")
        hours_layout.addWidget(self.group_minutes_input)
        hours_layout.addStretch(1)

        form_layout.addRow("Horas anuales del grupo", hours_container)

        layout.addLayout(form_layout)

        pdf_group = QVBoxLayout()
        pdf_group.setSpacing(8)
        pdf_title = QLabel("Opciones PDF")
        pdf_title.setProperty("role", "subtitle")
        pdf_group.addWidget(pdf_title)

        logo_row = QHBoxLayout()
        self.logo_path_input = QLineEdit()
        self.logo_path_input.setReadOnly(True)
        logo_row.addWidget(self.logo_path_input, 1)

        self.logo_button = QPushButton("Cambiar logo…")
        self.logo_button.setProperty("variant", "secondary")
        self.logo_button.clicked.connect(self._on_select_logo)
        logo_row.addWidget(self.logo_button)
        pdf_group.addLayout(logo_row)

        self.pdf_intro_input = QPlainTextEdit()
        self.pdf_intro_input.setPlaceholderText("Texto introductorio para los PDFs")
        self.pdf_intro_input.setFixedHeight(120)
        pdf_group.addWidget(self.pdf_intro_input)

        layout.addLayout(pdf_group)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch(1)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setProperty("variant", "secondary")
        self.cancel_button.clicked.connect(self.reject)
        actions_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("Guardar")
        self.save_button.setProperty("variant", "primary")
        self.save_button.clicked.connect(self._on_save)
        actions_layout.addWidget(self.save_button)

        layout.addLayout(actions_layout)

    def _load_config(self) -> None:
        try:
            self._config = self._use_cases.get_grupo_config()
        except BusinessRuleError:
            self._config = None
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error cargando configuración de grupo")
            QMessageBox.critical(self, "Error", str(exc))
            return

        if self._config:
            total_min = self._config.bolsa_anual_grupo_min
            self.group_hours_input.setValue(total_min // 60)
            self.group_minutes_input.setValue(total_min % 60)
            self.logo_path_input.setText(self._config.pdf_logo_path or "")
            self.pdf_intro_input.setPlainText(self._config.pdf_intro_text or "")
            self._include_hours = self._config.pdf_include_hours_in_horario

    def _on_select_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar logo",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.svg)",
        )
        if path:
            self.logo_path_input.setText(path)

    def _on_save(self) -> None:
        total_minutes = self.group_hours_input.value() * 60 + self.group_minutes_input.value()
        dto = GrupoConfigDTO(
            id=self._config.id if self._config else 1,
            nombre_grupo=self._config.nombre_grupo if self._config else None,
            bolsa_anual_grupo_min=total_minutes,
            pdf_logo_path=self.logo_path_input.text().strip(),
            pdf_intro_text=self.pdf_intro_input.toPlainText().strip(),
            pdf_include_hours_in_horario=self._include_hours,
        )
        try:
            self._use_cases.update_grupo_config(dto)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error guardando configuración de grupo")
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.accept()
