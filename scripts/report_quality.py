#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".config" / "quality_gate.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera reporte de señales de calidad")
    parser.add_argument("--out", default="logs/quality_report.txt", help="Ruta de salida del reporte TXT")
    parser.add_argument("--top", type=int, default=20, help="Cantidad de entradas en rankings")
    parser.add_argument(
        "--target",
        default=None,
        help="Objetivo puntual con formato archivo.py:funcion_o_metodo (ej: app/x.py:f o app/x.py:Clase.m)",
    )
    return parser.parse_args()


def _python_files() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "app").rglob("*.py")
        if ".venv" not in path.parts and "__pycache__" not in path.parts
    )


def _top_loc(files: list[Path], top_n: int) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for path in files:
        loc = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        rows.append((path.relative_to(ROOT).as_posix(), loc))
    rows.sort(key=lambda item: item[1], reverse=True)
    return rows[:top_n]


def _top_complexity(files: list[Path], top_n: int) -> tuple[str, list[tuple[str, int]]]:
    try:
        from radon.complexity import cc_visit
    except Exception:
        fallback = _top_loc(files, top_n)
        return (
            "radon no disponible: se muestra fallback por LOC (aproximación simple de complejidad).",
            fallback,
        )

    rows: list[tuple[str, int]] = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        for block in cc_visit(source):
            if block.letter not in {"F", "M"}:
                continue
            if block.classname:
                identifier = f"{relative}:{block.classname}.{block.name}"
            else:
                identifier = f"{relative}:{block.name}"
            rows.append((identifier, int(block.complexity)))

    rows.sort(key=lambda item: item[1], reverse=True)
    return ("radon disponible", rows[:top_n])


def _parse_target(raw_target: str) -> tuple[Path, list[str], str]:
    if ":" not in raw_target:
        raise ValueError("--target debe seguir el formato archivo.py:funcion_o_metodo")

    raw_file, raw_identifier = raw_target.split(":", maxsplit=1)
    if not raw_file.endswith(".py"):
        raise ValueError("--target debe apuntar a un archivo .py")
    if not raw_identifier.strip():
        raise ValueError("--target requiere un nombre de función o método")

    target_file = ROOT / raw_file
    if not target_file.exists():
        raise ValueError(f"No existe el archivo de --target: {raw_file}")

    identifier_parts = [part for part in raw_identifier.split(".") if part]
    if not identifier_parts:
        raise ValueError("--target requiere un identificador válido")

    relative = target_file.relative_to(ROOT).as_posix()
    return target_file, identifier_parts, f"{relative}:{'.'.join(identifier_parts)}"


class _ComplexityNodeVisitor(ast.NodeVisitor):
    BRANCH_NODES = (
        ast.If,
        ast.IfExp,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.ExceptHandler,
        ast.With,
        ast.AsyncWith,
        ast.Match,
        ast.BoolOp,
        ast.comprehension,
    )

    def __init__(self) -> None:
        self.count = 1

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, self.BRANCH_NODES):
            self.count += 1
        super().generic_visit(node)


def _find_ast_node(module: ast.Module, parts: list[str]) -> ast.AST | None:
    current: ast.AST = module
    for index, part in enumerate(parts):
        body: list[ast.stmt] = getattr(current, "body", [])
        node = next(
            (
                item
                for item in body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and item.name == part
            ),
            None,
        )
        if node is None:
            return None
        if index < len(parts) - 1 and not isinstance(node, ast.ClassDef):
            return None
        current = node
    if isinstance(current, ast.ClassDef):
        return None
    return current


def _target_complexity(raw_target: str) -> tuple[str, str, int]:
    target_file, identifier_parts, printable_identifier = _parse_target(raw_target)
    source = target_file.read_text(encoding="utf-8")

    try:
        from radon.complexity import cc_visit
    except Exception:
        module = ast.parse(source)
        node = _find_ast_node(module, identifier_parts)
        if node is None:
            raise ValueError(f"No se encontró el símbolo indicado en --target: {printable_identifier}")
        visitor = _ComplexityNodeVisitor()
        visitor.visit(node)
        return (
            "radon no disponible: se usa CC aproximada por AST (conteo de nodos condicionales).",
            printable_identifier,
            visitor.count,
        )

    for block in cc_visit(source):
        if block.letter not in {"F", "M"}:
            continue
        candidate_parts = [block.classname, block.name] if block.classname else [block.name]
        normalized_candidate = [part for part in candidate_parts if part]
        if normalized_candidate == identifier_parts:
            return ("radon disponible", printable_identifier, int(block.complexity))

    raise ValueError(f"No se encontró el símbolo indicado en --target: {printable_identifier}")


def _load_coverage_json() -> tuple[str, dict[str, Any] | None]:
    coverage_json = ROOT / "logs" / "coverage.json"
    coverage_json.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", str(coverage_json)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return ("coverage.py no disponible o sin datos (.coverage).", None)

    if not coverage_json.exists():
        return ("No se pudo generar logs/coverage.json.", None)

    return ("coverage.py disponible", json.loads(coverage_json.read_text(encoding="utf-8")))


