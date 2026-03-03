#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print("\n>>>", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    print("<<< exit=", completed.returncode)
    return completed.returncode


def main() -> int:
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
        print(
            "WARNING: pytest-cov no disponible; se omite paso de cobertura en este entorno."
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

    for command in commands:
        if _run(command) != 0:
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
        print("ERROR: docs/features*.md desactualizados respecto a docs/features.json")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
