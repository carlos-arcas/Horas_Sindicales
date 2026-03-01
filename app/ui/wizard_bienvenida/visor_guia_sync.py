from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout, QWidget

from presentacion.i18n import I18nManager


class VisorGuiaSyncDialog(QDialog):
    def __init__(self, markdown: str, i18n: I18nManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(i18n.t("wizard_sync_dialog_titulo"))

        layout = QVBoxLayout(self)
        visor = QTextBrowser(self)
        visor.setPlainText(markdown)
        layout.addWidget(visor)

        botonera = QDialogButtonBox(QDialogButtonBox.Close)
        botonera.rejected.connect(self.reject)
        botonera.accepted.connect(self.accept)
        layout.addWidget(botonera)

        self.resize(760, 520)
