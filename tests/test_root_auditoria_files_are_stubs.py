from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_auditoria_md_es_stub() -> None:
    ruta = ROOT / "AUDITORIA.md"
    assert ruta.exists()

    contenido = ruta.read_text(encoding="utf-8")
    contenido_lower = contenido.lower()

    assert "stub" in contenido_lower
    assert "deprecado" in contenido_lower
    assert "auditor e2e" in contenido_lower

    assert "scorecard" not in contenido_lower
    assert "hallazgos" not in contenido_lower
    assert "backlog" not in contenido_lower


def test_root_auditoria_json_es_stub() -> None:
    ruta = ROOT / "auditoria.json"
    assert ruta.exists()

    payload = json.loads(ruta.read_text(encoding="utf-8"))

    assert payload["stub"] is True
    assert payload["manual"] is False
    assert "mensaje" in payload
    assert "comando_generacion" in payload
    assert "ruta_salida" in payload

    assert "scorecard" not in payload
    assert "hallazgos" not in payload
    assert "backlog" not in payload
