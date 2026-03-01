from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.copy_catalog import copy_text

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def create_sync_panel(window: "MainWindow") -> None:
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
    config_help = QLabel(copy_text("ui.config.help"))
    config_help.setWordWrap(True)
    config_help.setProperty("role", "secondary")
    config_layout.addWidget(config_help)

    persona_card, persona_layout = window._create_card(copy_text("ui.config.delegada"))

    persona_actions = QHBoxLayout()
    persona_actions.setSpacing(8)
    window.config_delegada_combo = QComboBox()
    window.config_delegada_combo.currentIndexChanged.connect(window._on_config_delegada_changed)
    persona_actions.addWidget(window.config_delegada_combo, 1)

    window.edit_persona_button = QPushButton(copy_text("ui.config.editar"))
    window.edit_persona_button.setProperty("variant", "success")
    window.edit_persona_button.clicked.connect(window._on_edit_persona)
    persona_actions.addWidget(window.edit_persona_button)

    window.delete_persona_button = QPushButton(copy_text("ui.config.eliminar"))
    window.delete_persona_button.setProperty("variant", "primary")
    window.delete_persona_button.setProperty("intent", "destructive")
    window.delete_persona_button.clicked.connect(window._on_delete_persona)
    persona_actions.addWidget(window.delete_persona_button)

    persona_actions.addStretch(1)
    window.add_persona_button = QPushButton(copy_text("ui.config.nueva_delegada"))
    window.add_persona_button.setProperty("variant", "secondary")
    window.add_persona_button.clicked.connect(window._on_add_persona)
    persona_actions.addWidget(window.add_persona_button)
    persona_layout.addLayout(persona_actions)
    config_layout.addWidget(persona_card)

    grupo_card, grupo_layout = window._create_card(copy_text("ui.config.grupo"))
    grupo_actions = QHBoxLayout()
    grupo_actions.setSpacing(8)
    window.edit_grupo_button = QPushButton(copy_text("ui.config.configurar_grupo"))
    window.edit_grupo_button.setProperty("variant", "secondary")
    window.edit_grupo_button.clicked.connect(window._on_edit_grupo)
    grupo_actions.addWidget(window.edit_grupo_button)
    grupo_actions.addStretch(1)
    grupo_layout.addLayout(grupo_actions)
    config_layout.addWidget(grupo_card)

    pdf_card, pdf_layout = window._create_card(copy_text("ui.config.pdf"))
    pdf_actions = QHBoxLayout()
    pdf_actions.setSpacing(8)
    window.editar_pdf_button = QPushButton(copy_text("ui.config.configurar_pdf"))
    window.editar_pdf_button.setProperty("variant", "secondary")
    window.editar_pdf_button.clicked.connect(window._on_edit_pdf)
    pdf_actions.addWidget(window.editar_pdf_button)
    pdf_actions.addStretch(1)
    pdf_layout.addLayout(pdf_actions)
    config_layout.addWidget(pdf_card)

    preferencias_card, preferencias_layout = window._create_card(copy_text("ui.sync.preferencias"))
    window.preferencia_pantalla_completa_check = QCheckBox(copy_text("ui.sync.maximizada_por_defecto"))
    window.preferencia_pantalla_completa_check.toggled.connect(window._on_toggle_preferencia_pantalla_completa)
    preferencias_layout.addWidget(window.preferencia_pantalla_completa_check)
    config_layout.addWidget(preferencias_card)

    credenciales_card, credenciales_layout = window._create_card(copy_text("ui.sync.google_sheets"))
    window.sync_source_label = QLabel(copy_text("ui.sync.fuente_placeholder"))
    window.sync_source_label.setProperty("role", "secondary")
    credenciales_layout.addWidget(window.sync_source_label)
    window.sync_scope_label = QLabel(copy_text("ui.sync.rango_placeholder"))
    window.sync_scope_label.setProperty("role", "secondary")
    credenciales_layout.addWidget(window.sync_scope_label)
    sync_actions = QHBoxLayout()
    sync_actions.setSpacing(8)
    window.opciones_button = QPushButton(copy_text("ui.sync.configurar_conexion"))
    window.opciones_button.setProperty("variant", "secondary")
    window.opciones_button.clicked.connect(window._on_open_opciones)
    sync_actions.addWidget(window.opciones_button)

    window.config_test_connection_button = QPushButton(copy_text("ui.sync.probar_conexion"))
    window.config_test_connection_button.setProperty("variant", "secondary")
    window.config_test_connection_button.clicked.connect(window._on_simulate_sync)
    sync_actions.addWidget(window.config_test_connection_button)

    window.config_sync_button = QPushButton(copy_text("ui.sync.sincronizar_ahora"))
    window.config_sync_button.setProperty("variant", "success")
    window.config_sync_button.clicked.connect(window._on_sync)
    sync_actions.addWidget(window.config_sync_button)
    sync_actions.addStretch(1)
    credenciales_layout.addLayout(sync_actions)
    config_layout.addWidget(credenciales_card)
    config_layout.addStretch(1)
    window.main_tabs.addTab(config_tab, copy_text("ui.sync.configuracion"))

    sync_tab = QWidget()
    sync_tab_layout = QVBoxLayout(sync_tab)
    sync_tab_layout.setContentsMargins(0, 0, 0, 0)
    sync_tab_layout.setSpacing(12)
    sync_help = QLabel(copy_text("ui.sync.resumen"))
    sync_help.setWordWrap(True)
    sync_help.setProperty("role", "secondary")
    sync_tab_layout.addWidget(sync_help)

    sync_state_card, sync_state_layout = window._create_card(copy_text("ui.sync.estado"))
    window.last_sync_label = QLabel(copy_text("ui.sync.ultima_sync_placeholder"))
    window.last_sync_label.setProperty("role", "secondary")
    sync_state_layout.addWidget(window.last_sync_label)
    window.sync_panel_status = QLabel(copy_text("ui.sync.estado_pendiente"))
    window.sync_panel_status.setProperty("role", "secondary")
    sync_state_layout.addWidget(window.sync_panel_status)
    window.sync_status_badge = QLabel(window._status_to_label("IDLE"))
    window.sync_status_badge.setProperty("role", "badge")
    window.sync_status_badge.setProperty("syncStatus", "IDLE")
    sync_state_layout.addWidget(window.sync_status_badge, alignment=Qt.AlignLeft)
    sync_tab_layout.addWidget(sync_state_card)

    sync_card, sync_layout = window._create_card(copy_text("ui.sync.acciones"))
    sync_heading = QLabel(copy_text("ui.sync.google_sheets"))
    sync_heading.setProperty("role", "sectionTitle")
    sync_layout.addWidget(sync_heading)
    sync_actions = QHBoxLayout()
    sync_actions.setSpacing(8)
    window.sync_button = QPushButton(copy_text("ui.sync.sincronizar_ahora"))
    window.sync_button.setProperty("variant", "primary")
    window.sync_button.clicked.connect(window._on_sync)
    sync_actions.addWidget(window.sync_button)

    window.simulate_sync_button = QPushButton(copy_text("ui.sync.simular"))
    window.simulate_sync_button.setProperty("variant", "secondary")
    window.simulate_sync_button.clicked.connect(window._on_simulate_sync)
    sync_actions.addWidget(window.simulate_sync_button)

    window.confirm_sync_button = QPushButton(copy_text("ui.sync.sincronizar_ahora"))
    window.confirm_sync_button.setProperty("variant", "primary")
    window.confirm_sync_button.setEnabled(False)
    window.confirm_sync_button.clicked.connect(window._on_confirm_sync)
    sync_actions.addWidget(window.confirm_sync_button)

    window.retry_failed_button = QPushButton(copy_text("ui.sync.reintentar_fallidos"))
    window.retry_failed_button.setProperty("variant", "secondary")
    window.retry_failed_button.setEnabled(False)
    window.retry_failed_button.clicked.connect(window._on_retry_failed)
    sync_actions.addWidget(window.retry_failed_button)

    window.sync_details_button = QPushButton(copy_text("ui.sync.ver_detalles"))
    window.sync_details_button.setProperty("variant", "secondary")
    window.sync_details_button.setEnabled(False)
    window.sync_details_button.clicked.connect(window._on_show_sync_details)

    window.copy_sync_report_button = QPushButton(copy_text("ui.sync.copiar_informe"))
    window.copy_sync_report_button.setProperty("variant", "secondary")
    window.copy_sync_report_button.setEnabled(False)
    window.copy_sync_report_button.clicked.connect(window._on_copy_sync_report)

    window.open_sync_logs_button = QPushButton(copy_text("ui.sync.abrir_logs"))
    window.open_sync_logs_button.setProperty("variant", "secondary")
    window.open_sync_logs_button.clicked.connect(window._on_open_sync_logs)

    window.sync_history_button = QPushButton(copy_text("ui.sync.ver_historial"))
    window.sync_history_button.setProperty("variant", "secondary")
    window.sync_history_button.clicked.connect(window._on_show_sync_history)

    window.review_conflicts_button = QPushButton(copy_text("ui.sync.revisar_conflictos"))
    window.review_conflicts_button.setProperty("variant", "secondary")
    window.review_conflicts_button.setEnabled(False)
    window.review_conflicts_button.clicked.connect(window._on_review_conflicts)
    sync_actions.addWidget(window.review_conflicts_button)
    sync_layout.addLayout(sync_actions)

    window.last_sync_metrics_label = QLabel(copy_text("ui.sync.metricas_placeholder"))
    window.last_sync_metrics_label.setProperty("role", "secondary")
    sync_layout.addWidget(window.last_sync_metrics_label)

    window.sync_trend_label = QLabel(copy_text("ui.sync.tendencia_placeholder"))
    window.sync_trend_label.setProperty("role", "secondary")

    window.sync_idempotency_label = QLabel(copy_text("ui.sync.idempotencia_placeholder"))
    window.sync_idempotency_label.setProperty("role", "secondary")

    window.sync_counts_label = QLabel(copy_text("ui.sync.resumen_conteos_placeholder"))
    window.sync_counts_label.setProperty("role", "secondary")
    sync_layout.addWidget(window.sync_counts_label)

    window.go_to_sync_config_button = QPushButton(copy_text("ui.sync.ir_configuracion"))
    window.go_to_sync_config_button.setProperty("variant", "secondary")
    window.go_to_sync_config_button.setVisible(False)
    window.go_to_sync_config_button.clicked.connect(window._on_open_opciones)
    sync_layout.addWidget(window.go_to_sync_config_button, alignment=Qt.AlignLeft)

    window.sync_status_label = QLabel(copy_text("ui.sync.sincronizando"))
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

    window.alert_banner_label = QLabel(copy_text("ui.sync.alertas_sin_activas"))
    window.alert_banner_label.setProperty("role", "secondary")
    sync_layout.addWidget(window.alert_banner_label)

    window.conflicts_reminder_label = QLabel(copy_text("ui.sync.conflictos_pendientes"))
    window.conflicts_reminder_label.setProperty("role", "secondary")
    window.conflicts_reminder_label.setVisible(False)
    sync_layout.addWidget(window.conflicts_reminder_label)

    sync_tab_layout.addWidget(sync_card)

    resumen_card, resumen_layout = window._create_card(copy_text("ui.sync.resultado_resumido"))
    resumen_layout.addWidget(window.sync_counts_label)
    resumen_layout.addWidget(window.last_sync_metrics_label)
    sync_tab_layout.addWidget(resumen_card)

    diagnostics_card, diagnostics_layout = window._create_card(copy_text("ui.sync.panel_avanzado"))
    window.sync_diagnostics_button = QToolButton()
    window.sync_diagnostics_button.setText(copy_text("ui.sync.detalles_tecnicos"))
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

    health_card, health_layout = window._create_card(copy_text("ui.sync.salud_sistema"))
    window.health_summary_label = QLabel(copy_text("ui.sync.estado_general_pendiente"))
    window.health_summary_label.setProperty("role", "secondary")
    health_layout.addWidget(window.health_summary_label)
    window.health_checks_tree = QTreeWidget()
    window.health_checks_tree.setColumnCount(4)
    window.health_checks_tree.setHeaderLabels([
        copy_text("ui.sync.estado"),
        copy_text("ui.sync.columna_categoria"),
        copy_text("ui.sync.columna_mensaje"),
        copy_text("ui.sync.columna_accion"),
    ])
    window.health_checks_tree.setMinimumHeight(180)
    health_layout.addWidget(window.health_checks_tree)
    health_actions = QHBoxLayout()
    window.refresh_health_button = QPushButton(copy_text("ui.sync.actualizar_salud"))
    window.refresh_health_button.setProperty("variant", "secondary")
    window.refresh_health_button.clicked.connect(window._refresh_health_and_alerts)
    health_actions.addWidget(window.refresh_health_button)
    window.snooze_alerts_button = QPushButton(copy_text("ui.sync.no_mostrar_hoy"))
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
    sync_tab_index = window.main_tabs.addTab(sync_tab, copy_text("ui.sync.tab_sincronizacion"))
    window.main_tabs.setTabVisible(sync_tab_index, False)
