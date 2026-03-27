from __future__ import annotations

from pathlib import Path


def test_builder_solicitud_oculta_panel_estado_operativo() -> None:
    source = Path("app/ui/vistas/builders/formulario_solicitud/builders_solicitud.py").read_text(encoding="utf-8")

    assert "window.solicitudes_status_panel.setVisible(False)" in source
    assert "solicitud_layout.addWidget(window.solicitudes_status_panel)" in source
