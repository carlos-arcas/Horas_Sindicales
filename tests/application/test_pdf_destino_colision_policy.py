from __future__ import annotations

from pathlib import Path

from app.application.use_cases.solicitudes.pdf_destino_policy import (
    resolver_colision_archivo,
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
    (tmp_path / "X (1).pdf").write_bytes(b"1")

    resultado = resolver_colision_pdf(destino, _FsLocal())

    assert resultado == (tmp_path / "X (2).pdf").resolve(strict=False)


def test_resolver_colision_archivo_sin_colision_retorna_destino(tmp_path: Path) -> None:
    destino = tmp_path / "reporte (1).pdf"

    resultado = resolver_colision_archivo(destino, _FsLocal())

    assert resultado == destino.resolve(strict=False)


def test_resolver_colision_archivo_colision_en_1_propone_2(tmp_path: Path) -> None:
    destino = tmp_path / "reporte (1).pdf"
    destino.write_bytes(b"1")

    resultado = resolver_colision_archivo(destino, _FsLocal())

    assert resultado == (tmp_path / "reporte (2).pdf").resolve(strict=False)


def test_resolver_colision_archivo_colision_multiple_propone_4(tmp_path: Path) -> None:
    destino = tmp_path / "reporte (1).pdf"
    destino.write_bytes(b"1")
    (tmp_path / "reporte (2).pdf").write_bytes(b"2")
    (tmp_path / "reporte (3).pdf").write_bytes(b"3")

    resultado = resolver_colision_archivo(destino, _FsLocal())

    assert resultado == (tmp_path / "reporte (4).pdf").resolve(strict=False)
