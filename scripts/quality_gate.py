#!/usr/bin/env python3
from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import os
import sys
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / ".config" / "quality_gate.json"
BASELINE_NAMING_PATH = ROOT / ".config" / "naming_baseline.json"
LOGS_DIR = ROOT / "logs"
QUALITY_REPORT_JSON = LOGS_DIR / "quality_report.json"
QUALITY_REPORT_MD = LOGS_DIR / "quality_report.md"

LOGGER = logging.getLogger("quality_gate")


def _construir_reporte_naming(raiz: Path, umbral_offenders: int) -> dict[str, Any]:
    module = importlib.import_module("scripts.auditar_naming")
    return module.construir_reporte(raiz=raiz, umbral_offenders=umbral_offenders)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(module)s | %(funcName)s | %(message)s",
    )


def load_config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_coverage_threshold(config: dict[str, object]) -> int:
    threshold = config.get("coverage_fail_under_core", config.get("coverage_fail_under"))
    if not isinstance(threshold, int):
        raise SystemExit(
            f"Umbral de cobertura inválido en {CONFIG_PATH}. "
            "Se esperaba un entero en 'coverage_fail_under_core' o 'coverage_fail_under'."
        )
    return threshold


def load_core_coverage_targets(config: dict[str, object]) -> list[str]:
    raw_targets = config.get("core_coverage_targets")
    if raw_targets is None:
        return ["app"]
    if not isinstance(raw_targets, list) or not all(
        isinstance(item, str) for item in raw_targets
    ):
        raise SystemExit(
            f"Valor inválido para 'core_coverage_targets' en {CONFIG_PATH}. "
            "Se esperaba list[str]."
        )
    return raw_targets


def preflight_pytest(allow_missing_pytest_cov: bool = False) -> dict[str, Any]:
    if pytest.main(["--version"]) != 0:
        LOGGER.error(
            "Falta pytest en el entorno activo. Ejecuta: python -m pip install -r requirements-dev.txt"
        )
        raise SystemExit(2)

    if importlib.util.find_spec("pytest_cov") is None:
        if allow_missing_pytest_cov:
            LOGGER.warning(
                "pytest-cov no disponible; ejecutado en modo degradado por bandera/env explícito."
            )
            return {
                "degraded_mode": True,
                "degraded_reason": "pytest-cov no disponible; ejecutado en modo degradado",
            }

        LOGGER.error(
            "Falta pytest-cov en el entorno activo. "
            "Instala dependencias dev con: python -m pip install -r requirements-dev.txt"
        )
        LOGGER.error(
            "En CI, verifica que el job ejecute 'pip install -r requirements-dev.txt' antes del quality gate."
        )
        raise SystemExit(2)

    return {"degraded_mode": False, "degraded_reason": None}


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _make_result(status: str, detail: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status, "detail": detail}
    payload.update(extra)
    return payload


def _record(records: list[dict[str, str]], area: str, status: str, detail: str) -> None:
    records.append(
        {
            "timestamp": _timestamp(),
            "area": area,
            "status": status,
            "detalle": detail,
        }
    )


def run_pytest_coverage(
    threshold: int,
    coverage_targets: list[str],
    records: list[dict[str, str]],
    pytest_runner: Callable[[list[str]], int],
) -> dict[str, Any]:
    coverage_path = LOGS_DIR / "coverage.json"
    cmd = [
        "-q",
        "-m",
        "not ui",
        "--cov-report=term-missing",
        f"--cov-report=json:{coverage_path.as_posix()}",
        f"--cov-fail-under={threshold}",
    ]
    for target in coverage_targets:
        cmd.append(f"--cov={target}")

    exit_code = pytest_runner(cmd)
    coverage_value = None
    if coverage_path.exists():
        data = json.loads(coverage_path.read_text(encoding="utf-8"))
        total = data.get("totals", {})
        value = total.get("percent_covered")
        if isinstance(value, (int, float)):
            coverage_value = round(float(value), 2)

    passed = exit_code == 0 and coverage_value is not None and coverage_value >= threshold
    detail = (
        f"coverage_core={coverage_value}%, umbral={threshold}%"
        if coverage_value is not None
        else f"No se pudo leer cobertura (exit_code={exit_code})"
    )
    status = "PASS" if passed else "FAIL"
    _record(records, "coverage", status, detail)
    return _make_result(status, detail, value=coverage_value, threshold=threshold, exit_code=exit_code)


def run_contractual_test(
    area: str,
    test_ref: str,
    records: list[dict[str, str]],
    pytest_runner: Callable[[list[str]], int],
) -> dict[str, Any]:
    exit_code = pytest_runner(["-q", test_ref])
    status = "PASS" if exit_code == 0 else "FAIL"
    detail = f"{test_ref} exit_code={exit_code}"
    _record(records, area, status, detail)
    return _make_result(status, detail, exit_code=exit_code)


def _load_naming_baseline() -> dict[str, set[str]]:
    if not BASELINE_NAMING_PATH.exists():
        raise SystemExit("Falta .config/naming_baseline.json para controlar regresión de naming debt.")

    data = json.loads(BASELINE_NAMING_PATH.read_text(encoding="utf-8"))
    archivos = data.get("archivos_con_naming_ingles", [])
    simbolos = data.get("simbolos_publicos_en_ingles", [])
    if not isinstance(archivos, list) or not isinstance(simbolos, list):
        raise SystemExit("La baseline de naming debe contener listas válidas.")

    return {"archivos": set(archivos), "simbolos": set(simbolos)}


