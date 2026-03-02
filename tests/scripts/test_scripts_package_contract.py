from __future__ import annotations

import importlib
from pathlib import Path

from scripts import quality_gate


def test_import_i18n_checker_without_sys_path_hack() -> None:
    modulo = importlib.import_module("scripts.i18n.check_hardcode_i18n")
    assert hasattr(modulo, "analizar_rutas")


def test_quality_gate_i18n_guard_falla_con_hardcode(monkeypatch, tmp_path: Path) -> None:
    archivo = tmp_path / "presentacion" / "pantalla.py"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text('def build():\n    return "Texto duro"\n', encoding="utf-8")

    monkeypatch.setattr(quality_gate, "ROOT", tmp_path)

    result = quality_gate.run_i18n_hardcode_guard(config={}, records=[])

    assert result["status"] == "FAIL"
    assert result["total_hallazgos"] >= 1
