from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_auditoria_md_es_stub() -> None:
    ruta = ROOT / "AUDITORIA.md"
    assert ruta.exists()
    contenido = ruta.read_text(encoding="utf-8")
    assert "Generado por Auditor E2E" in contenido or "stub" in contenido.lower()
    assert contenido.count("\n") <= 30


def test_root_auditoria_json_es_stub() -> None:
    ruta = ROOT / "auditoria.json"
    assert ruta.exists()
    contenido = ruta.read_text(encoding="utf-8")
    assert "Generado por Auditor E2E" in contenido or "stub" in contenido.lower()
    assert len(contenido) < 1200
