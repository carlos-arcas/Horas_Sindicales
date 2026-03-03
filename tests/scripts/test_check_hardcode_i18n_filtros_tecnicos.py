from __future__ import annotations

from pathlib import Path

from scripts.i18n.check_hardcode_i18n import ConfigCheck, analizar_rutas


def _crear_archivo(base: Path, ruta: str, contenido: str) -> None:
    archivo = base / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido, encoding="utf-8")


def _hallazgos_para_literal(tmp_path: Path, literal: str):
    _crear_archivo(
        tmp_path,
        "app/ui/visibilidad.py",
        f'def render():\n    return "{literal}"\n',
    )
    return analizar_rutas([tmp_path / "app" / "ui"], ConfigCheck())


def test_filtros_tecnicos_i18n_hardcode(tmp_path: Path) -> None:
    casos = {
        "No se puede añadir la solicitud.": True,
        "Revisa el formulario": True,
        "id": False,
        "setEnabled": False,
        "sync_button": False,
        "ui.solicitudes.no_puede_aniadir": False,
        "-": False,
        "#AABBCC": False,
        "HH:MM": False,
    }

    for literal, esperado_reportado in casos.items():
        hallazgos = _hallazgos_para_literal(tmp_path, literal)
        if esperado_reportado:
            assert len(hallazgos) == 1
            assert hallazgos[0].texto == literal
        else:
            assert hallazgos == []
