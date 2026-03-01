from __future__ import annotations

from pathlib import Path
from typing import Protocol


class SistemaArchivosPuerto(Protocol):
    def existe_ruta(self, ruta: Path) -> bool: ...

    def existe(self, ruta: Path) -> bool: ...

    def leer_texto(self, ruta: Path) -> str: ...

    def leer_bytes(self, ruta: Path) -> bytes: ...

    def escribir_texto(self, ruta: Path, contenido: str) -> None: ...

    def escribir_bytes(self, ruta: Path, contenido: bytes) -> None: ...

    def mkdir(self, ruta: Path, *, parents: bool = True, exist_ok: bool = True) -> None: ...

    def listar(self, base: Path) -> list[Path]: ...


class DocumentoNoEncontradoError(FileNotFoundError):
    """Error de aplicación para documentos esperados que no existen."""


class ProveedorDocumentosPuerto(Protocol):
    def obtener_ruta_guia_sync(self) -> str: ...
