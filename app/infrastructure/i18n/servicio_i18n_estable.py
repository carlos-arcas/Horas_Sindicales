from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Callable

from aplicacion.puertos.proveedor_i18n import ProveedorI18N

LOGGER = logging.getLogger(__name__)
LEGACY_KEY_PATTERN = re.compile(r".+\.py:\d+:.+")


class _MapaSeguro(dict[str, object]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class ServicioI18nEstable(ProveedorI18N):
    def __init__(
        self,
        catalogos: dict[str, dict[str, str]],
        *,
        idioma_inicial: str = "es",
        mapa_legacy: dict[str, str] | None = None,
    ) -> None:
        self._catalogos = catalogos
        self._idioma = idioma_inicial if idioma_inicial in catalogos else "es"
        self._mapa_legacy = mapa_legacy or {}
        self._callbacks: list[Callable[[str], None]] = []

    @property
    def idioma(self) -> str:
        return self._idioma

    def registrar_cambio_idioma(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    def set_idioma(self, idioma: str) -> None:
        nuevo_idioma = idioma if idioma in self._catalogos else "es"
        if nuevo_idioma == self._idioma:
            return
        self._idioma = nuevo_idioma
        for callback in tuple(self._callbacks):
            callback(nuevo_idioma)

    def t(self, key: str, fallback: str | None = None, **params: object) -> str:
        if LEGACY_KEY_PATTERN.fullmatch(key):
            return self._resolver_legacy(key, params)

        plantilla = self._catalogo_actual().get(key)
        if plantilla is None:
            self._log_missing("MISSING", key)
            if fallback is not None:
                return self._formatear(fallback, params)
            return f"[MISSING:{key}]"
        return self._formatear(plantilla, params)

    def _resolver_legacy(self, legacy_key: str, params: dict[str, object]) -> str:
        nueva_key = self._mapa_legacy.get(legacy_key)
        if nueva_key is None:
            self._log_missing("MISSING_LEGACY", legacy_key)
            return f"[MISSING_LEGACY:{legacy_key}]"
        return self.t(nueva_key, **params)

    def _catalogo_actual(self) -> dict[str, str]:
        return self._catalogos.get(self._idioma, self._catalogos.get("es", {}))

    def _formatear(self, plantilla: str, params: dict[str, object]) -> str:
        if not params:
            return plantilla
        saneados = _MapaSeguro({k: _sanear_valor(v) for k, v in params.items()})
        return plantilla.format_map(saneados)

    def _log_missing(self, tipo: str, key: str) -> None:
        caller = self._resolver_caller()
        LOGGER.warning(
            "Clave de i18n faltante",
            extra={
                "extra": {
                    "tipo": tipo,
                    "key": key,
                    "idioma": self._idioma,
                    "caller": caller,
                }
            },
        )

    @staticmethod
    def _resolver_caller() -> str:
        frame = _obtener_frame(4)
        if frame is None:
            return "desconocido"
        filename = _normalizar_filename(frame.f_code.co_filename)
        return f"{filename}:{frame.f_code.co_name}:{frame.f_lineno}"


def _obtener_frame(profundidad: int) -> object | None:
    if not hasattr(sys, "_getframe"):
        return None
    try:
        return sys._getframe(profundidad)
    except ValueError:
        return None


def _normalizar_filename(filename: object) -> str:
    if isinstance(filename, str):
        return Path(filename).name
    if isinstance(filename, os.PathLike):
        return Path(filename).name
    return str(filename)


class CargadorI18nDesdeArchivos:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def cargar_catalogos(self) -> dict[str, dict[str, str]]:
        catalogos: dict[str, dict[str, str]] = {}
        for ruta in sorted(self._base_dir.glob("*.json")):
            if ruta.name.startswith("_"):
                continue
            catalogos[ruta.stem] = json.loads(ruta.read_text(encoding="utf-8"))
        return catalogos

    def cargar_mapa_legacy(self) -> dict[str, str]:
        ruta = self._base_dir / "_legacy_map.json"
        if not ruta.exists():
            return {}
        return json.loads(ruta.read_text(encoding="utf-8"))


def _sanear_valor(valor: object) -> object:
    return valor if isinstance(valor, (int, float)) else str(valor)
