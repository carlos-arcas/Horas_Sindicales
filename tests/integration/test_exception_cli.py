from __future__ import annotations

import json
import os
import subprocess
import sys


def test_exception_cli_genera_incidente_y_exit_code(tmp_path) -> None:
    env = os.environ.copy()
    env["HORAS_LOG_DIR"] = str(tmp_path)
    env["HORAS_FORCE_UNHANDLED_EXCEPTION"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "app"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode != 0
    assert result.returncode == 2
    assert "Error inesperado. ID de incidente:" in result.stderr

    crash_log = tmp_path / "crashes.log"
    assert crash_log.exists()
    events = [json.loads(line) for line in crash_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert events
    latest = events[-1]
    assert latest.get("correlation_id")
    assert "RuntimeError: Excepción forzada para pruebas de robustez global" in latest.get("exc_info", "")
