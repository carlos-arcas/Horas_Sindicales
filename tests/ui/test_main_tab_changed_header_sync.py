from __future__ import annotations

import pytest

from tests.ui.conftest import require_qt

require_qt()

from app.ui.vistas.main_window import TAB_HISTORICO
from app.ui.vistas.main_window.state_controller import MainWindow


class _Header:
    def __init__(self, texto: str) -> None:
        self._texto = texto

    def text(self) -> str:
        return self._texto

    def setText(self, texto: str) -> None:
        self._texto = texto


class _FakeDate:
    def isValid(self) -> bool:
        return True


class _DateControl:
    def date(self) -> _FakeDate:
        return _FakeDate()


class _DummyWindow:
    def __init__(self) -> None:
        self._active_sidebar_index = 1
        self.header_title_label = _Header("Solicitudes")
        self.historico_desde_date = _DateControl()
        self.historico_hasta_date = _DateControl()
        self.historico_refresh_calls = 0

    def _refresh_header_title(self) -> None:
        if self._active_sidebar_index == 2:
            self.header_title_label.setText("Histórico")

    def _current_persona(self):
        return None

    def _restore_draft_for_persona(self, _persona_id):
        return None

    @property
    def fecha_input(self):
        return type("_Focus", (), {"setFocus": lambda self: None})()

    def _apply_historico_last_30_days(self) -> None:
        pytest.fail("No debe recalcular rango si fechas son válidas")

    def _refresh_historico(self, *, force: bool = False) -> None:
        _ = force
        self.historico_refresh_calls += 1

    def _refresh_saldos(self) -> None:
        return None


@pytest.mark.ui
def test_on_main_tab_changed_actualiza_header_desde_tab() -> None:
    window = _DummyWindow()

    MainWindow._on_main_tab_changed(window, TAB_HISTORICO)

    assert window._active_sidebar_index == 2
    assert window.header_title_label.text() == "Histórico"
    assert window.historico_refresh_calls == 1
