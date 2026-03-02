from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from typing import Any

from aplicacion.puertos.proveedor_i18n import IProveedorI18N


class _HeadlessSignalInstance:
    def __init__(self) -> None:
        self._subscribers: list[Any] = []

    def connect(self, callback: Any) -> None:
        self._subscribers.append(callback)

    def emit(self, *args: Any, **kwargs: Any) -> None:
        for callback in self._subscribers:
            callback(*args, **kwargs)


class _HeadlessSignal:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._storage_name = ""

    def __set_name__(self, _owner: type[Any], name: str) -> None:
        self._storage_name = f"_{name}_headless_signal"

    def __get__(self, instance: Any, _owner: type[Any]) -> Any:
        if instance is None:
            return self
        signal = getattr(instance, self._storage_name, None)
        if signal is None:
            signal = _HeadlessSignalInstance()
            setattr(instance, self._storage_name, signal)
        return signal


if find_spec("PySide6.QtCore") is not None:
    qtcore = import_module("PySide6.QtCore")
    QObject = qtcore.QObject
    Signal = qtcore.Signal
else:
    class QObject:  # pragma: no cover - branch for headless CI
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            return

    Signal = _HeadlessSignal


class GestorI18N(QObject):
    idioma_cambiado = Signal(str)

    def __init__(self, proveedor: IProveedorI18N) -> None:
        super().__init__()
        self._proveedor = proveedor

    @property
    def idioma(self) -> str:
        return self._proveedor.idioma_actual

    def set_idioma(self, idioma: str) -> None:
        idioma_anterior = self.idioma
        idioma_resuelto = self._proveedor.cambiar_idioma(idioma)
        if idioma_resuelto != idioma_anterior:
            self.idioma_cambiado.emit(idioma_resuelto)

    def tr(self, clave: str, **kwargs: object) -> str:
        return self._proveedor.traducir(clave, **kwargs)

    def t(self, clave: str, **kwargs: object) -> str:
        return self.tr(clave, **kwargs)
