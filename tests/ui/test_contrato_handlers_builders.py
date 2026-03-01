from __future__ import annotations

import re
from pathlib import Path


BUILDERS = (
    "app/ui/vistas/builders/builders_formulario_solicitud.py",
    "app/ui/vistas/builders/builders_tablas.py",
    "app/ui/vistas/builders/builders_sync_panel.py",
    "app/ui/vistas/builders/builders_barra_superior.py",
)
STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
WINDOW_HANDLER_PATTERN = re.compile(r"window\.(?P<name>_[A-Za-z0-9_]+)")


def test_builders_solo_referencian_handlers_existentes_en_main_window() -> None:
    codigo_main_window = STATE_CONTROLLER.read_text(encoding="utf-8")
    handlers_referenciados: set[str] = set()

    for builder in BUILDERS:
        codigo_builder = Path(builder).read_text(encoding="utf-8")
        handlers_referenciados.update(
            match.group("name")
            for match in WINDOW_HANDLER_PATTERN.finditer(codigo_builder)
            if match.group("name").startswith("_")
        )

    faltantes = [
        handler
        for handler in sorted(handlers_referenciados)
        if f"def {handler}(" not in codigo_main_window
    ]

    assert not faltantes, f"Handlers faltantes en MainWindow: {', '.join(faltantes)}"
