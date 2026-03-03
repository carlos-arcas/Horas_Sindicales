from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.ui

try:
    from PySide6.QtWidgets import QApplication, QPushButton
except Exception as exc:  # pragma: no cover
    pytest.skip(f"Qt no disponible: {exc}", allow_module_level=True)

from aplicacion.casos_de_uso.documentos import ObtenerRutaGuiaSync
from presentacion.i18n import I18nManager
from presentacion.wizard_bienvenida import WizardBienvenida


class StubProveedorDocumentos:
    def __init__(self, ruta: Path) -> None:
        self._ruta = ruta

    def obtener_ruta_guia_sync(self) -> str:
        return self._ruta.as_posix()


def test_wizard_instancia_y_navega_basico(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    guia = tmp_path / "guia.md"
    guia.write_text("# Guia sync\n", encoding="utf-8")
    wizard = WizardBienvenida(
        I18nManager("es"),
        ObtenerRutaGuiaSync(StubProveedorDocumentos(guia)),
        idioma_inicial="es",
        pantalla_completa_inicial=False,
    )

    assert wizard.findChildren(QPushButton)

    wizard._ir_siguiente()
    wizard._ir_siguiente()
    wizard._ir_atras()

    assert wizard._stack.currentIndex() == 1
    assert app is not None
