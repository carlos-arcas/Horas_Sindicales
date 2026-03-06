from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.ui.copy_catalog import copy_text
from app.ui.historico_view import ESTADOS_HISTORICO, HistoricalViewModel
from app.ui.components.saldos_card import SaldosCard
from app.ui.vistas.main_window.wiring_helpers import conectar_signal

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def create_tablas(window: "MainWindow") -> None:
    historico_tab = QWidget()
    historico_tab_layout = QVBoxLayout(historico_tab)
    historico_tab_layout.setContentsMargins(0, 0, 0, 0)
    historico_tab_layout.setSpacing(12)
    historico_help = QLabel(copy_text("ui.historico.help"))
    historico_help.setWordWrap(True)
    historico_help.setProperty("role", "secondary")
    historico_tab_layout.addWidget(historico_help)

    historico_card, historico_layout = window._create_card(copy_text("ui.historico.tab"))

    window.historico_empty_state = QWidget()
    empty_layout = QVBoxLayout(window.historico_empty_state)
    empty_layout.setContentsMargins(0, 8, 0, 8)
    empty_layout.setSpacing(8)
    empty_title = QLabel(copy_text("ui.historico.empty_title"))
    empty_title.setProperty("role", "sectionTitle")
    empty_layout.addWidget(empty_title)
    empty_text = QLabel(copy_text("ui.historico.empty_text"))
    empty_text.setWordWrap(True)
    empty_text.setProperty("role", "secondary")
    empty_layout.addWidget(empty_text)
    window.historico_empty_button = QPushButton(copy_text("ui.historico.crear_primera"))
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
    window.historico_search_input.setPlaceholderText(copy_text("ui.historico.buscar"))

    window.historico_estado_combo = QComboBox()
    window.historico_estado_combo.addItem(copy_text("ui.historico.todos"), None)
    for estado in ESTADOS_HISTORICO.values():
        window.historico_estado_combo.addItem(estado.label, estado.code)

    filtros_row_search = QHBoxLayout()
    filtros_row_search.setSpacing(8)
    filtros_row_search.addWidget(QLabel(copy_text("ui.historico.buscar")))
    filtros_row_search.addWidget(window.historico_search_input, 1)
    filtros_row_search.addWidget(QLabel(copy_text("ui.historico.estado")))
    filtros_row_search.addWidget(window.historico_estado_combo)
    filtros_layout.addLayout(filtros_row_search)

    filtros_row_1 = QHBoxLayout()
    filtros_row_1.setSpacing(8)
    filtros_row_1.addWidget(QLabel(copy_text("solicitudes.label_delegada")))

    window.historico_delegada_combo = QComboBox()
    window.historico_delegada_combo.addItem(copy_text("ui.historico.delegada_todas"), None)
    window.historico_delegada_combo.setCurrentIndex(0)
    filtros_row_1.addWidget(window.historico_delegada_combo)
    filtros_row_1.addStretch(1)
    filtros_layout.addLayout(filtros_row_1)

    filtros_row_2 = QHBoxLayout()
    filtros_row_2.setSpacing(12)

    window.historico_periodo_anual_radio = QRadioButton(copy_text("ui.historico.periodo_anual"))
    window.historico_periodo_anual_spin = QSpinBox()
    window.historico_periodo_anual_spin.setRange(2000, 2100)
    window.historico_periodo_anual_spin.setValue(QDate.currentDate().year())
    filtros_row_2.addWidget(window.historico_periodo_anual_radio)
    filtros_row_2.addWidget(window.historico_periodo_anual_spin)

    window.historico_periodo_mes_radio = QRadioButton(copy_text("ui.historico.periodo_mes"))
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

    window.historico_periodo_rango_radio = QRadioButton(copy_text("ui.historico.periodo_rango"))
    window.historico_periodo_anual_radio.setChecked(True)
    filtros_row_2.addWidget(window.historico_periodo_rango_radio)

    window.historico_desde_date = QDateEdit()
    window.historico_desde_date.setCalendarPopup(True)
    window.historico_desde_date.setDisplayFormat(copy_text("ui.historico.formato_fecha"))
    filtros_row_2.addWidget(QLabel(copy_text("solicitudes.label_desde")))
    filtros_row_2.addWidget(window.historico_desde_date)

    window.historico_hasta_date = QDateEdit()
    window.historico_hasta_date.setCalendarPopup(True)
    window.historico_hasta_date.setDisplayFormat(copy_text("ui.historico.formato_fecha"))
    filtros_row_2.addWidget(QLabel(copy_text("solicitudes.label_hasta")))
    filtros_row_2.addWidget(window.historico_hasta_date)
    window._apply_historico_default_range()

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
    conectar_signal(
        window,
        window.historico_table.doubleClicked,
        "_on_open_historico_detalle",
        contexto="builders_tablas:create_tablas",
    )
    window.historico_table.setShowGrid(False)
    window.historico_table.setAlternatingRowColors(True)
    window.historico_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    window.historico_table.setMinimumHeight(260)
    window._configure_solicitudes_table(window.historico_table)
    window.historico_table.setSortingEnabled(True)
    historico_header = window.historico_table.horizontalHeader()
    historico_header.setSectionResizeMode(QHeaderView.Stretch)
    historico_details_layout.addWidget(window.historico_table, 1)

    window.historico_export_hint_label = QLabel(copy_text("ui.historico.export_hint"))
    window.historico_export_hint_label.setProperty("role", "secondary")
    window.historico_export_hint_label.setStyleSheet("font-size: 11px;")
    historico_details_layout.addWidget(window.historico_export_hint_label)

    historico_actions = QHBoxLayout()
    historico_actions.setSpacing(10)
    window.historico_actions_layout = historico_actions
    window.eliminar_button = QPushButton(copy_text("ui.historico.eliminar_cero"))
    window.eliminar_button.setProperty("variant", "primary")
    window.eliminar_button.setProperty("intent", "destructive")
    conectar_signal(
        window,
        window.eliminar_button.clicked,
        "_on_eliminar",
        contexto="builders_tablas:create_tablas",
    )
    historico_actions.addWidget(window.eliminar_button)

    window.generar_pdf_button = QPushButton(copy_text("ui.historico.exportar_pdf_cero"))
    window.generar_pdf_button.setProperty("variant", "secondary")
    conectar_signal(
        window,
        window.generar_pdf_button.clicked,
        "_on_generar_pdf_historico",
        contexto="builders_tablas:create_tablas",
    )
    historico_actions.addWidget(window.generar_pdf_button)

    window.historico_select_all_visible_check = QCheckBox(copy_text("ui.historico.select_visible"))
    conectar_signal(
        window,
        window.historico_select_all_visible_check.toggled,
        "_on_historico_select_all_visible_toggled",
        contexto="builders_tablas:create_tablas",
    )
    historico_actions.addWidget(window.historico_select_all_visible_check)

    historico_actions.addStretch(1)

    window.historico_sync_button = QPushButton(copy_text("ui.historico.sync"))
    window.historico_sync_button.setProperty("variant", "success")
    window.historico_sync_button.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
    conectar_signal(
        window,
        window.historico_sync_button.clicked,
        "_on_sync",
        contexto="builders_tablas:create_tablas",
    )
    historico_actions.addWidget(window.historico_sync_button)

    historico_details_layout.addLayout(historico_actions)
    historico_layout.addWidget(window.historico_details_content, 1)

    window.saldos_card = SaldosCard(window)
    historico_tab_layout.addWidget(historico_card, 1)

    window.main_tabs.addTab(historico_tab, copy_text("ui.historico.tab"))
