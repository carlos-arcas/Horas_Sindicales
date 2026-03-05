from __future__ import annotations

import json

from scripts.diagnosticar_pytest import (
    construir_resultado_json,
    recortar_primeras_lineas,
    serializar_resultado_json,
)


def test_recortar_primeras_lineas_limita_a_n() -> None:
    texto = "\n".join(f"linea-{indice}" for indice in range(50))

    resultado = recortar_primeras_lineas(texto, max_lineas=3)

    assert resultado == ["linea-0", "linea-1", "linea-2"]


def test_serializar_resultado_json_incluye_estructura_y_claves() -> None:
    resumen = construir_resultado_json(
        returncode=255,
        cmd=["pytest", "-q", "-m", "not ui"],
        stdout="ok\nrun",
        stderr="boom\ntrace",
        max_lineas=1,
    )

    serializado = serializar_resultado_json(resumen)
    data = json.loads(serializado)

    assert set(data) == {
        "returncode",
        "cmd",
        "python",
        "platform",
        "primeras_lineas_stdout",
        "primeras_lineas_stderr",
    }
    assert data["returncode"] == 255
    assert data["cmd"] == ["pytest", "-q", "-m", "not ui"]
    assert data["primeras_lineas_stdout"] == ["ok"]
    assert data["primeras_lineas_stderr"] == ["boom"]
