from __future__ import annotations

from infraestructura.i18n.proveedor_traducciones import ProveedorTraducciones
from presentacion.i18n.gestor_i18n import GestorI18N


class I18nManager(GestorI18N):
    def __init__(self, idioma: str = "es") -> None:
        super().__init__(ProveedorTraducciones(idioma))


def _crear_catalogo() -> dict[str, dict[str, str]]:
    return ProveedorTraducciones("es").catalogos


CATALOGO = _crear_catalogo()


def crear_gestor_i18n(idioma: str = "es") -> GestorI18N:
    return I18nManager(idioma)


__all__ = ["CATALOGO", "GestorI18N", "I18nManager", "crear_gestor_i18n"]
