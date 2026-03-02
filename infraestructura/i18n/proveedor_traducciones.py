from __future__ import annotations

import json
import logging
from pathlib import Path

from aplicacion.puertos.proveedor_i18n import IProveedorI18N

logger = logging.getLogger(__name__)


class ProveedorTraducciones(IProveedorI18N):
    def __init__(self, idioma_inicial: str = "es") -> None:
        self._catalogos = _cargar_catalogos()
        self._idioma_base = "es"
        self._idioma_actual = self._resolver_idioma(idioma_inicial)

    @property
    def idioma_actual(self) -> str:
        return self._idioma_actual

    @property
    def catalogos(self) -> dict[str, dict[str, str]]:
        return self._catalogos

    def idiomas_disponibles(self) -> tuple[str, ...]:
        return tuple(self._catalogos.keys())

    def cambiar_idioma(self, idioma: str) -> str:
        nuevo_idioma = self._resolver_idioma(idioma)
        self._idioma_actual = nuevo_idioma
        logger.info("i18n.idioma_cambiado", extra={"idioma": nuevo_idioma})
        return nuevo_idioma

    def traducir(self, clave: str, **kwargs: object) -> str:
        plantilla = self._resolver_plantilla(clave)
        if not kwargs:
            return plantilla
        try:
            return plantilla.format(**kwargs)
        except KeyError:
            logger.warning("i18n.parametros_faltantes", extra={"clave": clave, "idioma": self._idioma_actual})
            return plantilla

    def _resolver_idioma(self, idioma: str) -> str:
        if idioma in self._catalogos:
            return idioma
        logger.warning("i18n.idioma_no_soportado", extra={"idioma_solicitado": idioma, "idioma_fallback": self._idioma_base})
        return self._idioma_base

    def _resolver_plantilla(self, clave: str) -> str:
        catalogo_actual = self._catalogos.get(self._idioma_actual, {})
        if clave in catalogo_actual:
            return catalogo_actual[clave]
        catalogo_base = self._catalogos.get(self._idioma_base, {})
        if clave in catalogo_base:
            logger.info("i18n.fallback_idioma_base", extra={"clave": clave, "idioma": self._idioma_actual})
            return catalogo_base[clave]
        logger.warning("i18n.clave_inexistente", extra={"clave": clave, "idioma": self._idioma_actual})
        return f"[i18n:{clave}]"


def _cargar_catalogos() -> dict[str, dict[str, str]]:
    base_dir = Path(__file__).resolve().parent
    rutas = {"es": base_dir / "catalogo_es.json", "en": base_dir / "catalogo_en.json"}
    return {idioma: _cargar_catalogo(ruta) for idioma, ruta in rutas.items()}


def _cargar_catalogo(ruta: Path) -> dict[str, str]:
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    return {str(clave): str(valor) for clave, valor in contenido.items()}
