from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"


@dataclass(frozen=True)
class Capa:
    nombre: str
    prefijo: str
    ruta: Path


CAPAS = (
    Capa("domain", "app.domain", APP_ROOT / "domain"),
    Capa("application", "app.application", APP_ROOT / "application"),
    Capa("infrastructure", "app.infrastructure", APP_ROOT / "infrastructure"),
    Capa("ui", "app.ui", APP_ROOT / "ui"),
)


DEPENDENCIAS_PROHIBIDAS = {
    "domain": {"application", "infrastructure", "ui"},
    "application": {"infrastructure", "ui"},
    "infrastructure": {"ui"},
    "ui": {"infrastructure"},
}


def _detectar_capa_destino(modulo: str) -> str | None:
    for capa in CAPAS:
        if modulo == capa.prefijo or modulo.startswith(f"{capa.prefijo}."):
            return capa.nombre
    return None


def _iter_imports(tree: ast.AST) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))
    return imports


def test_guard_imports_clean_architecture() -> None:
    violaciones: list[str] = []

    for capa_origen in CAPAS:
        if not capa_origen.ruta.exists():
            continue
        for py_file in sorted(capa_origen.ruta.rglob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for modulo, linea in _iter_imports(tree):
                capa_destino = _detectar_capa_destino(modulo)
                if capa_destino is None:
                    continue
                if capa_destino in DEPENDENCIAS_PROHIBIDAS[capa_origen.nombre]:
                    ruta_relativa = py_file.relative_to(PROJECT_ROOT).as_posix()
                    violaciones.append(
                        f"{ruta_relativa}:{linea} importa {modulo} (prohibido {capa_origen.nombre} -> {capa_destino})"
                    )

    assert not violaciones, "\n".join(violaciones)
