#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import logging
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


class GateStepError(RuntimeError):
    pass


def _run(cmd: list[str]) -> int:
    LOGGER.info("gate_pr_step_start", extra={"cmd": cmd})
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    LOGGER.info(
        "gate_pr_step_end", extra={"cmd": cmd, "returncode": completed.returncode}
    )
    return completed.returncode


def _ejecutar_pytest_no_ui_con_diagnostico(marker: str = "not ui") -> int:
    comando = [sys.executable, "-m", "pytest", "-q", "-m", marker]
    returncode = _run(comando)
    if returncode != 255:
        return returncode

    LOGGER.error(
        "pytest_exit_255_detectado_lanzando_diagnostico",
        extra={
            "cmd": comando,
            "diagnostico_stdout": "logs/pytest_stdout.log",
            "diagnostico_stderr": "logs/pytest_stderr.log",
            "diagnostico_result": "logs/pytest_result.json",
        },
    )
    comando_diagnostico = [
        sys.executable,
        "-m",
        "scripts.diagnosticar_pytest",
        "--marker",
        marker,
    ]
    _run(comando_diagnostico)
    raise GateStepError(
        "pytest devolvió exit code 255; se generó diagnóstico en "
        "logs/pytest_stdout.log, logs/pytest_stderr.log y logs/pytest_result.json"
    )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    run_mypy = os.getenv("HS_RUN_MYPY", "0") in {"1", "true", "TRUE"}
    has_pytest_cov = importlib.util.find_spec("pytest_cov") is not None

    commands: list[list[str]] = [
        [sys.executable, "-m", "ruff", "check", "."],
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "scripts/gate_rapido.py",
            "scripts/gate_pr.py",
            "scripts/features_sync.py",
            "scripts/diagnosticar_pytest.py",
        ],
    ]
    if run_mypy:
        commands.append([sys.executable, "-m", "mypy", "app"])

    commands.append(
        [sys.executable, "-m", "pytest", "-q", "tests/domain", "tests/application"]
    )

    if has_pytest_cov:
        commands.append(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/domain",
                "tests/application",
                "--cov=app/domain",
                "--cov=app/application",
                "--cov-report=term-missing",
                "--cov-fail-under=85",
            ]
        )
    else:
        LOGGER.warning(
            "pytest-cov no disponible; se omite paso de cobertura en este entorno"
        )

    commands.extend(
        [
            [sys.executable, "-m", "pytest", "-q", "tests/golden/botones"],
            [sys.executable, "-m", "scripts.i18n.check_hardcode_i18n"],
            [sys.executable, "-m", "scripts.features_sync"],
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_no_secrets_committed.py",
            ],
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_no_secrets_content_scan.py",
            ],
        ]
    )

    try:
        if _ejecutar_pytest_no_ui_con_diagnostico("not ui") != 0:
            return 1
        for command in commands:
            if _run(command) != 0:
                return 1
    except GateStepError as error:
        LOGGER.error("gate_pr_error", extra={"error": str(error)})
        return 1

    verify_docs = subprocess.run(
        [
            "git",
            "diff",
            "--exit-code",
            "--",
            "docs/features.md",
            "docs/features_pendientes.md",
        ],
        cwd=ROOT,
        check=False,
    )
    if verify_docs.returncode != 0:
        LOGGER.error("docs/features*.md desactualizados respecto a docs/features.json")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
