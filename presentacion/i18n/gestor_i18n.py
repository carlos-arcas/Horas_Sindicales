from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from aplicacion.puertos.proveedor_i18n import IProveedorI18N

logger = logging.getLogger(__name__)
_LEGACY_KEY_PATTERN = re.compile(r"(?P<ruta>.+\.py):\d+:(?P<texto>.+)")


def build_legacy_alias(path: str, text: str) -> str:
    """Genera un alias estable para claves legacy (ruta+texto, sin línea)."""

    payload = f"{path.strip()}::{text.strip()}".encode("utf-8")
    return f"legacy_{hashlib.sha1(payload).hexdigest()[:12]}"


def _cargar_aliases_legacy() -> dict[str, dict[str, str]]:
    ruta = Path(__file__).resolve().parents[2] / ".config" / "ui_strings_aliases.json"
    if not ruta.exists():
        return {}
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    aliases = contenido.get("alias_legacy_sin_linea", {})
    return aliases if isinstance(aliases, dict) else {}


class GestorI18N(QObject):
    idioma_cambiado = Signal(str)

    def __init__(
        self,
        proveedor: IProveedorI18N,
        *,
        aliases_legacy: dict[str, dict[str, str]] | None = None,
    ) -> None:
        super().__init__()
        self._proveedor = proveedor
        self._aliases_legacy = aliases_legacy if aliases_legacy is not None else _cargar_aliases_legacy()

    @property
    def idioma(self) -> str:
        return self._proveedor.idioma_actual

    def set_idioma(self, idioma: str) -> None:
        idioma_anterior = self.idioma
        idioma_resuelto = self._proveedor.cambiar_idioma(idioma)
        if idioma_resuelto != idioma_anterior:
            self.idioma_cambiado.emit(idioma_resuelto)

    def tr(self, clave: str, **kwargs: object) -> str:
        return self._proveedor.traducir(clave, **kwargs)

    def t(self, key: str, *, fallback: str | None = None, **vars: object) -> str:
        traducido = self.tr(key, **vars)
        if traducido != f"[i18n:{key}]":
            return traducido
        if fallback is not None:
            logger.warning("i18n_missing_key", extra={"key": key, "idioma": self.idioma})
            return fallback.format(**vars) if vars else fallback
        legacy = self._resolver_alias_legacy(key)
        if legacy is not None:
            return self.tr(legacy, **vars)
        logger.error("i18n_missing_key_unresolved", extra={"key": key, "idioma": self.idioma})
        return f"[i18n:{key}]"

    def _resolver_alias_legacy(self, key: str) -> str | None:
        match = _LEGACY_KEY_PATTERN.fullmatch(key)
        if match is None:
            return None
        path = match.group("ruta").strip()
        text = match.group("texto").strip()
        alias = build_legacy_alias(path, text)
        entrada = self._aliases_legacy.get(alias)
        if not isinstance(entrada, dict):
            return None
        if entrada.get("ruta") != path or entrada.get("texto") != text:
            return None
        semantic_key = entrada.get("key_semantica")
        return semantic_key if isinstance(semantic_key, str) else None
