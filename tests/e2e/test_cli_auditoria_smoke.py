from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def test_cli_auditoria_dry_run_smoke() -> None:
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)

    result = subprocess.run(
        [sys.executable, "-m", "app.entrypoints.cli_auditoria", "--dry-run"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode in {0, 2}
    assert re.search(r"AUD-\d{8}-\d{6}-[0-9a-f]{8}", result.stdout)
