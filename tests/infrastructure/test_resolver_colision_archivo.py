from __future__ import annotations

from pathlib import Path

from app.infrastructure.sistema_archivos.resolver_colision_archivo import (
    resolver_colision_archivo,
)


def test_resolver_colision_archivo_sin_colision_retorna_destino(tmp_path: Path) -> None:
    destino = tmp_path / "export.pdf"

    assert resolver_colision_archivo(destino) == destino.resolve(strict=False)


def test_resolver_colision_archivo_usa_numeracion_desde_2(tmp_path: Path) -> None:
    destino = tmp_path / "export.pdf"
    destino.write_bytes(b"base")
    (tmp_path / "export (2).pdf").write_bytes(b"ocupado")

    assert resolver_colision_archivo(destino) == (tmp_path / "export (3).pdf").resolve(
        strict=False
    )
