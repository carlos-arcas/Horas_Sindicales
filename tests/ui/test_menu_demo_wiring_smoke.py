from __future__ import annotations

from pathlib import Path


def test_menu_demo_wiring_declara_accion_en_entrypoint() -> None:
    contenido = Path("app/entrypoints/ui_main.py").read_text(encoding="utf-8")

    assert "menu_cargar_demo" in contenido
    assert "cargar_datos_demo_caso_uso" in contenido
