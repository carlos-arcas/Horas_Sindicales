from pathlib import Path

from app.infrastructure.sistema_archivos.resolver_colision_archivo import resolver_ruta_sin_colision


def test_resolver_ruta_sin_colision_retorna_ruta_original_si_no_existe(tmp_path: Path) -> None:
    destino = tmp_path / "parte.pdf"
    assert resolver_ruta_sin_colision(destino) == destino.resolve(strict=False)


def test_resolver_ruta_sin_colision_agrega_sufijo_incremental(tmp_path: Path) -> None:
    base = tmp_path / "parte.pdf"
    base.write_text("x", encoding="utf-8")
    (tmp_path / "parte (2).pdf").write_text("x", encoding="utf-8")

    ruta = resolver_ruta_sin_colision(base)

    assert ruta.name == "parte (3).pdf"
