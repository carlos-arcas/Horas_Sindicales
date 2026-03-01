"""Puertos para el sistema de notificaciones Toast."""

from __future__ import annotations

from abc import ABC, abstractmethod

from aplicacion.notificaciones.dto_toast import NotificacionToastDTO


class INotificadorToast(ABC):
    """Contrato de salida para publicar notificaciones Toast."""

    @abstractmethod
    def notificar(self, toast: NotificacionToastDTO) -> None:
        """Publica una notificación Toast."""
