#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

from app.testing.qt_harness import (
    _construir_args_pytest_core_no_ui,
    _construir_env_pytest_core_no_ui,
)
from scripts.runtime_python import resolve_repo_python

ROOT = Path(__file__).resolve().parents[1]
PYTHON_BIN = resolve_repo_python()


def _run(cmd: list[str], env: dict[str, str] | None = None) -> int:
    print("\n>>>", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, check=False, env=env)
    print("<<< exit=", completed.returncode)
    return completed.returncode


def _comando_pytest_core_no_ui(
    args_pytest: list[str],
) -> tuple[list[str], dict[str, str]]:
    comando_pytest = _construir_args_pytest_core_no_ui(args_pytest)
    comando = [PYTHON_BIN, "-m", "pytest", *comando_pytest]
    return comando, _construir_env_pytest_core_no_ui()


def main() -> int:
    commands: list[tuple[list[str], dict[str, str] | None]] = [
        ([PYTHON_BIN, "-m", "ruff", "check", "."], None),
        [
            [
                PYTHON_BIN,
                "-m",
                "ruff",
                "format",
                "--check",
                "scripts/gate_rapido.py",
                "scripts/gate_pr.py",
                "scripts/features_sync.py",
                "scripts/runtime_python.py",
            ],
            None,
        ],
        _comando_pytest_core_no_ui(["-q", "tests/domain", "tests/application"]),
        _comando_pytest_core_no_ui(
            [
                "-q",
                "tests/test_architecture_imports.py",
                "tests/test_clean_architecture_imports_guard.py",
            ]
        ),
        ([PYTHON_BIN, "-m", "scripts.i18n.check_hardcode_i18n"], None),
    ]
    for command, env in commands:
        if _run(command, env=env) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
