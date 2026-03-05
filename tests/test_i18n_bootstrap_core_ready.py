from __future__ import annotations

import json
from pathlib import Path


def test_bootstrap_core_ready_existe_en_es_y_en() -> None:
    catalogo_es = json.loads(Path("configuracion/i18n/es.json").read_text(encoding="utf-8"))
    catalogo_en = json.loads(Path("configuracion/i18n/en.json").read_text(encoding="utf-8"))

    assert catalogo_es.get("bootstrap.core_ready")
    assert catalogo_en.get("bootstrap.core_ready")
