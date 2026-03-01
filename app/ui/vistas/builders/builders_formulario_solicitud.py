from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTableView,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.copy_catalog import copy_text
from app.ui.models_qt import SolicitudesTableModel

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


logger = logging.getLogger(__name__)


def create_formulario_solicitud(window: "MainWindow") -> None:
    solicitud_card, solicitud_layout = window._create_card("")
    solicitud_layout.setSpacing(8)

    window.pending_errors_frame = QFrame()
    window.pending_errors_frame.setProperty("role", "notice")
    pending_errors_layout = QVBoxLayout(window.pending_errors_frame)
    pending_errors_layout.setContentsMargins(10, 8, 10, 8)
    pending_errors_layout.setSpacing(6)
    window.pending_errors_title = QLabel(copy_text("solicitudes.pending_errors_title"))
    window.pending_errors_title.setProperty("role", "sectionTitle")
    pending_errors_layout.addWidget(window.pending_errors_title)
    window.pending_errors_summary = QLabel("")
    window.pending_errors_summary.setWordWrap(True)
    pending_errors_layout.addWidget(window.pending_errors_summary)
    window.goto_existing_button = QPushButton(copy_text("ui.solicitudes.ir_existente"))
    window.goto_existing_button.setProperty("variant", "ghost")
    window.goto_existing_button.clicked.connect(window._on_go_to_existing_duplicate)
    window.goto_existing_button.setVisible(False)
    pending_errors_layout.addWidget(window.goto_existing_button)
    window.pending_errors_frame.setVisible(False)

    datos_basicos_label = QLabel(copy_text("solicitudes.form_section_title"))
    datos_basicos_label.setProperty("role", "sectionTitle")
    solicitud_layout.addWidget(datos_basicos_label)

    persona_row = QHBoxLayout()
    persona_row.setSpacing(10)
    persona_label = QLabel(copy_text("solicitudes.label_delegada"))
    persona_label.setProperty("role", "sectionTitle")
    persona_row.addWidget(persona_label)
    window.persona_combo.currentIndexChanged.connect(window._on_persona_changed)
    persona_row.addWidget(window.persona_combo, 1)
    solicitud_layout.addLayout(persona_row)

    solicitud_row = QHBoxLayout()
    solicitud_row.setSpacing(10)
    solicitud_row.addWidget(QLabel(copy_text("solicitudes.label_fecha")))
    window.fecha_input = QDateEdit(QDate.currentDate())
    window.fecha_input.setCalendarPopup(True)
    window.fecha_input.dateChanged.connect(window._on_fecha_changed)
    solicitud_row.addWidget(window.fecha_input)

    window.desde_input = QTimeEdit(QTime(9, 0))
    window.desde_input.setDisplayFormat(copy_text("ui.solicitudes.formato_hora"))
    window.desde_input.timeChanged.connect(window._update_solicitud_preview)
    window.desde_container = QWidget()
    desde_layout = QHBoxLayout(window.desde_container)
    desde_layout.setContentsMargins(0, 0, 0, 0)
    desde_layout.setSpacing(6)
    desde_layout.addWidget(QLabel(copy_text("solicitudes.label_desde")))
    desde_layout.addWidget(window.desde_input)
    solicitud_row.addWidget(window.desde_container)

    window.desde_placeholder = QWidget()
    window.desde_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    solicitud_row.addWidget(window.desde_placeholder)

    window.hasta_input = QTimeEdit(QTime(17, 0))
    window.hasta_input.setDisplayFormat(copy_text("ui.solicitudes.formato_hora"))
    window.hasta_input.timeChanged.connect(window._update_solicitud_preview)
    window.hasta_container = QWidget()
    hasta_layout = QHBoxLayout(window.hasta_container)
    hasta_layout.setContentsMargins(0, 0, 0, 0)
    hasta_layout.setSpacing(6)
    hasta_layout.addWidget(QLabel(copy_text("solicitudes.label_hasta")))
    hasta_layout.addWidget(window.hasta_input)
    solicitud_row.addWidget(window.hasta_container)

    window.hasta_placeholder = QWidget()
    window.hasta_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    solicitud_row.addWidget(window.hasta_placeholder)

    window.completo_check = QCheckBox(copy_text("ui.solicitudes.completo"))
    window.completo_check.toggled.connect(window._on_completo_changed)
    solicitud_row.addWidget(window.completo_check)

    window.total_preview_label = QLabel(copy_text("ui.solicitudes.saldo_reservado"))
    window.total_preview_label.setProperty("role", "secondary")
    solicitud_row.addWidget(window.total_preview_label)

    window.total_preview_input = QLineEdit("00:00")
    window.total_preview_input.setReadOnly(True)
    window.total_preview_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.total_preview_input.setMaximumWidth(84)
    solicitud_row.addWidget(window.total_preview_input)

    window.cuadrante_warning_label = QLabel("")
    window.cuadrante_warning_label.setProperty("role", "secondary")
    window.cuadrante_warning_label.setVisible(False)
    solicitud_row.addWidget(window.cuadrante_warning_label)

    window.agregar_button = QPushButton(copy_text("solicitudes.button_add_pending"))
    window.agregar_button.setProperty("variant", "secondary")
    window.agregar_button.clicked.connect(
        window._on_add_pendiente,
        Qt.ConnectionType.UniqueConnection,
    )
    solicitud_row.addWidget(window.agregar_button)
    solicitud_row.addStretch(1)
    solicitud_layout.addLayout(solicitud_row)

    notas_row = QHBoxLayout()
    notas_row.setSpacing(8)
    notas_row.addWidget(QLabel(copy_text("solicitudes.label_notas")))
    window.notas_input = QPlainTextEdit()
    window.notas_input.setPlaceholderText(copy_text("solicitudes.placeholder_notas"))
    lineas_visibles_notas = 3
    altura_linea_notas = window.notas_input.fontMetrics().lineSpacing()
    margen_documento_notas = int(window.notas_input.document().documentMargin() * 2)
    altura_borde_notas = window.notas_input.frameWidth() * 2
    altura_compacta_notas = (altura_linea_notas * lineas_visibles_notas) + margen_documento_notas + altura_borde_notas
    window.notas_input.setFixedHeight(altura_compacta_notas)
    window.notas_input.installEventFilter(window)
    window.persona_combo.installEventFilter(window)
    window.fecha_input.installEventFilter(window)
    window.desde_input.installEventFilter(window)
    window.hasta_input.installEventFilter(window)
    window.completo_check.installEventFilter(window)
    window.notas_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    notas_row.addWidget(window.notas_input, 1)
    solicitud_layout.addLayout(notas_row)

    tips_row = QHBoxLayout()
    tips_row.setSpacing(8)
    window.solicitudes_tip_1 = QLabel(copy_text("solicitudes.tip_enter"))
    window.solicitudes_tip_1.setProperty("role", "secondary")
    window.solicitudes_tip_2 = QLabel(copy_text("solicitudes.tip_minutes"))
    window.solicitudes_tip_2.setProperty("role", "secondary")
    window.solicitudes_tip_3 = QLabel(copy_text("solicitudes.tip_full_day"))
    window.solicitudes_tip_3.setProperty("role", "secondary")
    tips_row.addWidget(window.solicitudes_tip_1)
    tips_row.addWidget(window.solicitudes_tip_2)
    tips_row.addWidget(window.solicitudes_tip_3)
    tips_row.addStretch(1)
    solicitud_layout.addLayout(tips_row)

    status_row = QHBoxLayout()
    status_row.setSpacing(8)
    window.solicitudes_status_title = QLabel(copy_text("ui.solicitudes.estado"))
    window.solicitudes_status_title.setProperty("role", "sectionTitle")
    status_row.addWidget(window.solicitudes_status_title)
    window.solicitudes_status_label = QLabel(copy_text("solicitudes.status_ready"))
    window.solicitudes_status_label.setProperty("role", "secondary")
    status_row.addWidget(window.solicitudes_status_label)
    status_row.addSpacing(8)
    window.solicitudes_status_hint = QLabel("")
    window.solicitudes_status_hint.setProperty("role", "secondary")
    window.solicitudes_status_hint.setWordWrap(True)
    status_row.addWidget(window.solicitudes_status_hint, 1)
    solicitud_layout.addLayout(status_row)

    window.show_help_toggle = QCheckBox(copy_text("solicitudes.help_toggle"))
    window.show_help_toggle.setChecked(True)
    solicitud_layout.addWidget(window.show_help_toggle)

    window.solicitud_inline_error = QLabel("")
    window.solicitud_inline_error.setProperty("role", "error")
    window.solicitud_inline_error.setVisible(False)
    solicitud_layout.addWidget(window.solicitud_inline_error)

    window.delegada_field_error = QLabel("")
    window.delegada_field_error.setProperty("role", "error")
    window.delegada_field_error.setVisible(False)
    solicitud_layout.addWidget(window.delegada_field_error)

    window.fecha_field_error = QLabel("")
    window.fecha_field_error.setProperty("role", "error")
    window.fecha_field_error.setVisible(False)
    solicitud_layout.addWidget(window.fecha_field_error)

    window.tramo_field_error = QLabel("")
    window.tramo_field_error.setProperty("role", "error")
    window.tramo_field_error.setVisible(False)
    solicitud_layout.addWidget(window.tramo_field_error)

    solicitud_layout.addWidget(window.pending_errors_frame)
    window._solicitudes_form_layout.addWidget(solicitud_card)

    pendientes_card, pendientes_layout = window._create_card(copy_text("ui.solicitudes.pendientes_confirmar"))
    window._pendientes_group = pendientes_card
    pending_tools = QHBoxLayout()
    pending_tools.setSpacing(8)
    window.ver_todas_pendientes_button = QCheckBox(copy_text("ui.solicitudes.ver_todas"))
    window.ver_todas_pendientes_button.setCursor(Qt.CursorShape.PointingHandCursor)
    window.ver_todas_pendientes_button.toggled.connect(window._on_toggle_ver_todas_pendientes)
    pending_tools.addWidget(window.ver_todas_pendientes_button)
    window.revisar_ocultas_button = QPushButton(copy_text("ui.solicitudes.revisar_ocultas"))
    window.revisar_ocultas_button.setProperty("variant", "ghost")
    window.revisar_ocultas_button.setVisible(False)
    window.revisar_ocultas_button.clicked.connect(window._on_review_hidden_pendientes)
    pending_tools.addWidget(window.revisar_ocultas_button)
    window.pending_filter_warning = QLabel("")
    window.pending_filter_warning.setProperty("role", "secondary")
    window.pending_filter_warning.setVisible(False)
    pending_tools.addWidget(window.pending_filter_warning)
    pending_tools.addStretch(1)
    pendientes_layout.addLayout(pending_tools)

    window.pending_details_content = QWidget()
    pending_details_layout = QVBoxLayout(window.pending_details_content)
    pending_details_layout.setContentsMargins(0, 0, 0, 0)
    pending_details_layout.setSpacing(12)

    window.pendientes_table = QTableView()
    window.pendientes_model = SolicitudesTableModel([])
    window.pendientes_table.setModel(window.pendientes_model)
    window.pendientes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    window.pendientes_table.setSelectionMode(QAbstractItemView.MultiSelection)
    window.pendientes_table.selectionModel().selectionChanged.connect(window._on_pending_selection_changed)
    window.pendientes_table.setShowGrid(False)
    window.pendientes_table.setAlternatingRowColors(True)
    window.pendientes_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    window.pendientes_table.setMinimumHeight(220)
    window._configure_solicitudes_table(window.pendientes_table)
    pending_details_layout.addWidget(window.pendientes_table, 1)

    window.huerfanas_label = QLabel(copy_text("ui.solicitudes.huerfanas"))
    window.huerfanas_label.setProperty("role", "sectionTitle")
    window.huerfanas_label.setVisible(False)
    pending_details_layout.addWidget(window.huerfanas_label)

    window.huerfanas_table = QTableView()
    window.huerfanas_model = SolicitudesTableModel([])
    window.huerfanas_table.setModel(window.huerfanas_model)
    window.huerfanas_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    window.huerfanas_table.setSelectionMode(QAbstractItemView.SingleSelection)
    window.huerfanas_table.setShowGrid(False)
    window.huerfanas_table.setAlternatingRowColors(True)
    window.huerfanas_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    window.huerfanas_table.setMinimumHeight(120)
    window._configure_solicitudes_table(window.huerfanas_table)
    window.huerfanas_table.setVisible(False)
    pending_details_layout.addWidget(window.huerfanas_table)

    footer_separator = QFrame()
    footer_separator.setProperty("role", "subtleSeparator")
    footer_separator.setFixedHeight(1)
    pending_details_layout.addWidget(footer_separator)

    pendientes_footer = QHBoxLayout()
    pendientes_footer.setSpacing(10)

    left_actions = QHBoxLayout()
    left_actions.setSpacing(8)
    window.eliminar_pendiente_button = QPushButton(copy_text("solicitudes.button_pending_delete"))
    window.eliminar_pendiente_button.setProperty("variant", "primary")
    window.eliminar_pendiente_button.setProperty("intent", "destructive")
    window.eliminar_pendiente_button.clicked.connect(window._on_remove_pendiente)
    left_actions.addWidget(window.eliminar_pendiente_button)

    window.eliminar_huerfana_button = QPushButton(copy_text("ui.solicitudes.eliminar_huerfana"))
    window.eliminar_huerfana_button.setProperty("variant", "ghost")
    window.eliminar_huerfana_button.clicked.connect(window._on_remove_huerfana)
    window.eliminar_huerfana_button.setVisible(False)
    left_actions.addWidget(window.eliminar_huerfana_button)

    window.insertar_sin_pdf_button = QPushButton(copy_text("solicitudes.button_confirm_without_pdf"))
    window.insertar_sin_pdf_button.setProperty("variant", "success")
    window.insertar_sin_pdf_button.clicked.connect(window._on_insertar_sin_pdf)
    left_actions.addWidget(window.insertar_sin_pdf_button)
    pendientes_footer.addLayout(left_actions)

    pendientes_footer.addStretch(1)

    right_actions = QHBoxLayout()
    right_actions.setSpacing(10)
    window.total_pendientes_label = QLabel(copy_text("ui.solicitudes.total_cero"))
    window.total_pendientes_label.setProperty("role", "sectionTitle")
    right_actions.addWidget(window.total_pendientes_label)

    window.abrir_pdf_check = QCheckBox(copy_text("ui.solicitudes.abrir_pdf"))
    window.abrir_pdf_check.setChecked(True)
    right_actions.addWidget(window.abrir_pdf_check)

    window.confirmar_button = QPushButton(copy_text("solicitudes.button_confirm_with_pdf"))
    window.confirmar_button.setProperty("variant", "success")
    confirmar_handler = getattr(window, "_on_confirmar", None)
    if callable(confirmar_handler):
        window.confirmar_button.clicked.connect(confirmar_handler)
    else:
        logger.warning("UI_CONFIRMAR_PDF_BUTTON_NOT_WIRED")
    right_actions.addWidget(window.confirmar_button)

    pendientes_footer.addLayout(right_actions)
    pending_details_layout.addLayout(pendientes_footer)
    pendientes_layout.addWidget(window.pending_details_content, 1)
    window.pending_details_content.setVisible(True)
    window._solicitudes_list_layout.addWidget(pendientes_card, 1)
    window.solicitudes_splitter.addWidget(window._solicitudes_form_panel)
    window.solicitudes_splitter.addWidget(window._solicitudes_list_panel)
    window.solicitudes_splitter.setStretchFactor(0, 1)
    window.solicitudes_splitter.setStretchFactor(1, 3)

    window.main_tabs.addTab(window._operativa_tab, copy_text("solicitudes.section_title"))
