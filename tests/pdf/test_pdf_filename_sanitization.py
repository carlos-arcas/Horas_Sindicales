from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.models import Persona
from app.pdf.pdf_builder import build_nombre_archivo, construir_pdf_solicitudes


def _persona() -> Persona:
    return Persona(
        id=1,
        nombre="Ana",
        genero="F",
        horas_mes_min=600,
        horas_ano_min=7200,
        is_active=True,
        cuad_lun_man_min=0,
        cuad_lun_tar_min=0,
        cuad_mar_man_min=0,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=0,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=0,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=0,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


def test_nombre_con_barras_no_contiene_separadores_ni_path_traversal() -> None:
    nombre = build_nombre_archivo("Ana/../Pepe", ["2025-01-01"])
    assert "/" not in nombre
    assert "\\" not in nombre
    assert ".." not in nombre


def test_nombre_con_caracteres_windows_invalidos_se_limpia() -> None:
    nombre = build_nombre_archivo('A<>:"/\\|?*B', ["2025-01-01"])
    assert "(A" in nombre and "B)" in nombre
    for invalido in '<>:"/\\|?*':
        assert invalido not in nombre


def test_nombre_con_unicode_fullwidth_se_normaliza() -> None:
    nombre = build_nombre_archivo("Ａｎａ＿Ｌóｐｅｚ", ["2025-01-01"])
    assert "(Ana_López)" in nombre


def test_nombre_vacio_o_simbolos_devuelve_sin_nombre() -> None:
    nombre = build_nombre_archivo("...***___", ["2025-01-01"])
    assert "(SIN_NOMBRE)" in nombre


def test_nombre_extremo_se_trunca_a_80_mas_extension_pdf() -> None:
    nombre = build_nombre_archivo("A" * 300, ["2025-01-01"])
    base = nombre.removesuffix(".pdf")
    nombre_persona = base.split("(")[1].split(")")[0]
    assert len(nombre_persona) == 80
    assert nombre.endswith(".pdf")


def test_build_nombre_archivo_siempre_termina_en_pdf() -> None:
    nombre = build_nombre_archivo("Ana", ["2025-01-01"])
    assert nombre.endswith(".pdf")


def test_build_nombre_archivo_no_es_absoluto_ni_contiene_separadores() -> None:
    nombre = build_nombre_archivo("Ana", ["2025-01-01"])
    assert not Path(nombre).is_absolute()
    assert "/" not in nombre
    assert "\\" not in nombre


def test_construir_pdf_rechaza_destino_con_traversal() -> None:
    persona = _persona()
    with pytest.raises(ValueError):
        construir_pdf_solicitudes([object()], persona, Path("../salida.pdf"))
