from __future__ import annotations

from typing import Any


def resolver_texto_i18n(
    *,
    i18n: Any,
    key: str,
    fallback: str,
    catalogo: dict[str, dict[str, str]] | None = None,
    **params: object,
) -> str:
    """Resuelve un texto UI con compatibilidad para i18n legacy/headless."""

    if hasattr(i18n, "t"):
        try:
            traducido = i18n.t(key, fallback=fallback, **params)
        except TypeError:
            traducido = i18n.t(key, **params)
        if isinstance(traducido, str) and traducido.strip():
            return traducido
    catalogo_es = (catalogo or {}).get("es", {})
    if isinstance(catalogo_es, dict):
        texto_catalogo = catalogo_es.get(key)
        if isinstance(texto_catalogo, str) and texto_catalogo.strip():
            return texto_catalogo.format(**params) if params else texto_catalogo
    return fallback.format(**params) if params else fallback
