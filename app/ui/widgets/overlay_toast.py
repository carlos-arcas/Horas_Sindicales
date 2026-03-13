from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget


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

    def event(self, evento: QEvent) -> bool:
        if self._debe_ignorar_evento_mouse(evento):
            evento.ignore()
            return False
        return super().event(evento)

    def _debe_ignorar_evento_mouse(self, evento: QEvent) -> bool:
        tipos_mouse = {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.MouseMove,
            QEvent.Type.Wheel,
        }
        if evento.type() not in tipos_mouse:
            return False
        posicion = self._extraer_posicion_local(evento)
        if posicion is None:
            return False
        return self.childAt(posicion) is None

    def _extraer_posicion_local(self, evento: QEvent) -> QPoint | None:
        if hasattr(evento, "position"):
            return evento.position().toPoint()  # type: ignore[no-any-return]
        if hasattr(evento, "pos"):
            return evento.pos()  # type: ignore[no-any-return]
        return None

    @property
    def layout_toasts(self) -> QVBoxLayout:
        return self._layout

    def reposicionar(self) -> None:
        self.setGeometry(self._host.rect())


__all__ = [CapaToasts.__name__]
