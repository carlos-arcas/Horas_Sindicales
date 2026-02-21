from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.components.status_badge import StatusBadge


class ContextoTrabajoWidget(QWidget):
    delegada_cambiada = Signal(int)
    editar_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(8)

        titulo = QLabel("Contexto de trabajo")
        titulo.setProperty("role", "sectionTitle")
        fila.addWidget(titulo)

        fila.addWidget(QLabel("Delegada"))
        self.delegada_combo = QComboBox()
        self.delegada_combo.setObjectName("contexto_delegada_combo")
        self.delegada_combo.currentIndexChanged.connect(self._emitir_cambio_delegada)
        fila.addWidget(self.delegada_combo, 1)

        fila.addWidget(QLabel("Grupo/servicio"))
        self.grupo_label = QLabel("—")
        self.grupo_label.setProperty("role", "secondary")
        fila.addWidget(self.grupo_label)

        self.sync_badge = StatusBadge("Sin estado", variant="neutral")
        self.sync_badge.setObjectName("contexto_sync_badge")
        fila.addWidget(self.sync_badge)

        self.editar_button = QPushButton("Cambiar…")
        self.editar_button.setProperty("variant", "secondary")
        self.editar_button.clicked.connect(self.editar_clicked.emit)
        fila.addWidget(self.editar_button)

        root.addLayout(fila)

        self.aviso_label = QLabel("Selecciona una delegada para empezar.")
        self.aviso_label.setProperty("role", "secondary")
        self.aviso_label.setObjectName("contexto_aviso_label")
        self.aviso_label.setVisible(False)
        root.addWidget(self.aviso_label)

    def _emitir_cambio_delegada(self) -> None:
        self.delegada_cambiada.emit(self.delegada_combo.currentIndex())

    def set_aviso_delegada(self, visible: bool) -> None:
        self.aviso_label.setVisible(visible)

    def set_grupo_servicio(self, value: str | None) -> None:
        self.grupo_label.setText(value or "—")

    def set_sync_estado(self, texto: str, *, variant: str = "neutral") -> None:
        self.sync_badge.setText(texto)
        self.sync_badge.setProperty("variant", variant)
