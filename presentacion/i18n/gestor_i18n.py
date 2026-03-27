from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Callable

from aplicacion.puertos.proveedor_i18n import IProveedorI18N

logger = logging.getLogger(__name__)
_LEGACY_KEY_PATTERN = re.compile(r"(?P<ruta>.+\.py):\d+:(?P<texto>.+)")


class _SignalLigera:
    def __init__(self) -> None:
        self._suscriptores: list[Callable[..., Any]] = []

    def connect(self, callback: Callable[..., Any]) -> None:
        self._suscriptores.append(callback)

    def emit(self, *args: object, **kwargs: object) -> None:
        for callback in tuple(self._suscriptores):
            callback(*args, **kwargs)


class _SignalDescriptorLigero:
    def __set_name__(self, owner: type[object], name: str) -> None:
        self._storage_name = f"_{name}_signal"

    def __get__(self, instance: object | None, owner: type[object]) -> _SignalLigera | _SignalDescriptorLigero:
        if instance is None:
            return self
        signal = getattr(instance, self._storage_name, None)
        if signal is None:
            signal = _SignalLigera()
            setattr(instance, self._storage_name, signal)
        return signal


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


def _qt_core_stub_cargado() -> bool:
    qt_core = sys.modules.get("PySide6.QtCore")
    if qt_core is not None:
        return True
    pyside6 = sys.modules.get("PySide6")
    return getattr(pyside6, "QtCore", None) is not None


def _qt_core_disponible() -> bool:
    if _qt_core_stub_cargado():
        return True
    try:
        return importlib.util.find_spec("PySide6.QtCore") is not None
    except (ImportError, ValueError):
        return _qt_core_stub_cargado()


class GestorI18N:
    """Gestor i18n importable en headless sin depender de Qt.

    Expone una señal ligera compatible con el contrato usado por la UI
    (`connect`/`emit`) sin importar PySide6 durante el import del módulo.
    """

    idioma_cambiado = _SignalDescriptorLigero()
    qt_disponible = _qt_core_disponible()

    def __init__(
        self,
        proveedor: IProveedorI18N,
        *,
        aliases_legacy: dict[str, dict[str, str]] | None = None,
    ) -> None:
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
