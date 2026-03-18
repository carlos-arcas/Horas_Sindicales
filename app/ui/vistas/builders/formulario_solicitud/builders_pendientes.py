from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.ui.copy_catalog import copy_text
from app.ui.models_qt import SolicitudesTableModel
from app.ui.vistas.builders.formulario_solicitud.bindings_senales import conectar_accion
from app.ui.vistas.builders.formulario_solicitud.contratos import TarjetaSeccion

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def construir_tarjeta_pendientes(window: "MainWindow") -> TarjetaSeccion:
    pendientes_card, pendientes_layout = window._create_card(
        copy_text("ui.solicitudes.pendientes_confirmar")
    )
    window._pendientes_group = pendientes_card
    _construir_herramientas_pendientes(window, pendientes_layout)
    _construir_detalles_pendientes(window, pendientes_layout)
    return TarjetaSeccion(card=pendientes_card, layout=pendientes_layout)


def adjuntar_tarjetas_y_tabs(
    window: "MainWindow",
    tarjeta_solicitud: TarjetaSeccion,
    tarjeta_pendientes: TarjetaSeccion,
) -> None:
    window._solicitudes_form_layout.addWidget(tarjeta_solicitud.card)
    window._solicitudes_list_layout.addWidget(tarjeta_pendientes.card, 1)
    window.solicitudes_splitter.addWidget(window._solicitudes_form_panel)
    window.solicitudes_splitter.addWidget(window._solicitudes_list_panel)
    window.solicitudes_splitter.setStretchFactor(0, 1)
    window.solicitudes_splitter.setStretchFactor(1, 3)
    window.main_tabs.addTab(
        window._operativa_tab, copy_text("solicitudes.section_title")
    )


def _construir_herramientas_pendientes(
    window: "MainWindow", pendientes_layout: QVBoxLayout
) -> None:
    pending_tools = QHBoxLayout()
    pending_tools.setSpacing(8)
    window.ver_todas_pendientes_button = QCheckBox(
        copy_text("ui.solicitudes.ver_todas")
    )
    window.ver_todas_pendientes_button.setCursor(Qt.CursorShape.PointingHandCursor)
    conectar_accion(
        window,
        window.ver_todas_pendientes_button.toggled,
        "_on_toggle_ver_todas_pendientes",
    )
    pending_tools.addWidget(window.ver_todas_pendientes_button)

    window.pending_select_all_visible_check = QCheckBox(
        copy_text("ui.solicitudes.select_visible")
    )
    window.pending_select_all_visible_check.setTristate(True)
    window.pending_select_all_visible_check.setCursor(Qt.CursorShape.PointingHandCursor)
    conectar_accion(
        window,
        window.pending_select_all_visible_check.toggled,
        "_on_pending_select_all_visible_toggled",
    )
    pending_tools.addWidget(window.pending_select_all_visible_check)

    window.revisar_ocultas_button = QPushButton(
        copy_text("ui.solicitudes.revisar_ocultas")
    )
    window.revisar_ocultas_button.setProperty("variant", "ghost")
    window.revisar_ocultas_button.setVisible(False)
    conectar_accion(
        window, window.revisar_ocultas_button.clicked, "_on_review_hidden_pendientes"
    )
    pending_tools.addWidget(window.revisar_ocultas_button)

    window.pending_filter_warning = QLabel("")
    window.pending_filter_warning.setProperty("role", "secondary")
    window.pending_filter_warning.setVisible(False)
    pending_tools.addWidget(window.pending_filter_warning)
    pending_tools.addStretch(1)
    pendientes_layout.addLayout(pending_tools)


def _construir_detalles_pendientes(
    window: "MainWindow", pendientes_layout: QVBoxLayout
) -> None:
    window.pending_details_content = QWidget()
    pending_details_layout = QVBoxLayout(window.pending_details_content)
    pending_details_layout.setContentsMargins(0, 0, 0, 0)
    pending_details_layout.setSpacing(12)
    _construir_tablas_pendientes(window, pending_details_layout)
    _construir_footer_pendientes(window, pending_details_layout)
    pendientes_layout.addWidget(window.pending_details_content, 1)
    window.pending_details_content.setVisible(True)


