from __future__ import annotations

import logging
import threading
from typing import Any

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text
from app.ui.qt_compat import QAbstractItemView, QDate, QHeaderView, QTableView
from app.ui.patterns import status_badge
from . import handlers_layout

SINGLE_LINE_CLASS_NAMES = {
    "QComboBox",
    "QDateEdit",
    "QTimeEdit",
    "QLineEdit",
    "QSpinBox",
    "QDoubleSpinBox",
}


def safe_conflicts_count(window: Any) -> int:
    service = getattr(window, "_conflicts_service", None)
    if service is None or not hasattr(service, "count_conflicts"):
        return 0
    raw_total = service.count_conflicts()
    if isinstance(raw_total, bool) or not isinstance(raw_total, (int, float)):
        return 0
    return max(int(raw_total), 0)


def apply_help_preferences(window: Any) -> None:
    show_help_toggle = getattr(window, "show_help_toggle", None)
    if show_help_toggle is None:
        return
    settings_key = copy_text("ui.preferencias.settings_show_help_key")
    raw_value = window._settings.value(settings_key, True)
    show_help = (
        raw_value.strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(raw_value, str)
        else bool(raw_value)
    )
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


def on_help_toggle_changed(window: Any, enabled: bool) -> None:
    settings_key = copy_text("ui.preferencias.settings_show_help_key")
    window._settings.setValue(settings_key, bool(enabled))
    for attr_name in ("solicitudes_tip_1", "solicitudes_tip_2", "solicitudes_tip_3"):
        widget = getattr(window, attr_name, None)
        if widget is not None and hasattr(widget, "setVisible"):
            widget.setVisible(enabled)
    window._apply_solicitudes_tooltips(enabled)


def apply_solicitudes_tooltips(window: Any, enabled: bool | None = None) -> None:
    if enabled is None:
        enabled = bool(
            getattr(
                getattr(window, "show_help_toggle", None), "isChecked", lambda: True
            )()
        )
    help_text_by_widget = (
        ("persona_combo", "solicitudes.tooltip_delegada"),
        ("fecha_input", "solicitudes.tooltip_fecha"),
        ("desde_input", "solicitudes.tooltip_desde"),
        ("hasta_input", "solicitudes.tooltip_hasta"),
        ("total_preview_input", "solicitudes.tooltip_minutos"),
        ("notas_input", "solicitudes.tooltip_notas"),
    )
    for widget_name, copy_key in help_text_by_widget:
        widget = getattr(window, widget_name, None)
        if widget is not None and hasattr(widget, "setToolTip"):
            widget.setToolTip(copy_text(copy_key) if enabled else "")


def warmup_sync_client(window: Any, logger_obj: logging.Logger) -> None:
    try:
        if window._sync_warmup_iniciado:
            return
    except AttributeError:
        pass
    window._sync_warmup_iniciado = True

    try:
        ensure_connection = window._sync_service.ensure_connection
    except AttributeError:
        return
    if not callable(ensure_connection):
        return

    def _run_warmup() -> None:
        try:
            ensure_connection()
        except Exception as exc:  # pragma: no cover
            log_operational_error(
                logger_obj,
                "SYNC_WARMUP_FAILED",
                exc=exc,
                extra={"operation": "sync_warmup"},
            )

    threading.Thread(target=_run_warmup, daemon=True).start()


def update_conflicts_reminder(window: Any, logger_obj: logging.Logger) -> None:
    try:
        reminder_widget = window.conflicts_reminder_label
    except AttributeError:
        return
    if reminder_widget is None:
        return
    try:
        i18n_actual = window._i18n
    except AttributeError:
        return
    if i18n_actual is None:
        return
    try:
        total_conflictos_pendientes = (
            int(window._conflicts_service.count_conflicts())
            if hasattr(window, "_conflicts_service")
            and window._conflicts_service is not None
            else 0
        )
        if total_conflictos_pendientes > 0:
            reminder_widget.setVisible(True)
            texto_base = copy_text("ui.sync.conflictos_pendientes")
            reminder_widget.setText(
                texto_base.replace("0", str(total_conflictos_pendientes), 1)
            )
            return
        reminder_widget.setVisible(False)
    except Exception:
        logger_obj.exception("UI_UPDATE_CONFLICTS_REMINDER_FAILED")


def configure_time_placeholders(window: Any) -> None:
    handlers_layout.configure_time_placeholders(window)
    placeholder_hora = _resolver_placeholder_hora(window)
    for input_name in ("desde_input", "hasta_input"):
        input_widget = getattr(window, input_name, None)
        if input_widget is None:
            continue
        line_edit = getattr(input_widget, "lineEdit", lambda: None)()
        if line_edit is not None and hasattr(line_edit, "setPlaceholderText"):
            line_edit.setPlaceholderText(placeholder_hora)
        elif hasattr(input_widget, "setPlaceholderText"):
            input_widget.setPlaceholderText(placeholder_hora)


