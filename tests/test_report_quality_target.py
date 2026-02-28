from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from scripts.report_quality import _target_complexity

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "report_quality.py"
TARGET = "app/ui/vistas/confirmacion_actions.py:iterar_pendientes_en_tabla"


def test_report_quality_target_argument_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--target", TARGET, "--top", "1", "--out", "logs/quality_report_target.txt"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "## Complejidad target" in result.stdout
    assert TARGET in result.stdout


def test_report_quality_target_invalid_argument_returns_error() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--target", "target_invalido"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "ERROR:" in result.stdout


@pytest.mark.metrics
def test_report_quality_target_budget_with_radon() -> None:
    pytest.importorskip("radon", reason="Control de CC real requiere radon.", exc_type=ImportError)

    note, identifier, complexity = _target_complexity(TARGET)

    assert note == "radon disponible"
    assert identifier == TARGET
    assert complexity <= 12, f"{TARGET} excede CC límite: {complexity} > 12"
