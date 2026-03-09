from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from app.infrastructure.cargador_comunidad_demo_sqlite import CargadorComunidadDemoSQLite
from app.infrastructure.db import get_connection
from app.infrastructure.migrations import run_migrations

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga dataset demo para módulo de descubrimiento de comunidad")
    parser.add_argument("--db", default=None, help="Ruta sqlite. Si se omite usa runtime por defecto")
    parser.add_argument(
        "--dataset",
        default=str(Path("app/infrastructure/recursos/comunidad_demo.json")),
        help="Ruta al dataset JSON",
    )
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else None
    connection = get_connection(db_path)
    try:
        run_migrations(connection)
        dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
        cargador = CargadorComunidadDemoSQLite(connection, dataset)
        perfiles, publicaciones = cargador.cargar()
        logger.info("Demo comunidad cargada", extra={"perfiles": perfiles, "publicaciones": publicaciones})
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
