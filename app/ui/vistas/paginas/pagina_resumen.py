from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.components.card_widget import CardWidget
from app.ui.components.primary_button import PrimaryButton
from app.ui.components.secondary_button import SecondaryButton


class PaginaResumen(QWidget):
    nueva_solicitud = Signal()
    ver_pendientes = Signal()
    sincronizar_ahora = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Resumen")
        title.setProperty("role", "sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Tu jornada de hoy, en un vistazo claro y accionable.")
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "secondary")
        layout.addWidget(subtitle)

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(16)
        kpi_grid.setVerticalSpacing(16)

        self.kpi_solicitudes_hoy = self._build_kpi_card("Solicitudes hoy", "—")
        self.kpi_pendientes = self._build_kpi_card("Pendientes", "—")
        self.kpi_ultima_sync = self._build_kpi_card("Última sincronización", "No disponible")
        self.kpi_saldo_restante = self._build_kpi_card("Saldo restante", "No calculado")

        kpi_grid.addWidget(self.kpi_solicitudes_hoy, 0, 0)
        kpi_grid.addWidget(self.kpi_pendientes, 0, 1)
        kpi_grid.addWidget(self.kpi_ultima_sync, 1, 0)
        kpi_grid.addWidget(self.kpi_saldo_restante, 1, 1)
        layout.addLayout(kpi_grid)

        acciones_card = CardWidget("Acciones rápidas")
        acciones_layout = QHBoxLayout()
        acciones_layout.setSpacing(16)

        self.nueva_solicitud_button = PrimaryButton("Nueva solicitud")
        self.nueva_solicitud_button.clicked.connect(self.nueva_solicitud.emit)
        acciones_layout.addWidget(self.nueva_solicitud_button)

        self.ver_pendientes_button = SecondaryButton("Ver pendientes")
        self.ver_pendientes_button.clicked.connect(self.ver_pendientes.emit)
        acciones_layout.addWidget(self.ver_pendientes_button)

        self.sincronizar_ahora_button = SecondaryButton("Sincronizar ahora")
        self.sincronizar_ahora_button.clicked.connect(self.sincronizar_ahora.emit)
        acciones_layout.addWidget(self.sincronizar_ahora_button)

        acciones_layout.addStretch(1)
        acciones_card.layout().addLayout(acciones_layout)
        layout.addWidget(acciones_card)
        layout.addStretch(1)

    def _build_kpi_card(self, titulo: str, valor: str) -> CardWidget:
        card = CardWidget(titulo)
        label_valor = QLabel(valor)
        label_valor.setProperty("role", "title")
        card.layout().addWidget(label_valor)
        card.value_label = label_valor
        return card
