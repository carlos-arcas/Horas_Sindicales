from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


def _instalar_stub_pyside6() -> None:
    qtcore = ModuleType("PySide6.QtCore")
    qtcore.QDate = SimpleNamespace(currentDate=lambda: None)
    qtcore.QItemSelectionModel = SimpleNamespace(SelectionFlag=SimpleNamespace(Select=1, Deselect=2, Rows=4))
    qtcore.QTimer = SimpleNamespace(singleShot=lambda _delay, fn: fn())

    qtwidgets = ModuleType("PySide6.QtWidgets")
    qtwidgets.QAbstractItemView = SimpleNamespace(ScrollHint=SimpleNamespace(PositionAtCenter=1))
    qtwidgets.QDialog = object
    qtwidgets.QMessageBox = SimpleNamespace(information=Mock())

    pyside6 = ModuleType("PySide6")
    pyside6.QtCore = qtcore
    pyside6.QtWidgets = qtwidgets

    sys.modules.setdefault("PySide6", pyside6)
    sys.modules.setdefault("PySide6.QtCore", qtcore)
    sys.modules.setdefault("PySide6.QtWidgets", qtwidgets)


def _window_stub() -> SimpleNamespace:
    return SimpleNamespace(
        historico_periodo_anual_radio=SimpleNamespace(isChecked=Mock(return_value=False), setChecked=Mock()),
        historico_periodo_mes_radio=SimpleNamespace(isChecked=Mock(return_value=False), setChecked=Mock()),
        historico_periodo_rango_radio=SimpleNamespace(isChecked=Mock(return_value=True), setChecked=Mock()),
        historico_periodo_anual_spin=SimpleNamespace(setEnabled=Mock()),
        historico_periodo_mes_ano_spin=SimpleNamespace(setEnabled=Mock()),
        historico_periodo_mes_combo=SimpleNamespace(setEnabled=Mock()),
        historico_desde_date=SimpleNamespace(setEnabled=Mock()),
        historico_hasta_date=SimpleNamespace(setEnabled=Mock()),
        _apply_historico_filters=Mock(),
    )


def test_on_historico_periodo_mode_changed_acepta_payload_sin_lanzar() -> None:
    _instalar_stub_pyside6()
    historico_actions = importlib.import_module("app.ui.vistas.historico_actions")
    window = _window_stub()

    historico_actions.on_historico_periodo_mode_changed(window, True)

    window._apply_historico_filters.assert_called_once_with()
