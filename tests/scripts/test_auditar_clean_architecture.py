from __future__ import annotations

import json
from pathlib import Path

from scripts.auditar_clean_architecture import (
    generar_reporte_json,
    generar_reporte_md,
    obtener_indicios_negocio_en_ui,
    obtener_violaciones_imports,
)


def _crear_archivo(base: Path, ruta: str, contenido: str) -> None:
    archivo = base / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido, encoding="utf-8")


def test_auditoria_detecta_violaciones_e_indicios_y_reporte(tmp_path: Path) -> None:
    _crear_archivo(
        tmp_path,
        "aplicacion/casos_de_uso/onboarding.py",
        "def ejecutar():\n    return None\n",
    )
    _crear_archivo(
        tmp_path,
        "dominio/modelo.py",
        "from aplicacion.casos_de_uso.onboarding import ejecutar\n",
    )
    _crear_archivo(
        tmp_path,
        "infraestructura/repositorio_preferencias_qsettings.py",
        "class Repo: ...\n",
    )
    _crear_archivo(
        tmp_path,
        "app/ui/pantalla.py",
        "import infraestructura.repositorio_preferencias_qsettings\n",
    )
    _crear_archivo(tmp_path, "app/ui/exportador.py", "import sqlite3\n")

    violaciones = obtener_violaciones_imports(tmp_path)
    indicios = obtener_indicios_negocio_en_ui(tmp_path)

    assert any(
        item["tipo"] == "dominio_importa_fuera_de_dominio" for item in violaciones
    )
    assert any(item["tipo"] == "ui_importa_infraestructura" for item in violaciones)
    assert any(item["tipo"] == "ui_importa_acceso_datos" for item in indicios)
    assert any(item["tipo"] == "ui_usa_libreria_sensible" for item in indicios)

    reporte_json = generar_reporte_json(violaciones, indicios)
    reporte_md = generar_reporte_md(violaciones, indicios)

    assert reporte_json["estado"] == "FAIL"
    assert "## Violaciones de imports entre capas" in reporte_md
    assert "## Indicios de negocio en UI" in reporte_md
    assert "ui_importa_infraestructura" in reporte_md

    datos = json.loads(json.dumps(reporte_json, ensure_ascii=False))
    assert datos["total_violaciones"] == len(violaciones)
    assert datos["total_indicios_ui"] == len(indicios)
