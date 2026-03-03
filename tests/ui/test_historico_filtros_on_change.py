from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


def _import_historico_actions():
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
    return importlib.import_module("app.ui.vistas.historico_actions")


class _FakeTimer:
    def __init__(self, callback):
        self._callback = callback
        self.started_with: list[int] = []

    def start(self, interval: int) -> None:
        self.started_with.append(interval)

    def fire(self) -> None:
        self._callback()


def test_delegada_todas_resuelve_none() -> None:
    historico_actions = _import_historico_actions()
    window = SimpleNamespace(
        _historico_period_filter_state=Mock(return_value=("RANGE", None, None)),
        historico_delegada_combo=SimpleNamespace(currentData=Mock(return_value=None)),
        historico_desde_date=SimpleNamespace(date=Mock(return_value=object())),
        historico_hasta_date=SimpleNamespace(date=Mock(return_value=object())),
    )

    filtro = historico_actions.build_historico_filters(window)

    assert filtro["delegada_id"] is None


def test_debounce_buscar_dispara_una_vez() -> None:
    historico_actions = _import_historico_actions()
    apply_filters = Mock()
    timer = _FakeTimer(apply_filters)
    window = SimpleNamespace(_historico_filtro_timer=timer)

    historico_actions.on_historico_search_text_changed(window, "a")
    historico_actions.on_historico_search_text_changed(window, "ab")
    historico_actions.on_historico_search_text_changed(window, "abc")
    timer.fire()

    assert timer.started_with == [300, 300, 300]
    apply_filters.assert_called_once_with()