def _resolver_placeholder_hora(window: Any) -> str:
    try:
        i18n = window._i18n
        traductor = i18n.t
    except AttributeError:
        return ""
    if callable(traductor):
        try:
            texto = traductor("ui.placeholder_hora_hhmm", fallback="")
        except Exception:
            return ""
        return texto if isinstance(texto, str) else ""
    return ""


def _size_hint_height(widget: object) -> int | None:
    size_hint = getattr(widget, "sizeHint", None)
    if not callable(size_hint):
        return None
    hint = size_hint()
    height_getter = getattr(hint, "height", None)
    if not callable(height_getter):
        return None
    height = height_getter()
    return height if isinstance(height, int) and height > 0 else None


def normalize_input_heights(window: Any, logger_obj: logging.Logger) -> None:
    try:
        names = (
            "persona_combo",
            "fecha_input",
            "desde_input",
            "hasta_input",
            "notas_input",
        )
        widgets = [
            widget
            for name in names
            if (widget := getattr(window, name, None)) is not None
        ]
        single_line_widgets = [
            widget
            for widget in widgets
            if type(widget).__name__ in SINGLE_LINE_CLASS_NAMES
        ]
        heights = [
            height
            for widget in single_line_widgets
            if (height := _size_hint_height(widget)) is not None
        ]
        if not heights:
            return
        target_height = max(heights)
        for widget in single_line_widgets:
            set_fixed_height = getattr(widget, "setFixedHeight", None)
            if callable(set_fixed_height):
                set_fixed_height(target_height)
    except Exception as exc:
        log_operational_error(
            logger_obj,
            "UI_NORMALIZE_INPUT_HEIGHTS_FAILED",
            exc=exc,
            extra={"contexto": "mainwindow._normalize_input_heights"},
        )


def update_responsive_columns(window: Any, logger_obj: logging.Logger) -> None:
    try:
        handlers_layout.update_responsive_columns(window)
    except Exception as exc:
        log_operational_error(
            logger_obj,
            "UI_UPDATE_RESPONSIVE_COLUMNS_FAILED",
            exc=exc,
            extra={"contexto": "mainwindow._update_responsive_columns"},
        )


def configure_operativa_focus_order(window: Any) -> None:
    focus_chain = (
        ("persona_combo", "fecha_input"),
        ("fecha_input", "desde_input"),
        ("desde_input", "hasta_input"),
        ("hasta_input", "completo_check"),
        ("completo_check", "notas_input"),
        ("notas_input", "agregar_button"),
        ("agregar_button", "insertar_sin_pdf_button"),
        ("insertar_sin_pdf_button", "confirmar_button"),
    )
    for before_name, after_name in focus_chain:
        before_widget = getattr(window, before_name, None)
        after_widget = getattr(window, after_name, None)
        if before_widget is not None and after_widget is not None:
            window.setTabOrder(before_widget, after_widget)


def configure_historico_focus_order(window: Any, logger_obj: logging.Logger) -> None:
    focus_chain = (
        ("historico_search_input", "historico_estado_combo"),
        ("historico_estado_combo", "historico_delegada_combo"),
        ("historico_delegada_combo", "historico_desde_date"),
        ("historico_desde_date", "historico_hasta_date"),
        ("historico_hasta_date", "historico_table"),
    )
    set_tab_order = getattr(window, "setTabOrder", None)
    if not callable(set_tab_order):
        logger_obj.warning("UI_SET_TAB_ORDER_NOT_AVAILABLE")
        return
    for before_name, after_name in focus_chain:
        before_widget = getattr(window, before_name, None)
        after_widget = getattr(window, after_name, None)
        if before_widget is None or after_widget is None:
            logger_obj.warning(
                "UI_TAB_ORDER_SKIPPED_MISSING_WIDGET",
                extra={"before": before_name, "after": after_name},
            )
            continue
        set_tab_order(before_widget, after_widget)


def status_to_label(status: str) -> str:
    return {
        "IDLE": copy_text("ui.sync.estado_en_espera"),
        "RUNNING": copy_text("ui.sync.estado_pendiente_sincronizando"),
        "OK": status_badge("CONFIRMED"),
        "OK_WARN": status_badge("WARNING"),
        "ERROR": status_badge("ERROR"),
        "CONFIG_INCOMPLETE": copy_text("ui.sync.estado_error_config_incompleta"),
    }.get(status, status)


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


def on_fecha_changed(window: Any, qdate: QDate) -> None:
    window._fecha_seleccionada = (
        QDate(qdate) if hasattr(qdate, "isValid") and qdate.isValid() else None
    )
    update_preview = getattr(window, "_update_solicitud_preview", None)
    if callable(update_preview):
        update_preview()
