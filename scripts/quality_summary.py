#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON_PATH = ROOT / "logs" / "quality_report.json"
QUALITY_REPORT_MD_PATH = ROOT / "logs" / "quality_report.md"
SUMMARY_MD_PATH = ROOT / "_backstage" / "reportes" / "quality_summary.md"
HOTSPOT_LOC_THRESHOLD = 180
TOP_N = 10


class QualitySummaryError(RuntimeError):
    """Error de contrato para generación de resumen de quality gate."""


def _read_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise QualitySummaryError(f"No existe el reporte requerido: {path.as_posix()}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QualitySummaryError(f"JSON inválido en {path.as_posix()}: {exc}") from exc

    if not isinstance(payload, dict) or "results" not in payload:
        raise QualitySummaryError(
            "El archivo logs/quality_report.json debe incluir un objeto raíz con clave 'results'."
        )

    results = payload.get("results")
    if not isinstance(results, dict):
        raise QualitySummaryError("La clave 'results' debe ser un objeto JSON válido.")

    required_sections = [
        "global_status",
        "coverage",
        "cc_budget",
        "cc_targets",
        "architecture",
        "secrets",
        "naming",
        "release_contract",
    ]
    missing = [section for section in required_sections if section not in results]
    if missing:
        raise QualitySummaryError(
            "Faltan campos obligatorios en 'results': " + ", ".join(sorted(missing))
        )

    return results


def _coverage_highlight(results: dict[str, Any]) -> str:
    coverage = results["coverage"]
    value = coverage.get("value")
    threshold = coverage.get("threshold")
    status = coverage.get("status")
    if value is None:
        return f"Coverage core: {status} (sin valor medible, umbral={threshold}%)."
    return f"Coverage core: {status} ({value}% vs umbral {threshold}%)."


def _cc_highlight(results: dict[str, Any]) -> str:
    cc_budget = results["cc_budget"]
    cc_targets = results["cc_targets"]
    return (
        f"Objetivos CC globales: {cc_budget.get('status')} ({cc_budget.get('detail', 'sin detalle')}) | "
        f"targets explícitos: {cc_targets.get('status')} ({cc_targets.get('detail', 'sin detalle')})."
    )


def _naming_highlight(results: dict[str, Any]) -> str:
    naming = results["naming"]
    offenders = naming.get("total_offenders", "N/D")
    nuevos_archivos = len(naming.get("nuevos_archivos", []))
    nuevos_simbolos = len(naming.get("nuevos_simbolos", []))
    return (
        "Baseline de naming: "
        f"{naming.get('status')} (offenders_totales={offenders}, "
        f"nuevos_archivos={nuevos_archivos}, nuevos_simbolos={nuevos_simbolos})."
    )


def _architecture_highlight(results: dict[str, Any]) -> str:
    architecture = results["architecture"]
    return f"Arquitectura: {architecture.get('status')} ({architecture.get('detail', 'sin detalle')})."


def _release_highlight(results: dict[str, Any]) -> str:
    release = results["release_contract"]
    secrets = results["secrets"]
    return (
        f"Release build: {release.get('status')} ({release.get('detail', 'sin detalle')}) | "
        f"Secretos: {secrets.get('status')} ({secrets.get('detail', 'sin detalle')})."
    )


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
        return (
            "radon no disponible: se usa fallback por LOC.",
            _top_loc(files, top_n),
        )

    rows: list[tuple[str, int]] = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        for block in cc_visit(source):
            if block.letter not in {"F", "M"}:
                continue
            identifier = f"{relative}:{block.classname}.{block.name}" if block.classname else f"{relative}:{block.name}"
            rows.append((identifier, int(block.complexity)))

    rows.sort(key=lambda item: item[1], reverse=True)
    return ("radon disponible", rows[:top_n])


def _build_hotspot_recommendations(loc_rows: list[tuple[str, int]], threshold: int = HOTSPOT_LOC_THRESHOLD) -> list[str]:
    over_threshold = [item for item in loc_rows if item[1] > threshold]
    candidates = over_threshold[:3] if over_threshold else loc_rows[:3]
    recommendations: list[str] = []
    for file_path, loc in candidates:
        recommendations.append(
            f"Refactorizar `{file_path}` ({loc} LOC) priorizando extracción de helpers y reducción de responsabilidades."
        )

    while len(recommendations) < 3:
        recommendations.append("Mantener monitoreo: no hay nuevos archivos por encima del umbral de hotspot LOC.")

    return recommendations[:3]


def build_summary(results: dict[str, Any]) -> str:
    fecha = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    commit_sha = os.getenv("GITHUB_SHA", "N/D")
    global_status = results["global_status"]

    highlights = [
        _coverage_highlight(results),
        _cc_highlight(results),
        _naming_highlight(results),
        _architecture_highlight(results),
        _release_highlight(results),
    ]

    files = _python_files()
    loc_rows = _top_loc(files, TOP_N)
    cc_note, cc_rows = _top_complexity(files, TOP_N)
    recommendations = _build_hotspot_recommendations(loc_rows)

    lines = [
        "# Resumen de Quality Gate",
        "",
        f"- Fecha: {fecha}",
        f"- Commit SHA: {commit_sha}",
        f"- Global Status: **{global_status}**",
        "",
        "## Highlights",
    ]
    for index, highlight in enumerate(highlights, start=1):
        lines.append(f"{index}. {highlight}")

    lines.extend(["", "## Top 10 archivos por LOC"])
    for index, (file_path, loc) in enumerate(loc_rows, start=1):
        lines.append(f"{index:02d}. {file_path} -> {loc} LOC")

    lines.extend(["", "## Top 10 por complejidad", f"- Nota: {cc_note}"])
    for index, (identifier, complexity) in enumerate(cc_rows, start=1):
        lines.append(f"{index:02d}. {identifier} -> {complexity}")

    lines.extend(["", "## Próximos hotspots recomendados"])
    for index, recommendation in enumerate(recommendations, start=1):
        lines.append(f"{index}. {recommendation}")

    return "\n".join(lines) + "\n"


def _append_or_replace_snapshot(existing_markdown: str, summary_block: str) -> str:
    marker = "## Snapshot refactor-friendly"
    replacement_block = f"{marker}\n\n{summary_block.strip()}\n"
    pattern = re.compile(r"## Snapshot refactor-friendly\n(?:.|\n)*\Z", re.MULTILINE)
    if marker in existing_markdown:
        return pattern.sub(replacement_block, existing_markdown).rstrip() + "\n"
    base = existing_markdown.rstrip()
    if base:
        base += "\n\n"
    return base + replacement_block


def main() -> int:
    try:
        results = _read_report(REPORT_JSON_PATH)
        summary = build_summary(results)
        QUALITY_REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = (
            QUALITY_REPORT_MD_PATH.read_text(encoding="utf-8") if QUALITY_REPORT_MD_PATH.exists() else ""
        )
        QUALITY_REPORT_MD_PATH.write_text(_append_or_replace_snapshot(existing, summary), encoding="utf-8")
        SUMMARY_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_MD_PATH.write_text(summary, encoding="utf-8")
    except QualitySummaryError as exc:
        print(f"ERROR: {exc}")
        return 2

    print(
        "Resumen generado en "
        f"{SUMMARY_MD_PATH.as_posix()} y snapshot integrado en {QUALITY_REPORT_MD_PATH.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
