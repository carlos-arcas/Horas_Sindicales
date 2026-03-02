from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.ui
@pytest.mark.smoke
def test_ui_thread_parent_warning_smoke() -> None:
    script_path = Path("scripts/ui_main_window_smoke.py")

    resultado = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    diagnostico = (
        "Smoke UI de thread-parent falló.\n"
        f"returncode={resultado.returncode}\n"
        f"stdout:\n{resultado.stdout}\n"
        f"stderr:\n{resultado.stderr}"
    )
    assert resultado.returncode == 0, diagnostico
