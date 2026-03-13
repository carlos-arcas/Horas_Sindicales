from __future__ import annotations

from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout, QWidget

from app.ui.components.saldos_card import SaldosCard
from app.ui.copy_catalog import copy_text
from app.ui.patterns import apply_modal_behavior, build_modal_actions


class SaldosDetalleDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(copy_text("ui.solicitudes.saldos"))
        self.resize(560, 460)
        layout = QVBoxLayout(self)

        saldos_card = SaldosCard(self)
        saldos_card.saldos_details_button.setChecked(True)
        saldos_card.saldos_details_button.setVisible(False)
        layout.addWidget(saldos_card, 1)

        if parent is not None and getattr(parent, "saldos_card", None) is not None:
            copiar_estado_saldos(parent.saldos_card, saldos_card)

        close_button = QPushButton(copy_text("ui.comun.cerrar"))
        close_button.setProperty("variant", "primary")
        close_button.clicked.connect(self.accept)
        layout.addLayout(build_modal_actions(close_button))
        apply_modal_behavior(self, primary_button=close_button)


def copiar_estado_saldos(origen: SaldosCard, destino: SaldosCard) -> None:
    destino.update_periodo_label(origen.saldo_periodo_label.text())
    for attr in (
        "saldo_periodo_consumidas",
        "saldo_periodo_restantes",
        "saldo_anual_consumidas",
        "saldo_anual_restantes",
        "saldo_grupo_consumidas",
        "saldo_grupo_restantes",
    ):
        getattr(destino, attr).setText(getattr(origen, attr).text())
    for attr in ("bolsa_mensual_label", "bolsa_delegada_label", "bolsa_grupo_label"):
        getattr(destino, attr).setText(getattr(origen, attr).text())
    destino.exceso_badge.setVisible(origen.exceso_badge.isVisible())
    destino.exceso_badge.setText(origen.exceso_badge.text())
