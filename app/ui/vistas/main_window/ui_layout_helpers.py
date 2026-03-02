from __future__ import annotations

from collections.abc import Iterable

from app.ui.qt_compat import QHeaderView

_INPUT_NAMES = ("persona_combo", "fecha_input", "desde_input", "hasta_input", "notas_input")
_TABLE_NAMES = (
    "pendientes_table",
    "historico_table",
    "personas_table",
    "conflictos_table",
)
_SINGLE_LINE_WIDGET_CLASS_NAMES = {
    "QComboBox",
    "QDateEdit",
    "QTimeEdit",
    "QLineEdit",
    "QSpinBox",
    "QDoubleSpinBox",
}


def _iter_present_widgets(window: object, names: Iterable[str]) -> list[object]:
    return [widget for name in names if (widget := getattr(window, name, None)) is not None]


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


def normalize_input_heights(window: object) -> None:
    widgets = _iter_present_widgets(window, _INPUT_NAMES)
    heights = [height for widget in widgets if (height := _safe_height_from_size_hint(widget)) is not None]
    if not heights:
        return

    target_height = max(heights)
    for widget in widgets:
        if type(widget).__name__ not in _SINGLE_LINE_WIDGET_CLASS_NAMES:
            continue
        set_fixed_height = getattr(widget, "setFixedHeight", None)
        if callable(set_fixed_height):
            set_fixed_height(target_height)


def _available_width(table: object) -> int:
    viewport = getattr(table, "viewport", None)
    if callable(viewport):
        viewport_widget = viewport()
        width_getter = getattr(viewport_widget, "width", None)
        if callable(width_getter):
            width = width_getter()
            if isinstance(width, int) and width > 0:
                return width

    width_getter = getattr(table, "width", None)
    if callable(width_getter):
        width = width_getter()
        if isinstance(width, int):
            return max(0, width)
    return 0


def _window_width(window: object) -> int:
    width_getter = getattr(window, "width", None)
    if callable(width_getter):
        width = width_getter()
        if isinstance(width, int) and width > 0:
            return width
    return 0


def _apply_header_policy(table: object, available_width: int) -> None:
    model_getter = getattr(table, "model", None)
    model = model_getter() if callable(model_getter) else None
    column_count_getter = getattr(model, "columnCount", None)
    column_count = column_count_getter() if callable(column_count_getter) else 0
    if not isinstance(column_count, int) or column_count <= 0:
        return

    header_getter = getattr(table, "horizontalHeader", None)
    header = header_getter() if callable(header_getter) else None
    if header is None:
        return

    set_mode = getattr(header, "setSectionResizeMode", None)
    if not callable(set_mode):
        return

    for column in range(max(0, column_count - 1)):
        set_mode(column, QHeaderView.ResizeToContents)

    last_column = column_count - 1
    set_mode(last_column, QHeaderView.Stretch)

    set_column_width = getattr(table, "setColumnWidth", None)
    if not callable(set_column_width):
        return

    if available_width <= 0:
        return

    target_last_width = max(180, int(available_width * 0.32))
    set_column_width(last_column, target_last_width)


def _apply_form_policy(window: object, window_width: int) -> None:
    is_compact = 0 < window_width < 1160

    persona_combo = getattr(window, "persona_combo", None)
    set_minimum_width = getattr(persona_combo, "setMinimumWidth", None)
    if callable(set_minimum_width):
        target_persona_width = max(220, min(360, int(window_width * 0.28))) if window_width > 0 else 260
        set_minimum_width(target_persona_width)

    for input_name in ("fecha_input", "desde_input", "hasta_input"):
        widget = getattr(window, input_name, None)
        set_minimum_width = getattr(widget, "setMinimumWidth", None)
        if callable(set_minimum_width):
            set_minimum_width(108 if is_compact else 124)

    for placeholder_name in ("desde_placeholder", "hasta_placeholder"):
        placeholder = getattr(window, placeholder_name, None)
        set_fixed_width = getattr(placeholder, "setFixedWidth", None)
        if callable(set_fixed_width):
            set_fixed_width(0 if is_compact else 28)

    total_preview_input = getattr(window, "total_preview_input", None)
    set_maximum_width = getattr(total_preview_input, "setMaximumWidth", None)
    if callable(set_maximum_width):
        set_maximum_width(72 if is_compact else 96)

    for tip_name in ("solicitudes_tip_1", "solicitudes_tip_2", "solicitudes_tip_3"):
        tip_label = getattr(window, tip_name, None)
        set_word_wrap = getattr(tip_label, "setWordWrap", None)
        if callable(set_word_wrap):
            set_word_wrap(is_compact)


def update_responsive_columns(window: object) -> None:
    window_width = _window_width(window)
    for table in _iter_present_widgets(window, _TABLE_NAMES):
        available_width = _available_width(table)
        _apply_header_policy(table, available_width)
    _apply_form_policy(window, window_width)
