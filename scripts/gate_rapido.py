#!/usr/bin/env python3
from __future__ import annotations

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
    commands = [
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
        [sys.executable, "-m", "pytest", "-q", "tests/domain", "tests/application"],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_architecture_imports.py",
            "tests/test_clean_architecture_imports_guard.py",
        ],
        [sys.executable, "-m", "scripts.i18n.check_hardcode_i18n"],
    ]
    for command in commands:
        if _run(command) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
