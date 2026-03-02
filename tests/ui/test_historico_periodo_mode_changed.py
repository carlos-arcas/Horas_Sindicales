from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from app.ui.vistas import historico_actions


class _Control:
    def __init__(self, checked: bool = False) -> None:
        self._checked = checked
        self.enabled = False

    def isChecked(self) -> bool:
        return self._checked

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled


class _WindowHistorico:
    def __init__(self) -> None:
        self.historico_periodo_anual_radio = _Control(checked=False)
        self.historico_periodo_mes_radio = _Control(checked=True)
        self.historico_periodo_rango_radio = _Control(checked=False)
        self.historico_periodo_anual_spin = _Control()
        self.historico_periodo_mes_ano_spin = _Control()
        self.historico_periodo_mes_combo = _Control()
        self.historico_desde_date = _Control()
        self.historico_hasta_date = _Control()


def test_on_historico_periodo_mode_changed_acepta_bool_emitido_por_signal() -> None:
    window = _WindowHistorico()

    historico_actions.on_historico_periodo_mode_changed(window, True)

    assert window.historico_periodo_anual_spin.enabled is False
    assert window.historico_periodo_mes_ano_spin.enabled is True
    assert window.historico_periodo_mes_combo.enabled is True
    assert window.historico_desde_date.enabled is False
    assert window.historico_hasta_date.enabled is False


def test_on_historico_periodo_mode_changed_soporta_invocacion_programatica() -> None:
    window = _WindowHistorico()

    historico_actions.on_historico_periodo_mode_changed(window)

    assert window.historico_periodo_mes_ano_spin.enabled is True
