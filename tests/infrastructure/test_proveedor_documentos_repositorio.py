from __future__ import annotations

from pathlib import Path

import pytest

from app.application.ports.proveedor_documentos_puerto import DocumentoNoEncontradoError
from app.infrastructure.proveedor_documentos_repositorio import ProveedorDocumentosRepositorio


def test_obtener_ruta_guia_sync_devuelve_ruta_existente_y_md_correcto() -> None:
    proveedor = ProveedorDocumentosRepositorio()

    ruta = Path(proveedor.obtener_ruta_guia_sync())

    assert ruta.exists()
    assert ruta.name == "guia_sync_paso_a_paso.md"
    assert ruta.suffix == ".md"


def test_obtener_ruta_guia_sync_lanza_error_controlado_si_falta_archivo(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    proveedor = ProveedorDocumentosRepositorio(raiz_repo=tmp_path)

    with pytest.raises(DocumentoNoEncontradoError):
        proveedor.obtener_ruta_guia_sync()
