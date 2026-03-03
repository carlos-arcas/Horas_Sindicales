#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALITY_REPORT_JSON = ROOT / "logs" / "quality_report.json"


def main() -> int:
    env = os.environ.copy()
    env["QUALITY_GATE_STRICT"] = "0"

    command = [sys.executable, "-m", "scripts.quality_gate"]
    completed = subprocess.run(command, cwd=ROOT, env=env, check=False)

    status = "UNKNOWN"
    if QUALITY_REPORT_JSON.exists():
        payload = json.loads(QUALITY_REPORT_JSON.read_text(encoding="utf-8"))
        status = payload.get("results", {}).get("global_status", status)

    print("\n=== GATE LOCAL ===")
    print(f"Resultado: {status}")
    print("Reportes: logs/quality_report.txt | logs/quality_report.md | logs/quality_report.json")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
