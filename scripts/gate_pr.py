#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from app.testing.qt_harness import (
    _construir_args_pytest_core_no_ui,
    _construir_env_pytest_core_no_ui,
)

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


class GateStepError(RuntimeError):
    pass


def _run(cmd: list[str], env: dict[str, str] | None = None) -> int:
    LOGGER.info("gate_pr_step_start", extra={"cmd": cmd})
    completed = subprocess.run(cmd, cwd=ROOT, check=False, env=env)
    LOGGER.info(
        "gate_pr_step_end", extra={"cmd": cmd, "returncode": completed.returncode}
    )
    return completed.returncode


def _pytest_cov_disponible() -> bool:
    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0:
        LOGGER.error(
            "pytest_help_fallo_no_se_puede_validar_cobertura",
            extra={"returncode": resultado.returncode},
        )
        return False

    if "--cov" not in resultado.stdout:
        LOGGER.error(
            "pytest_cov_no_activo_en_pytest_help",
            extra={"detalle": "Instala dependencias dev con requirements-dev.txt"},
        )
        return False

    return True


def _comando_pytest_core_no_ui(
    args_pytest: list[str], *, habilitar_pytest_cov: bool = False
) -> tuple[list[str], dict[str, str]]:
    comando_pytest = _construir_args_pytest_core_no_ui(
        args_pytest,
        habilitar_pytest_cov=habilitar_pytest_cov,
    )
    comando = [sys.executable, "-m", "pytest", *comando_pytest]
    return comando, _construir_env_pytest_core_no_ui()


def _ejecutar_pytest_no_ui_con_diagnostico(marker: str = "not ui") -> int:
    comando, entorno = _comando_pytest_core_no_ui(["-q", "-m", marker])
    returncode = _run(comando, env=entorno)
    if returncode != 255:
        return returncode

    LOGGER.error(
        "pytest_exit_255_detectado_lanzando_diagnostico_verbose",
        extra={
            "cmd": comando,
            "diagnostico_stdout": "logs/pytest_stdout.log",
            "diagnostico_stderr": "logs/pytest_stderr.log",
            "diagnostico_result": "logs/pytest_result.json",
            "diagnostico_stdout_255_vv": "logs/pytest_stdout_255_vv.log",
            "diagnostico_stderr_255_vv": "logs/pytest_stderr_255_vv.log",
            "diagnostico_result_255_vv": "logs/pytest_result_255_vv.json",
        },
    )
    comando_diagnostico = [
        sys.executable,
        "-m",
        "scripts.diagnosticar_pytest",
        "--marker",
        marker,
        "--core-no-ui",
        "true",
        "--rerun-verbose-on-255",
        "true",
    ]
    _run(comando_diagnostico)
    raise GateStepError(
        "Pytest devolvió 255. Ver logs/pytest_stdout_255_vv.log y "
        "logs/pytest_result_255_vv.json (last_test_seen)."
    )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    run_mypy = os.getenv("HS_RUN_MYPY", "0") in {"1", "true", "TRUE"}
    if not _pytest_cov_disponible():
        LOGGER.error(
            "gate_pr_rechazado_sin_cobertura_real",
            extra={
                "detalle": (
                    "Falta pytest-cov o pytest no expone --cov; instala requirements-dev.txt antes del gate"
                )
            },
        )
        return 1

    commands: list[tuple[list[str], dict[str, str] | None]] = [
        ([sys.executable, "-m", "ruff", "check", "."], None),
        (
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
            None,
        ),
    ]
    if run_mypy:
        commands.append(([sys.executable, "-m", "mypy", "app"], None))

    commands.append(
        _comando_pytest_core_no_ui(["-q", "tests/domain", "tests/application"])
    )

    commands.append(
        _comando_pytest_core_no_ui(
            [
                "-q",
                "tests/domain",
                "tests/application",
                "--cov=app/domain",
                "--cov=app/application",
                "--cov-report=term-missing",
                "--cov-fail-under=85",
            ],
            habilitar_pytest_cov=True,
        )
    )

    commands.extend(
        [
            _comando_pytest_core_no_ui(["-q", "tests/golden/botones"]),
            ([sys.executable, "-m", "scripts.i18n.check_hardcode_i18n"], None),
            ([sys.executable, "-m", "scripts.features_sync"], None),
            _comando_pytest_core_no_ui(["-q", "tests/test_no_secrets_committed.py"]),
            _comando_pytest_core_no_ui(["-q", "tests/test_no_secrets_content_scan.py"]),
        ]
    )

    try:
        if _ejecutar_pytest_no_ui_con_diagnostico("not ui") != 0:
            return 1
        for command, env in commands:
            if _run(command, env=env) != 0:
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
