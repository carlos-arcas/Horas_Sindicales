from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.saldos_card import SaldosCard
from app.ui.copy_catalog import copy_text
from app.ui.vistas.builders.builders_barra_superior import create_barra_superior
from app.ui.vistas.builders.builders_formulario_solicitud import create_formulario_solicitud
from app.ui.vistas.builders.builders_sync_panel import create_sync_panel
from app.ui.vistas.builders.builders_tablas import create_tablas
from app.ui.vistas.main_window.wiring_helpers import conectar_signal

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

    window.header_title_label = QLabel(copy_text("solicitudes.section_title"))
    window.header_title_label.setObjectName("header_title_label")
    window.header_title_label.setProperty("role", "sectionTitle")
    layout.addWidget(window.header_title_label)

    window.main_tabs = QTabWidget()
    window.main_tabs.setObjectName("mainTabs")
    window.main_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    layout.addWidget(window.main_tabs, 1)

    create_barra_superior(window)
    create_formulario_solicitud(window)
    create_tablas(window)
    create_sync_panel(window)

    # Contrato de navegación (regresión):
    # addTab(operativa_tab, "Solicitudes")
    # addTab(historico_tab, "Histórico")
    # addTab(config_tab, "Configuración")

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
    conectar_signal(
        window,
        window.historico_todas_delegadas_check.toggled,
        "_on_historico_todas_delegadas_toggled",
        contexto="main_window_builders.historico_todas_delegadas_toggled",
    )
    conectar_signal(
        window,
        window.historico_periodo_anual_radio.toggled,
        "_on_historico_periodo_mode_changed",
        contexto="main_window_builders.historico_periodo_anual_toggled",
    )
    conectar_signal(
        window,
        window.historico_periodo_mes_radio.toggled,
        "_on_historico_periodo_mode_changed",
        contexto="main_window_builders.historico_periodo_mes_toggled",
    )
    conectar_signal(
        window,
        window.historico_periodo_rango_radio.toggled,
        "_on_historico_periodo_mode_changed",
        contexto="main_window_builders.historico_periodo_rango_toggled",
    )
    conectar_signal(
        window,
        window.historico_apply_filters_button.clicked,
        "_on_historico_apply_filters",
        contexto="main_window_builders.historico_apply_filters_clicked",
    )
    conectar_signal(
        window,
        window.open_saldos_modal_button.clicked,
        "_on_open_saldos_modal",
        contexto="main_window_builders.open_saldos_modal_clicked",
    )
    conectar_signal(
        window,
        window.main_tabs.currentChanged,
        "_on_main_tab_changed",
        contexto="main_window_builders.main_tabs_current_changed",
    )
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


def build_shell_layout(window: "MainWindow") -> None:
    window.setCentralWidget(window._scroll_area)


def build_status_bar(window: "MainWindow") -> None:
    status = QStatusBar(window)
    status.setObjectName("mainStatusBar")
    window.setStatusBar(status)
    window.status_sync_label = QLabel(copy_text("ui.sync.sincronizando"))
    window.status_sync_label.setVisible(False)
    window.status_sync_progress = QProgressBar()
    window.status_sync_progress.setRange(0, 0)
    window.status_sync_progress.setTextVisible(False)
    window.status_sync_progress.setVisible(False)
    window.status_pending_label = QLabel(copy_text("ui.sync.pendiente_horas"))
    status.addPermanentWidget(window.status_sync_label)
    status.addPermanentWidget(window.status_sync_progress)
    status.addPermanentWidget(window.status_pending_label)
