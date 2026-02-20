from __future__ import annotations

import logging
import sys

from app.bootstrap.logging import write_crash_log
from app.bootstrap.settings import resolve_log_dir
from app.entrypoints.main import main


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error no controlado en entrypoint main.__main__")
        exc_type, _, tb = sys.exc_info()
        log_dir = resolve_log_dir()
        if exc_type and tb:
            write_crash_log(exc_type, exc, tb, log_dir)
        logger.error(
            "Se produjo un error interno en main.__main__. Revisa el archivo de logs para más detalles."
        )
        raise
