from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

# TODO(architecture): eliminar estas excepciones temporales moviendo dependencias técnicas
# (sqlite3/gspread) a infraestructura y exponiendo puertos en application.
ALLOWED_VIOLATIONS: set[tuple[str, str]] = {
    ("app/application/delegada_resolution.py", "sqlite3"),
    ("app/application/use_cases/sync_sheets.py", "sqlite3"),
    ("app/application/use_cases/sync_sheets.py", "gspread"),
}

TECHNICAL_LIBRARIES_BLOCKED_IN_APPLICATION = {
    "sqlite3",
    "gspread",
    "googleapiclient",
}


@dataclass(frozen=True)
class ImportRecord:
    source_file: str
    source_layer: str
    imported_module: str


def _layer_from_file(path: Path) -> str | None:
    try:
        relative_parts = path.relative_to(PROJECT_ROOT).parts
    except ValueError:
        return None

    if len(relative_parts) < 2 or relative_parts[0] != "app":
        return None

    layer = relative_parts[1]
    if layer in {"domain", "application", "infrastructure", "ui"}:
        return layer
    return None


def _layer_from_module(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) >= 2 and parts[0] == "app":
        layer = parts[1]
        if layer in {"domain", "application", "infrastructure", "ui"}:
            return layer
    return None


def _resolve_imported_module(node: ast.ImportFrom, current_module: str) -> str | None:
    if node.level == 0:
        return node.module

    current_parts = current_module.split(".")
    if node.level > len(current_parts):
        return None

    base_parts = current_parts[: len(current_parts) - node.level]
    if node.module:
        base_parts.extend(node.module.split("."))

    return ".".join(base_parts) if base_parts else None


def _iter_imports(py_file: Path) -> list[ImportRecord]:
    source_text = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(py_file))
    relative_file = py_file.relative_to(PROJECT_ROOT).as_posix()
    source_layer = _layer_from_file(py_file)
    if source_layer is None:
        return []

    current_module = py_file.relative_to(PROJECT_ROOT).with_suffix("").as_posix().replace("/", ".")
    imports: list[ImportRecord] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    ImportRecord(
                        source_file=relative_file,
                        source_layer=source_layer,
                        imported_module=alias.name,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            imported_module = _resolve_imported_module(node, current_module)
            if imported_module:
                imports.append(
                    ImportRecord(
                        source_file=relative_file,
                        source_layer=source_layer,
                        imported_module=imported_module,
                    )
                )

    return imports


def _violation_for(record: ImportRecord) -> tuple[str, str] | None:
    destination_layer = _layer_from_module(record.imported_module)
    top_level_module = record.imported_module.split(".")[0]

    if record.source_layer == "domain" and destination_layer in {"application", "infrastructure", "ui"}:
        return (
            "Domain no puede depender de capas superiores (application/infrastructure/ui).",
            "Mueve la integración a application o define un puerto en domain para invertir la dependencia.",
        )

    if record.source_layer == "application":
        if destination_layer in {"ui", "infrastructure"}:
            return (
                "Application no puede importar UI ni módulos concretos de infraestructura.",
                "Extrae un puerto en domain/application y deja la implementación concreta en infrastructure.",
            )

        if top_level_module in TECHNICAL_LIBRARIES_BLOCKED_IN_APPLICATION:
            return (
                "Application no debe importar librerías técnicas específicas (sqlite3/gspread/googleapiclient).",
                "Mueve el acceso técnico a infrastructure y consume un puerto/servicio abstracto en application.",
            )

    if record.source_layer == "ui" and destination_layer == "infrastructure":
        return (
            "UI no puede importar infrastructure directamente.",
            "Haz que UI dependa de casos de uso/servicios de application (y puertos), no de adaptadores técnicos.",
        )

    if record.source_layer == "infrastructure" and destination_layer == "ui":
        return (
            "Infrastructure no puede depender de UI.",
            "Mueve la lógica de presentación a UI y conserva infrastructure enfocada en adaptadores técnicos.",
        )

    return None


def test_architecture_import_rules() -> None:
    violations: list[str] = []

    for py_file in sorted(APP_ROOT.rglob("*.py")):
        for record in _iter_imports(py_file):
            if (record.source_file, record.imported_module) in ALLOWED_VIOLATIONS:
                continue

            result = _violation_for(record)
            if result is None:
                continue

            broken_rule, suggestion = result
            violations.append(
                "\n".join(
                    [
                        f"Archivo origen: {record.source_file}",
                        f"Import prohibido: {record.imported_module}",
                        f"Regla violada: {broken_rule}",
                        f"Sugerencia: {suggestion}",
                    ]
                )
            )

    assert not violations, (
        "Se detectaron violaciones de arquitectura por imports entre capas:\n\n"
        + "\n\n".join(violations)
    )
