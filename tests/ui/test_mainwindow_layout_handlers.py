from __future__ import annotations

import pytest

handlers_layout = pytest.importorskip(
    "app.ui.vistas.main_window.handlers_layout",
    reason="Entorno sin librerías Qt requeridas por el paquete main_window.",
    exc_type=ImportError,
)


class _WindowSinWidgets:
    pass


class _WindowConTabOrder:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object]] = []
        self.persona_combo = object()
        self.fecha_input = object()

    def setTabOrder(self, before: object, after: object) -> None:
        self.calls.append((before, after))


def test_configure_time_placeholders_no_lanza_si_faltan_widgets() -> None:
    handlers_layout.configure_time_placeholders(_WindowSinWidgets())


def test_configure_operativa_focus_order_aplica_solo_pares_disponibles() -> None:
    window = _WindowConTabOrder()

    handlers_layout.configure_operativa_focus_order(window)

    assert len(window.calls) == 1
    assert window.calls[0] == (window.persona_combo, window.fecha_input)
