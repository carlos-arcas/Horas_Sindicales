from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from app.ui.copy_catalog import copy_text
from app.ui.vistas.builders.formulario_solicitud.ayudantes_puros import calcular_altura_compacta_texto


def crear_contenedor_hora(label_key: str, time_edit: object) -> QWidget:
    contenedor = QWidget()
    layout = QHBoxLayout(contenedor)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(QLabel(copy_text(label_key)))
    layout.addWidget(time_edit)
    return contenedor


def crear_placeholder_hora() -> QWidget:
    placeholder = QWidget()
    placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    return placeholder


def configurar_altura_notas_compacta(notas_input: object, lineas_visibles: int = 3) -> None:
    altura_linea = notas_input.fontMetrics().lineSpacing()
    margen_documento = int(notas_input.document().documentMargin() * 2)
    altura_borde = notas_input.frameWidth() * 2
    altura = calcular_altura_compacta_texto(lineas_visibles, altura_linea, margen_documento, altura_borde)
    notas_input.setFixedHeight(altura)
