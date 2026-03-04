from __future__ import annotations

from collections.abc import Mapping


def normalizar_clave(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bytes):
        valor = valor.decode("utf-8", errors="ignore")
    return str(valor).strip()


def normalizar_texto(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bytes):
        valor = valor.decode("utf-8", errors="ignore")
    texto = str(valor)
    return texto.replace("\r\n", "\n").replace("\r", "\n").strip()


def parsear_catalogo_crudo(raw_catalogo: Mapping[object, object] | None) -> dict[str, str]:
    if not raw_catalogo:
        return {}

    normalizado: dict[str, str] = {}
    for clave_raw, texto_raw in raw_catalogo.items():
        clave = normalizar_clave(clave_raw)
        if not clave:
            continue
        normalizado[clave] = normalizar_texto(texto_raw)
    return normalizado


def seleccionar_claves(catalogo: Mapping[str, str], claves: tuple[str, ...]) -> dict[str, str]:
    return {clave: catalogo[clave] for clave in claves if clave in catalogo}
