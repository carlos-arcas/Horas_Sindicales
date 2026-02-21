from __future__ import annotations

import json

from app.bootstrap.exception_handler import manejar_excepcion_global
from app.bootstrap.logging import configure_logging


def test_exception_handler_devuelve_incident_id_y_lo_loguea(tmp_path) -> None:
    configure_logging(tmp_path)

    try:
        raise ValueError("fallo controlado para test")
    except ValueError as exc:
        incident_id = manejar_excepcion_global(ValueError, exc, exc.__traceback__)

    assert incident_id.startswith("INC-")

    crash_log = tmp_path / "crashes.log"
    assert crash_log.exists()
    lines = [json.loads(line) for line in crash_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(event.get("mensaje", "").find(incident_id) >= 0 for event in lines)
