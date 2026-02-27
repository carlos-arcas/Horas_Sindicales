#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera reporte de señales de calidad")
    parser.add_argument("--out", default="logs/quality_report.txt", help="Ruta de salida del reporte TXT")
    parser.add_argument("--top", type=int, default=20, help="Cantidad de entradas en rankings")
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

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    files = _python_files()
    loc_rows = _top_loc(files, top_n=args.top)
    cc_note, cc_rows = _top_complexity(files, top_n=args.top)
    coverage_note, coverage_data = _load_coverage_json()
    coverage_rows = _coverage_by_package(coverage_data)

    report = _format_report(loc_rows, cc_note, cc_rows, coverage_note, coverage_rows)
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
