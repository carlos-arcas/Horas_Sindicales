from __future__ import annotations

from pathlib import Path


def test_no_colision_nombres_modulo_entre_ui_y_presentacion() -> None:
    raiz = Path(__file__).resolve().parent
    ui = {path.name for path in (raiz / "ui").glob("test_*.py")}
    presentacion = {path.name for path in (raiz / "presentacion").glob("test_*.py")}

    repetidos = sorted(ui.intersection(presentacion))

    assert repetidos == [], (
        "Nombres de módulo de test duplicados entre tests/ui y tests/presentacion: "
        f"{repetidos}."
    )
