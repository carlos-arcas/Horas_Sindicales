from __future__ import annotations

from scripts import auditar_ui_strings


def test_main_window_no_new_hardcoded_strings() -> None:
    reporte = auditar_ui_strings.auditar_scope("main_window")

    assert reporte["scope"] == "main_window"
    assert reporte["estado"] == "PASS", (
        "Se detectaron strings hardcodeadas en módulos nuevos de main_window/. "
        "Mueve los textos de UI a app/ui/copy_catalog.py y referencia con copy_text()."
    )
