from __future__ import annotations

import sys

from app.bootstrap.exception_handler import manejar_excepcion_global
from app.entrypoints.main import main


try:
    raise SystemExit(main())
except SystemExit:
    raise
except Exception:  # noqa: BLE001
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_type is None or exc_value is None or exc_traceback is None:
        raise SystemExit(2)
    incident_id = manejar_excepcion_global(exc_type, exc_value, exc_traceback)
    sys.stderr.write(f"Error inesperado. ID de incidente: {incident_id}\n")
    raise SystemExit(2)
