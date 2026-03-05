from __future__ import annotations

import subprocess
import sys


def test_main_window_exporta_tab_historico() -> None:
    comando = [
        sys.executable,
        "-c",
        (
            "import sys, types;"
            "dummy=type('Dummy',(),{});"
            "pyside6=types.ModuleType('PySide6');"
            "qtcore=types.ModuleType('PySide6.QtCore');"
            "qtgui=types.ModuleType('PySide6.QtGui');"
            "qtwidgets=types.ModuleType('PySide6.QtWidgets');"
            "qtcore.__getattr__=lambda name: dummy;"
            "qtgui.__getattr__=lambda name: dummy;"
            "qtwidgets.__getattr__=lambda name: dummy;"
            "sys.modules['PySide6']=pyside6;"
            "sys.modules['PySide6.QtCore']=qtcore;"
            "sys.modules['PySide6.QtGui']=qtgui;"
            "sys.modules['PySide6.QtWidgets']=qtwidgets;"
            "import app.ui.vistas.main_window as mw;"
            "assert hasattr(mw, 'TAB_HISTORICO')"
        ),
    ]

    resultado = subprocess.run(comando, capture_output=True, text=True, check=False)

    assert resultado.returncode == 0, resultado.stderr
