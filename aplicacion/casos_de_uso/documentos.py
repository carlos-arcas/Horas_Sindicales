"""Casos de uso relacionados con documentación de ayuda."""

from __future__ import annotations

from aplicacion.puertos.proveedor_documentos import IProveedorDocumentos


class ObtenerRutaGuiaSync:
    """Expone la ruta de la guía de Sync para la capa de presentación."""

    def __init__(self, proveedor_documentos: IProveedorDocumentos) -> None:
        self._proveedor_documentos = proveedor_documentos

    def ejecutar(self) -> str:
        return self._proveedor_documentos.obtener_ruta_guia_sync()
