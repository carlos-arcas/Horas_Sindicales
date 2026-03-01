from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from app.ui.copy_catalog import copy_text
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def create_barra_superior(window: "MainWindow") -> None:
    operativa_tab = QWidget()
    operativa_layout = QVBoxLayout(operativa_tab)
    operativa_layout.setContentsMargins(0, 0, 0, 0)
    operativa_layout.setSpacing(12)
    operativa_header_row = QHBoxLayout()
    operativa_header_row.setSpacing(10)
    operativa_help = QLabel(copy_text("ui.solicitudes.operativa_help"))
    operativa_help.setWordWrap(True)
    operativa_help.setProperty("role", "secondary")
    operativa_header_row.addWidget(operativa_help, 1)
    window.open_saldos_modal_button = QPushButton(copy_text("ui.solicitudes.saldos"))
    window.open_saldos_modal_button.setProperty("variant", "secondary")
    window.open_saldos_modal_button.setMaximumWidth(110)
    operativa_header_row.addWidget(window.open_saldos_modal_button, alignment=Qt.AlignRight)
    operativa_layout.addLayout(operativa_header_row)

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

    window._operativa_tab = operativa_tab
    window._solicitudes_form_panel = solicitudes_form_panel
    window._solicitudes_list_panel = solicitudes_list_panel
    window._solicitudes_form_layout = solicitudes_form_layout
    window._solicitudes_list_layout = solicitudes_list_layout
