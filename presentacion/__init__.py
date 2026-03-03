"""API pública de :mod:`presentacion` con imports diferidos para evitar side-effects Qt."""

from __future__ import annotations

from typing import Any

__all__ = [
    "CATALOGO",
    "GestorI18N",
    "I18nManager",
    "crear_gestor_i18n",
    "DependenciasArranque",
    "OrquestadorArranqueUI",
]


def __getattr__(name: str) -> Any:
    if name in {"CATALOGO", "GestorI18N", "I18nManager", "crear_gestor_i18n"}:
        from presentacion import i18n as _i18n

        return getattr(_i18n, name)
    if name in {"DependenciasArranque", "OrquestadorArranqueUI"}:
        from presentacion import orquestador_arranque as _orquestador

        return getattr(_orquestador, name)
    raise AttributeError(f"module 'presentacion' has no attribute {name!r}")
