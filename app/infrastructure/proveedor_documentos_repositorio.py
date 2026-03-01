from __future__ import annotations

from pathlib import Path

from app.application.ports.proveedor_documentos_puerto import (
    DocumentoNoEncontradoError,
    ProveedorDocumentosPuerto,
)


class ProveedorDocumentosRepositorio(ProveedorDocumentosPuerto):
    _NOMBRE_GUIA_SYNC = "guia_sync_paso_a_paso.md"

    def __init__(self, raiz_repo: Path | None = None) -> None:
        self._raiz_repo = raiz_repo.resolve() if raiz_repo else self._detectar_raiz_repo()

    def obtener_ruta_guia_sync(self) -> str:
        ruta = self._raiz_repo / "docs" / self._NOMBRE_GUIA_SYNC
        if not ruta.is_file():
            raise DocumentoNoEncontradoError(
                "No se encontró la guía de Sync en la ruta esperada: "
                f"{ruta.as_posix()}"
            )
        return ruta.as_posix()

    @staticmethod
    def _detectar_raiz_repo() -> Path:
        actual = Path(__file__).resolve()
        for candidato in actual.parents:
            if (candidato / ".git").exists() and (candidato / "docs").is_dir():
                return candidato

        raise DocumentoNoEncontradoError(
            "No se pudo detectar la raíz del repositorio para resolver documentos."
        )
