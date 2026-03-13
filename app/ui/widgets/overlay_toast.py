from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget


class CapaToasts(QWidget):
    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self._host = host
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.hide()
        self.reposicionar()

    def mousePressEvent(self, evento: QMouseEvent) -> None:
        if self._reenviar_evento_si_fuera_de_toast(evento):
            return
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento: QMouseEvent) -> None:
        if self._reenviar_evento_si_fuera_de_toast(evento):
            return
        super().mouseReleaseEvent(evento)

    def mouseDoubleClickEvent(self, evento: QMouseEvent) -> None:
        if self._reenviar_evento_si_fuera_de_toast(evento):
            return
        super().mouseDoubleClickEvent(evento)

    def _reenviar_evento_si_fuera_de_toast(self, evento: QMouseEvent) -> bool:
        posicion_local = evento.position().toPoint()
        if self.childAt(posicion_local) is not None:
            return False

        posicion_global = evento.globalPosition().toPoint()
        destino = self._obtener_widget_passthrough(posicion_global)
        if destino is None:
            return False

        posicion_destino = destino.mapFromGlobal(posicion_global)
        evento_reenviado = QMouseEvent(
            evento.type(),
            QPointF(posicion_destino),
            QPointF(posicion_global),
            evento.button(),
            evento.buttons(),
            evento.modifiers(),
        )
        QApplication.sendEvent(destino, evento_reenviado)
        evento.accept()
        return True

    def _obtener_widget_passthrough(self, posicion_global: QPoint) -> QWidget | None:
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        try:
            destino = QApplication.widgetAt(posicion_global)
        finally:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        if destino is None:
            return None
        if destino is self or self.isAncestorOf(destino):
            return None
        return destino

    @property
    def layout_toasts(self) -> QVBoxLayout:
        return self._layout

    def reposicionar(self) -> None:
        self.setGeometry(self._host.rect())


__all__ = [CapaToasts.__name__]
