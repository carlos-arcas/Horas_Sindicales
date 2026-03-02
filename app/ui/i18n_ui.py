from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from app.infrastructure.i18n import CargadorI18nDesdeArchivos, ServicioI18nEstable

LOGGER = logging.getLogger(__name__)
_FALLBACK_TEXTO = "(texto no disponible)"


class RegistroIdiomaUI:
    def __init__(self, servicio: ServicioI18nEstable) -> None:
        self._servicio = servicio
        self._callbacks: list[Callable[[], None]] = []

    @property
    def servicio(self) -> ServicioI18nEstable:
        return self._servicio

    def configurar_servicio(self, servicio: ServicioI18nEstable) -> None:
        self._servicio = servicio

    def registrar(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def cambiar_idioma(self, idioma: str) -> None:
        self._servicio.set_idioma(idioma)
        for callback in tuple(self._callbacks):
            callback()



def _build_default_service() -> ServicioI18nEstable:
    base_dir = Path("configuracion") / "i18n"
    cargador = CargadorI18nDesdeArchivos(base_dir)
    return ServicioI18nEstable(cargador.cargar_catalogos(), mapa_legacy=cargador.cargar_mapa_legacy())


_REGISTRO_IDIOMA = RegistroIdiomaUI(_build_default_service())


def configurar_ui_i18n(servicio: ServicioI18nEstable) -> None:
    _REGISTRO_IDIOMA.configurar_servicio(servicio)


def registrar_refresco_idioma(callback: Callable[[], None]) -> None:
    _REGISTRO_IDIOMA.registrar(callback)


def cambiar_idioma_ui(idioma: str) -> None:
    _REGISTRO_IDIOMA.cambiar_idioma(idioma)


def idioma_actual_ui() -> str:
    return _REGISTRO_IDIOMA.servicio.idioma


def ui_text(key: str, **params: object) -> str:
    return _resolver_texto(key, **params)


def ui_text_legacy(legacy: str, **params: object) -> str:
    return _resolver_texto(legacy, **params)


def _resolver_texto(key: str, **params: object) -> str:
    traducido = _REGISTRO_IDIOMA.servicio.t(key, **params)
    if traducido.startswith("[MISSING"):
        LOGGER.warning("i18n_missing_ui_key", extra={"extra": {"key": key, "idioma": idioma_actual_ui()}})
        return _FALLBACK_TEXTO
    return traducido
