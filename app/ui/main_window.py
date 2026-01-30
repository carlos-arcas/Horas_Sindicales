from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.application.use_cases import PersonaUseCases
from app.domain.services import ValidacionError
from app.ui.models_qt import PersonasTableModel
from app.ui.person_dialog import PersonaDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, persona_use_cases: PersonaUseCases) -> None:
        super().__init__()
        self._persona_use_cases = persona_use_cases
        self.setWindowTitle("Horas Sindicales")
        self._build_ui()
        self._load_personas()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        self.table = QTableView()
        self.model = PersonasTableModel([])
        self.table.setModel(self.model)
        layout.addWidget(self.table)

        toolbar = QToolBar("Acciones")
        self.addToolBar(toolbar)

        add_persona = QPushButton("Nueva persona")
        add_persona.clicked.connect(self._on_add_persona)
        toolbar.addWidget(add_persona)

        self.setCentralWidget(central)

    def _load_personas(self) -> None:
        personas = list(self._persona_use_cases.listar())
        self.model.set_personas(personas)

    def _on_add_persona(self) -> None:
        dialog = PersonaDialog(self)
        persona_dto = dialog.get_persona()
        if persona_dto is None:
            logger.info("Creación de persona cancelada")
            return
        try:
            self._persona_use_cases.crear(persona_dto)
        except ValidacionError as exc:
            QMessageBox.warning(self, "Validación", str(exc))
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.exception("Error creando persona")
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._load_personas()
