from __future__ import annotations

import pytest

from tests.ui.conftest import require_qt

QApplication = require_qt()

from app.ui.wizard_bienvenida.paginas.pagina_sync import PaginaSync
from presentacion.i18n import I18nManager


def test_pagina_sync_no_falla_por_orden_de_inicializacion() -> None:
    app = QApplication.instance() or QApplication([])

    try:
        pagina = PaginaSync(I18nManager("es"), lambda: None)
    except AttributeError as exc:  # pragma: no cover - defensivo ante regresión
        pytest.fail(f"PaginaSync lanzó AttributeError durante __init__: {exc}")

    assert pagina._boton_ver_guia.text() == pagina._i18n.t("wizard_boton_ver_guia_sync")
    assert app is not None
