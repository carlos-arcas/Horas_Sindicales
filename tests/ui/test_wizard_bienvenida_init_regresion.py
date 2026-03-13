from __future__ import annotations

from pathlib import Path

import pytest

from tests.ui.conftest import require_qt

QApplication = require_qt()

from aplicacion.casos_de_uso.documentos import ObtenerRutaGuiaSync
from presentacion.i18n import I18nManager
from presentacion.wizard_bienvenida import WizardBienvenida


class ProveedorDocumentosFalso:
    def __init__(self, ruta: Path) -> None:
        self._ruta = ruta

    def obtener_ruta_guia_sync(self) -> str:
        return str(self._ruta)


def test_wizard_bienvenida_no_lanza_attribute_error_en_init(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    ruta_guia = tmp_path / "guia_sync.md"
    ruta_guia.write_text("# Guia\n", encoding="utf-8")

    try:
        wizard = WizardBienvenida(
            I18nManager("es"),
            ObtenerRutaGuiaSync(ProveedorDocumentosFalso(ruta_guia)),
            idioma_inicial="es",
            iniciar_maximizada_inicial=False,
        )
    except AttributeError as exc:  # pragma: no cover - test de regresión
        pytest.fail(f"WizardBienvenida lanzó AttributeError durante __init__: {exc}")

    assert wizard is not None
    assert app is not None
