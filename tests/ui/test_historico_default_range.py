from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

historico_actions = pytest.importorskip("app.ui.vistas.historico_actions", exc_type=ImportError)
state_historico = pytest.importorskip("app.ui.vistas.main_window.state_historico", exc_type=ImportError)


def _window_stub() -> SimpleNamespace:
    return SimpleNamespace(
        historico_desde_date=SimpleNamespace(setDate=Mock()),
        historico_hasta_date=SimpleNamespace(setDate=Mock()),
        historico_periodo_rango_radio=SimpleNamespace(setChecked=Mock()),
        historico_proxy_model=object(),
        _apply_historico_filters=Mock(),
    )


def test_apply_historico_default_range_activa_rango_y_refresca_filtros() -> None:
    window = _window_stub()

    historico_actions.apply_historico_default_range(window)

    assert window.historico_desde_date.setDate.call_count == 1
    assert window.historico_hasta_date.setDate.call_count == 1
    window.historico_periodo_rango_radio.setChecked.assert_called_once_with(True)
    window._apply_historico_filters.assert_called_once_with()


def test_state_historico_rango_por_defecto_refresca_filtros() -> None:
    window = _window_stub()

    state_historico.aplicar_rango_por_defecto_historico(window)

    assert window.historico_desde_date.setDate.call_count == 1
    assert window.historico_hasta_date.setDate.call_count == 1
    window.historico_periodo_rango_radio.setChecked.assert_called_once_with(True)
    window._apply_historico_filters.assert_called_once_with()
