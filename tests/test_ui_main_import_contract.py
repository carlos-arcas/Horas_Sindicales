from __future__ import annotations

import subprocess
import sys


def test_import_ui_main_no_carga_pyside6() -> None:
    comando = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "import app.entrypoints.ui_main; "
            "assert not any(nombre.startswith('PySide6') for nombre in sys.modules)"
        ),
    ]

    resultado = subprocess.run(comando, capture_output=True, text=True, check=False)

    assert resultado.returncode == 0, resultado.stderr
