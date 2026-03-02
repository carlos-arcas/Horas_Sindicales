from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from aplicacion.puertos.proveedor_i18n import IProveedorI18N


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
