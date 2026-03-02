from __future__ import annotations

from PySide6.QtWidgets import QPushButton

from app.ui.wizard_bienvenida.paginas.pagina_base import PaginaTexto
from presentacion.i18n import I18nManager


class PaginaSync(PaginaTexto):
    def __init__(self, i18n: I18nManager, on_ver_guia) -> None:
        self._on_ver_guia = on_ver_guia
        self._boton_ver_guia = QPushButton()
        self._boton_ver_guia.clicked.connect(self._abrir_guia_sync)
        super().__init__(
            i18n,
            "wizard_paso_3",
            "wizard_sync_texto",
        )
        self.inicializar_textos()

    def _construir_ui(self) -> None:
        super()._construir_ui()
        self.layout().addWidget(self._boton_ver_guia)

    def _abrir_guia_sync(self) -> None:
        self._on_ver_guia()

    def actualizar_textos(self) -> None:
        super().actualizar_textos()
        self._boton_ver_guia.setText(self._i18n.t("wizard_boton_ver_guia_sync"))
