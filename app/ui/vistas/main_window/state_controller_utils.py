from __future__ import annotations

import logging

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text
from app.ui.qt_compat import QAbstractItemView, QHeaderView, QTableView

HELP_WIDGETS = (
    "solicitudes_tip_1",
    "solicitudes_tip_2",
    "solicitudes_tip_3",
    "solicitudes_status_hint",
)

HELP_TEXT_BY_WIDGET = (
    ("persona_combo", "solicitudes.tooltip_delegada"),
    ("fecha_input", "solicitudes.tooltip_fecha"),
    ("desde_input", "solicitudes.tooltip_desde"),
    ("hasta_input", "solicitudes.tooltip_hasta"),
    ("total_preview_input", "solicitudes.tooltip_minutos"),
    ("notas_input", "solicitudes.tooltip_notas"),
)

OPERATIVA_FOCUS_CHAIN = (
    ("persona_combo", "fecha_input"),
    ("fecha_input", "desde_input"),
    ("desde_input", "hasta_input"),
    ("hasta_input", "completo_check"),
    ("completo_check", "notas_input"),
    ("notas_input", "agregar_button"),
    ("agregar_button", "insertar_sin_pdf_button"),
    ("insertar_sin_pdf_button", "confirmar_button"),
)

HISTORICO_FOCUS_CHAIN = (
    ("historico_search_input", "historico_estado_combo"),
    ("historico_estado_combo", "historico_delegada_combo"),
    ("historico_delegada_combo", "historico_desde_date"),
    ("historico_desde_date", "historico_hasta_date"),
    ("historico_hasta_date", "historico_apply_filters_button"),
    ("historico_apply_filters_button", "historico_table"),
)


SYNC_STATUS_COPY_BY_CODE = {
    "IDLE": "ui.sync.estado_en_espera",
    "RUNNING": "ui.sync.estado_pendiente_sincronizando",
    "CONFIG_INCOMPLETE": "ui.sync.estado_error_config_incompleta",
}


INPUT_NAMES_FOR_HEIGHT_NORMALIZATION = (
    "persona_combo",
    "fecha_input",
    "desde_input",
    "hasta_input",
    "notas_input",
)

SINGLE_LINE_CLASS_NAMES = {
    "QComboBox",
    "QDateEdit",
    "QTimeEdit",
    "QLineEdit",
    "QSpinBox",
    "QDoubleSpinBox",
}


def apply_help_preferences(window: object) -> None:
    show_help_toggle = getattr(window, "show_help_toggle", None)
    if show_help_toggle is None:
        return
    settings_key = copy_text("ui.preferencias.settings_show_help_key")
    raw_value = window._settings.value(settings_key, True)
    show_help = raw_value.strip().lower() in {"1", "true", "yes", "on"} if isinstance(raw_value, str) else bool(raw_value)
    show_help_toggle.blockSignals(True)
    show_help_toggle.setChecked(show_help)
    show_help_toggle.blockSignals(False)
    if window._help_toggle_conectado:
        show_help_toggle.toggled.disconnect(window._on_help_toggle_changed)
        window._help_toggle_conectado = False
    if not window._help_toggle_conectado:
        show_help_toggle.toggled.connect(window._on_help_toggle_changed)
        window._help_toggle_conectado = True
    window._on_help_toggle_changed(show_help)


def on_help_toggle_changed(window: object, enabled: bool) -> None:
    settings_key = copy_text("ui.preferencias.settings_show_help_key")
    window._settings.setValue(settings_key, bool(enabled))
    for attr_name in HELP_WIDGETS:
        widget = getattr(window, attr_name, None)
        if widget is not None and hasattr(widget, "setVisible"):
            widget.setVisible(enabled)
    window._apply_solicitudes_tooltips(enabled)


def apply_solicitudes_tooltips(window: object, enabled: bool | None = None) -> None:
    if enabled is None:
        enabled = bool(getattr(getattr(window, "show_help_toggle", None), "isChecked", lambda: True)())
    for widget_name, copy_key in HELP_TEXT_BY_WIDGET:
        widget = getattr(window, widget_name, None)
        if widget is None or not hasattr(widget, "setToolTip"):
            continue
        widget.setToolTip(copy_text(copy_key) if enabled else "")


