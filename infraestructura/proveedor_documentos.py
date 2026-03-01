"""Adaptador de infraestructura para resolver documentos de ayuda."""

from __future__ import annotations

from app.infrastructure.proveedor_documentos_repositorio import ProveedorDocumentosRepositorio
from aplicacion.puertos.proveedor_documentos import IProveedorDocumentos


class ProveedorDocumentosInfra(IProveedorDocumentos):
    def __init__(self) -> None:
        self._repositorio = ProveedorDocumentosRepositorio()

    def obtener_ruta_guia_sync(self) -> str:
        return self._repositorio.obtener_ruta_guia_sync()
