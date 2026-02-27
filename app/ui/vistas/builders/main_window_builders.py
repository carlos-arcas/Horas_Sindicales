from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QDate, QTimer, QTime, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableView,
    QTimeEdit,
    QToolButton,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.historico_view import ESTADOS_HISTORICO, HistoricalViewModel
from app.ui.models_qt import SolicitudesTableModel
from app.ui.components.saldos_card import SaldosCard

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


logger = logging.getLogger(__name__)


def build_saldos_widget(parent: QWidget | None = None) -> SaldosCard:
    return SaldosCard(parent)

def build_main_window_widgets(window: "MainWindow") -> None:
    window.persona_combo = QComboBox()
    window._scroll_area = QScrollArea()
    window._scroll_area.setWidgetResizable(True)
    window._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    window._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    content = QWidget()
    content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(12, 8, 12, 12)
    layout.setSpacing(16)

    window.main_tabs = QTabWidget()
    window.main_tabs.setObjectName("mainTabs")
    window.main_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    layout.addWidget(window.main_tabs, 1)

    operativa_tab = QWidget()
    operativa_layout = QVBoxLayout(operativa_tab)
    operativa_layout.setContentsMargins(0, 0, 0, 0)
    operativa_layout.setSpacing(12)
    operativa_header_row = QHBoxLayout()
    operativa_header_row.setSpacing(10)
    operativa_help = QLabel("Completa la solicitud y confirma solo cuando estés lista.")
    operativa_help.setWordWrap(True)
    operativa_help.setProperty("role", "secondary")
    operativa_header_row.addWidget(operativa_help, 1)
    window.open_saldos_modal_button = QPushButton("Saldos")
    window.open_saldos_modal_button.setProperty("variant", "secondary")
    window.open_saldos_modal_button.setMaximumWidth(110)
    operativa_header_row.addWidget(window.open_saldos_modal_button, alignment=Qt.AlignRight)
    operativa_layout.addLayout(operativa_header_row)

    # UX: Operativa concentra solo tareas diarias (alta + pendientes + confirmación)
    # para reducir cambios de contexto y evitar mezclar navegación histórica.
    window.solicitudes_splitter = QSplitter(Qt.Orientation.Vertical)
    window.solicitudes_splitter.setObjectName("solicitudesSplitter")
    window.solicitudes_splitter.setChildrenCollapsible(False)
    window.solicitudes_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    operativa_layout.addWidget(window.solicitudes_splitter, 1)

    solicitudes_list_panel = QWidget()
    solicitudes_list_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    solicitudes_list_layout = QVBoxLayout(solicitudes_list_panel)
    solicitudes_list_layout.setContentsMargins(0, 0, 0, 0)
    solicitudes_list_layout.setSpacing(0)

    solicitudes_form_panel = QWidget()
    solicitudes_form_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    solicitudes_form_layout = QVBoxLayout(solicitudes_form_panel)
    solicitudes_form_layout.setContentsMargins(0, 0, 0, 0)
    solicitudes_form_layout.setSpacing(0)

    solicitud_card, solicitud_layout = window._create_card("")
    solicitud_layout.setSpacing(8)

    window.pending_errors_frame = QFrame()
    window.pending_errors_frame.setProperty("role", "notice")
    pending_errors_layout = QVBoxLayout(window.pending_errors_frame)
    pending_errors_layout.setContentsMargins(10, 8, 10, 8)
    pending_errors_layout.setSpacing(6)
    window.pending_errors_title = QLabel("Errores pendientes")
    window.pending_errors_title.setProperty("role", "sectionTitle")
    pending_errors_layout.addWidget(window.pending_errors_title)
    window.pending_errors_summary = QLabel("")
    window.pending_errors_summary.setWordWrap(True)
    pending_errors_layout.addWidget(window.pending_errors_summary)
    window.goto_existing_button = QPushButton("Ir a la existente")
    window.goto_existing_button.setProperty("variant", "ghost")
    window.goto_existing_button.clicked.connect(window._on_go_to_existing_duplicate)
    window.goto_existing_button.setVisible(False)
    pending_errors_layout.addWidget(window.goto_existing_button)
    window.pending_errors_frame.setVisible(False)

    datos_basicos_label = QLabel("Datos de la reserva")
    datos_basicos_label.setProperty("role", "sectionTitle")
    solicitud_layout.addWidget(datos_basicos_label)

    persona_row = QHBoxLayout()
    persona_row.setSpacing(10)
    persona_label = QLabel("Delegada")
    persona_label.setProperty("role", "sectionTitle")
    persona_row.addWidget(persona_label)
    window.persona_combo.currentIndexChanged.connect(window._on_persona_changed)
    persona_row.addWidget(window.persona_combo, 1)
    solicitud_layout.addLayout(persona_row)

    solicitud_row = QHBoxLayout()
    solicitud_row.setSpacing(10)
    solicitud_row.addWidget(QLabel("Fecha"))
    window.fecha_input = QDateEdit(QDate.currentDate())
    window.fecha_input.setCalendarPopup(True)
    window.fecha_input.dateChanged.connect(window._on_fecha_changed)
    solicitud_row.addWidget(window.fecha_input)

    window.desde_input = QTimeEdit(QTime(9, 0))
    window.desde_input.setDisplayFormat("HH:mm")
    window.desde_input.timeChanged.connect(window._update_solicitud_preview)
    window.desde_container = QWidget()
    desde_layout = QHBoxLayout(window.desde_container)
    desde_layout.setContentsMargins(0, 0, 0, 0)
    desde_layout.setSpacing(6)
    desde_layout.addWidget(QLabel("Desde"))
    desde_layout.addWidget(window.desde_input)
    solicitud_row.addWidget(window.desde_container)

    window.desde_placeholder = QWidget()
    window.desde_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    solicitud_row.addWidget(window.desde_placeholder)

    window.hasta_input = QTimeEdit(QTime(17, 0))
    window.hasta_input.setDisplayFormat("HH:mm")
    window.hasta_input.timeChanged.connect(window._update_solicitud_preview)
    window.hasta_container = QWidget()
    hasta_layout = QHBoxLayout(window.hasta_container)
    hasta_layout.setContentsMargins(0, 0, 0, 0)
    hasta_layout.setSpacing(6)
    hasta_layout.addWidget(QLabel("Hasta"))
    hasta_layout.addWidget(window.hasta_input)
    solicitud_row.addWidget(window.hasta_container)

    window.hasta_placeholder = QWidget()
    window.hasta_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    solicitud_row.addWidget(window.hasta_placeholder)

    window.completo_check = QCheckBox("Completo")
    window.completo_check.toggled.connect(window._on_completo_changed)
    solicitud_row.addWidget(window.completo_check)

    window.total_preview_label = QLabel("Saldo reservado")
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

    window.agregar_button = QPushButton("Añadir pendiente")
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
    notas_row.addWidget(QLabel("Notas"))
    window.notas_input = QPlainTextEdit()
    window.notas_input.setPlaceholderText("Notas para la solicitud")
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
    solicitudes_form_layout.addWidget(solicitud_card)

    pendientes_card, pendientes_layout = window._create_card("Pendientes de confirmar")
    window._pendientes_group = pendientes_card
    pending_tools = QHBoxLayout()
    pending_tools.setSpacing(8)
    window.ver_todas_pendientes_button = QCheckBox("Ver peticiones de todas las delegadas")
    window.ver_todas_pendientes_button.setCursor(Qt.CursorShape.PointingHandCursor)
    window.ver_todas_pendientes_button.toggled.connect(window._on_toggle_ver_todas_pendientes)
    pending_tools.addWidget(window.ver_todas_pendientes_button)
    window.revisar_ocultas_button = QPushButton("Revisar pendientes ocultas")
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

    window.huerfanas_label = QLabel("Reparar · Pendientes huérfanas")
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
    window.eliminar_pendiente_button = QPushButton("Eliminar selección")
    window.eliminar_pendiente_button.setProperty("variant", "primary")
    window.eliminar_pendiente_button.setProperty("intent", "destructive")
    window.eliminar_pendiente_button.clicked.connect(window._on_remove_pendiente)
    left_actions.addWidget(window.eliminar_pendiente_button)

    window.eliminar_huerfana_button = QPushButton("Eliminar huérfana")
    window.eliminar_huerfana_button.setProperty("variant", "ghost")
    window.eliminar_huerfana_button.clicked.connect(window._on_remove_huerfana)
    window.eliminar_huerfana_button.setVisible(False)
    left_actions.addWidget(window.eliminar_huerfana_button)

    window.insertar_sin_pdf_button = QPushButton("Confirmar sin PDF")
    window.insertar_sin_pdf_button.setProperty("variant", "success")
    window.insertar_sin_pdf_button.clicked.connect(window._on_insertar_sin_pdf)
    left_actions.addWidget(window.insertar_sin_pdf_button)
    pendientes_footer.addLayout(left_actions)

    pendientes_footer.addStretch(1)

    right_actions = QHBoxLayout()
    right_actions.setSpacing(10)
    window.total_pendientes_label = QLabel("Total: 00:00")
    window.total_pendientes_label.setProperty("role", "sectionTitle")
    right_actions.addWidget(window.total_pendientes_label)

    window.abrir_pdf_check = QCheckBox("Abrir PDF")
    window.abrir_pdf_check.setChecked(True)
    right_actions.addWidget(window.abrir_pdf_check)

    window.confirmar_button = QPushButton("Confirmar y generar PDF")
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
    solicitudes_list_layout.addWidget(pendientes_card, 1)
    window.solicitudes_splitter.addWidget(solicitudes_form_panel)
    window.solicitudes_splitter.addWidget(solicitudes_list_panel)
    window.solicitudes_splitter.setStretchFactor(0, 1)
    window.solicitudes_splitter.setStretchFactor(1, 3)

    window.main_tabs.addTab(operativa_tab, "Solicitudes")

    historico_tab = QWidget()
    historico_tab_layout = QVBoxLayout(historico_tab)
    historico_tab_layout.setContentsMargins(0, 0, 0, 0)
    historico_tab_layout.setSpacing(12)
    historico_help = QLabel("Consulta y filtra solicitudes confirmadas. Si no hay registros, crea la primera solicitud.")
    historico_help.setWordWrap(True)
    historico_help.setProperty("role", "secondary")
    historico_tab_layout.addWidget(historico_help)

    historico_card, historico_layout = window._create_card("Histórico")

    window.historico_empty_state = QWidget()
    empty_layout = QVBoxLayout(window.historico_empty_state)
    empty_layout.setContentsMargins(0, 8, 0, 8)
    empty_layout.setSpacing(8)
    empty_title = QLabel("Aún no hay histórico")
    empty_title.setProperty("role", "sectionTitle")
    empty_layout.addWidget(empty_title)
    empty_text = QLabel("Cuando confirmes solicitudes aparecerán aquí con filtros por texto, estado y fechas.")
    empty_text.setWordWrap(True)
    empty_text.setProperty("role", "secondary")
    empty_layout.addWidget(empty_text)
    window.historico_empty_button = QPushButton("Crear primera solicitud")
    window.historico_empty_button.setProperty("variant", "primary")
    window.historico_empty_button.clicked.connect(lambda: window.main_tabs.setCurrentIndex(0))
    empty_layout.addWidget(window.historico_empty_button, alignment=Qt.AlignLeft)
    historico_layout.addWidget(window.historico_empty_state)

    window.historico_details_content = QWidget()
    historico_details_layout = QVBoxLayout(window.historico_details_content)
    historico_details_layout.setContentsMargins(0, 0, 0, 0)
    historico_details_layout.setSpacing(8)
    window._historico_group = historico_card
    historico_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    filtros_layout = QVBoxLayout()
    filtros_layout.setSpacing(10)

    window.historico_search_input = QLineEdit()
    window.historico_search_input.setPlaceholderText("Buscar")
    window.historico_search_input.setVisible(False)

    window.historico_estado_combo = QComboBox()
    window.historico_estado_combo.addItem("Todos", None)
    for estado in ESTADOS_HISTORICO.values():
        window.historico_estado_combo.addItem(estado.label, estado.code)
    window.historico_estado_combo.setVisible(False)

    filtros_row_1 = QHBoxLayout()
    filtros_row_1.setSpacing(8)
    filtros_row_1.addWidget(QLabel("Delegada"))

    window.historico_todas_delegadas_check = QCheckBox("Todas las delegadas (todos los registros)")
    window.historico_todas_delegadas_check.setChecked(True)
    filtros_row_1.addWidget(window.historico_todas_delegadas_check)

    window.historico_delegada_combo = QComboBox()
    window.historico_delegada_combo.addItem("Todas", None)
    filtros_row_1.addWidget(window.historico_delegada_combo)
    filtros_row_1.addStretch(1)
    filtros_layout.addLayout(filtros_row_1)

    filtros_row_2 = QHBoxLayout()
    filtros_row_2.setSpacing(12)

    window.historico_periodo_anual_radio = QRadioButton("Año completo")
    window.historico_periodo_anual_spin = QSpinBox()
    window.historico_periodo_anual_spin.setRange(2000, 2100)
    window.historico_periodo_anual_spin.setValue(QDate.currentDate().year())
    filtros_row_2.addWidget(window.historico_periodo_anual_radio)
    filtros_row_2.addWidget(window.historico_periodo_anual_spin)

    window.historico_periodo_mes_radio = QRadioButton("Año/mes")
    window.historico_periodo_mes_ano_spin = QSpinBox()
    window.historico_periodo_mes_ano_spin.setRange(2000, 2100)
    window.historico_periodo_mes_ano_spin.setValue(QDate.currentDate().year())
    window.historico_periodo_mes_combo = QComboBox()
    for mes in range(1, 13):
        window.historico_periodo_mes_combo.addItem(f"{mes:02d}", mes)
    window.historico_periodo_mes_combo.setCurrentIndex(QDate.currentDate().month() - 1)
    filtros_row_2.addWidget(window.historico_periodo_mes_radio)
    filtros_row_2.addWidget(window.historico_periodo_mes_ano_spin)
    filtros_row_2.addWidget(window.historico_periodo_mes_combo)

    window.historico_periodo_rango_radio = QRadioButton("Rango fechas")
    window.historico_periodo_anual_radio.setChecked(True)
    filtros_row_2.addWidget(window.historico_periodo_rango_radio)

    window.historico_desde_date = QDateEdit()
    window.historico_desde_date.setCalendarPopup(True)
    window.historico_desde_date.setDisplayFormat("yyyy-MM-dd")
    filtros_row_2.addWidget(QLabel("Desde"))
    filtros_row_2.addWidget(window.historico_desde_date)

    window.historico_hasta_date = QDateEdit()
    window.historico_hasta_date.setCalendarPopup(True)
    window.historico_hasta_date.setDisplayFormat("yyyy-MM-dd")
    filtros_row_2.addWidget(QLabel("Hasta"))
    filtros_row_2.addWidget(window.historico_hasta_date)
    window._apply_historico_default_range()

    window.historico_apply_filters_button = QPushButton("Aplicar")
    window.historico_apply_filters_button.setProperty("variant", "secondary")
    filtros_row_2.addWidget(window.historico_apply_filters_button)

    filtros_row_2.addStretch(1)
    filtros_layout.addLayout(filtros_row_2)
    historico_filters_panel = QWidget()
    historico_filters_layout = QVBoxLayout(historico_filters_panel)
    historico_filters_layout.setContentsMargins(0, 0, 0, 0)
    historico_filters_layout.setSpacing(0)
    historico_filters_layout.addLayout(filtros_layout)
    historico_details_layout.addWidget(historico_filters_panel)

    window.historico_table = QTableView()
    window.historico_view_model = HistoricalViewModel([])
    window.historico_model = window.historico_view_model.source_model
    window.historico_proxy_model = window.historico_view_model.proxy_model
    window.historico_model.set_show_delegada(True)
    window.historico_table.setModel(window.historico_proxy_model)
    window.historico_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    window.historico_table.setSelectionMode(QAbstractItemView.MultiSelection)
    window.historico_table.selectionModel().selectionChanged.connect(window._on_historico_selection_changed)
    window.historico_table.doubleClicked.connect(window._on_open_historico_detalle)
    window.historico_table.setShowGrid(False)
    window.historico_table.setAlternatingRowColors(True)
    window.historico_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    window.historico_table.setMinimumHeight(260)
    window._configure_solicitudes_table(window.historico_table)
    window.historico_table.setSortingEnabled(True)
    historico_header = window.historico_table.horizontalHeader()
    historico_header.setSectionResizeMode(QHeaderView.Stretch)
    historico_details_layout.addWidget(window.historico_table, 1)

    window.historico_export_hint_label = QLabel("Para exportar, selecciona los registros que quieras exportar.")
    window.historico_export_hint_label.setProperty("role", "secondary")
    window.historico_export_hint_label.setStyleSheet("font-size: 11px;")
    historico_details_layout.addWidget(window.historico_export_hint_label)

    historico_actions = QHBoxLayout()
    historico_actions.setSpacing(10)
    window.historico_actions_layout = historico_actions
    window.eliminar_button = QPushButton("Eliminar (0)")
    window.eliminar_button.setProperty("variant", "primary")
    window.eliminar_button.setProperty("intent", "destructive")
    window.eliminar_button.clicked.connect(window._on_eliminar)
    historico_actions.addWidget(window.eliminar_button)

    window.generar_pdf_button = QPushButton("Exportar histórico PDF (0)")
    window.generar_pdf_button.setProperty("variant", "secondary")
    window.generar_pdf_button.clicked.connect(window._on_generar_pdf_historico)
    historico_actions.addWidget(window.generar_pdf_button)

    window.historico_select_all_visible_check = QCheckBox("Seleccionar todo (visible)")
    window.historico_select_all_visible_check.toggled.connect(window._on_historico_select_all_visible_toggled)
    historico_actions.addWidget(window.historico_select_all_visible_check)

    historico_actions.addStretch(1)

    window.historico_sync_button = QPushButton("Sincronizar con Google Sheets")
    window.historico_sync_button.setProperty("variant", "success")
    window.historico_sync_button.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
    window.historico_sync_button.clicked.connect(window._on_sync)
    historico_actions.addWidget(window.historico_sync_button)

    historico_details_layout.addLayout(historico_actions)
    historico_layout.addWidget(window.historico_details_content, 1)

    window.saldos_card = build_saldos_widget(window)
    historico_tab_layout.addWidget(historico_card, 1)

    window.main_tabs.addTab(historico_tab, "Histórico")

    config_tab = QWidget()
    config_tab_layout = QVBoxLayout(config_tab)
    config_tab_layout.setContentsMargins(0, 0, 0, 0)
    config_tab_layout.setSpacing(0)

    window.config_scroll_area = QScrollArea()
    window.config_scroll_area.setWidgetResizable(True)
    window.config_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.config_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    config_tab_layout.addWidget(window.config_scroll_area, 1)

    config_content = QWidget()
    config_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    config_layout = QVBoxLayout(config_content)
    config_layout.setContentsMargins(0, 0, 0, 0)
    config_layout.setSpacing(12)
    window.config_scroll_area.setWidget(config_content)
    config_help = QLabel("Define la configuración principal de la app: delegada, grupo/PDF y credenciales.")
    config_help.setWordWrap(True)
    config_help.setProperty("role", "secondary")
    config_layout.addWidget(config_help)

    # UX: Configuración reúne controles avanzados (delegado + ajustes + sync)
    # para que el uso diario no se distraiga con opciones administrativas.
    persona_card, persona_layout = window._create_card("Configuración delegada")

    persona_actions = QHBoxLayout()
    persona_actions.setSpacing(8)
    window.config_delegada_combo = QComboBox()
    window.config_delegada_combo.currentIndexChanged.connect(window._on_config_delegada_changed)
    persona_actions.addWidget(window.config_delegada_combo, 1)

    window.edit_persona_button = QPushButton("Editar")
    window.edit_persona_button.setProperty("variant", "success")
    window.edit_persona_button.clicked.connect(window._on_edit_persona)
    persona_actions.addWidget(window.edit_persona_button)

    window.delete_persona_button = QPushButton("Eliminar")
    window.delete_persona_button.setProperty("variant", "primary")
    window.delete_persona_button.setProperty("intent", "destructive")
    window.delete_persona_button.clicked.connect(window._on_delete_persona)
    persona_actions.addWidget(window.delete_persona_button)

    persona_actions.addStretch(1)
    window.add_persona_button = QPushButton("Nueva delegada")
    window.add_persona_button.setProperty("variant", "secondary")
    window.add_persona_button.clicked.connect(window._on_add_persona)
    persona_actions.addWidget(window.add_persona_button)
    persona_layout.addLayout(persona_actions)
    config_layout.addWidget(persona_card)

    grupo_card, grupo_layout = window._create_card("Grupo")
    grupo_actions = QHBoxLayout()
    grupo_actions.setSpacing(8)
    window.edit_grupo_button = QPushButton("Configurar grupo")
    window.edit_grupo_button.setProperty("variant", "secondary")
    window.edit_grupo_button.clicked.connect(window._on_edit_grupo)
    grupo_actions.addWidget(window.edit_grupo_button)
    grupo_actions.addStretch(1)
    grupo_layout.addLayout(grupo_actions)
    config_layout.addWidget(grupo_card)

    pdf_card, pdf_layout = window._create_card("PDF")
    pdf_actions = QHBoxLayout()
    pdf_actions.setSpacing(8)
    window.editar_pdf_button = QPushButton("Configurar PDF")
    window.editar_pdf_button.setProperty("variant", "secondary")
    window.editar_pdf_button.clicked.connect(window._on_edit_pdf)
    pdf_actions.addWidget(window.editar_pdf_button)
    pdf_actions.addStretch(1)
    pdf_layout.addLayout(pdf_actions)
    config_layout.addWidget(pdf_card)

    credenciales_card, credenciales_layout = window._create_card("Google Sheets")
    window.sync_source_label = QLabel("Fuente: --")
    window.sync_source_label.setProperty("role", "secondary")
    credenciales_layout.addWidget(window.sync_source_label)
    window.sync_scope_label = QLabel("Rango: --")
    window.sync_scope_label.setProperty("role", "secondary")
    credenciales_layout.addWidget(window.sync_scope_label)
    sync_actions = QHBoxLayout()
    sync_actions.setSpacing(8)
    window.opciones_button = QPushButton("Configurar conexión Google Sheets")
    window.opciones_button.setProperty("variant", "secondary")
    window.opciones_button.clicked.connect(window._on_open_opciones)
    sync_actions.addWidget(window.opciones_button)

    window.config_test_connection_button = QPushButton("Probar conexión")
    window.config_test_connection_button.setProperty("variant", "secondary")
    window.config_test_connection_button.clicked.connect(window._on_simulate_sync)
    sync_actions.addWidget(window.config_test_connection_button)

    window.config_sync_button = QPushButton("Sincronizar ahora")
    window.config_sync_button.setProperty("variant", "success")
    window.config_sync_button.clicked.connect(window._on_sync)
    sync_actions.addWidget(window.config_sync_button)
    sync_actions.addStretch(1)
    credenciales_layout.addLayout(sync_actions)
    config_layout.addWidget(credenciales_card)
    config_layout.addStretch(1)
    window.main_tabs.addTab(config_tab, "Configuración")

    sync_tab = QWidget()
    sync_tab_layout = QVBoxLayout(sync_tab)
    sync_tab_layout.setContentsMargins(0, 0, 0, 0)
    sync_tab_layout.setSpacing(12)
    sync_help = QLabel("Resumen de sincronización con acciones rápidas. El detalle técnico está en modo avanzado.")
    sync_help.setWordWrap(True)
    sync_help.setProperty("role", "secondary")
    sync_tab_layout.addWidget(sync_help)

    sync_state_card, sync_state_layout = window._create_card("Estado")
    window.last_sync_label = QLabel("Última sync: --")
    window.last_sync_label.setProperty("role", "secondary")
    sync_state_layout.addWidget(window.last_sync_label)
    window.sync_panel_status = QLabel("Estado: Pendiente")
    window.sync_panel_status.setProperty("role", "secondary")
    sync_state_layout.addWidget(window.sync_panel_status)
    window.sync_status_badge = QLabel(window._status_to_label("IDLE"))
    window.sync_status_badge.setProperty("role", "badge")
    window.sync_status_badge.setProperty("syncStatus", "IDLE")
    sync_state_layout.addWidget(window.sync_status_badge, alignment=Qt.AlignLeft)
    sync_tab_layout.addWidget(sync_state_card)

    sync_card, sync_layout = window._create_card("Acciones")
    sync_heading = QLabel("Google Sheets")
    sync_heading.setProperty("role", "sectionTitle")
    sync_layout.addWidget(sync_heading)
    sync_actions = QHBoxLayout()
    sync_actions.setSpacing(8)
    window.sync_button = QPushButton("Sincronizar ahora")
    window.sync_button.setProperty("variant", "primary")
    window.sync_button.clicked.connect(window._on_sync)
    sync_actions.addWidget(window.sync_button)

    window.simulate_sync_button = QPushButton("Simular sincronización")
    window.simulate_sync_button.setProperty("variant", "secondary")
    window.simulate_sync_button.clicked.connect(window._on_simulate_sync)
    sync_actions.addWidget(window.simulate_sync_button)

    window.confirm_sync_button = QPushButton("Sincronizar ahora")
    window.confirm_sync_button.setProperty("variant", "primary")
    window.confirm_sync_button.setEnabled(False)
    window.confirm_sync_button.clicked.connect(window._on_confirm_sync)
    sync_actions.addWidget(window.confirm_sync_button)

    window.retry_failed_button = QPushButton("Reintentar solo fallidos")
    window.retry_failed_button.setProperty("variant", "secondary")
    window.retry_failed_button.setEnabled(False)
    window.retry_failed_button.clicked.connect(window._on_retry_failed)
    sync_actions.addWidget(window.retry_failed_button)

    window.sync_details_button = QPushButton("Ver detalles")
    window.sync_details_button.setProperty("variant", "secondary")
    window.sync_details_button.setEnabled(False)
    window.sync_details_button.clicked.connect(window._on_show_sync_details)

    window.copy_sync_report_button = QPushButton("Copiar informe")
    window.copy_sync_report_button.setProperty("variant", "secondary")
    window.copy_sync_report_button.setEnabled(False)
    window.copy_sync_report_button.clicked.connect(window._on_copy_sync_report)

    window.open_sync_logs_button = QPushButton("Abrir carpeta de logs")
    window.open_sync_logs_button.setProperty("variant", "secondary")
    window.open_sync_logs_button.clicked.connect(window._on_open_sync_logs)

    window.sync_history_button = QPushButton("Ver historial")
    window.sync_history_button.setProperty("variant", "secondary")
    window.sync_history_button.clicked.connect(window._on_show_sync_history)

    window.review_conflicts_button = QPushButton("Revisar conflictos")
    window.review_conflicts_button.setProperty("variant", "secondary")
    window.review_conflicts_button.setEnabled(False)
    window.review_conflicts_button.clicked.connect(window._on_review_conflicts)
    sync_actions.addWidget(window.review_conflicts_button)
    sync_layout.addLayout(sync_actions)

    window.last_sync_metrics_label = QLabel("Duración: -- · Cambios: -- · Conflictos: -- · Errores: --")
    window.last_sync_metrics_label.setProperty("role", "secondary")
    sync_layout.addWidget(window.last_sync_metrics_label)

    window.sync_trend_label = QLabel("Tendencia (5): --")
    window.sync_trend_label.setProperty("role", "secondary")

    window.sync_idempotency_label = QLabel("Evita duplicados: --")
    window.sync_idempotency_label.setProperty("role", "secondary")

    window.sync_counts_label = QLabel("Resumen: creadas 0 · actualizadas 0 · omitidas 0 · conflictos 0 · errores 0")
    window.sync_counts_label.setProperty("role", "secondary")
    sync_layout.addWidget(window.sync_counts_label)

    window.go_to_sync_config_button = QPushButton("Ir a configuración")
    window.go_to_sync_config_button.setProperty("variant", "secondary")
    window.go_to_sync_config_button.setVisible(False)
    window.go_to_sync_config_button.clicked.connect(window._on_open_opciones)
    sync_layout.addWidget(window.go_to_sync_config_button, alignment=Qt.AlignLeft)

    window.sync_status_label = QLabel("Sincronizando con Google Sheets…")
    window.sync_status_label.setProperty("role", "secondary")
    window.sync_status_label.setVisible(False)
    window.sync_progress = QProgressBar()
    window.sync_progress.setRange(0, 0)
    window.sync_progress.setTextVisible(False)
    window.sync_progress.setVisible(False)
    sync_status_row = QHBoxLayout()
    sync_status_row.setSpacing(8)
    sync_status_row.addWidget(window.sync_status_label)
    sync_status_row.addWidget(window.sync_progress, 1)
    sync_layout.addLayout(sync_status_row)

    window.alert_banner_label = QLabel("Alertas: sin alertas activas.")
    window.alert_banner_label.setProperty("role", "secondary")
    sync_layout.addWidget(window.alert_banner_label)

    window.conflicts_reminder_label = QLabel("Hay 0 conflictos pendientes de revisión.")
    window.conflicts_reminder_label.setProperty("role", "secondary")
    window.conflicts_reminder_label.setVisible(False)
    sync_layout.addWidget(window.conflicts_reminder_label)

    sync_tab_layout.addWidget(sync_card)

    resumen_card, resumen_layout = window._create_card("Resultado resumido")
    resumen_layout.addWidget(window.sync_counts_label)
    resumen_layout.addWidget(window.last_sync_metrics_label)
    sync_tab_layout.addWidget(resumen_card)

    diagnostics_card, diagnostics_layout = window._create_card("Panel avanzado")
    window.sync_diagnostics_button = QToolButton()
    window.sync_diagnostics_button.setText("Detalles técnicos")
    window.sync_diagnostics_button.setCheckable(True)
    window.sync_diagnostics_button.setChecked(False)
    window.sync_diagnostics_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
    diagnostics_layout.addWidget(window.sync_diagnostics_button, alignment=Qt.AlignLeft)
    window.sync_diagnostics_content = QWidget()
    window.sync_diagnostics_content.setVisible(False)
    diagnostics_content_layout = QVBoxLayout(window.sync_diagnostics_content)
    diagnostics_content_layout.setContentsMargins(0, 0, 0, 0)
    diagnostics_content_layout.setSpacing(8)

    diagnostics_content_layout.addWidget(window.sync_source_label)
    diagnostics_content_layout.addWidget(window.sync_scope_label)
    diagnostics_content_layout.addWidget(window.sync_idempotency_label)
    diagnostics_content_layout.addWidget(window.sync_trend_label)
    diagnostics_content_layout.addWidget(window.sync_details_button)
    diagnostics_content_layout.addWidget(window.copy_sync_report_button)
    diagnostics_content_layout.addWidget(window.open_sync_logs_button)
    diagnostics_content_layout.addWidget(window.sync_history_button)

    health_card, health_layout = window._create_card("Salud del sistema")
    window.health_summary_label = QLabel("Estado general: pendiente de comprobación")
    window.health_summary_label.setProperty("role", "secondary")
    health_layout.addWidget(window.health_summary_label)
    window.health_checks_tree = QTreeWidget()
    window.health_checks_tree.setColumnCount(4)
    window.health_checks_tree.setHeaderLabels(["Estado", "Categoría", "Mensaje", "Acción"])
    window.health_checks_tree.setMinimumHeight(180)
    health_layout.addWidget(window.health_checks_tree)
    health_actions = QHBoxLayout()
    window.refresh_health_button = QPushButton("Actualizar salud")
    window.refresh_health_button.setProperty("variant", "secondary")
    window.refresh_health_button.clicked.connect(window._refresh_health_and_alerts)
    health_actions.addWidget(window.refresh_health_button)
    window.snooze_alerts_button = QPushButton("No mostrar hoy")
    window.snooze_alerts_button.setProperty("variant", "secondary")
    window.snooze_alerts_button.clicked.connect(window._on_snooze_alerts_today)
    health_actions.addWidget(window.snooze_alerts_button)
    health_actions.addStretch(1)
    health_layout.addLayout(health_actions)

    diagnostics_content_layout.addWidget(health_card)
    diagnostics_card.layout().addWidget(window.sync_diagnostics_content)
    window.sync_diagnostics_button.toggled.connect(window.sync_diagnostics_content.setVisible)
    sync_tab_layout.addWidget(diagnostics_card)
    sync_tab_layout.addStretch(1)
    sync_tab_index = window.main_tabs.addTab(sync_tab, "Sincronización")
    window.main_tabs.setTabVisible(sync_tab_index, False)

    window._scroll_area.setWidget(content)
    window._build_shell_layout()
    window._build_status_bar()

    window._normalize_input_heights()
    window._update_responsive_columns()
    window._configure_time_placeholders()
    window._configure_operativa_focus_order()
    window._configure_historico_focus_order()
    window._bind_preventive_validation_events()
    window._historico_search_timer = QTimer(window)
    window._historico_search_timer.setSingleShot(True)
    window._historico_search_timer.setInterval(250)
    window._historico_search_timer.timeout.connect(window._apply_historico_text_filter)
    window.historico_todas_delegadas_check.toggled.connect(window._on_historico_todas_delegadas_toggled)
    window.historico_periodo_anual_radio.toggled.connect(window._on_historico_periodo_mode_changed)
    window.historico_periodo_mes_radio.toggled.connect(window._on_historico_periodo_mode_changed)
    window.historico_periodo_rango_radio.toggled.connect(window._on_historico_periodo_mode_changed)
    window.historico_apply_filters_button.clicked.connect(window._on_historico_apply_filters)
    window.open_saldos_modal_button.clicked.connect(window._on_open_saldos_modal)
    window.main_tabs.currentChanged.connect(window._on_main_tab_changed)
    window._restaurar_contexto_guardado()
    window._on_historico_todas_delegadas_toggled(window.historico_todas_delegadas_check.isChecked())
    window._on_historico_periodo_mode_changed()
    logger.info("UI_HISTORICO_FILTERS_BUILT")

    from PySide6.QtGui import QKeySequence, QShortcut

    window._historico_find_shortcut = QShortcut(QKeySequence.Find, window)
    window._historico_find_shortcut.activated.connect(window._focus_historico_search)
    window._historico_detail_shortcut = QShortcut(QKeySequence(Qt.Key_Return), window.historico_table)
    window._historico_detail_shortcut.activated.connect(window._on_open_historico_detalle)
    window._historico_escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), window)
    window._historico_escape_shortcut.activated.connect(window._on_historico_escape)

    window._apply_historico_filters()
    window._update_solicitud_preview()
    window._update_action_state()
    window.main_tabs.currentChanged.connect(lambda index: on_tab_changed(window, index))

def build_shell_layout(window: "MainWindow") -> None:
    window.setCentralWidget(window._scroll_area)



def on_tab_changed(window: "MainWindow", index: int) -> None:
    if index == 0:
        persona = window._current_persona()
        window._restore_draft_for_persona(persona.id if persona is not None else None)
        window.fecha_input.setFocus()
        return
    if index == 1:
        window._refresh_historico()
        return
    if index == 2:
        window._refresh_saldos()

def build_status_bar(window: "MainWindow") -> None:
    status = QStatusBar(window)
    status.setObjectName("mainStatusBar")
    window.setStatusBar(status)
    window.status_sync_label = QLabel("Sincronizando con Google Sheets…")
    window.status_sync_label.setVisible(False)
    window.status_sync_progress = QProgressBar()
    window.status_sync_progress.setRange(0, 0)
    window.status_sync_progress.setTextVisible(False)
    window.status_sync_progress.setVisible(False)
    window.status_pending_label = QLabel("Pendiente: 00:00")
    status.addPermanentWidget(window.status_sync_label)
    status.addPermanentWidget(window.status_sync_progress)
    status.addPermanentWidget(window.status_pending_label)
