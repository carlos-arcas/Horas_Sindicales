from __future__ import annotations

from pathlib import Path

import pytest

from tests.ui.conftest import require_qt

QApplication = require_qt()

from aplicacion.casos_de_uso.documentos import ObtenerRutaGuiaSync
from app.ui.wizard_bienvenida.wizard import WizardBienvenida
from presentacion.i18n import I18nManager


class ProveedorDocumentosStub:
    def __init__(self, ruta_guia: Path) -> None:
        self._ruta_guia = ruta_guia

    def obtener_ruta_guia_sync(self) -> str:
        return self._ruta_guia.as_posix()


def test_wizard_bienvenida_no_lanza_attribute_error_en_init(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    ruta_guia = tmp_path / "guia_sync.md"
    ruta_guia.write_text("# Guía de sincronización\n", encoding="utf-8")

    try:
        wizard = WizardBienvenida(
            I18nManager("es"),
            ObtenerRutaGuiaSync(ProveedorDocumentosStub(ruta_guia)),
            idioma_inicial="es",
            pantalla_completa_inicial=False,
        )
    except AttributeError as exc:  # pragma: no cover - regresión
        pytest.fail(f"WizardBienvenida lanzó AttributeError durante __init__: {exc}")

    assert wizard is not None
    assert app is not None
