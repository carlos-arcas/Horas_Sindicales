from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


def _import_historico_actions():
    qtcore = ModuleType("PySide6.QtCore")
    qtcore.QDate = SimpleNamespace(currentDate=lambda: None)
    qtcore.QItemSelectionModel = SimpleNamespace(
        SelectionFlag=SimpleNamespace(Select=1, Deselect=2, Rows=4)
    )
    qtcore.QTimer = SimpleNamespace(singleShot=lambda _delay, fn: fn())

    qtwidgets = ModuleType("PySide6.QtWidgets")
    qtwidgets.QAbstractItemView = SimpleNamespace(
        ScrollHint=SimpleNamespace(PositionAtCenter=1)
    )
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


def test_apply_historico_filters_actualiza_proxy_y_estado_vacio() -> None:
    historico_actions = _import_historico_actions()
    date_from = SimpleNamespace(isValid=lambda: True)
    date_to = SimpleNamespace(isValid=lambda: True)
    proxy = SimpleNamespace(set_filters=Mock(), set_estado_code=Mock())
    window = SimpleNamespace(
        _historico_period_filter_state=Mock(return_value=("RANGE", None, None)),
        historico_delegada_combo=SimpleNamespace(currentData=Mock(return_value=None)),
        historico_desde_date=SimpleNamespace(date=Mock(return_value=date_from)),
        historico_hasta_date=SimpleNamespace(date=Mock(return_value=date_to)),
        historico_estado_combo=SimpleNamespace(
            currentData=Mock(return_value="APROBADA")
        ),
        historico_proxy_model=proxy,
        _settings=SimpleNamespace(setValue=Mock()),
        _apply_historico_text_filter=Mock(),
        _update_historico_empty_state=Mock(),
    )

    historico_actions.apply_historico_filters(window)

    proxy.set_filters.assert_called_once_with(
        delegada_id=None,
        ver_todas=True,
        year_mode="RANGE",
        year=None,
        month=None,
        date_from=date_from,
        date_to=date_to,
    )
    proxy.set_estado_code.assert_called_once_with("APROBADA")
    window._settings.setValue.assert_called_once_with("historico/delegada", None)
    window._apply_historico_text_filter.assert_called_once_with()
    window._update_historico_empty_state.assert_called_once_with()


def test_on_historico_filter_changed_y_periodo_convergen_en_un_mismo_refresh() -> None:
    historico_actions = _import_historico_actions()
    apply_filters = Mock()
    window = SimpleNamespace(
        _apply_historico_filters=apply_filters,
        historico_periodo_anual_radio=SimpleNamespace(
            isChecked=Mock(return_value=False), setChecked=Mock()
        ),
        historico_periodo_mes_radio=SimpleNamespace(
            isChecked=Mock(return_value=False), setChecked=Mock()
        ),
        historico_periodo_rango_radio=SimpleNamespace(
            isChecked=Mock(return_value=True), setChecked=Mock()
        ),
        historico_periodo_anual_spin=SimpleNamespace(setEnabled=Mock()),
        historico_periodo_mes_ano_spin=SimpleNamespace(setEnabled=Mock()),
        historico_periodo_mes_combo=SimpleNamespace(setEnabled=Mock()),
        historico_desde_date=SimpleNamespace(setEnabled=Mock()),
        historico_hasta_date=SimpleNamespace(setEnabled=Mock()),
    )

    historico_actions.on_historico_filter_changed(window)
    historico_actions.on_historico_periodo_mode_changed(window)

    assert apply_filters.call_count == 2
