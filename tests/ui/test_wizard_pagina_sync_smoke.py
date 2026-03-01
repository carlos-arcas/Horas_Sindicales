from __future__ import annotations

from tests.ui.conftest import require_qt

QApplication = require_qt()

from app.ui.wizard_bienvenida.paginas.pagina_sync import PaginaSync
from presentacion.i18n import I18nManager


def test_pagina_sync_construye_sin_crash() -> None:
    app = QApplication.instance() or QApplication([])

    pagina = PaginaSync(I18nManager("es"), lambda: None)

    assert pagina is not None
    assert hasattr(pagina, "_boton_ver_guia")
    assert pagina._boton_ver_guia.text()
    assert app is not None
