from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.domain.time_utils import minutes_to_hhmm


class SaldosCard(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setProperty("card", True)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        title_label = QLabel("Saldos detallados")
        title_label.setProperty("role", "cardTitle")
        card_layout.addWidget(title_label)

        separator = QFrame()
        separator.setProperty("role", "cardSeparator")
        separator.setFixedHeight(1)
        card_layout.addWidget(separator)

        self.saldos_details_button = QPushButton("Ver detalles")
        self.saldos_details_button.setProperty("variant", "secondary")
        card_layout.addWidget(self.saldos_details_button)

        self.saldos_details_content = QWidget()
        saldos_details_layout = QVBoxLayout(self.saldos_details_content)
        saldos_details_layout.setContentsMargins(0, 0, 0, 0)
        saldos_details_layout.setSpacing(8)

        saldos_grid = QGridLayout()
        saldos_grid.setHorizontalSpacing(10)
        saldos_grid.setVerticalSpacing(8)

        saldos_grid.addWidget(QLabel(""), 0, 0)
        consumidas_header = QLabel("Consumidas")
        consumidas_header.setProperty("role", "secondary")
        saldos_grid.addWidget(consumidas_header, 0, 1)
        restantes_header = QLabel("Restantes")
        restantes_header.setProperty("role", "secondary")
        saldos_grid.addWidget(restantes_header, 0, 2)

        self.saldo_periodo_consumidas = self._build_saldo_field()
        self.saldo_periodo_restantes = self._build_saldo_field()
        self.saldo_anual_consumidas = self._build_saldo_field()
        self.saldo_anual_restantes = self._build_saldo_field()
        self.saldo_grupo_consumidas = self._build_saldo_field()
        self.saldo_grupo_restantes = self._build_saldo_field()

        self.saldo_periodo_label = QLabel("Mensual")
        saldos_grid.addWidget(self.saldo_periodo_label, 1, 0)
        saldos_grid.addWidget(self.saldo_periodo_consumidas, 1, 1)
        saldos_grid.addWidget(self.saldo_periodo_restantes, 1, 2)

        saldos_grid.addWidget(QLabel("Anual delegada"), 2, 0)
        saldos_grid.addWidget(self.saldo_anual_consumidas, 2, 1)
        saldos_grid.addWidget(self.saldo_anual_restantes, 2, 2)

        saldos_grid.addWidget(QLabel("Anual grupo"), 3, 0)
        saldos_grid.addWidget(self.saldo_grupo_consumidas, 3, 1)
        saldos_grid.addWidget(self.saldo_grupo_restantes, 3, 2)
        saldos_details_layout.addLayout(saldos_grid)

        self.exceso_badge = QLabel("")
        self.exceso_badge.setProperty("role", "badge")
        self.exceso_badge.setVisible(False)
        exceso_row = QHBoxLayout()
        exceso_row.addStretch(1)
        exceso_row.addWidget(self.exceso_badge)
        saldos_details_layout.addLayout(exceso_row)

        bolsas_separator = QFrame()
        bolsas_separator.setProperty("role", "subtleSeparator")
        bolsas_separator.setFixedHeight(1)
        saldos_details_layout.addWidget(bolsas_separator)

        bolsas_grid = QGridLayout()
        bolsas_grid.setHorizontalSpacing(8)
        bolsas_grid.setVerticalSpacing(6)
        bolsas_grid.addWidget(QLabel("Bolsa mensual delegada"), 0, 0)
        self.bolsa_mensual_label = QLabel("00:00")
        self.bolsa_mensual_label.setProperty("role", "secondary")
        bolsas_grid.addWidget(self.bolsa_mensual_label, 0, 1)
        bolsas_grid.addWidget(QLabel("Bolsa anual delegada"), 1, 0)
        self.bolsa_delegada_label = QLabel("00:00")
        self.bolsa_delegada_label.setProperty("role", "secondary")
        bolsas_grid.addWidget(self.bolsa_delegada_label, 1, 1)
        bolsas_grid.addWidget(QLabel("Bolsa anual grupo"), 2, 0)
        self.bolsa_grupo_label = QLabel("00:00")
        self.bolsa_grupo_label.setProperty("role", "secondary")
        bolsas_grid.addWidget(self.bolsa_grupo_label, 2, 1)
        saldos_details_layout.addLayout(bolsas_grid)

        card_layout.addWidget(self.saldos_details_content)
        self._configure_disclosure(self.saldos_details_button, self.saldos_details_content)

    def _configure_disclosure(
        self,
        button: QPushButton,
        content: QWidget,
        *,
        collapsed_text: str = "Ver detalles",
        expanded_text: str = "Ocultar detalles",
    ) -> None:
        content.setVisible(False)
        button.setCheckable(True)

        def _toggle(checked: bool) -> None:
            content.setVisible(checked)
            button.setText(expanded_text if checked else collapsed_text)

        button.toggled.connect(_toggle)
        _toggle(False)

    def _build_saldo_field(self) -> QLineEdit:
        field = QLineEdit("00:00")
        field.setReadOnly(True)
        field.setProperty("role", "saldoField")
        field.setAlignment(Qt.AlignCenter)
        field.setMinimumWidth(90)
        return field

    def update_periodo_label(self, text: str = "Mensual") -> None:
        self.saldo_periodo_label.setText(text)

    def update_saldos(self, resumen, pendientes_periodo: int = 0, pendientes_ano: int = 0) -> None:
        if resumen is None:
            self._set_saldo_line(self.saldo_periodo_consumidas, self.saldo_periodo_restantes, 0, 0)
            self._set_saldo_line(self.saldo_anual_consumidas, self.saldo_anual_restantes, 0, 0)
            self._set_saldo_line(self.saldo_grupo_consumidas, self.saldo_grupo_restantes, 0, 0)
            self.update_bolsa(0, 0, 0)
            self.set_exceso(None)
            return

        consumidas_periodo = resumen.individual.consumidas_periodo_min + pendientes_periodo
        bolsa_periodo = resumen.individual.bolsa_periodo_min
        restantes_periodo = bolsa_periodo - consumidas_periodo

        consumidas_anual = resumen.individual.consumidas_anual_min + pendientes_ano
        bolsa_anual = resumen.individual.bolsa_anual_min
        restantes_anual = bolsa_anual - consumidas_anual

        consumidas_grupo = resumen.grupo_anual.consumidas_anual_min
        bolsa_grupo = resumen.grupo_anual.bolsa_anual_grupo_min
        restantes_grupo = bolsa_grupo - consumidas_grupo

        self._set_saldo_line(
            self.saldo_periodo_consumidas,
            self.saldo_periodo_restantes,
            consumidas_periodo,
            restantes_periodo,
        )
        self._set_saldo_line(
            self.saldo_anual_consumidas,
            self.saldo_anual_restantes,
            consumidas_anual,
            restantes_anual,
        )
        self._set_saldo_line(
            self.saldo_grupo_consumidas,
            self.saldo_grupo_restantes,
            consumidas_grupo,
            restantes_grupo,
        )
        self.update_bolsa(bolsa_periodo, bolsa_anual, bolsa_grupo)

        exceso = min(restantes_periodo, restantes_anual, restantes_grupo)
        self.set_exceso(exceso if exceso < 0 else None)

    def update_bolsa(self, bolsa_mensual: int, bolsa_delegada: int, bolsa_grupo: int) -> None:
        self.bolsa_mensual_label.setText(self._format_minutes(bolsa_mensual))
        self.bolsa_delegada_label.setText(self._format_minutes(bolsa_delegada))
        self.bolsa_grupo_label.setText(self._format_minutes(bolsa_grupo))

    def set_exceso(self, exceso_min: int | None) -> None:
        if exceso_min is None or exceso_min >= 0:
            self.exceso_badge.setVisible(False)
            return
        self.exceso_badge.setText(f"Exceso {self._format_minutes(abs(exceso_min))}")
        self.exceso_badge.setVisible(True)

    def saldo_periodo_restante_text(self) -> str:
        return self.saldo_periodo_restantes.text()

    def _set_saldo_line(
        self,
        consumidas_field: QLineEdit,
        restantes_field: QLineEdit,
        consumidas: int,
        restantes: int,
    ) -> None:
        consumidas_field.setText(self._format_minutes(consumidas))
        restantes_text, warning = self._format_restantes(restantes)
        restantes_field.setText(restantes_text)
        self._set_warning_state(restantes_field, warning)

    def _set_warning_state(self, field: QLineEdit, warning: bool) -> None:
        field.setProperty("status", "warning" if warning else None)
        field.style().unpolish(field)
        field.style().polish(field)
        field.update()

    def _format_restantes(self, minutos: int) -> tuple[str, bool]:
        if minutos < 0:
            return f"Exceso {minutes_to_hhmm(abs(minutos))}", True
        return self._format_minutes(minutos), False

    def _format_minutes(self, minutes: int) -> str:
        return minutes_to_hhmm(minutes)
