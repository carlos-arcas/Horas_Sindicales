from __future__ import annotations

from tests.ui.conftest import require_qt

QApplication = require_qt()

from PySide6.QtWidgets import QPushButton  # noqa: E402

from app.ui.wizard_bienvenida.paginas.pagina_base import PaginaBase  # noqa: E402
from presentacion.i18n import I18nManager  # noqa: E402


class PaginaPrueba(PaginaBase):
    def __init__(self, i18n: I18nManager) -> None:
        super().__init__(i18n, "wizard_paso_1", "wizard_bienvenida_texto")
        self._boton_tardio = QPushButton()
        self.inicializar_textos()

    def actualizar_textos(self) -> None:
        super().actualizar_textos()
        self._boton_tardio.setText("ok")


def test_pagina_base_no_invoca_metodo_virtual_en_init() -> None:
    app = QApplication.instance() or QApplication([])

    pagina = PaginaPrueba(I18nManager("es"))

    assert pagina._boton_tardio.text() == "ok"
    assert app is not None
