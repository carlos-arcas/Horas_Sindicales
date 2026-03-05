from __future__ import annotations

import json

from scripts.diagnosticar_pytest_255 import (
    recortar_primeras_lineas,
    serializar_resumen_json,
)


def test_recortar_primeras_lineas_limita_a_maximo() -> None:
    texto = "\n".join(f"linea-{indice}" for indice in range(300))

    lineas = recortar_primeras_lineas(texto, max_lineas=5)

    assert lineas == [
        "linea-0",
        "linea-1",
        "linea-2",
        "linea-3",
        "linea-4",
    ]


def test_serializar_resumen_json_emite_json_esperado() -> None:
    resumen = {
        "returncode": 255,
        "first_200_lines_stdout": ["ok"],
        "first_200_lines_stderr": ["boom"],
        "platform": "linux",
        "python_version": "3.x",
    }

    serializado = serializar_resumen_json(resumen)

    data = json.loads(serializado)
    assert data == resumen
