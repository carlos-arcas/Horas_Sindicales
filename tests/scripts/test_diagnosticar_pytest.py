from __future__ import annotations

import json

from scripts.diagnosticar_pytest import (
    construir_resultado_json,
    serializar_resultado_json,
)


def test_serializar_resultado_json_incluye_estructura_y_claves() -> None:
    resumen = construir_resultado_json(
        returncode=255,
        cmd=["python", "-X", "faulthandler", "-m", "pytest", "-q", "-m", "not ui"],
        stdout="ok\nrun",
        stderr="boom\ntrace",
        head=1,
        tail=1,
    )

    serializado = serializar_resultado_json(resumen)
    data = json.loads(serializado)

    assert set(data) == {
        "returncode",
        "returncode_hex",
        "cmd",
        "python",
        "platform",
        "stdout_head",
        "stdout_tail",
        "stderr_head",
        "stderr_tail",
    }
    assert data["returncode"] == 255
    assert data["stdout_head"] == ["ok"]
    assert data["stdout_tail"] == ["run"]
    assert data["stderr_head"] == ["boom"]
    assert data["stderr_tail"] == ["trace"]
