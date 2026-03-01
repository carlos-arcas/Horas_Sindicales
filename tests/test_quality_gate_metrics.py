from __future__ import annotations

import ast
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

import pytest


def _load_quality_limits() -> dict[str, object]:
    """Carga configuración de métricas por lectura estática del archivo fuente.

    Este test no debe importar módulos de la app para evitar side effects de UI/Qt.
    """

    root = Path(__file__).resolve().parents[1]
    quality_path = root / "app" / "configuracion" / "calidad.py"
    tree = ast.parse(quality_path.read_text(encoding="utf-8"), filename=quality_path.as_posix())

    expected_keys = {
        "MAX_LOC_POR_ARCHIVO",
        "MAX_CC_POR_FUNCION",
        "RUTAS_EXCLUIDAS",
        "EXCEPCIONES_LOC",
        "EXCEPCIONES_CC",
    }
    values: dict[str, object] = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue

        name = node.targets[0].id
        if name not in expected_keys:
            continue
        values[name] = ast.literal_eval(node.value)

    missing = sorted(expected_keys - values.keys())
    if missing:
        raise AssertionError(
            "Faltan constantes de quality gate en app/configuracion/calidad.py: " + ", ".join(missing)
        )

    return values


@dataclass(frozen=True)
class LocViolation:
    file: str
    value: int
    limit: int

    @property
    def excess(self) -> int:
        return self.value - self.limit


@dataclass(frozen=True)
class CcViolation:
    identifier: str
    complexity: int
    limit: int

    @property
    def excess(self) -> int:
        return self.complexity - self.limit


def _iter_python_files() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    app_root = root / "app"
    config = _load_quality_limits()
    rutas_excluidas = set(config["RUTAS_EXCLUIDAS"])
    files: list[Path] = []

    for path in app_root.rglob("*.py"):
        relative = path.relative_to(root)
        if any(part in rutas_excluidas for part in relative.parts):
            continue
        files.append(path)

    return sorted(files)


def _format_loc_violations(violations: list[LocViolation]) -> str:
    top = sorted(violations, key=lambda item: item.value, reverse=True)[:10]
    lines = [
        "Top 10 archivos con LOC fuera de límite:",
        *[
            (
                f"  - {item.file}: {item.value} LOC "
                f"(límite {item.limit}, +{item.excess})"
            )
            for item in top
        ],
    ]
    return "\n".join(lines)


def _format_cc_violations(violations: list[CcViolation]) -> str:
    top = sorted(violations, key=lambda item: item.complexity, reverse=True)[:10]
    lines = [
        "Top 10 funciones/métodos con CC fuera de límite:",
        *[
            (
                f"  - {item.identifier}: CC {item.complexity} "
                f"(límite {item.limit}, +{item.excess})"
            )
            for item in top
        ],
    ]
    return "\n".join(lines)


@pytest.mark.metrics
def test_quality_gate_size_and_complexity() -> None:
    pytest.importorskip(
        "radon",
        reason="Métricas de complejidad requieren la dependencia dev opcional 'radon'.",
        exc_type=ImportError,
    )
    cc_visit = import_module("radon.complexity").cc_visit
    analyze = import_module("radon.raw").analyze

    root = Path(__file__).resolve().parents[1]
    config = _load_quality_limits()
    max_loc_por_archivo = int(config["MAX_LOC_POR_ARCHIVO"])
    max_cc_por_funcion = int(config["MAX_CC_POR_FUNCION"])
    excepciones_loc = dict(config["EXCEPCIONES_LOC"])
    excepciones_cc = dict(config["EXCEPCIONES_CC"])

    loc_violations: list[LocViolation] = []
    cc_violations: list[CcViolation] = []

    for path in _iter_python_files():
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()

        loc_value = analyze(source).sloc
        loc_limit = int(excepciones_loc.get(relative, max_loc_por_archivo))
        if loc_value > loc_limit:
            loc_violations.append(LocViolation(file=relative, value=loc_value, limit=loc_limit))

        for block in cc_visit(source):
            if block.letter not in {"F", "M"}:
                continue

            if block.classname:
                identifier = f"{relative}:{block.classname}.{block.name}"
            else:
                identifier = f"{relative}:{block.name}"

            cc_limit = int(excepciones_cc.get(identifier, max_cc_por_funcion))
            if block.complexity > cc_limit:
                cc_violations.append(
                    CcViolation(identifier=identifier, complexity=block.complexity, limit=cc_limit)
                )

    report_sections: list[str] = []
    if loc_violations:
        report_sections.append(_format_loc_violations(loc_violations))
    if cc_violations:
        report_sections.append(_format_cc_violations(cc_violations))

    if report_sections:
        report_sections.append(
            "Sugerencia: refactorizar/extraer responsabilidades para reducir tamaño y complejidad."
        )

    assert not report_sections, "\n\n" + "\n\n".join(report_sections)