def update_conflicts_reminder(window: object, logger: logging.Logger) -> None:
    try:
        if not hasattr(window, "conflicts_reminder_label") or not hasattr(window, "_i18n"):
            return
        reminder_widget = window.conflicts_reminder_label
        if reminder_widget is None:
            return
        total_conflictos_pendientes = 0
        if hasattr(window, "_conflicts_service") and window._conflicts_service is not None:
            total_conflictos_pendientes = int(window._conflicts_service.count_conflicts())
        if total_conflictos_pendientes > 0:
            reminder_widget.setVisible(True)
            texto_base = copy_text("ui.sync.conflictos_pendientes")
            reminder_widget.setText(texto_base.replace("0", str(total_conflictos_pendientes), 1))
            return
        reminder_widget.setVisible(False)
    except Exception:
        logger.exception("UI_UPDATE_CONFLICTS_REMINDER_FAILED")


def configure_time_placeholders(window: object, handlers_layout_module: object) -> None:
    handlers_layout_module.configure_time_placeholders(window)
    for input_name in ("desde_input", "hasta_input"):
        input_widget = getattr(window, input_name, None)
        if input_widget is None:
            continue
        line_edit = getattr(input_widget, "lineEdit", lambda: None)()
        if line_edit is not None and hasattr(line_edit, "setPlaceholderText"):
            line_edit.setPlaceholderText("HH:MM")
            continue
        if hasattr(input_widget, "setPlaceholderText"):
            input_widget.setPlaceholderText("HH:MM")


def normalize_input_heights(window: object, logger: logging.Logger) -> None:
    try:
        widgets = [widget for name in INPUT_NAMES_FOR_HEIGHT_NORMALIZATION if (widget := getattr(window, name, None)) is not None]
        single_line_widgets = [widget for widget in widgets if type(widget).__name__ in SINGLE_LINE_CLASS_NAMES]
        heights = [_size_hint_height(widget) for widget in single_line_widgets]
        valid_heights = [height for height in heights if height is not None]
        if not valid_heights:
            return
        target_height = max(valid_heights)
        for widget in single_line_widgets:
            set_fixed_height = getattr(widget, "setFixedHeight", None)
            if callable(set_fixed_height):
                set_fixed_height(target_height)
    except Exception as exc:
        log_operational_error(logger, "UI_NORMALIZE_INPUT_HEIGHTS_FAILED", exc=exc, extra={"contexto": "mainwindow._normalize_input_heights"})


def _size_hint_height(widget: object) -> int | None:
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


def configure_operativa_focus_order(window: object) -> None:
    for before_name, after_name in OPERATIVA_FOCUS_CHAIN:
        before_widget = getattr(window, before_name, None)
        after_widget = getattr(window, after_name, None)
        if before_widget is None or after_widget is None:
            continue
        window.setTabOrder(before_widget, after_widget)


def configure_historico_focus_order(window: object, logger: logging.Logger) -> None:
    set_tab_order = getattr(window, "setTabOrder", None)
    if not callable(set_tab_order):
        logger.warning("UI_SET_TAB_ORDER_NOT_AVAILABLE")
        return
    for before_name, after_name in HISTORICO_FOCUS_CHAIN:
        before_widget = getattr(window, before_name, None)
        after_widget = getattr(window, after_name, None)
        if before_widget is None or after_widget is None:
            logger.warning("UI_TAB_ORDER_SKIPPED_MISSING_WIDGET", extra={"before": before_name, "after": after_name})
            continue
        set_tab_order(before_widget, after_widget)


def status_to_label(status: str, status_badge_func: object) -> str:
    if status in SYNC_STATUS_COPY_BY_CODE:
        return copy_text(SYNC_STATUS_COPY_BY_CODE[status])
    if status == "OK":
        return status_badge_func("CONFIRMED")
    if status == "OK_WARN":
        return status_badge_func("WARNING")
    if status == "ERROR":
        return status_badge_func("ERROR")
    return status


def configure_solicitudes_table(table: QTableView) -> None:
    model = table.model()
    column_count = model.columnCount() if model is not None else 6
    if column_count <= 0:
        return
    table.setProperty("role", "dataTable")
    table.setAlternatingRowColors(True)
    header = table.horizontalHeader()
    header.setMinimumSectionSize(78)
    for column in range(max(0, column_count - 1)):
        header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(column_count - 1, QHeaderView.Stretch)
    header.setStretchLastSection(False)
    table.setColumnWidth(column_count - 1, 240)
    table.verticalHeader().setDefaultSectionSize(30)
    table.verticalHeader().setVisible(False)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
