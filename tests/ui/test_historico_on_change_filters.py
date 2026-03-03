from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock
import importlib
import sys
import types


if "app.ui.patterns" not in sys.modules:
    sys.modules["app.ui.patterns"] = types.SimpleNamespace(status_badge=lambda value: value)
if "app.ui.notification_service" not in sys.modules:
    sys.modules["app.ui.notification_service"] = types.SimpleNamespace(OperationFeedback=object)


historico_actions = importlib.import_module("app.ui.vistas.historico_actions")


class _FakeDate:
    def __init__(self, value: int) -> None:
        self.value = value

    def isValid(self) -> bool:  # noqa: N802
        return True

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, _FakeDate):
            return NotImplemented
        return self.value > other.value


class _FakeDateEdit:
    def __init__(self, value: int) -> None:
        self._date = _FakeDate(value)
        self.setDate = Mock()

    def date(self) -> _FakeDate:
        return self._date


class _FakeTimer:
    def __init__(self) -> None:
        self.interval = -1
        self.pending = False

    def stop(self) -> None:
        self.pending = False

    def setInterval(self, interval: int) -> None:  # noqa: N802
        self.interval = interval

    def start(self) -> None:
        self.pending = True

    def flush(self, callback: Mock) -> None:
        if not self.pending:
            return
        self.pending = False
        callback()


def test_delegada_todas_envia_delegada_id_none() -> None:
    proxy_model = SimpleNamespace(set_filters=Mock(), set_estado_code=Mock())
    window = SimpleNamespace(
        _historico_period_filter_state=Mock(return_value=("RANGE", None, None)),
        historico_delegada_combo=SimpleNamespace(currentIndex=Mock(return_value=0), currentData=Mock(return_value=44)),
        historico_desde_date=_FakeDateEdit(1),
        historico_hasta_date=_FakeDateEdit(2),
        historico_proxy_model=proxy_model,
        historico_estado_combo=SimpleNamespace(currentData=Mock(return_value=None)),
        _settings=SimpleNamespace(setValue=Mock()),
        _apply_historico_text_filter=Mock(),
        _update_historico_empty_state=Mock(),
    )

    historico_actions.apply_historico_filters(window)

    proxy_model.set_filters.assert_called_once_with(
        delegada_id=None,
        ver_todas=True,
        year_mode="RANGE",
        year=None,
        month=None,
        date_from=window.historico_desde_date.date(),
        date_to=window.historico_hasta_date.date(),
    )


def test_busqueda_debounce_dispara_una_sola_aplicacion() -> None:
    timer = _FakeTimer()
    window = SimpleNamespace(
        _historico_refresh_timer=timer,
        _aplicar_filtros_historico=Mock(),
    )
    window._schedule_historico_refresh = lambda delay: historico_actions.schedule_historico_refresh(window, delay)

    historico_actions.on_historico_search_changed(window, "d")
    historico_actions.on_historico_search_changed(window, "de")
    historico_actions.on_historico_search_changed(window, "del")

    assert timer.interval == 300
    timer.flush(window._aplicar_filtros_historico)

    window._aplicar_filtros_historico.assert_called_once_with()