def _construir_tablas_pendientes(window: "MainWindow", layout: QVBoxLayout) -> None:
    window.pendientes_table = QTableView()
    window.pendientes_model = SolicitudesTableModel([])
    window.pendientes_table.setModel(window.pendientes_model)
    window.pendientes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    window.pendientes_table.setSelectionMode(QAbstractItemView.MultiSelection)
    window.pendientes_table.setShowGrid(False)
    window.pendientes_table.setAlternatingRowColors(True)
    window.pendientes_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    window.pendientes_table.setMinimumHeight(220)
    window._configure_solicitudes_table(window.pendientes_table)
    if window.pendientes_table.selectionModel() is not None:
        conectar_accion(
            window,
            window.pendientes_table.selectionModel().selectionChanged,
            "_on_pending_selection_changed",
        )
    conectar_accion(window, window.pendientes_table.clicked, "_on_pending_row_clicked")
    layout.addWidget(window.pendientes_table, 1)

    window.huerfanas_label = QLabel(copy_text("ui.solicitudes.huerfanas"))
    window.huerfanas_label.setProperty("role", "sectionTitle")
    window.huerfanas_label.setVisible(False)
    layout.addWidget(window.huerfanas_label)

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
    layout.addWidget(window.huerfanas_table)


def _construir_footer_pendientes(window: "MainWindow", layout: QVBoxLayout) -> None:
    footer_separator = QFrame()
    footer_separator.setProperty("role", "subtleSeparator")
    footer_separator.setFixedHeight(1)
    layout.addWidget(footer_separator)

    pendientes_footer = QHBoxLayout()
    pendientes_footer.setSpacing(10)
    pendientes_footer.addLayout(_crear_acciones_izquierda(window))
    pendientes_footer.addStretch(1)
    pendientes_footer.addLayout(_crear_acciones_derecha(window))
    layout.addLayout(pendientes_footer)


def _crear_acciones_izquierda(window: "MainWindow") -> QHBoxLayout:
    left_actions = QHBoxLayout()
    left_actions.setSpacing(8)

    window.eliminar_pendiente_button = QPushButton(
        copy_text("solicitudes.button_pending_delete")
    )
    window.eliminar_pendiente_button.setObjectName("eliminar_pendiente_button")
    window.eliminar_pendiente_button.setProperty("variant", "primary")
    window.eliminar_pendiente_button.setProperty("intent", "destructive")
    conectar_accion(
        window, window.eliminar_pendiente_button.clicked, "_on_remove_pendiente"
    )
    left_actions.addWidget(window.eliminar_pendiente_button)

    window.eliminar_huerfana_button = QPushButton(
        copy_text("ui.solicitudes.eliminar_huerfana")
    )
    window.eliminar_huerfana_button.setObjectName("eliminar_huerfana_button")
    window.eliminar_huerfana_button.setProperty("variant", "ghost")
    conectar_accion(
        window, window.eliminar_huerfana_button.clicked, "_on_remove_huerfana"
    )
    window.eliminar_huerfana_button.setVisible(False)
    left_actions.addWidget(window.eliminar_huerfana_button)

    window.insertar_sin_pdf_button = QPushButton(
        copy_text("solicitudes.button_confirm_without_pdf")
    )
    window.insertar_sin_pdf_button.setObjectName("insertar_sin_pdf_button")
    window.insertar_sin_pdf_button.setProperty("variant", "success")
    conectar_accion(
        window, window.insertar_sin_pdf_button.clicked, "_on_insertar_sin_pdf"
    )
    left_actions.addWidget(window.insertar_sin_pdf_button)
    return left_actions


def _crear_acciones_derecha(window: "MainWindow") -> QHBoxLayout:
    right_actions = QHBoxLayout()
    right_actions.setSpacing(10)
    window.total_pendientes_label = QLabel(copy_text("ui.solicitudes.total_cero"))
    window.total_pendientes_label.setProperty("role", "sectionTitle")
    right_actions.addWidget(window.total_pendientes_label)

    window.abrir_pdf_check = QCheckBox(copy_text("ui.solicitudes.abrir_pdf"))
    window.abrir_pdf_check.setChecked(True)
    right_actions.addWidget(window.abrir_pdf_check)

    window.confirmar_button = QPushButton(
        copy_text("solicitudes.button_confirm_with_pdf")
    )
    window.confirmar_button.setObjectName("confirmar_button")
    window.confirmar_button.setProperty("variant", "success")
    conectar_accion(window, window.confirmar_button.clicked, "_on_confirmar")
    right_actions.addWidget(window.confirmar_button)
    return right_actions
