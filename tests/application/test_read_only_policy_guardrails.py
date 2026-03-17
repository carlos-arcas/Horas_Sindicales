from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USE_CASES_ROOT = PROJECT_ROOT / "app" / "application" / "use_cases"

ARCHIVOS_MUTANTES_READ_ONLY = {
    "app/application/use_cases/solicitudes/use_case.py",
    "app/application/use_cases/personas/use_case.py",
    "app/application/use_cases/confirmacion_pdf/caso_uso.py",
}

ARCHIVOS_PERMITIDOS_IS_READ_ONLY = {
    "app/configuracion/settings.py",
    "app/application/use_cases/politica_modo_solo_lectura.py",
}


def _iter_archivos_use_cases() -> list[Path]:
    return sorted(path for path in USE_CASES_ROOT.rglob("*.py"))


def test_guardarrail_no_usa_is_read_only_directo_fuera_de_politica() -> None:
    violaciones: list[str] = []

    for archivo in _iter_archivos_use_cases():
        relativo = archivo.relative_to(PROJECT_ROOT).as_posix()
        if relativo in ARCHIVOS_PERMITIDOS_IS_READ_ONLY:
            continue
        tree = ast.parse(archivo.read_text(encoding="utf-8"), filename=relativo)
        for nodo in ast.walk(tree):
            if isinstance(nodo, ast.Name) and nodo.id == "is_read_only_enabled":
                violaciones.append(f"{relativo}: uso directo de is_read_only_enabled")

    assert not violaciones, (
        "Todos los casos de uso deben invocar la política común "
        "verificar_modo_solo_lectura() en vez de usar is_read_only_enabled directo:\n"
        + "\n".join(violaciones)
    )


def test_guardarrail_no_usa_literal_read_only_en_casos_uso_mutantes() -> None:
    violaciones: list[str] = []

    for relativo in sorted(ARCHIVOS_MUTANTES_READ_ONLY):
        archivo = PROJECT_ROOT / relativo
        tree = ast.parse(archivo.read_text(encoding="utf-8"), filename=relativo)
        for nodo in ast.walk(tree):
            if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
                if "Modo solo lectura activado" in nodo.value:
                    violaciones.append(f"{relativo}: literal read-only no canónico")

    assert not violaciones, (
        "Los casos de uso mutantes deben reutilizar MENSAJE_MODO_SOLO_LECTURA, "
        "sin literales duplicados:\n" + "\n".join(violaciones)
    )


def test_guardarrail_casos_uso_mutantes_invocan_politica_comun() -> None:
    faltantes: list[str] = []

    for relativo in sorted(ARCHIVOS_MUTANTES_READ_ONLY):
        texto = (PROJECT_ROOT / relativo).read_text(encoding="utf-8")
        if "verificar_modo_solo_lectura()" not in texto:
            faltantes.append(relativo)

    assert not faltantes, (
        "Cada owner mutante debe aplicar verificar_modo_solo_lectura() en su capa:\n"
        + "\n".join(faltantes)
    )
