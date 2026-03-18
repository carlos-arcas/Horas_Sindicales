from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USE_CASES_ROOT = PROJECT_ROOT / "app" / "application" / "use_cases"
POLITICA_PATH = PROJECT_ROOT / "app" / "application" / "use_cases" / "politica_modo_solo_lectura.py"

ARCHIVOS_MUTANTES_READ_ONLY = {
    "app/application/use_cases/solicitudes/use_case.py",
    "app/application/use_cases/personas/use_case.py",
    "app/application/use_cases/confirmacion_pdf/caso_uso.py",
}

ARCHIVOS_PERMITIDOS_IS_READ_ONLY = {
    "app/configuracion/settings.py",
    "app/bootstrap/container.py",
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
        "Todos los casos de uso deben recibir la política explícita en vez de usar "
        "is_read_only_enabled directo:\n" + "\n".join(violaciones)
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


def test_guardarrail_casos_uso_mutantes_invocan_politica_inyectada() -> None:
    faltantes: list[str] = []

    for relativo in sorted(ARCHIVOS_MUTANTES_READ_ONLY):
        texto = (PROJECT_ROOT / relativo).read_text(encoding="utf-8")
        if "_politica_modo_solo_lectura.verificar()" not in texto and "politica_modo_solo_lectura.verificar()" not in texto:
            faltantes.append(relativo)

    assert not faltantes, (
        "Cada owner mutante debe aplicar la política explícita en su capa:\n"
        + "\n".join(faltantes)
    )


def test_guardarrail_politica_no_importa_settings_global() -> None:
    relativo = "app/application/use_cases/politica_modo_solo_lectura.py"
    tree = ast.parse(POLITICA_PATH.read_text(encoding="utf-8"), filename=relativo)

    violaciones: list[str] = []
    for nodo in ast.walk(tree):
        if isinstance(nodo, ast.ImportFrom) and nodo.module == "app.configuracion.settings":
            nombres = {alias.name for alias in nodo.names}
            if "is_read_only_enabled" in nombres:
                violaciones.append(
                    f"{relativo}: import directo de app.configuracion.settings.is_read_only_enabled"
                )

    assert not violaciones, (
        "La política de aplicación debe estar desacoplada de settings globales:\n"
        + "\n".join(violaciones)
    )


def test_guardarrail_politica_no_define_estado_global_mutable() -> None:
    relativo = "app/application/use_cases/politica_modo_solo_lectura.py"
    tree = ast.parse(POLITICA_PATH.read_text(encoding="utf-8"), filename=relativo)

    simbolos_prohibidos = {
        "_proveedor_modo_solo_lectura",
        "configurar_proveedor_modo_solo_lectura",
        "restablecer_proveedor_modo_solo_lectura",
        "verificar_modo_solo_lectura",
    }
    encontrados: list[str] = []

    for nodo in tree.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if nodo.name in simbolos_prohibidos:
                encontrados.append(nodo.name)
        elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            if nodo.target.id in simbolos_prohibidos:
                encontrados.append(nodo.target.id)
        elif isinstance(nodo, ast.Assign):
            for target in nodo.targets:
                if isinstance(target, ast.Name) and target.id in simbolos_prohibidos:
                    encontrados.append(target.id)

    assert not encontrados, (
        "La política read-only no debe reintroducir estado global mutable ni helpers globales heredados:\n"
        + "\n".join(sorted(encontrados))
    )