def _load_cc_targets() -> dict[str, int]:
    if not CONFIG_PATH.exists():
        return {}

    try:
        raw_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"No se pudo parsear {CONFIG_PATH.relative_to(ROOT)}: {exc}") from exc

    raw_targets = raw_config.get("cc_targets", {})
    if not isinstance(raw_targets, dict):
        raise ValueError("El campo cc_targets en .config/quality_gate.json debe ser un objeto JSON")

    parsed_targets: dict[str, int] = {}
    for key, value in raw_targets.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Cada clave de cc_targets debe ser un target no vacío con formato ruta.py:simbolo")
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"cc_targets[{key!r}] debe ser un entero positivo")
        parsed_targets[key] = value

    return parsed_targets


def _package_name(file_path: str) -> str | None:
    normalized = file_path.replace("\\", "/")
    if not normalized.startswith("app/"):
        return None
    parts = normalized.split("/")
    if len(parts) < 2:
        return None
    package = parts[1]
    if package not in {"domain", "application", "infrastructure", "ui"}:
        return None
    return package


def _coverage_by_package(data: dict[str, Any] | None) -> dict[str, float]:
    if data is None:
        return {"domain": 0.0, "application": 0.0, "infrastructure": 0.0, "ui": 0.0}

    files = data.get("files", {})
    totals: dict[str, dict[str, int]] = {
        "domain": {"covered": 0, "statements": 0},
        "application": {"covered": 0, "statements": 0},
        "infrastructure": {"covered": 0, "statements": 0},
        "ui": {"covered": 0, "statements": 0},
    }

    for file_path, payload in files.items():
        package = _package_name(file_path)
        if package is None:
            continue
        summary = payload.get("summary", {})
        totals[package]["covered"] += int(summary.get("covered_lines", 0))
        totals[package]["statements"] += int(summary.get("num_statements", 0))

    result: dict[str, float] = {}
    for package, values in totals.items():
        statements = values["statements"]
        if statements == 0:
            result[package] = 0.0
            continue
        result[package] = (values["covered"] / statements) * 100
    return result


def _format_report(
    loc_rows: list[tuple[str, int]],
    cc_note: str,
    cc_rows: list[tuple[str, int]],
    coverage_note: str,
    coverage_rows: dict[str, float],
    target_result: tuple[str, str, int] | None,
    budget_status: tuple[str, int, int, bool] | None,
) -> str:
    lines: list[str] = []
    lines.append("# Reporte de calidad")
    lines.append("")
    lines.append("## Top 20 archivos por LOC")
    for idx, (file_path, loc) in enumerate(loc_rows, start=1):
        lines.append(f"{idx:02d}. {file_path} -> {loc} LOC")

    lines.append("")
    lines.append("## Top 20 por complejidad")
    lines.append(f"- Nota: {cc_note}")
    for idx, (identifier, complexity) in enumerate(cc_rows, start=1):
        lines.append(f"{idx:02d}. {identifier} -> {complexity}")

    lines.append("")
    lines.append("## Coverage por paquete")
    lines.append(f"- Nota: {coverage_note}")
    for package in ["domain", "application", "infrastructure", "ui"]:
        lines.append(f"- {package}: {coverage_rows[package]:.2f}%")

    if target_result is not None:
        target_note, target_identifier, target_cc = target_result
        lines.append("")
        lines.append("## Complejidad target")
        lines.append(f"- Nota: {target_note}")
        lines.append(f"- {target_identifier} -> {target_cc}")

    if budget_status is not None:
        target_identifier, target_cc, target_limit, target_ok = budget_status
        lines.append("")
        lines.append("## Presupuesto CC target")
        lines.append(f"- Fuente: .config/quality_gate.json > cc_targets[{target_identifier!r}]")
        lines.append(f"- Límite: {target_limit}")
        lines.append(f"- Medido: {target_cc}")
        lines.append(f"- Resultado: {'PASS' if target_ok else 'FAIL'}")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    files = _python_files()
    loc_rows = _top_loc(files, top_n=args.top)
    cc_note, cc_rows = _top_complexity(files, top_n=args.top)
    coverage_note, coverage_data = _load_coverage_json()
    coverage_rows = _coverage_by_package(coverage_data)
    try:
        cc_targets = _load_cc_targets()
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    try:
        target_result = _target_complexity(args.target) if args.target else None
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    budget_status: tuple[str, int, int, bool] | None = None
    budget_failed = False
    if target_result is not None:
        _, target_identifier, target_cc = target_result
        if target_identifier in cc_targets:
            target_limit = cc_targets[target_identifier]
            target_ok = target_cc <= target_limit
            budget_status = (target_identifier, target_cc, target_limit, target_ok)
            budget_failed = not target_ok

    report = _format_report(loc_rows, cc_note, cc_rows, coverage_note, coverage_rows, target_result, budget_status)
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(report)
    if budget_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
