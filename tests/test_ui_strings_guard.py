from __future__ import annotations

import json
from pathlib import Path

from scripts.auditar_ui_strings import construir_reporte


RAIZ = Path(__file__).resolve().parents[1]
BASELINE = RAIZ / ".config" / "ui_strings_baseline.json"


def _cargar_baseline() -> set[str]:
    if not BASELINE.exists():
        raise AssertionError("Falta .config/ui_strings_baseline.json para controlar regresión de copy.")

    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    offenders = data.get("offenders", [])
    if not isinstance(offenders, list):
        raise AssertionError("La baseline de UI strings debe contener una lista 'offenders'.")

    return set(offenders)


def test_no_hay_nuevos_ui_strings_hardcoded() -> None:
    baseline = _cargar_baseline()
    reporte = construir_reporte(RAIZ)
    offenders_actuales = {item["offender_id"] for item in reporte["offenders"]}
    nuevos = sorted(offenders_actuales - baseline)

    assert not nuevos, (
        "Se detectaron nuevos strings hardcoded en app/ui.\n"
        + "\n".join(f"- {item}" for item in nuevos)
        + "\n\nSi es intencional, actualiza .config/ui_strings_baseline.json en este PR."
    )
