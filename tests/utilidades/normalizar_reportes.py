from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_PATRON_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
_PATRON_AUDIT_ID = re.compile(r"\bAUD-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")
_PATRON_FECHA_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b")
_PATRON_RUTA_UNIX = re.compile(r"(?<!\w)/(?:[\w.-]+/)*[\w.-]+")
_PATRON_RUTA_WINDOWS = re.compile(r"\b[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]+")
_CLAVES_RUTA = {"root", "base_dir", "auditoria_md", "auditoria_json", "manifest_json", "status_txt"}


def _normalizar_texto(texto: str) -> str:
    normalizado = _PATRON_UUID.sub("<ID>", texto)
    normalizado = _PATRON_AUDIT_ID.sub("<ID>", normalizado)
    normalizado = _PATRON_FECHA_ISO.sub("<FECHA>", normalizado)
    normalizado = _PATRON_RUTA_WINDOWS.sub("<RUTA>", normalizado)
    normalizado = _PATRON_RUTA_UNIX.sub("<RUTA>", normalizado)
    return normalizado


def _ordenar_checks_en_lista(items: list[Any]) -> list[Any]:
    if not items:
        return items
    if all(isinstance(item, dict) and "id_check" in item for item in items):
        return sorted(items, key=lambda item: str(item["id_check"]))
    return items


def normalizar_markdown(texto: str) -> str:
    texto_normalizado = _normalizar_texto(texto)
    lineas = [linea.rstrip() for linea in texto_normalizado.splitlines()]
    return "\n".join(lineas).strip() + "\n"


def normalizar_json(data: dict) -> dict:
    def _normalizar_valor(valor: Any, *, clave: str | None = None) -> Any:
        if isinstance(valor, dict):
            return {k: _normalizar_valor(valor[k], clave=k) for k in sorted(valor)}
        if isinstance(valor, list):
            normalizada = [_normalizar_valor(item, clave=clave) for item in valor]
            return _ordenar_checks_en_lista(normalizada)
        if isinstance(valor, str):
            if clave == "sha256":
                return "<HASH>"
            if clave in _CLAVES_RUTA:
                return "<RUTA>"
            return _normalizar_texto(valor)
        return valor

    resultado = _normalizar_valor(data)
    return resultado if isinstance(resultado, dict) else {"valor": resultado}


def guardar_golden(path: Path, contenido: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contenido, encoding="utf-8")
