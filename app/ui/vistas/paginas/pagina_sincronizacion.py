from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.components.card_widget import CardWidget
from app.ui.components.primary_button import PrimaryButton
from app.ui.components.secondary_button import SecondaryButton


class PaginaSincronizacion(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Sincronización")
        title.setProperty("role", "sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Supervisa el estado de integración con Google Sheets y ejecuta sincronizaciones de forma segura."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "secondary")
        layout.addWidget(subtitle)

        acciones = QHBoxLayout()
        self.sync_now_button = PrimaryButton("Sincronizar ahora")
        acciones.addWidget(self.sync_now_button)
        self.sync_history_button = SecondaryButton("Ver historial")
        acciones.addWidget(self.sync_history_button)
        self.sync_diagnostics_button = SecondaryButton("Diagnóstico")
        acciones.addWidget(self.sync_diagnostics_button)
        acciones.addStretch(1)
        layout.addLayout(acciones)

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(12)
        kpi_grid.setVerticalSpacing(12)

        self.kpi_creadas = self._build_kpi_card("Creadas", "0", "#1F7A3A")
        self.kpi_actualizadas = self._build_kpi_card("Actualizadas", "0", "#1F7A3A")
        self.kpi_conflictos = self._build_kpi_card("Conflictos", "0", "#C27A00")
        self.kpi_errores = self._build_kpi_card("Errores", "0", "#B00020")

        kpi_grid.addWidget(self.kpi_creadas, 0, 0)
        kpi_grid.addWidget(self.kpi_actualizadas, 0, 1)
        kpi_grid.addWidget(self.kpi_conflictos, 1, 0)
        kpi_grid.addWidget(self.kpi_errores, 1, 1)
        layout.addLayout(kpi_grid)
        layout.addStretch(1)

    def _build_kpi_card(self, titulo: str, valor: str, color: str) -> CardWidget:
        card = CardWidget(titulo)
        card.setProperty("card", True)
        label_valor = QLabel(valor)
        label_valor.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {color};")
        card.layout().addWidget(label_valor)
        return card
