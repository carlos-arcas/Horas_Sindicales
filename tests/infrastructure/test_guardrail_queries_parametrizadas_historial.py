from pathlib import Path


def test_list_historico_batch_usa_parametros_en_limit_offset() -> None:
    contenido = Path("app/infrastructure/repos_sqlite.py").read_text(encoding="utf-8")
    bloque_inicio = contenido.index("def list_historico_batch")
    bloque = contenido[bloque_inicio: bloque_inicio + 900]

    assert "LIMIT ? OFFSET ?" in bloque
    assert "(limit, offset)" in bloque
