from __future__ import annotations

import json
from pathlib import Path

from .parseo_catalogo import parsear_catalogo_crudo


RUTA_CATALOGO_DEFAULT = Path(__file__).with_name("catalogo.json")


def leer_catalogo_json(ruta: Path = RUTA_CATALOGO_DEFAULT) -> dict[str, str]:
    data = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError
    return parsear_catalogo_crudo(data)


def escribir_catalogo_json(catalogo: dict[str, str], ruta: Path) -> None:
    contenido = json.dumps(catalogo, ensure_ascii=False, indent=2, sort_keys=True)
    ruta.write_text(f"{contenido}\n", encoding="utf-8")
