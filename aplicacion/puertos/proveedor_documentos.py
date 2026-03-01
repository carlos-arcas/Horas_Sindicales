"""Puerto de documentos consumido por la capa de presentación."""

from __future__ import annotations

from typing import Protocol


class IProveedorDocumentos(Protocol):
    """Entrega rutas a documentación funcional para la UI."""

    def obtener_ruta_guia_sync(self) -> str:
        """Devuelve la ruta absoluta de la guía de sincronización."""
