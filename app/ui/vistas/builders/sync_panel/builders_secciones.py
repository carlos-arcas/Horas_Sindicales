from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.copy_catalog import copy_text
from app.ui.vistas.builders.sync_panel.bindings_senales import conectar_evento_sync_panel
from app.ui.vistas.builders.sync_panel.builders_diagnostico import construir_seccion_diagnostico
from app.ui.vistas.builders.sync_panel.ayudantes_qt import crear_boton_accion, crear_label_secundario

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def construir_tab_configuracion(window: "MainWindow") -> None:
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

    config_help = crear_label_secundario("ui.config.help")
    config_help.setWordWrap(True)
    config_layout.addWidget(config_help)

    _construir_seccion_persona(window, config_layout)
    _construir_seccion_grupo(window, config_layout)
    _construir_seccion_pdf(window, config_layout)
    _construir_seccion_preferencias(window, config_layout)
    _construir_seccion_credenciales(window, config_layout)

    config_layout.addStretch(1)
    window.main_tabs.addTab(config_tab, copy_text("ui.sync.configuracion"))


def _construir_seccion_persona(window: "MainWindow", config_layout: QVBoxLayout) -> None:
    persona_card, persona_layout = window._create_card(copy_text("ui.config.delegada"))
    persona_actions = QHBoxLayout()
    persona_actions.setSpacing(8)

    window.config_delegada_combo = QComboBox()
    conectar_evento_sync_panel(window, window.config_delegada_combo.currentIndexChanged, "_on_config_delegada_changed")
    persona_actions.addWidget(window.config_delegada_combo, 1)

    window.edit_persona_button = crear_boton_accion(window, "ui.config.editar", "success", "_on_edit_persona")
    persona_actions.addWidget(window.edit_persona_button)

    window.delete_persona_button = crear_boton_accion(window, "ui.config.eliminar", "primary", "_on_delete_persona")
    window.delete_persona_button.setProperty("intent", "destructive")
    persona_actions.addWidget(window.delete_persona_button)

    persona_actions.addStretch(1)
    window.add_persona_button = crear_boton_accion(window, "ui.config.nueva_delegada", "secondary", "_on_add_persona")
    persona_actions.addWidget(window.add_persona_button)
    persona_layout.addLayout(persona_actions)
    config_layout.addWidget(persona_card)


def _construir_seccion_grupo(window: "MainWindow", config_layout: QVBoxLayout) -> None:
    grupo_card, grupo_layout = window._create_card(copy_text("ui.config.grupo"))
    grupo_actions = QHBoxLayout()
    grupo_actions.setSpacing(8)
    window.edit_grupo_button = crear_boton_accion(window, "ui.config.configurar_grupo", "secondary", "_on_edit_grupo")
    grupo_actions.addWidget(window.edit_grupo_button)
    grupo_actions.addStretch(1)
    grupo_layout.addLayout(grupo_actions)
    config_layout.addWidget(grupo_card)


def _construir_seccion_pdf(window: "MainWindow", config_layout: QVBoxLayout) -> None:
    pdf_card, pdf_layout = window._create_card(copy_text("ui.config.pdf"))
    pdf_actions = QHBoxLayout()
    pdf_actions.setSpacing(8)
    window.editar_pdf_button = crear_boton_accion(window, "ui.config.configurar_pdf", "secondary", "_on_edit_pdf")
    pdf_actions.addWidget(window.editar_pdf_button)
    pdf_actions.addStretch(1)
    pdf_layout.addLayout(pdf_actions)
    config_layout.addWidget(pdf_card)


def _construir_seccion_preferencias(window: "MainWindow", config_layout: QVBoxLayout) -> None:
    preferencias_card, preferencias_layout = window._create_card(copy_text("ui.sync.preferencias"))
    window.preferencia_pantalla_completa_check = QCheckBox(copy_text("ui.sync.maximizada_por_defecto"))
    conectar_evento_sync_panel(
        window,
        window.preferencia_pantalla_completa_check.toggled,
        "_on_toggle_preferencia_pantalla_completa",
    )
    preferencias_layout.addWidget(window.preferencia_pantalla_completa_check)
    config_layout.addWidget(preferencias_card)


def _construir_seccion_credenciales(window: "MainWindow", config_layout: QVBoxLayout) -> None:
    credenciales_card, credenciales_layout = window._create_card(copy_text("ui.sync.google_sheets"))
    window.sync_source_label = crear_label_secundario("ui.sync.fuente_placeholder")
    credenciales_layout.addWidget(window.sync_source_label)
    window.sync_scope_label = crear_label_secundario("ui.sync.rango_placeholder")
    credenciales_layout.addWidget(window.sync_scope_label)

    sync_actions = QHBoxLayout()
    sync_actions.setSpacing(8)
    window.opciones_button = crear_boton_accion(window, "ui.sync.configurar_conexion", "secondary", "_on_open_opciones")
    sync_actions.addWidget(window.opciones_button)
    window.config_test_connection_button = crear_boton_accion(
        window,
        "ui.sync.probar_conexion",
        "secondary",
        "_on_simulate_sync",
    )
    sync_actions.addWidget(window.config_test_connection_button)
    window.config_sync_button = crear_boton_accion(window, "ui.sync.sincronizar_ahora", "success", "_on_sync")
    sync_actions.addWidget(window.config_sync_button)
    sync_actions.addStretch(1)
    credenciales_layout.addLayout(sync_actions)
    config_layout.addWidget(credenciales_card)


