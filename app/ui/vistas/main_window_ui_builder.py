from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialogButtonBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTableView,
    QTextEdit,
    QTimeEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.saldos_card import SaldosCard
from app.ui.historico_view import ESTADOS_HISTORICO, HistoricalViewModel
from app.ui.models_qt import SolicitudesTableModel
from app.ui.patterns import STATUS_PATTERNS
from app.ui.vistas.paginas.pagina_solicitudes import PaginaSolicitudes


def create_widgets(window) -> None:
    self = window
    self.persona_combo = QComboBox()
    self._scroll_area = QScrollArea()
    self._scroll_area.setWidgetResizable(True)
    self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    content = QWidget()
    content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(20, 16, 20, 20)
    layout.setSpacing(16)

    self.main_tabs = QTabWidget()
    self.main_tabs.setObjectName("mainTabs")
    self.main_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    self.main_tabs.tabBar().hide()
    # Navegación y acciones viven en la propia página, no en una cabecera global.
    layout.addWidget(self.main_tabs, 1)

    operativa_tab = QWidget()
    operativa_layout = QVBoxLayout(operativa_tab)
    operativa_layout.setContentsMargins(0, 0, 0, 0)
    operativa_layout.setSpacing(12)
    operativa_help = QLabel("Completa la solicitud y confirma solo cuando estés lista.")
    operativa_help.setWordWrap(True)
    operativa_help.setProperty("role", "secondary")
    operativa_layout.addWidget(operativa_help)

    # UX: Operativa concentra solo tareas diarias (alta + pendientes + confirmación)
    # para reducir cambios de contexto y evitar mezclar navegación histórica.
    self.solicitudes_splitter = QSplitter(Qt.Orientation.Vertical)
    self.solicitudes_splitter.setObjectName("solicitudesSplitter")
    self.solicitudes_splitter.setChildrenCollapsible(False)
    self.solicitudes_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    operativa_layout.addWidget(self.solicitudes_splitter, 1)

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

    solicitud_card, solicitud_layout = self._create_card("Alta de solicitud")
    solicitud_layout.setSpacing(12)

    self.stepper_labels: list[QLabel] = []
    self._step_bullets: list[QLabel] = []
    self._step_titles = [
        "Completar datos",
        "Revisar pendientes",
        "Confirmar",
    ]
    stepper_layout = QHBoxLayout()
    stepper_layout.setSpacing(8)
    stepper_layout.setContentsMargins(0, 0, 0, 0)
    for step_text in self._step_titles:
        step_container = QFrame()
        step_container.setProperty("role", "stepContainer")
        step_container.setFixedHeight(30)
        step_container_layout = QHBoxLayout(step_container)
        step_container_layout.setContentsMargins(8, 4, 8, 4)
        step_container_layout.setSpacing(6)

        bullet = QLabel("1")
        bullet.setProperty("role", "stepBulletIdle")
        self._step_bullets.append(bullet)
        step_container_layout.addWidget(bullet)

        step_label = QLabel(step_text)
        step_label.setProperty("role", "stepIdle")
        self.stepper_labels.append(step_label)
        step_container_layout.addWidget(step_label)

        stepper_layout.addWidget(step_container)
    stepper_layout.addStretch(1)
    solicitud_layout.addLayout(stepper_layout)

    self.stepper_context_label = QLabel("Pendientes: 0 · Seleccionadas: 0 · Modo: Delegada")
    self.stepper_context_label.setProperty("role", "secondary")
    solicitud_layout.addWidget(self.stepper_context_label)

    self.confirmation_summary_label = QLabel("")
    self.confirmation_summary_label.setProperty("role", "secondary")
    self.confirmation_summary_label.setVisible(False)
    self.confirmation_summary_label.setWordWrap(True)
    solicitud_layout.addWidget(self.confirmation_summary_label)

    self.pending_errors_frame = QFrame()
    self.pending_errors_frame.setProperty("role", "error")
    pending_errors_layout = QVBoxLayout(self.pending_errors_frame)
    pending_errors_layout.setContentsMargins(10, 8, 10, 8)
    pending_errors_layout.setSpacing(6)
    self.pending_errors_title = QLabel("Errores pendientes")
    self.pending_errors_title.setProperty("role", "sectionTitle")
    pending_errors_layout.addWidget(self.pending_errors_title)
    self.pending_errors_summary = QLabel("")
    self.pending_errors_summary.setWordWrap(True)
    pending_errors_layout.addWidget(self.pending_errors_summary)
    self.goto_existing_button = QPushButton("Ir a la existente")
    self.goto_existing_button.setProperty("variant", "ghost")
    self.goto_existing_button.clicked.connect(self._on_go_to_existing_duplicate)
    self.goto_existing_button.setVisible(False)
    pending_errors_layout.addWidget(self.goto_existing_button)
    self.pending_errors_frame.setVisible(False)
    solicitud_layout.addWidget(self.pending_errors_frame)

    datos_basicos_label = QLabel("Datos de la Reserva")
    datos_basicos_label.setProperty("role", "sectionTitle")
    solicitud_layout.addWidget(datos_basicos_label)

    persona_row = QHBoxLayout()
    persona_row.setSpacing(10)
    persona_label = QLabel("Delegada")
    persona_label.setProperty("role", "sectionTitle")
    persona_row.addWidget(persona_label)
    self.persona_combo.currentIndexChanged.connect(self._on_persona_changed)
    persona_row.addWidget(self.persona_combo, 1)
    persona_row.addStretch(1)
    self.nueva_solicitud_button = QPushButton("Nueva solicitud")
    self.nueva_solicitud_button.setProperty("variant", "primary")
    self.nueva_solicitud_button.clicked.connect(self._clear_form)
    persona_row.addWidget(self.nueva_solicitud_button)
    solicitud_layout.addLayout(persona_row)

    solicitud_row = QHBoxLayout()
    solicitud_row.setSpacing(10)
    solicitud_row.addWidget(QLabel("Fecha"))
    self.fecha_input = QDateEdit(QDate.currentDate())
    self.fecha_input.setCalendarPopup(True)
    self.fecha_input.dateChanged.connect(self._on_fecha_changed)
    solicitud_row.addWidget(self.fecha_input)

    self.desde_input = QTimeEdit(QTime(9, 0))
    self.desde_input.setDisplayFormat("HH:mm")
    self.desde_input.timeChanged.connect(self._update_solicitud_preview)
    self.desde_container = QWidget()
    desde_layout = QHBoxLayout(self.desde_container)
    desde_layout.setContentsMargins(0, 0, 0, 0)
    desde_layout.setSpacing(6)
    desde_layout.addWidget(QLabel("Desde"))
    desde_layout.addWidget(self.desde_input)
    solicitud_row.addWidget(self.desde_container)

    self.desde_placeholder = QWidget()
    self.desde_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    solicitud_row.addWidget(self.desde_placeholder)

    self.hasta_input = QTimeEdit(QTime(17, 0))
    self.hasta_input.setDisplayFormat("HH:mm")
    self.hasta_input.timeChanged.connect(self._update_solicitud_preview)
    self.hasta_container = QWidget()
    hasta_layout = QHBoxLayout(self.hasta_container)
    hasta_layout.setContentsMargins(0, 0, 0, 0)
    hasta_layout.setSpacing(6)
    hasta_layout.addWidget(QLabel("Hasta"))
    hasta_layout.addWidget(self.hasta_input)
    solicitud_row.addWidget(self.hasta_container)

    self.hasta_placeholder = QWidget()
    self.hasta_placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    solicitud_row.addWidget(self.hasta_placeholder)

    self.completo_check = QCheckBox("Completo")
    self.completo_check.toggled.connect(self._on_completo_changed)
    solicitud_row.addWidget(self.completo_check)

    self.total_preview_label = QLabel("Información de saldo")
    self.total_preview_label.setProperty("role", "secondary")
    solicitud_row.addWidget(self.total_preview_label)

    self.total_preview_input = QLineEdit("00:00")
    self.total_preview_input.setReadOnly(True)
    self.total_preview_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.total_preview_input.setMaximumWidth(84)
    solicitud_row.addWidget(self.total_preview_input)

    self.consequence_microcopy_label = QLabel("Esta acción consumirá 0 horas del saldo disponible.")
    self.consequence_microcopy_label.setProperty("role", "secondary")
    solicitud_row.addWidget(self.consequence_microcopy_label)

    self.cuadrante_warning_label = QLabel("")
    self.cuadrante_warning_label.setProperty("role", "secondary")
    self.cuadrante_warning_label.setVisible(False)
    solicitud_row.addWidget(self.cuadrante_warning_label)

    self.agregar_button = QPushButton("Añadir a pendientes")
    self.agregar_button.setProperty("variant", "secondary")
    self.agregar_button.clicked.connect(
        self._on_add_pendiente,
        Qt.ConnectionType.UniqueConnection,
    )
    solicitud_row.addWidget(self.agregar_button)
    solicitud_row.addStretch(1)
    solicitud_layout.addLayout(solicitud_row)

    validacion_label = QLabel("Errores pendientes")
    validacion_label.setProperty("role", "sectionTitle")
    solicitud_layout.addWidget(validacion_label)

    self.solicitud_inline_error = QLabel("")
    self.solicitud_inline_error.setProperty("role", "error")
    self.solicitud_inline_error.setVisible(False)
    solicitud_layout.addWidget(self.solicitud_inline_error)

    self.delegada_field_error = QLabel("")
    self.delegada_field_error.setProperty("role", "error")
    self.delegada_field_error.setVisible(False)
    solicitud_layout.addWidget(self.delegada_field_error)

    self.fecha_field_error = QLabel("")
    self.fecha_field_error.setProperty("role", "error")
    self.fecha_field_error.setVisible(False)
    solicitud_layout.addWidget(self.fecha_field_error)

    self.tramo_field_error = QLabel("")
    self.tramo_field_error.setProperty("role", "error")
    self.tramo_field_error.setVisible(False)
    solicitud_layout.addWidget(self.tramo_field_error)


    notas_row = QHBoxLayout()
    notas_row.setSpacing(8)
    notas_row.addWidget(QLabel("Notas"))
    self.notas_input = QPlainTextEdit()
    self.notas_input.setPlaceholderText("Notas para la solicitud")
    lineas_visibles_notas = 3
    altura_linea_notas = self.notas_input.fontMetrics().lineSpacing()
    margen_documento_notas = int(self.notas_input.document().documentMargin() * 2)
    altura_borde_notas = self.notas_input.frameWidth() * 2
    altura_compacta_notas = (altura_linea_notas * lineas_visibles_notas) + margen_documento_notas + altura_borde_notas
    self.notas_input.setFixedHeight(altura_compacta_notas)
    self.notas_input.installEventFilter(self)
    self.persona_combo.installEventFilter(self)
    self.fecha_input.installEventFilter(self)
    self.desde_input.installEventFilter(self)
    self.hasta_input.installEventFilter(self)
    self.completo_check.installEventFilter(self)
    self.notas_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    notas_row.addWidget(self.notas_input, 1)
    solicitud_layout.addLayout(notas_row)
    solicitudes_form_layout.addWidget(solicitud_card)

    pendientes_card, pendientes_layout = self._create_card("Pendientes de confirmar")
    self._pendientes_group = pendientes_card
    pending_tools = QHBoxLayout()
    pending_tools.setSpacing(8)
    self.ver_todas_pendientes_button = QPushButton("Ver todas")
    self.ver_todas_pendientes_button.setProperty("variant", "ghost")
    self.ver_todas_pendientes_button.setCheckable(True)
    self.ver_todas_pendientes_button.toggled.connect(self._on_toggle_ver_todas_pendientes)
    pending_tools.addWidget(self.ver_todas_pendientes_button)
    self.revisar_ocultas_button = QPushButton("Revisar pendientes ocultas")
    self.revisar_ocultas_button.setProperty("variant", "ghost")
    self.revisar_ocultas_button.setVisible(False)
    self.revisar_ocultas_button.clicked.connect(self._on_review_hidden_pendientes)
    pending_tools.addWidget(self.revisar_ocultas_button)
    self.pending_details_button = QPushButton("Detalles activos")
    self.pending_details_button.setProperty("variant", "ghost")
    pending_tools.addWidget(self.pending_details_button)
    self.pending_filter_warning = QLabel("")
    self.pending_filter_warning.setProperty("role", "secondary")
    self.pending_filter_warning.setVisible(False)
    pending_tools.addWidget(self.pending_filter_warning)
    pending_tools.addStretch(1)
    pendientes_layout.addLayout(pending_tools)

    self.pending_details_content = QWidget()
    pending_details_layout = QVBoxLayout(self.pending_details_content)
    pending_details_layout.setContentsMargins(0, 0, 0, 0)
    pending_details_layout.setSpacing(12)

    self.pendientes_table = QTableView()
    self.pendientes_model = SolicitudesTableModel([])
    self.pendientes_table.setModel(self.pendientes_model)
    self.pendientes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    self.pendientes_table.setSelectionMode(QAbstractItemView.MultiSelection)
    self.pendientes_table.selectionModel().selectionChanged.connect(self._update_action_state)
    self.pendientes_table.setShowGrid(False)
    self.pendientes_table.setAlternatingRowColors(True)
    self.pendientes_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    self.pendientes_table.setMinimumHeight(220)
    self._configure_solicitudes_table(self.pendientes_table)
    pending_details_layout.addWidget(self.pendientes_table, 1)

    self.huerfanas_label = QLabel("Reparar · Pendientes huérfanas")
    self.huerfanas_label.setProperty("role", "sectionTitle")
    self.huerfanas_label.setVisible(False)
    pending_details_layout.addWidget(self.huerfanas_label)

    self.huerfanas_table = QTableView()
    self.huerfanas_model = SolicitudesTableModel([])
    self.huerfanas_table.setModel(self.huerfanas_model)
    self.huerfanas_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    self.huerfanas_table.setSelectionMode(QAbstractItemView.SingleSelection)
    self.huerfanas_table.setShowGrid(False)
    self.huerfanas_table.setAlternatingRowColors(True)
    self.huerfanas_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    self.huerfanas_table.setMinimumHeight(120)
    self._configure_solicitudes_table(self.huerfanas_table)
    self.huerfanas_table.setVisible(False)
    pending_details_layout.addWidget(self.huerfanas_table)

    footer_separator = QFrame()
    footer_separator.setProperty("role", "subtleSeparator")
    footer_separator.setFixedHeight(1)
    pending_details_layout.addWidget(footer_separator)

    pendientes_footer = QHBoxLayout()
    pendientes_footer.setSpacing(10)

    left_actions = QHBoxLayout()
    left_actions.setSpacing(8)
    self.eliminar_pendiente_button = QPushButton("Eliminar selección")
    self.eliminar_pendiente_button.setProperty("variant", "ghost")
    self.eliminar_pendiente_button.clicked.connect(self._on_remove_pendiente)
    left_actions.addWidget(self.eliminar_pendiente_button)

    self.eliminar_huerfana_button = QPushButton("Eliminar huérfana")
    self.eliminar_huerfana_button.setProperty("variant", "ghost")
    self.eliminar_huerfana_button.clicked.connect(self._on_remove_huerfana)
    self.eliminar_huerfana_button.setVisible(False)
    left_actions.addWidget(self.eliminar_huerfana_button)

    self.insertar_sin_pdf_button = QPushButton("Confirmar sin PDF")
    self.insertar_sin_pdf_button.setProperty("variant", "secondary")
    self.insertar_sin_pdf_button.clicked.connect(self._on_insertar_sin_pdf)
    left_actions.addWidget(self.insertar_sin_pdf_button)
    pendientes_footer.addLayout(left_actions)

    pendientes_footer.addStretch(1)

    right_actions = QHBoxLayout()
    right_actions.setSpacing(10)
    self.total_pendientes_label = QLabel("Total: 00:00")
    self.total_pendientes_label.setProperty("role", "sectionTitle")
    right_actions.addWidget(self.total_pendientes_label)

    self.abrir_pdf_check = QCheckBox("Abrir PDF")
    self.abrir_pdf_check.setChecked(True)
    right_actions.addWidget(self.abrir_pdf_check)

    self.confirmar_button = QPushButton("Confirmar y generar PDF")
    self.confirmar_button.setProperty("variant", "secondary")
    self.confirmar_button.clicked.connect(self._on_confirmar)
    right_actions.addWidget(self.confirmar_button)

    self.primary_cta_button = QPushButton("Añadir a pendientes")
    self.primary_cta_button.setProperty("variant", "primary")
    self.primary_cta_button.setProperty("role", "dominantCta")
    self.primary_cta_button.clicked.connect(self._on_primary_cta_clicked)
    right_actions.addWidget(self.primary_cta_button)

    self.primary_cta_hint = QLabel("")
    self.primary_cta_hint.setProperty("role", "secondary")
    right_actions.addWidget(self.primary_cta_hint)

    pendientes_footer.addLayout(right_actions)
    pending_details_layout.addLayout(pendientes_footer)
    pendientes_layout.addWidget(self.pending_details_content, 1)
    self.pending_details_button.setCheckable(False)
    self.pending_details_button.setEnabled(False)
    self.pending_details_content.setVisible(True)
    solicitudes_list_layout.addWidget(pendientes_card, 1)
    self.solicitudes_splitter.addWidget(solicitudes_form_panel)
    self.solicitudes_splitter.addWidget(solicitudes_list_panel)
    self.solicitudes_splitter.setStretchFactor(0, 3)
    self.solicitudes_splitter.setStretchFactor(1, 2)

    self.main_tabs.addTab(operativa_tab, "Operativa")

    historico_tab = QWidget()
    historico_tab_layout = QVBoxLayout(historico_tab)
    historico_tab_layout.setContentsMargins(0, 0, 0, 0)
    historico_tab_layout.setSpacing(12)
    historico_help = QLabel("Consulta y filtra solicitudes confirmadas. Si no hay registros, crea la primera solicitud.")
    historico_help.setWordWrap(True)
    historico_help.setProperty("role", "secondary")
    historico_tab_layout.addWidget(historico_help)

    historico_card, historico_layout = self._create_card("Histórico")

    self.historico_empty_state = QWidget()
    empty_layout = QVBoxLayout(self.historico_empty_state)
    empty_layout.setContentsMargins(0, 8, 0, 8)
    empty_layout.setSpacing(8)
    empty_title = QLabel("Aún no hay histórico")
    empty_title.setProperty("role", "sectionTitle")
    empty_layout.addWidget(empty_title)
    empty_text = QLabel("Cuando confirmes solicitudes aparecerán aquí con filtros por texto, estado y fechas.")
    empty_text.setWordWrap(True)
    empty_text.setProperty("role", "secondary")
    empty_layout.addWidget(empty_text)
    self.historico_empty_button = QPushButton("Crear primera solicitud")
    self.historico_empty_button.setProperty("variant", "primary")
    self.historico_empty_button.clicked.connect(lambda: self.main_tabs.setCurrentIndex(0))
    empty_layout.addWidget(self.historico_empty_button, alignment=Qt.AlignLeft)
    historico_layout.addWidget(self.historico_empty_state)

    self.historico_details_button = QPushButton("Ver filtros y listado")
    self.historico_details_button.setProperty("variant", "secondary")
    historico_layout.addWidget(self.historico_details_button)
    self.historico_details_content = QWidget()
    historico_details_layout = QVBoxLayout(self.historico_details_content)
    historico_details_layout.setContentsMargins(0, 0, 0, 0)
    historico_details_layout.setSpacing(8)
    self._historico_group = historico_card
    historico_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    filtros_layout = QVBoxLayout()
    filtros_layout.setSpacing(8)

    filtros_row_1 = QHBoxLayout()
    filtros_row_1.setSpacing(8)
    self.historico_search_input = QLineEdit()
    self.historico_search_input.setPlaceholderText("Buscar en concepto/notas/columnas…")
    filtros_row_1.addWidget(QLabel("Buscar"))
    filtros_row_1.addWidget(self.historico_search_input, 1)

    self.historico_estado_combo = QComboBox()
    self.historico_estado_combo.addItem("Todos", None)
    for estado in ESTADOS_HISTORICO.values():
        self.historico_estado_combo.addItem(estado.label, estado.code)
    filtros_row_1.addWidget(QLabel("Estado"))
    filtros_row_1.addWidget(self.historico_estado_combo)

    self.historico_delegada_combo = QComboBox()
    self.historico_delegada_combo.addItem("Todas", None)
    filtros_row_1.addWidget(QLabel("Delegada"))
    filtros_row_1.addWidget(self.historico_delegada_combo)
    filtros_layout.addLayout(filtros_row_1)

    filtros_row_2 = QHBoxLayout()
    filtros_row_2.setSpacing(8)
    self.historico_desde_date = QDateEdit()
    self.historico_desde_date.setCalendarPopup(True)
    self.historico_desde_date.setDisplayFormat("yyyy-MM-dd")
    self.historico_desde_date.setDate(QDate.currentDate().addDays(-30))
    filtros_row_2.addWidget(QLabel("Desde"))
    filtros_row_2.addWidget(self.historico_desde_date)

    self.historico_hasta_date = QDateEdit()
    self.historico_hasta_date.setCalendarPopup(True)
    self.historico_hasta_date.setDisplayFormat("yyyy-MM-dd")
    self.historico_hasta_date.setDate(QDate.currentDate())
    filtros_row_2.addWidget(QLabel("Hasta"))
    filtros_row_2.addWidget(self.historico_hasta_date)

    self.historico_last_30_button = QPushButton("Últimos 30 días")
    self.historico_last_30_button.setProperty("variant", "secondary")
    filtros_row_2.addWidget(self.historico_last_30_button)

    self.historico_clear_filters_button = QPushButton("Limpiar filtros")
    self.historico_clear_filters_button.setProperty("variant", "secondary")
    filtros_row_2.addWidget(self.historico_clear_filters_button)
    self.historico_sync_button = QPushButton("Sync")
    self.historico_sync_button.setProperty("variant", "secondary")
    self.historico_sync_button.clicked.connect(self._on_sync)
    filtros_row_2.addWidget(self.historico_sync_button)
    filtros_row_2.addStretch(1)
    filtros_layout.addLayout(filtros_row_2)
    historico_filters_panel = QWidget()
    historico_filters_layout = QVBoxLayout(historico_filters_panel)
    historico_filters_layout.setContentsMargins(0, 0, 0, 0)
    historico_filters_layout.setSpacing(0)
    historico_filters_layout.addLayout(filtros_layout)
    historico_details_layout.addWidget(historico_filters_panel)

    self.historico_table = QTableView()
    self.historico_view_model = HistoricalViewModel([])
    self.historico_model = self.historico_view_model.source_model
    self.historico_proxy_model = self.historico_view_model.proxy_model
    self.historico_model.set_show_delegada(True)
    self.historico_table.setModel(self.historico_proxy_model)
    self.historico_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    self.historico_table.setSelectionMode(QAbstractItemView.MultiSelection)
    self.historico_table.selectionModel().selectionChanged.connect(self._on_historico_selection_changed)
    self.historico_table.doubleClicked.connect(self._on_open_historico_detalle)
    self.historico_table.setShowGrid(False)
    self.historico_table.setAlternatingRowColors(True)
    self.historico_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    self.historico_table.setMinimumHeight(260)
    self._configure_solicitudes_table(self.historico_table)
    self.historico_table.setSortingEnabled(True)
    historico_header = self.historico_table.horizontalHeader()
    historico_header.setSectionResizeMode(QHeaderView.Stretch)
    historico_details_layout.addWidget(self.historico_table, 1)

    historico_actions = QHBoxLayout()
    historico_actions.setSpacing(10)
    historico_actions.addStretch(1)
    self.eliminar_button = QPushButton("Eliminar (0)")
    self.eliminar_button.setProperty("variant", "primary")
    self.eliminar_button.setProperty("intent", "destructive")
    self.eliminar_button.clicked.connect(self._on_eliminar)
    historico_actions.addWidget(self.eliminar_button)

    self.ver_detalle_button = QPushButton("Ver detalle (0)")
    self.ver_detalle_button.setProperty("variant", "secondary")
    self.ver_detalle_button.clicked.connect(self._on_open_historico_detalle)
    historico_actions.addWidget(self.ver_detalle_button)

    self.resync_historico_button = QPushButton("Re-sincronizar (0)")
    self.resync_historico_button.setProperty("variant", "secondary")
    self.resync_historico_button.clicked.connect(self._on_resync_historico)
    historico_actions.addWidget(self.resync_historico_button)

    self.generar_pdf_button = QPushButton("Exportar histórico PDF (0)")
    self.generar_pdf_button.setProperty("variant", "secondary")
    self.generar_pdf_button.clicked.connect(self._on_generar_pdf_historico)
    historico_actions.addWidget(self.generar_pdf_button)
    historico_details_layout.addLayout(historico_actions)
    historico_layout.addWidget(self.historico_details_content, 1)
    self._configure_disclosure(
        self.historico_details_button,
        self.historico_details_content,
        collapsed_text="Ver filtros y listado",
        expanded_text="Ocultar filtros y listado",
        expandido_por_defecto=True,
    )

    self.saldos_card = SaldosCard()
    historico_tab_layout.addWidget(self.saldos_card)
    historico_tab_layout.addWidget(historico_card, 1)

    self.main_tabs.addTab(historico_tab, "Histórico")

    config_tab = QWidget()
    config_tab_layout = QVBoxLayout(config_tab)
    config_tab_layout.setContentsMargins(0, 0, 0, 0)
    config_tab_layout.setSpacing(0)

    self.config_scroll_area = QScrollArea()
    self.config_scroll_area.setWidgetResizable(True)
    self.config_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.config_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    config_tab_layout.addWidget(self.config_scroll_area, 1)

    config_content = QWidget()
    config_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    config_layout = QVBoxLayout(config_content)
    config_layout.setContentsMargins(0, 0, 0, 0)
    config_layout.setSpacing(12)
    self.config_scroll_area.setWidget(config_content)
    config_help = QLabel("Define la configuración principal de la app: delegada, grupo/PDF y credenciales.")
    config_help.setWordWrap(True)
    config_help.setProperty("role", "secondary")
    config_layout.addWidget(config_help)

    # UX: Configuración reúne controles avanzados (delegado + ajustes + sync)
    # para que el uso diario no se distraiga con opciones administrativas.
    persona_card, persona_layout = self._create_card("Delegada seleccionada")

    persona_actions = QHBoxLayout()
    persona_actions.setSpacing(8)
    self.add_persona_button = QPushButton("Nueva delegada")
    self.add_persona_button.setProperty("variant", "secondary")
    self.add_persona_button.clicked.connect(self._on_add_persona)
    persona_actions.addWidget(self.add_persona_button)

    self.edit_persona_button = QPushButton("Editar")
    self.edit_persona_button.setProperty("variant", "secondary")
    self.edit_persona_button.clicked.connect(self._on_edit_persona)
    persona_actions.addWidget(self.edit_persona_button)
    persona_layout.addLayout(persona_actions)

    persona_delete = QHBoxLayout()
    self.delete_persona_button = QPushButton("Eliminar")
    self.delete_persona_button.setProperty("variant", "primary")
    self.delete_persona_button.setProperty("intent", "destructive")
    self.delete_persona_button.clicked.connect(self._on_delete_persona)
    persona_delete.addWidget(self.delete_persona_button)
    persona_delete.addStretch(1)
    persona_layout.addLayout(persona_delete)
    self.config_delegada_combo = QComboBox()
    self.config_delegada_combo.addItem("Todas", None)
    self.config_delegada_combo.currentIndexChanged.connect(self._on_config_delegada_changed)
    persona_layout.addWidget(QLabel("Delegada activa"))
    persona_layout.addWidget(self.config_delegada_combo)
    config_layout.addWidget(persona_card)

    ajustes_card, ajustes_layout = self._create_card("Grupo y PDF")
    ajustes_help = QLabel("Configura grupo y plantilla PDF del informe.")
    ajustes_help.setWordWrap(True)
    ajustes_help.setProperty("role", "secondary")
    ajustes_layout.addWidget(ajustes_help)

    ajustes_actions = QHBoxLayout()
    ajustes_actions.setSpacing(8)
    self.edit_grupo_button = QPushButton("Configurar grupo")
    self.edit_grupo_button.setProperty("variant", "secondary")
    self.edit_grupo_button.clicked.connect(self._on_edit_grupo)
    ajustes_actions.addWidget(self.edit_grupo_button)

    self.editar_pdf_button = QPushButton("Configurar PDF")
    self.editar_pdf_button.setProperty("variant", "secondary")
    self.editar_pdf_button.clicked.connect(self._on_edit_pdf)
    ajustes_actions.addWidget(self.editar_pdf_button)

    self.opciones_button = QPushButton("Configurar credenciales")
    self.opciones_button.setProperty("variant", "secondary")
    self.opciones_button.clicked.connect(self._on_open_opciones)
    ajustes_actions.addWidget(self.opciones_button)
    ajustes_actions.addStretch(1)
    ajustes_layout.addLayout(ajustes_actions)
    config_layout.addWidget(ajustes_card)

    credenciales_card, credenciales_layout = self._create_card("Google Sheets")
    self.sync_source_label = QLabel("Fuente: --")
    self.sync_source_label.setProperty("role", "secondary")
    credenciales_layout.addWidget(self.sync_source_label)
    self.sync_scope_label = QLabel("Rango: --")
    self.sync_scope_label.setProperty("role", "secondary")
    credenciales_layout.addWidget(self.sync_scope_label)
    self.config_sync_button = QPushButton("Sync ahora")
    self.config_sync_button.setProperty("variant", "secondary")
    self.config_sync_button.clicked.connect(self._on_sync)
    credenciales_layout.addWidget(self.config_sync_button)
    self.config_test_connection_button = QPushButton("Probar conexión")
    self.config_test_connection_button.setProperty("variant", "secondary")
    self.config_test_connection_button.clicked.connect(self._on_simulate_sync)
    credenciales_layout.addWidget(self.config_test_connection_button)
    config_layout.addWidget(credenciales_card)
    config_layout.addStretch(1)
    self.main_tabs.addTab(config_tab, "Configuración")

    sync_tab = QWidget()
    sync_tab_layout = QVBoxLayout(sync_tab)
    sync_tab_layout.setContentsMargins(0, 0, 0, 0)
    sync_tab_layout.setSpacing(12)
    sync_help = QLabel("Resumen de sincronización con acciones rápidas. El detalle técnico está en modo avanzado.")
    sync_help.setWordWrap(True)
    sync_help.setProperty("role", "secondary")
    sync_tab_layout.addWidget(sync_help)

    sync_state_card, sync_state_layout = self._create_card("Estado")
    self.last_sync_label = QLabel("Última sync: --")
    self.last_sync_label.setProperty("role", "secondary")
    sync_state_layout.addWidget(self.last_sync_label)
    self.sync_panel_status = QLabel("Estado: Pendiente")
    self.sync_panel_status.setProperty("role", "secondary")
    sync_state_layout.addWidget(self.sync_panel_status)
    self.sync_status_badge = QLabel(self._status_to_label("IDLE"))
    self.sync_status_badge.setProperty("role", "badge")
    self.sync_status_badge.setProperty("syncStatus", "IDLE")
    sync_state_layout.addWidget(self.sync_status_badge, alignment=Qt.AlignLeft)
    sync_tab_layout.addWidget(sync_state_card)

    sync_card, sync_layout = self._create_card("Acciones")
    sync_heading = QLabel("Google Sheets")
    sync_heading.setProperty("role", "sectionTitle")
    sync_layout.addWidget(sync_heading)
    sync_actions = QHBoxLayout()
    sync_actions.setSpacing(8)
    self.sync_button = QPushButton("Sincronizar ahora")
    self.sync_button.setProperty("variant", "primary")
    self.sync_button.clicked.connect(self._on_sync)
    sync_actions.addWidget(self.sync_button)

    self.simulate_sync_button = QPushButton("Simular sincronización")
    self.simulate_sync_button.setProperty("variant", "secondary")
    self.simulate_sync_button.clicked.connect(self._on_simulate_sync)
    sync_actions.addWidget(self.simulate_sync_button)

    self.confirm_sync_button = QPushButton("Sincronizar ahora")
    self.confirm_sync_button.setProperty("variant", "primary")
    self.confirm_sync_button.setEnabled(False)
    self.confirm_sync_button.clicked.connect(self._on_confirm_sync)
    sync_actions.addWidget(self.confirm_sync_button)

    self.retry_failed_button = QPushButton("Reintentar solo fallidos")
    self.retry_failed_button.setProperty("variant", "secondary")
    self.retry_failed_button.setEnabled(False)
    self.retry_failed_button.clicked.connect(self._on_retry_failed)
    sync_actions.addWidget(self.retry_failed_button)

    self.sync_details_button = QPushButton("Ver detalles")
    self.sync_details_button.setProperty("variant", "secondary")
    self.sync_details_button.setEnabled(False)
    self.sync_details_button.clicked.connect(self._on_show_sync_details)

    self.copy_sync_report_button = QPushButton("Copiar informe")
    self.copy_sync_report_button.setProperty("variant", "secondary")
    self.copy_sync_report_button.setEnabled(False)
    self.copy_sync_report_button.clicked.connect(self._on_copy_sync_report)

    self.open_sync_logs_button = QPushButton("Abrir carpeta de logs")
    self.open_sync_logs_button.setProperty("variant", "secondary")
    self.open_sync_logs_button.clicked.connect(self._on_open_sync_logs)

    self.sync_history_button = QPushButton("Ver historial")
    self.sync_history_button.setProperty("variant", "secondary")
    self.sync_history_button.clicked.connect(self._on_show_sync_history)

    self.review_conflicts_button = QPushButton("Revisar conflictos")
    self.review_conflicts_button.setProperty("variant", "secondary")
    self.review_conflicts_button.setEnabled(False)
    self.review_conflicts_button.clicked.connect(self._on_review_conflicts)
    sync_actions.addWidget(self.review_conflicts_button)
    sync_layout.addLayout(sync_actions)

    self.last_sync_metrics_label = QLabel("Duración: -- · Cambios: -- · Conflictos: -- · Errores: --")
    self.last_sync_metrics_label.setProperty("role", "secondary")
    sync_layout.addWidget(self.last_sync_metrics_label)

    self.sync_trend_label = QLabel("Tendencia (5): --")
    self.sync_trend_label.setProperty("role", "secondary")

    self.sync_idempotency_label = QLabel("Evita duplicados: --")
    self.sync_idempotency_label.setProperty("role", "secondary")

    self.sync_counts_label = QLabel("Resumen: creadas 0 · actualizadas 0 · omitidas 0 · conflictos 0 · errores 0")
    self.sync_counts_label.setProperty("role", "secondary")
    sync_layout.addWidget(self.sync_counts_label)

    self.go_to_sync_config_button = QPushButton("Ir a configuración")
    self.go_to_sync_config_button.setProperty("variant", "secondary")
    self.go_to_sync_config_button.setVisible(False)
    self.go_to_sync_config_button.clicked.connect(self._on_open_opciones)
    sync_layout.addWidget(self.go_to_sync_config_button, alignment=Qt.AlignLeft)

    self.sync_status_label = QLabel("Sincronizando con Google Sheets…")
    self.sync_status_label.setProperty("role", "secondary")
    self.sync_status_label.setVisible(False)
    self.sync_progress = QProgressBar()
    self.sync_progress.setRange(0, 0)
    self.sync_progress.setTextVisible(False)
    self.sync_progress.setVisible(False)
    sync_status_row = QHBoxLayout()
    sync_status_row.setSpacing(8)
    sync_status_row.addWidget(self.sync_status_label)
    sync_status_row.addWidget(self.sync_progress, 1)
    sync_layout.addLayout(sync_status_row)

    self.alert_banner_label = QLabel("Alertas: sin alertas activas.")
    self.alert_banner_label.setProperty("role", "secondary")
    sync_layout.addWidget(self.alert_banner_label)

    self.conflicts_reminder_label = QLabel("Hay 0 conflictos pendientes de revisión.")
    self.conflicts_reminder_label.setProperty("role", "secondary")
    self.conflicts_reminder_label.setVisible(False)
    sync_layout.addWidget(self.conflicts_reminder_label)

    sync_tab_layout.addWidget(sync_card)

    resumen_card, resumen_layout = self._create_card("Resultado resumido")
    resumen_layout.addWidget(self.sync_counts_label)
    resumen_layout.addWidget(self.last_sync_metrics_label)
    sync_tab_layout.addWidget(resumen_card)

    diagnostics_card, diagnostics_layout = self._create_card("Panel avanzado")
    self.sync_diagnostics_button = QToolButton()
    self.sync_diagnostics_button.setText("Detalles técnicos")
    self.sync_diagnostics_button.setCheckable(True)
    self.sync_diagnostics_button.setChecked(False)
    self.sync_diagnostics_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
    diagnostics_layout.addWidget(self.sync_diagnostics_button, alignment=Qt.AlignLeft)
    self.sync_diagnostics_content = QWidget()
    self.sync_diagnostics_content.setVisible(False)
    diagnostics_content_layout = QVBoxLayout(self.sync_diagnostics_content)
    diagnostics_content_layout.setContentsMargins(0, 0, 0, 0)
    diagnostics_content_layout.setSpacing(8)

    diagnostics_content_layout.addWidget(self.sync_source_label)
    diagnostics_content_layout.addWidget(self.sync_scope_label)
    diagnostics_content_layout.addWidget(self.sync_idempotency_label)
    diagnostics_content_layout.addWidget(self.sync_trend_label)
    diagnostics_content_layout.addWidget(self.sync_details_button)
    diagnostics_content_layout.addWidget(self.copy_sync_report_button)
    diagnostics_content_layout.addWidget(self.open_sync_logs_button)
    diagnostics_content_layout.addWidget(self.sync_history_button)

    health_card, health_layout = self._create_card("Salud del sistema")
    self.health_summary_label = QLabel("Estado general: pendiente de comprobación")
    self.health_summary_label.setProperty("role", "secondary")
    health_layout.addWidget(self.health_summary_label)
    self.health_checks_tree = QTreeWidget()
    self.health_checks_tree.setColumnCount(4)
    self.health_checks_tree.setHeaderLabels(["Estado", "Categoría", "Mensaje", "Acción"])
    self.health_checks_tree.setMinimumHeight(180)
    health_layout.addWidget(self.health_checks_tree)
    health_actions = QHBoxLayout()
    self.refresh_health_button = QPushButton("Actualizar salud")
    self.refresh_health_button.setProperty("variant", "secondary")
    self.refresh_health_button.clicked.connect(self._refresh_health_and_alerts)
    health_actions.addWidget(self.refresh_health_button)
    self.snooze_alerts_button = QPushButton("No mostrar hoy")
    self.snooze_alerts_button.setProperty("variant", "secondary")
    self.snooze_alerts_button.clicked.connect(self._on_snooze_alerts_today)
    health_actions.addWidget(self.snooze_alerts_button)
    health_actions.addStretch(1)
    health_layout.addLayout(health_actions)

    diagnostics_content_layout.addWidget(health_card)
    diagnostics_card.layout().addWidget(self.sync_diagnostics_content)
    self.sync_diagnostics_button.toggled.connect(self.sync_diagnostics_content.setVisible)
    sync_tab_layout.addWidget(diagnostics_card)
    sync_tab_layout.addStretch(1)
    self.main_tabs.addTab(sync_tab, "Sincronización")

    self._scroll_area.setWidget(content)
    self._build_shell_layout()
    self._build_status_bar()

    self._normalize_input_heights()
    self._update_responsive_columns()
    self._configure_time_placeholders()
    self._configure_operativa_focus_order()
    self._configure_historico_focus_order()
    self._bind_preventive_validation_events()
    self._historico_search_timer = QTimer(self)
    self._historico_search_timer.setSingleShot(True)
    self._historico_search_timer.setInterval(250)
    self._historico_search_timer.timeout.connect(self._apply_historico_text_filter)
    self.historico_search_input.textChanged.connect(lambda _: self._historico_search_timer.start())
    self.historico_estado_combo.currentIndexChanged.connect(self._apply_historico_filters)
    self.historico_delegada_combo.currentIndexChanged.connect(self._apply_historico_filters)
    self.historico_desde_date.dateChanged.connect(self._apply_historico_filters)
    self.historico_hasta_date.dateChanged.connect(self._apply_historico_filters)
    self.historico_last_30_button.clicked.connect(self._apply_historico_last_30_days)
    self.historico_clear_filters_button.clicked.connect(self._clear_historico_filters)
    self._restaurar_contexto_guardado()

    from PySide6.QtGui import QKeySequence, QShortcut

    self._historico_find_shortcut = QShortcut(QKeySequence.Find, self)
    self._historico_find_shortcut.activated.connect(self._focus_historico_search)
    self._historico_detail_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self.historico_table)
    self._historico_detail_shortcut.activated.connect(self._on_open_historico_detalle)
    self._historico_escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
    self._historico_escape_shortcut.activated.connect(self._on_historico_escape)

    self._apply_historico_filters()
    self._update_solicitud_preview()
    self._update_action_state()


