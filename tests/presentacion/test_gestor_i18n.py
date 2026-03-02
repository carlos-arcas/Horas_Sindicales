from __future__ import annotations

from infraestructura.i18n.proveedor_traducciones import ProveedorTraducciones
from presentacion.i18n.gestor_i18n import GestorI18N


def test_cambio_dinamico_de_idioma_en_runtime() -> None:
    gestor = GestorI18N(ProveedorTraducciones("es"))

    gestor.set_idioma("en")

    assert gestor.tr("splash_window.titulo") == "Starting Horas Sindicales…"
