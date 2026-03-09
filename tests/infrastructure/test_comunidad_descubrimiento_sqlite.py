from __future__ import annotations

import json
from pathlib import Path

from app.domain.comunidad_descubrimiento import FiltroDescubrimiento
from app.infrastructure.cargador_comunidad_demo_sqlite import CargadorComunidadDemoSQLite
from app.infrastructure.comunidad_sqlite import RepositorioComunidadSQLite
from app.infrastructure.db import get_connection
from app.infrastructure.migrations import run_migrations


def _dataset_demo() -> dict[str, object]:
    path = Path("app/infrastructure/recursos/comunidad_demo.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_carga_demo_es_idempotente(tmp_path: Path) -> None:
    connection = get_connection(tmp_path / "demo.db")
    try:
        run_migrations(connection)
        cargador = CargadorComunidadDemoSQLite(connection, _dataset_demo())
        cargador.cargar()
        cargador.cargar()

        total_publicaciones = connection.execute("SELECT COUNT(1) AS total FROM comunidad_publicaciones").fetchone()["total"]
        total_perfiles = connection.execute("SELECT COUNT(1) AS total FROM comunidad_perfiles").fetchone()["total"]
    finally:
        connection.close()

    assert total_publicaciones == 5
    assert total_perfiles == 4


def test_feed_populares_y_filtrado_por_disciplina(tmp_path: Path) -> None:
    connection = get_connection(tmp_path / "demo.db")
    try:
        run_migrations(connection)
        CargadorComunidadDemoSQLite(connection, _dataset_demo()).cargar()
        repo = RepositorioComunidadSQLite(connection)

        populares = repo.listar_publicaciones(FiltroDescubrimiento(orden="populares", limit=3))
        bjj = repo.listar_publicaciones(FiltroDescubrimiento(orden="recientes", disciplina="BJJ", limit=10))
    finally:
        connection.close()

    assert [p.publicacion_id for p in populares] == ["pub-005", "pub-001", "pub-003"]
    assert len(bjj) == 1
    assert bjj[0].disciplina == "BJJ"


def test_feed_vacio_si_no_hay_datos(tmp_path: Path) -> None:
    connection = get_connection(tmp_path / "demo.db")
    try:
        run_migrations(connection)
        repo = RepositorioComunidadSQLite(connection)
        publicaciones = repo.listar_publicaciones(FiltroDescubrimiento())
    finally:
        connection.close()

    assert publicaciones == []
