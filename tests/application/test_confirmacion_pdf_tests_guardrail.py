from __future__ import annotations

from pathlib import Path


def test_no_hay_acceso_privado_a_coordinador_confirmacion_pdf_desde_tests() -> None:
    raiz_tests = Path("tests")
    violaciones: list[str] = []
    permitidos = {
        Path("tests/application/test_confirmacion_pdf_superficie_publica_guardrail.py"),
    }

    patron_prohibido = "._coordinador_" + "confirmacion_pdf"

    for ruta in raiz_tests.rglob("test_*.py"):
        contenido = ruta.read_text(encoding="utf-8")
        if patron_prohibido not in contenido or ruta in permitidos:
            continue
        violaciones.append(str(ruta))

    assert violaciones == [], (
        "No se permite usar el atajo privado patrón privado del coordinador en tests. "
        f"Archivos con violación: {violaciones}"
    )