def run_naming_guard(records: list[dict[str, str]]) -> dict[str, Any]:
    baseline = _load_naming_baseline()
    reporte = _construir_reporte_naming(raiz=ROOT, umbral_offenders=10**9)

    archivos_actuales = set(reporte["archivos_con_naming_ingles"])
    simbolos_actuales = {
        f"{item['archivo']}::{item['simbolo']}" for item in reporte["simbolos_publicos_en_ingles"]
    }
    nuevos_archivos = sorted(archivos_actuales - baseline["archivos"])
    nuevos_simbolos = sorted(simbolos_actuales - baseline["simbolos"])

    has_regression = bool(nuevos_archivos or nuevos_simbolos)
    status = "FAIL" if has_regression else "PASS"
    detail = (
        f"nuevos_archivos={len(nuevos_archivos)}, nuevos_simbolos={len(nuevos_simbolos)}"
    )
    _record(records, "naming", status, detail)

    return _make_result(
        status,
        detail,
        baseline_archivos=len(baseline["archivos"]),
        baseline_simbolos=len(baseline["simbolos"]),
        nuevos_archivos=nuevos_archivos,
        nuevos_simbolos=nuevos_simbolos,
        total_offenders=reporte["total_offenders"],
    )


def write_reports(payload: dict[str, Any], records: list[dict[str, str]]) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT_JSON.write_text(
        json.dumps({"results": payload, "events": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = ["# Quality Gate Unificado", "", "## Estado global", f"- **{payload['global_status']}**", ""]
    lines.append("## Modo degradado")
    lines.append(f"- activo: **{str(payload['degraded_mode']).lower()}**")
    if payload.get("degraded_reason"):
        lines.append(f"- razón: {payload['degraded_reason']}")
    lines.append("")
    lines.append("## Eventos")
    lines.append("| timestamp | area | status | detalle |")
    lines.append("|---|---|---|---|")
    for event in records:
        lines.append(
            f"| {event['timestamp']} | {event['area']} | {event['status']} | {event['detalle']} |"
        )

    lines.extend(["", "## Resumen JSON", "```json", json.dumps(payload, ensure_ascii=False, indent=2), "```"])
    QUALITY_REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report(
    pytest_runner: Callable[[list[str]], int] | None = None,
    degraded_mode: bool = False,
    degraded_reason: str | None = None,
) -> dict[str, Any]:
    config = load_config()
    threshold = load_coverage_threshold(config)
    coverage_targets = load_core_coverage_targets(config)
    runner = pytest_runner or pytest.main
    records: list[dict[str, str]] = []

    results: dict[str, Any] = {}
    if degraded_mode:
        detail = degraded_reason or "pytest-cov no disponible; ejecutado en modo degradado"
        _record(records, "coverage", "SKIP", detail)
        results["coverage"] = _make_result("SKIP", detail, value=None, threshold=threshold, exit_code=None)
    else:
        results["coverage"] = run_pytest_coverage(threshold, coverage_targets, records, runner)

    results["cc_budget"] = run_contractual_test(
        "cc_budget", "tests/test_quality_gate_metrics.py::test_quality_gate_size_and_complexity", records, runner
    )
    results["architecture"] = run_contractual_test(
        "architecture", "tests/test_architecture_imports.py", records, runner
    )
    results["secrets"] = run_contractual_test(
        "secrets", "tests/test_no_secrets_committed.py", records, runner
    )
    results["naming"] = run_naming_guard(records)
    results["release_contract"] = run_contractual_test(
        "release_contract", "tests/test_release_build_contract.py", records, runner
    )

    statuses = [
        value["status"]
        for key, value in results.items()
        if key not in {"global_status", "degraded_mode", "degraded_reason"}
    ]
    has_coverage_skip = results["coverage"]["status"] == "SKIP"
    results["degraded_mode"] = degraded_mode
    results["degraded_reason"] = degraded_reason if degraded_mode else None
    results["global_status"] = (
        "PASS" if all(item == "PASS" for item in statuses) and not has_coverage_skip else "FAIL"
    )

    write_reports(results, records)
    return results


def print_human_summary(results: dict[str, Any]) -> None:
    print("\n=== QUALITY GATE UNIFICADO ===")
    for area in ["coverage", "cc_budget", "architecture", "secrets", "naming", "release_contract"]:
        area_result = results[area]
        print(f"- {area}: {area_result['status']} | {area_result['detail']}")
    if results.get("degraded_mode"):
        print(f"- degraded_mode: true | razón: {results.get('degraded_reason')}")
    print(f"GLOBAL: {results['global_status']}")
    print(f"Reportes: {QUALITY_REPORT_MD.as_posix()} | {QUALITY_REPORT_JSON.as_posix()}")


def _parse_args(argv: list[str] | None = None) -> Any:
    parser = ArgumentParser(description="Quality Gate Unificado")
    parser.add_argument(
        "--allow-missing-pytest-cov",
        action="store_true",
        help="Permite modo degradado si falta pytest-cov (coverage=SKIP, global=FAIL).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = _parse_args(argv)
    allow_missing_pytest_cov = args.allow_missing_pytest_cov or os.getenv(
        "ALLOW_MISSING_PYTEST_COV", ""
    ) in {"1", "true", "TRUE", "yes", "YES"}

    preflight_info = preflight_pytest(allow_missing_pytest_cov=allow_missing_pytest_cov)
    results = build_report(
        degraded_mode=bool(preflight_info["degraded_mode"]),
        degraded_reason=preflight_info["degraded_reason"],
    )
    print_human_summary(results)
    return 0 if results["global_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
