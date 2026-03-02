from __future__ import annotations

import json
from pathlib import Path

from scripts.i18n.check_hardcode_i18n import (
    ConfigCheck,
    analizar_rutas,
    cargar_baseline,
    escribir_baseline,
    filtrar_nuevos,
)


def _crear_archivo(base: Path, ruta: str, contenido: str) -> None:
    archivo = base / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido, encoding="utf-8")


def test_baseline_i18n_incremental(tmp_path: Path) -> None:
    ruta_archivo = "app/ui/pantalla.py"
    _crear_archivo(
        tmp_path,
        ruta_archivo,
        'def render():\n    return "Texto inicial"\n',
    )

    hallazgos_iniciales = analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())
    assert len(hallazgos_iniciales) == 1

    baseline_path = tmp_path / ".config" / "i18n_hardcode_baseline.json"
    escribir_baseline(baseline_path, hallazgos_iniciales)

    baseline_ids = cargar_baseline(baseline_path)
    hallazgos_mismo_estado = analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())
    nuevos_mismo_estado = filtrar_nuevos(hallazgos_mismo_estado, baseline_ids)
    assert nuevos_mismo_estado == []

    _crear_archivo(
        tmp_path,
        ruta_archivo,
        'def render():\n    return "Texto inicial"\n\n\ndef extra():\n    return "Texto nuevo"\n',
    )
    hallazgos_actualizados = analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())
    nuevos = filtrar_nuevos(hallazgos_actualizados, baseline_ids)
    assert len(nuevos) == 1
    assert nuevos[0].texto == "Texto nuevo"


def test_baseline_ordenada_y_reproducible(tmp_path: Path) -> None:
    _crear_archivo(tmp_path, "app/ui/z.py", 'def zeta():\n    return "Zeta"\n')
    _crear_archivo(tmp_path, "app/ui/a.py", 'def alfa():\n    return "Alfa"\n')

    hallazgos = analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())
    baseline_path = tmp_path / ".config" / "i18n_hardcode_baseline.json"

    escribir_baseline(baseline_path, hallazgos)
    primera = baseline_path.read_text(encoding="utf-8")
    escribir_baseline(baseline_path, hallazgos)
    segunda = baseline_path.read_text(encoding="utf-8")

    assert primera == segunda

    payload = json.loads(primera)
    entries = payload["entries"]
    assert entries == sorted(entries, key=lambda item: (item["ruta"], item["texto"], item["id"]))
