from __future__ import annotations

from dataclasses import dataclass, replace
from time import monotonic
from typing import Literal


@dataclass(slots=True)
class ToastModelo:
    id: str
    tipo: Literal["info", "success", "warning", "error"]
    titulo: str
    mensaje: str
    detalles: str | None
    dedupe_key: str | None
    created_at_monotonic: float
    updated_at_monotonic: float


class GestorToasts:
    def __init__(self, max_toasts: int = 3) -> None:
        self._max_toasts = max(1, int(max_toasts))
        self._toasts: list[ToastModelo] = []

    def agregar_toast(self, modelo: ToastModelo) -> ToastModelo:
        if modelo.dedupe_key:
            existente = next((toast for toast in self._toasts if toast.dedupe_key == modelo.dedupe_key), None)
            if existente is not None:
                actualizado = replace(
                    existente,
                    tipo=modelo.tipo,
                    titulo=modelo.titulo,
                    mensaje=modelo.mensaje,
                    detalles=modelo.detalles,
                    updated_at_monotonic=monotonic(),
                )
                self._toasts = [actualizado if toast.id == existente.id else toast for toast in self._toasts]
                return actualizado

        self._toasts.append(modelo)
        if len(self._toasts) > self._max_toasts:
            self._toasts.pop(0)
        return modelo

    def cerrar_toast(self, toast_id: str) -> None:
        self._toasts = [toast for toast in self._toasts if toast.id != toast_id]

    def listar(self) -> list[ToastModelo]:
        return list(self._toasts)


__all__ = [ToastModelo.__name__, GestorToasts.__name__]
