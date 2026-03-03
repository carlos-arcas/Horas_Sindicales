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


def test_literal_visible_se_reporta(tmp_path: Path) -> None:
    hallazgos = _hallazgos_para_literal(tmp_path, "No se puede añadir la solicitud.")

    assert len(hallazgos) == 1
    assert hallazgos[0].texto == "No se puede añadir la solicitud."


def test_identificador_simple_no_visible_se_ignora(tmp_path: Path) -> None:
    hallazgos = _hallazgos_para_literal(tmp_path, "id")

    assert hallazgos == []


def test_metodo_qt_no_visible_se_ignora(tmp_path: Path) -> None:
    hallazgos = _hallazgos_para_literal(tmp_path, "setEnabled")

    assert hallazgos == []


def test_clave_i18n_fuerte_no_visible_se_ignora(tmp_path: Path) -> None:
    hallazgos = _hallazgos_para_literal(tmp_path, "ui.solicitudes.no_puede_aniadir")

    assert hallazgos == []


def test_simbolo_corto_no_visible_se_ignora(tmp_path: Path) -> None:
    hallazgos = _hallazgos_para_literal(tmp_path, "-")

    assert hallazgos == []


def test_hh_mm_se_trata_como_tecnico_e_ignorado(tmp_path: Path) -> None:
    hallazgos = _hallazgos_para_literal(tmp_path, "HH:MM")

    assert hallazgos == []
