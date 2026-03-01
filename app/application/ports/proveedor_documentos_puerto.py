from __future__ import annotations

from typing import Protocol


class DocumentoNoEncontradoError(FileNotFoundError):
    """Error de aplicación para documentos esperados que no existen."""


class ProveedorDocumentosPuerto(Protocol):
    def obtener_ruta_guia_sync(self) -> str: ...
