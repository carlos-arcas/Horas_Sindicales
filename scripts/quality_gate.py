#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".config" / "quality_gate.json"


def load_coverage_threshold() -> int:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    threshold = data.get("coverage_fail_under")
    if not isinstance(threshold, int):
        raise SystemExit(
            f"Invalid 'coverage_fail_under' in {CONFIG_PATH}. Expected integer."
        )
    return threshold


def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    threshold = load_coverage_threshold()
    print(f"Using coverage threshold: {threshold}%")

    run(["ruff", "check", "."])
    run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--cov=app",
            "--cov-report=term-missing",
            f"--cov-fail-under={threshold}",
        ]
    )


if __name__ == "__main__":
    main()
