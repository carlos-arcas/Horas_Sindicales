"""Adaptador Qt thread-safe para publicar notificaciones Toast."""

from __future__ import annotations

from abc import ABCMeta

from PySide6.QtCore import QObject, Qt, Signal, Slot

from aplicacion.notificaciones.dto_toast import NotificacionToastDTO
from aplicacion.notificaciones.puertos import INotificadorToast


class _QObjectABCMeta(type(QObject), ABCMeta):
    """Metaclase de compatibilidad para combinar QObject y ABC."""


class ToastControllerAdapter(QObject, INotificadorToast, metaclass=_QObjectABCMeta):
    """Implementa ``INotificadorToast`` exponiendo señales Qt para la capa UI."""

    toast_emitido = Signal(NotificacionToastDTO)
    _solicitud_notificacion = Signal(NotificacionToastDTO)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._solicitud_notificacion.connect(
            self._emitir_en_hilo_qt,
            Qt.ConnectionType.QueuedConnection,
        )

    def notificar(self, toast: NotificacionToastDTO) -> None:
        """Solicita la emisión de una notificación Toast en el hilo de Qt."""
        self._solicitud_notificacion.emit(toast)

    @Slot(NotificacionToastDTO)
    def _emitir_en_hilo_qt(self, toast: NotificacionToastDTO) -> None:
        self.toast_emitido.emit(toast)
