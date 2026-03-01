from __future__ import annotations

import importlib.util
from pathlib import Path

_HEADER_STATE_PATH = Path(__file__).resolve().parents[2] / "app" / "ui" / "vistas" / "main_window" / "header_state.py"
_spec = importlib.util.spec_from_file_location("_header_state_test_module", _HEADER_STATE_PATH)
assert _spec is not None and _spec.loader is not None
_header_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_header_state)
resolve_section_title = _header_state.resolve_section_title
resolve_sidebar_tab_index = _header_state.resolve_sidebar_tab_index


class _FakeTabs:
    def __init__(self, index: int) -> None:
        self._index = index
        self.set_calls = 0

    def currentIndex(self) -> int:
        return self._index

    def setCurrentIndex(self, index: int) -> None:
        self._index = index
        self.set_calls += 1


class _DummyHeader:
    def __init__(self, text: str = "") -> None:
        self._text = text
        self.set_calls = 0

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text
        self.set_calls += 1


def _switch_sidebar_page(window, index: int) -> None:
    target_tab_index = resolve_sidebar_tab_index(index)
    if target_tab_index is None and index != 0:
        return

    window._active_sidebar_index = index

    if target_tab_index is not None and window.main_tabs.currentIndex() != target_tab_index:
        window.main_tabs.setCurrentIndex(target_tab_index)

    title = resolve_section_title(window._active_sidebar_index)
    if window.header_title_label.text() != title:
        window.header_title_label.setText(title)


def test_resolve_section_title_usa_estado_actual() -> None:
    assert resolve_section_title(1) == "Solicitudes"
    assert resolve_section_title(2) == "Histórico"
    assert resolve_section_title(3) == "Configuración"


def test_switch_sidebar_actualiza_una_sola_vez_header_y_tab() -> None:
    window = type("DummyWindow", (), {})()
    window.main_tabs = _FakeTabs(index=0)
    window.header_title_label = _DummyHeader(text="Solicitudes")
    window._active_sidebar_index = 1

    _switch_sidebar_page(window, 2)

    assert window._active_sidebar_index == 2
    assert window.main_tabs.currentIndex() == 1
    assert window.main_tabs.set_calls == 1
    assert window.header_title_label.text() == "Histórico"
    assert window.header_title_label.set_calls == 1
