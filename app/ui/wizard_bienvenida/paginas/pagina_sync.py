from __future__ import annotations

from PySide6.QtWidgets import QPushButton

from app.ui.wizard_bienvenida.paginas.pagina_base import PaginaTexto
from presentacion.i18n import I18nManager


class PaginaSync(PaginaTexto):
    def __init__(self, i18n: I18nManager, on_ver_guia) -> None:
        self._boton_ver_guia = QPushButton()
        super().__init__(i18n, "wizard_paso_3", "wizard_sync_texto")
        self._i18n = i18n
        self._boton_ver_guia.clicked.connect(on_ver_guia)
        self.layout().addWidget(self._boton_ver_guia)
        self.actualizar_textos()

    def actualizar_textos(self) -> None:
        super().actualizar_textos()
        if hasattr(self, "_boton_ver_guia") and self._boton_ver_guia is not None:
            self._boton_ver_guia.setText(self._i18n.t("wizard_boton_ver_guia_sync"))
