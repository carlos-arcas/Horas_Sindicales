from __future__ import annotations

from app.infrastructure.sistema_archivos.local import SistemaArchivosLocal


class PathFileSystem(SistemaArchivosLocal):
    """Alias legacy de compatibilidad para implementación local del sistema de archivos."""


__all__ = ["PathFileSystem"]