def construir_tab_sincronizacion(window: "MainWindow") -> None:
    sync_tab = QWidget()
    sync_tab_layout = QVBoxLayout(sync_tab)
    sync_tab_layout.setContentsMargins(0, 0, 0, 0)
    sync_tab_layout.setSpacing(12)

    sync_help = crear_label_secundario("ui.sync.resumen")
    sync_help.setWordWrap(True)
    sync_tab_layout.addWidget(sync_help)

    _construir_seccion_estado(window, sync_tab_layout)
    _construir_seccion_acciones(window, sync_tab_layout)
    _construir_seccion_resumen(window, sync_tab_layout)
    construir_seccion_diagnostico(window, sync_tab_layout)

    sync_tab_layout.addStretch(1)
    sync_tab_index = window.main_tabs.addTab(sync_tab, copy_text("ui.sync.tab_sincronizacion"))
    window.main_tabs.setTabVisible(sync_tab_index, False)


def _construir_seccion_estado(window: "MainWindow", sync_tab_layout: QVBoxLayout) -> None:
    sync_state_card, sync_state_layout = window._create_card(copy_text("ui.sync.estado"))
    window.last_sync_label = crear_label_secundario("ui.sync.ultima_sync_placeholder")
    sync_state_layout.addWidget(window.last_sync_label)
    window.sync_panel_status = crear_label_secundario("ui.sync.estado_pendiente")
    sync_state_layout.addWidget(window.sync_panel_status)
    window.sync_status_badge = QLabel(window._status_to_label("IDLE"))
    window.sync_status_badge.setProperty("role", "badge")
    window.sync_status_badge.setProperty("syncStatus", "IDLE")
    sync_state_layout.addWidget(window.sync_status_badge, alignment=Qt.AlignLeft)
    sync_tab_layout.addWidget(sync_state_card)


def _construir_seccion_acciones(window: "MainWindow", sync_tab_layout: QVBoxLayout) -> None:
    sync_card, sync_layout = window._create_card(copy_text("ui.sync.acciones"))
    sync_heading = QLabel(copy_text("ui.sync.google_sheets"))
    sync_heading.setProperty("role", "sectionTitle")
    sync_layout.addWidget(sync_heading)

    sync_actions = QHBoxLayout()
    sync_actions.setSpacing(8)
    _construir_botones_acciones(window, sync_actions)
    sync_layout.addLayout(sync_actions)

    window.last_sync_metrics_label = crear_label_secundario("ui.sync.metricas_placeholder")
    sync_layout.addWidget(window.last_sync_metrics_label)
    window.sync_trend_label = crear_label_secundario("ui.sync.tendencia_placeholder")
    window.sync_idempotency_label = crear_label_secundario("ui.sync.idempotencia_placeholder")
    window.sync_counts_label = crear_label_secundario("ui.sync.resumen_conteos_placeholder")
    sync_layout.addWidget(window.sync_counts_label)

    window.go_to_sync_config_button = crear_boton_accion(window, "ui.sync.ir_configuracion", "secondary", "_on_open_opciones")
    window.go_to_sync_config_button.setVisible(False)
    sync_layout.addWidget(window.go_to_sync_config_button, alignment=Qt.AlignLeft)

    _construir_estado_progreso(window, sync_layout)
    window.alert_banner_label = crear_label_secundario("ui.sync.alertas_sin_activas")
    sync_layout.addWidget(window.alert_banner_label)
    window.conflicts_reminder_label = crear_label_secundario("ui.sync.conflictos_pendientes")
    window.conflicts_reminder_label.setVisible(False)
    sync_layout.addWidget(window.conflicts_reminder_label)
    sync_tab_layout.addWidget(sync_card)


def _construir_botones_acciones(window: "MainWindow", sync_actions: QHBoxLayout) -> None:
    window.sync_button = crear_boton_accion(window, "ui.sync.sincronizar_ahora", "primary", "_on_sync")
    sync_actions.addWidget(window.sync_button)
    window.simulate_sync_button = crear_boton_accion(window, "ui.sync.simular", "secondary", "_on_simulate_sync")
    sync_actions.addWidget(window.simulate_sync_button)
    window.confirm_sync_button = crear_boton_accion(
        window,
        "ui.sync.sincronizar_ahora",
        "primary",
        "_on_confirm_sync",
        habilitado=False,
    )
    sync_actions.addWidget(window.confirm_sync_button)
    window.retry_failed_button = crear_boton_accion(
        window,
        "ui.sync.reintentar_fallidos",
        "secondary",
        "_on_retry_failed",
        habilitado=False,
    )
    sync_actions.addWidget(window.retry_failed_button)
    window.review_conflicts_button = crear_boton_accion(
        window,
        "ui.sync.revisar_conflictos",
        "secondary",
        "_on_review_conflicts",
        habilitado=False,
    )
    sync_actions.addWidget(window.review_conflicts_button)


def _construir_estado_progreso(window: "MainWindow", sync_layout: QVBoxLayout) -> None:
    window.sync_status_label = crear_label_secundario("ui.sync.sincronizando")
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


def _construir_seccion_resumen(window: "MainWindow", sync_tab_layout: QVBoxLayout) -> None:
    resumen_card, resumen_layout = window._create_card(copy_text("ui.sync.resultado_resumido"))
    resumen_layout.addWidget(window.sync_counts_label)
    resumen_layout.addWidget(window.last_sync_metrics_label)
    sync_tab_layout.addWidget(resumen_card)


