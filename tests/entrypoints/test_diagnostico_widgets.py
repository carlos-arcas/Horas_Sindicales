from __future__ import annotations

from app.entrypoints.diagnostico_widgets import (
    construir_info_top_level_widgets,
    hay_ventana_visible,
)


class _WidgetStub:
    def __init__(
        self,
        *,
        object_name: str,
        window_title: str,
        visible: bool,
        hidden: bool,
        is_window: bool,
    ) -> None:
        self._object_name = object_name
        self._window_title = window_title
        self._visible = visible
        self._hidden = hidden
        self._is_window = is_window

    def objectName(self) -> str:
        return self._object_name

    def windowTitle(self) -> str:
        return self._window_title

    def isVisible(self) -> bool:
        return self._visible

    def isHidden(self) -> bool:
        return self._hidden

    def isWindow(self) -> bool:
        return self._is_window


def test_hay_ventana_visible_cubre_vacio_visible_y_no_visible() -> None:
    assert hay_ventana_visible([]) is False
    assert hay_ventana_visible([{"is_visible": True}]) is True
    assert (
        hay_ventana_visible([{"is_visible": False}, {"is_visible": False}]) is False
    )


def test_construir_info_top_level_widgets_genera_payload_esperado() -> None:
    widgets = [
        _WidgetStub(
            object_name="main_window",
            window_title="Horas Sindicales",
            visible=True,
            hidden=False,
            is_window=True,
        )
    ]

    payload = construir_info_top_level_widgets(widgets)

    assert payload == [
        {
            "clase": "_WidgetStub",
            "object_name": "main_window",
            "window_title": "Horas Sindicales",
            "is_visible": True,
            "is_hidden": False,
            "is_window": True,
        }
    ]
