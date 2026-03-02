from __future__ import annotations

import logging
from typing import Callable

from aplicacion.puertos.proveedor_i18n import ProveedorI18N

LOGGER = logging.getLogger(__name__)
_FALLBACK_TEXTO = "(texto no disponible)"


class _ProveedorI18NNull:
    def t(self, key: str, fallback: str | None = None, **vars: object) -> str:
        return fallback if fallback is not None else f"[MISSING:{key}]"


class RegistroIdiomaInterfaz:
    def __init__(self, servicio: ProveedorI18N) -> None:
        self._servicio = servicio
        self._callbacks: list[Callable[[], None]] = []

    @property
    def servicio(self) -> ProveedorI18N:
        return self._servicio

    def configurar_servicio(self, servicio: ProveedorI18N) -> None:
        self._servicio = servicio

    def registrar(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def cambiar_idioma(self, idioma: str) -> None:
        servicio = self._servicio
        set_idioma = getattr(servicio, "set_idioma", None)
        if callable(set_idioma):
            set_idioma(idioma)
        for callback in tuple(self._callbacks):
            callback()


_REGISTRO_IDIOMA = RegistroIdiomaInterfaz(_ProveedorI18NNull())


def configurar_i18n_interfaz(servicio: ProveedorI18N) -> None:
    _REGISTRO_IDIOMA.configurar_servicio(servicio)


def registrar_refresco_idioma(callback: Callable[[], None]) -> None:
    _REGISTRO_IDIOMA.registrar(callback)


def cambiar_idioma_interfaz(idioma: str) -> None:
    _REGISTRO_IDIOMA.cambiar_idioma(idioma)


def idioma_actual_interfaz() -> str:
    servicio = _REGISTRO_IDIOMA.servicio
    return getattr(servicio, "idioma", "es")


def texto_interfaz(key: str, **params: object) -> str:
    return _resolver_texto(key, **params)


def texto_interfaz_heredado(legacy: str, **params: object) -> str:
    return _resolver_texto(legacy, **params)


def _resolver_texto(key: str, **params: object) -> str:
    traducido = _REGISTRO_IDIOMA.servicio.t(key, **params)
    if traducido.startswith("[MISSING"):
        LOGGER.warning("i18n_missing_ui_key", extra={"extra": {"key": key, "idioma": idioma_actual_interfaz()}})
        return _FALLBACK_TEXTO
    return traducido
