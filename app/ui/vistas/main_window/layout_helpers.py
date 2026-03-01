from __future__ import annotations

from typing import Iterable


_SINGLE_LINE_WIDGET_CLASS_NAMES = {
    "QComboBox",
    "QDateEdit",
    "QTimeEdit",
    "QLineEdit",
    "QSpinBox",
    "QDoubleSpinBox",
}
_MULTILINE_WIDGET_CLASS_NAMES = {"QTextEdit", "QPlainTextEdit"}
_INPUT_NAMES = ("persona_combo", "fecha_input", "desde_input", "hasta_input", "notas_input")


def _iter_present_widgets(window: object, names: Iterable[str]) -> list[object]:
    widgets: list[object] = []
    for name in names:
        widget = getattr(window, name, None)
        if widget is not None:
            widgets.append(widget)
    return widgets


def _safe_height_from_size_hint(widget: object) -> int | None:
    size_hint = getattr(widget, "sizeHint", None)
    if not callable(size_hint):
        return None
    hint = size_hint()
    height_getter = getattr(hint, "height", None)
    if not callable(height_getter):
        return None
    height = height_getter()
    if isinstance(height, int) and height > 0:
        return height
    return None


def _widget_class_name(widget: object) -> str:
    return type(widget).__name__


def normalize_input_heights(window: object) -> None:
    widgets = _iter_present_widgets(window, _INPUT_NAMES)
    heights = [height for widget in widgets if (height := _safe_height_from_size_hint(widget)) is not None]
    if not heights:
        return
    target_height = max(heights)
    for widget in widgets:
        class_name = _widget_class_name(widget)
        if class_name in _MULTILINE_WIDGET_CLASS_NAMES:
            continue
        if class_name not in _SINGLE_LINE_WIDGET_CLASS_NAMES:
            continue
        set_fixed_height = getattr(widget, "setFixedHeight", None)
        if callable(set_fixed_height):
            set_fixed_height(target_height)
