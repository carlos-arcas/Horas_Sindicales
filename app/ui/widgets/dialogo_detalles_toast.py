from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.ui.copy_catalog import copy_text
from app.ui.widgets.widget_toast import NotificacionToast


class DialogoDetallesNotificacion(QDialog):
    def __init__(self, notificacion: NotificacionToast, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._notificacion = notificacion
        self.setWindowTitle(copy_text("ui.toast.detalles_notificacion"))
        self.setModal(True)
        self.resize(560, 420)

        root = QVBoxLayout(self)
        for line in self._lineas_resumen():
            label = QLabel(line)
            label.setWordWrap(True)
            root.addWidget(label)

        self._detalles = QTextEdit()
        self._detalles.setReadOnly(True)
        self._detalles.setPlainText(self._construir_texto())
        root.addWidget(self._detalles, 1)

        acciones = QHBoxLayout()
        self._btn_copiar = QPushButton(copy_text("ui.toast.copiar"))
        self._btn_cerrar = QPushButton(copy_text("ui.preferencias.cerrar"))
        self._btn_copiar.clicked.connect(self._copiar_al_portapapeles)
        self._btn_cerrar.clicked.connect(self.accept)
        acciones.addStretch(1)
        acciones.addWidget(self._btn_copiar)
        acciones.addWidget(self._btn_cerrar)
        root.addLayout(acciones)

    def _lineas_resumen(self) -> list[str]:
        return [
            f"{copy_text('ui.toast.titulo')} {self._notificacion.titulo}",
            f"{copy_text('ui.toast.mensaje')} {self._notificacion.mensaje}",
            f"{copy_text('ui.toast.codigo')} {self._notificacion.codigo or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.correlacion')} {self._notificacion.correlacion_id or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.fecha_hora')} {self._notificacion.timestamp}",
        ]

    def _construir_texto(self) -> str:
        bloques = [
            f"{copy_text('ui.toast.titulo')} {self._notificacion.titulo}",
            f"{copy_text('ui.toast.mensaje')} {self._notificacion.mensaje}",
            f"{copy_text('ui.toast.detalles')} {self._notificacion.detalles or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.codigo')} {self._notificacion.codigo or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.correlacion')} {self._notificacion.correlacion_id or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.timestamp')} {self._notificacion.timestamp}",
        ]
        return "\n".join(bloques)

    def _copiar_al_portapapeles(self) -> None:
        QGuiApplication.clipboard().setText(self._construir_texto())


__all__ = [DialogoDetallesNotificacion.__name__]
