from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
TARGET = (
    "app/application/use_cases/confirmacion_pdf/caso_uso.py:"
    "ConfirmarPendientesPdfCasoUso.execute"
)


def test_ci_quality_gate_enforces_config_targets() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8", errors="ignore"
    )

    assert "python scripts/report_quality.py --enforce-config-targets --out logs/quality_report.txt" in workflow


def test_cc_target_budget_declared_for_confirmar_pendientes_pdf() -> None:
    quality_config = json.loads(
        (ROOT / ".config" / "quality_gate.json").read_text(encoding="utf-8", errors="ignore")
    )
    cc_targets = quality_config["cc_targets"]

    assert TARGET in cc_targets
    assert cc_targets[TARGET] == 20
