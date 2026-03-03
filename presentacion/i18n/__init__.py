from __future__ import annotations

from typing import Any

from presentacion.i18n.catalogo import CATALOGO

__all__ = ["CATALOGO", "GestorI18N", "I18nManager", "crear_gestor_i18n"]


def __getattr__(name: str) -> Any:
    if name in {"GestorI18N", "I18nManager", "crear_gestor_i18n"}:
        from presentacion.i18n import gestor_i18n as _gestor
        from infraestructura.i18n.proveedor_traducciones import ProveedorTraducciones

        if name == "GestorI18N":
            return _gestor.GestorI18N

        class I18nManager(_gestor.GestorI18N):
            def __init__(self, idioma: str = "es") -> None:
                super().__init__(ProveedorTraducciones(idioma))

        if name == "I18nManager":
            return I18nManager

        def crear_gestor_i18n(idioma: str = "es") -> _gestor.GestorI18N:
            return I18nManager(idioma)

        return crear_gestor_i18n
    raise AttributeError(f"module 'presentacion.i18n' has no attribute {name!r}")
