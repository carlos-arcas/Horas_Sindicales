from __future__ import annotations

from pathlib import Path


def test_builder_solicitud_colapsa_bloque_ayuda_y_no_renderiza_toggle_visible() -> None:
    source = Path("app/ui/vistas/builders/formulario_solicitud/builders_solicitud.py").read_text(encoding="utf-8")

    assert "solicitud_layout.addWidget(window.show_help_toggle)" not in source
    assert "window.show_help_toggle.setVisible(False)" in source
    assert "solicitud_layout.addLayout(tips_row)" not in source


def test_builder_barra_superior_ya_no_renderiza_texto_operativa_help() -> None:
    source = Path("app/ui/vistas/builders/builders_barra_superior.py").read_text(encoding="utf-8")

    assert "ui.solicitudes.operativa_help" not in source
