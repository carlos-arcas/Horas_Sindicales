from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _ejecutar_script(repo_root: Path) -> None:
    subprocess.run(
        [sys.executable, "scripts/migrar_ui_strings_baseline.py"],
        cwd=repo_root,
        check=True,
    )


def test_migracion_genera_claves_estables_e_idempotentes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".config").mkdir(parents=True)

    origen = Path("scripts/migrar_ui_strings_baseline.py").read_text(encoding="utf-8")
    (repo / "scripts/migrar_ui_strings_baseline.py").write_text(origen, encoding="utf-8")
    baseline = {
        "offenders": [
            "app/ui/controllers/sync_controller.py:88:Sin configuración",
            "app/ui/controllers/sync_controller.py:71:Sin plan",
        ]
    }
    (repo / ".config/ui_strings_baseline.json").write_text(json.dumps(baseline), encoding="utf-8")

    _ejecutar_script(repo)
    es_primero = (repo / "configuracion/i18n/es.json").read_text(encoding="utf-8")
    map_primero = (repo / "configuracion/i18n/_legacy_map.json").read_text(encoding="utf-8")

    _ejecutar_script(repo)
    es_segundo = (repo / "configuracion/i18n/es.json").read_text(encoding="utf-8")
    map_segundo = (repo / "configuracion/i18n/_legacy_map.json").read_text(encoding="utf-8")

    assert es_primero == es_segundo
    assert map_primero == map_segundo

    es_catalogo = json.loads(es_primero)
    assert all(":88:" not in k and ":71:" not in k for k in es_catalogo)
    assert all(k.startswith("ui.app.sync_controller.") for k in es_catalogo)
