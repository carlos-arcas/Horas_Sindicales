#!/usr/bin/env python3
from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _display(cmd: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def _run(cmd: list[str]) -> int:
    print(f"\n>>> {_display(cmd)}")
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    print(f"<<< exit code: {completed.returncode}")
    return completed.returncode


def main() -> int:
    commands = [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "pytest", "-q", "-m", "not ui"],
        [
            sys.executable,
            "scripts/quality_gate.py",
            "--allow-missing-pytest-cov",
        ],
    ]

    failures = 0
    for cmd in commands:
        if _run(cmd) != 0:
            failures += 1

    if failures:
        print(f"\nLint all finalizado con {failures} comando(s) fallido(s).")
        return 1

    print("\nLint all finalizado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
