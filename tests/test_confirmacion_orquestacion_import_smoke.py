from __future__ import annotations

import subprocess
import sys


def test_import_confirmacion_orquestacion_no_name_error() -> None:
    comando = [
        sys.executable,
        "-c",
        "import app.ui.vistas.confirmacion_orquestacion",
    ]

    resultado = subprocess.run(comando, capture_output=True, text=True, check=False)

    assert resultado.returncode == 0, resultado.stderr
