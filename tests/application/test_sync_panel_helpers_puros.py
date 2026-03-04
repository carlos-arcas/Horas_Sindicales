from app.ui.vistas.builders.sync_panel.ayudantes_puros import claves_columnas_salud


def test_claves_columnas_salud_en_orden_estable() -> None:
    assert claves_columnas_salud() == [
        "ui.sync.estado",
        "ui.sync.columna_categoria",
        "ui.sync.columna_mensaje",
        "ui.sync.columna_accion",
    ]
