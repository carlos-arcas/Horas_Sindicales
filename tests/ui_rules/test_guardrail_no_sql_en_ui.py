from pathlib import Path


PATRONES_PROHIBIDOS = ("SELECT", ".execute(", "cursor(")
RUTAS_UI = (
    Path("app/ui/dialogos"),
    Path("app/ui/vistas"),
)


def test_no_sql_en_modulos_ui_historial_dialogos() -> None:
    archivos = [
        archivo
        for base in RUTAS_UI
        for archivo in base.rglob("*.py")
    ]
    hallazgos: list[str] = []
    for archivo in archivos:
        texto = archivo.read_text(encoding="utf-8")
        for patron in PATRONES_PROHIBIDOS:
            if patron in texto:
                hallazgos.append(f"{archivo}: {patron}")
    assert not hallazgos, "Se detectó SQL en UI:\n" + "\n".join(hallazgos)