def clear_form(window) -> None:
    self = window
def _clear_form(self) -> None:
    """Alias legado: mantener compatibilidad con conexiones antiguas.

    Este método sólo debe tocar estado UI; no ejecuta lógica de negocio.
    Incluye guard clauses para que sea seguro en escenarios de tests donde
    parte de la vista aún no esté completamente inicializada.
    """
    limpiar_formulario = getattr(self, "_limpiar_formulario", None)
    if callable(limpiar_formulario):
        try:
            limpiar_formulario()
        except AttributeError:
            # Fallback defensivo para entornos de inicialización parcial.
            pass

    persona_combo = getattr(self, "persona_combo", None)
    if isinstance(persona_combo, QComboBox):
        persona_combo.setCurrentIndex(-1)

    fecha_input = getattr(self, "fecha_input", None)
    if isinstance(fecha_input, QDateEdit):
        fecha_input.setDate(QDate.currentDate())

    desde_input = getattr(self, "desde_input", None)
    if isinstance(desde_input, QTimeEdit):
        desde_input.setTime(QTime(9, 0))

    hasta_input = getattr(self, "hasta_input", None)
    if isinstance(hasta_input, QTimeEdit):
        hasta_input.setTime(QTime(17, 0))

    completo_check = getattr(self, "completo_check", None)
    if isinstance(completo_check, QCheckBox):
        completo_check.setChecked(False)

    notas_input = getattr(self, "notas_input", None)
    if isinstance(notas_input, QPlainTextEdit):
        notas_input.clear()

    for attr_name in ("_field_touched", "_blocking_errors", "_warnings"):
        state = getattr(self, attr_name, None)
        if hasattr(state, "clear"):
            state.clear()

    for label_name in (
        "solicitud_inline_error",
        "delegada_field_error",
        "fecha_field_error",
        "tramo_field_error",
    ):
        label = getattr(self, label_name, None)
        if isinstance(label, QLabel):
            label.setVisible(False)

    update_preview = getattr(self, "_update_solicitud_preview", None)
    if callable(update_preview):
        update_preview()

    update_actions = getattr(self, "_update_action_state", None)
    if callable(update_actions):
        update_actions()
