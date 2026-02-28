#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON_PATH = ROOT / "logs" / "quality_report.json"
SUMMARY_MD_PATH = ROOT / "_backstage" / "reportes" / "quality_summary.md"


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
    return f"Objetivos CC: {cc_budget.get('status')} ({cc_budget.get('detail', 'sin detalle')})."


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

    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        results = _read_report(REPORT_JSON_PATH)
        summary = build_summary(results)
        SUMMARY_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_MD_PATH.write_text(summary, encoding="utf-8")
    except QualitySummaryError as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"Resumen generado en {SUMMARY_MD_PATH.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
