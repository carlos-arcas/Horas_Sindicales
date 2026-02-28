#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".config" / "quality_gate.json"


LOGGER = logging.getLogger("quality_gate")


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


def run(command: list[str]) -> None:
    LOGGER.info("Ejecutando comando: %s", " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def preflight_pytest() -> None:
    if subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).returncode != 0:
        LOGGER.error(
            "Falta pytest en el entorno activo. Ejecuta: python -m pip install -r requirements-dev.txt"
        )
        raise SystemExit(2)



def pytest_cov_disponible() -> bool:
    if importlib.util.find_spec("pytest_cov") is None:
        return False

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    return "--cov" in result.stdout


def construir_comando_pytest(threshold: int, coverage_targets: list[str]) -> list[str]:
    command = [sys.executable, "-m", "pytest", "-q", "-m", "not ui"]

    if not pytest_cov_disponible():
        LOGGER.warning(
            "pytest-cov no disponible; se ejecuta pytest sin verificación de cobertura en este entorno."
        )
        LOGGER.warning(
            "Para activar el gate estricto de cobertura: python -m pip install -r requirements-dev.txt"
        )
        return command

    command.extend(["--cov-report=term-missing", f"--cov-fail-under={threshold}"])
    for target in coverage_targets:
        command.append(f"--cov={target}")
    return command


def main() -> None:
    configure_logging()
    config = load_config()
    threshold = load_coverage_threshold(config)
    coverage_targets = load_core_coverage_targets(config)

    LOGGER.info("Umbral CORE configurado: %s%%", threshold)
    LOGGER.info("Targets CORE configurados: %s", ", ".join(coverage_targets))

    preflight_pytest()

    run(["ruff", "check", "."])

    pytest_command = construir_comando_pytest(threshold, coverage_targets)
    run(pytest_command)
    run([sys.executable, "scripts/report_quality.py", "--out", "logs/quality_report.txt"])


if __name__ == "__main__":
    main()
