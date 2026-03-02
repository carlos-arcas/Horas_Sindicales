from __future__ import annotations

from pathlib import Path

from app.application.use_cases.solicitudes.pdf_destino_policy import (
    resolver_colision_pdf,
)


class _FsLocal:
    def existe(self, ruta: Path) -> bool:
        return ruta.exists()


def test_policy_pdf_sin_colision_retorna_misma_ruta(tmp_path: Path) -> None:
    destino = tmp_path / "X.pdf"

    resultado = resolver_colision_pdf(destino, _FsLocal())

    assert resultado == destino.resolve(strict=False)


def test_policy_pdf_colision_propone_numeracion_incremental(tmp_path: Path) -> None:
    destino = tmp_path / "X.pdf"
    destino.write_bytes(b"0")
    (tmp_path / "X (2).pdf").write_bytes(b"1")

    resultado = resolver_colision_pdf(destino, _FsLocal())

    assert resultado == (tmp_path / "X (3).pdf").resolve(strict=False)
