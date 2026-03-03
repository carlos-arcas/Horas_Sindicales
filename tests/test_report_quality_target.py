from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from scripts.report_quality import _evaluate_config_targets, _target_complexity

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "report_quality.py"
TARGET = "app/ui/vistas/confirmacion_actions.py:iterar_pendientes_en_tabla"
TARGET_CONFIRMAR_PDF = (
    "app/application/use_cases/confirmacion_pdf/caso_uso.py:"
    "ConfirmarPendientesPdfCasoUso.execute"
)


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


def test_evaluate_config_targets_falla_si_target_supera_budget() -> None:
    cc_targets = {TARGET_CONFIRMAR_PDF: 20}

    def _fake_complexity_resolver(target_identifier: str) -> tuple[str, str, int]:
        assert target_identifier == TARGET_CONFIRMAR_PDF
        return ("fake", target_identifier, 21)

    rows, has_failures = _evaluate_config_targets(cc_targets, _fake_complexity_resolver)

    assert rows == [(TARGET_CONFIRMAR_PDF, 21, 20, False)]
    assert has_failures is True


def test_evaluate_config_targets_pasa_con_budget_en_limite() -> None:
    cc_targets = {TARGET_CONFIRMAR_PDF: 20}

    def _fake_complexity_resolver(target_identifier: str) -> tuple[str, str, int]:
        return ("fake", target_identifier, 20)

    rows, has_failures = _evaluate_config_targets(cc_targets, _fake_complexity_resolver)

    assert rows == [(TARGET_CONFIRMAR_PDF, 20, 20, True)]
    assert has_failures is False


@pytest.mark.metrics
def test_report_quality_target_budget_with_radon() -> None:
    pytest.importorskip("radon", reason="Control de CC real requiere radon.", exc_type=ImportError)

    note, identifier, complexity = _target_complexity(TARGET)

    assert note == "radon disponible"
    assert identifier == TARGET
    assert complexity <= 12, f"{TARGET} excede CC límite: {complexity} > 12"
