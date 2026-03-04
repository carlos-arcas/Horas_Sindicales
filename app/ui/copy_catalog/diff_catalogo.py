from __future__ import annotations

from collections.abc import Mapping

from .modelos import CambioCatalogo, EntradaCatalogo, ResultadoDiff


def calcular_diff_catalogos(base: Mapping[str, str], objetivo: Mapping[str, str]) -> ResultadoDiff:
    claves_base = set(base)
    claves_objetivo = set(objetivo)

    missing = tuple(
        EntradaCatalogo(clave, objetivo[clave])
        for clave in sorted(claves_objetivo - claves_base)
    )
    extra = tuple(
        EntradaCatalogo(clave, base[clave])
        for clave in sorted(claves_base - claves_objetivo)
    )
    changed = tuple(
        CambioCatalogo(clave, base[clave], objetivo[clave])
        for clave in sorted(claves_base & claves_objetivo)
        if base[clave] != objetivo[clave]
    )
    return ResultadoDiff(missing=missing, extra=extra, changed=changed)


def fusionar_catalogos(base: Mapping[str, str], sobreescrituras: Mapping[str, str]) -> dict[str, str]:
    fusion = dict(base)
    for clave in sorted(sobreescrituras):
        fusion[clave] = sobreescrituras[clave]
    return fusion
