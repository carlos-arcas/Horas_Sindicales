from __future__ import annotations

from pathlib import Path

from app.infrastructure.db import get_connection
from app.bootstrap.container import build_container


def test_build_container_smoke(tmp_path: Path) -> None:
    db_path = tmp_path / "smoke.db"

    def connection_factory():
        return get_connection(db_path)

    container = build_container(connection_factory=connection_factory)

    assert container.persona_use_cases is not None
    assert container.solicitud_use_cases is not None
    assert container.grupo_use_cases is not None
    assert container.sheets_service is not None
    assert container.sync_service is not None
    assert container.conflicts_service is not None
    assert container.health_check_use_case is not None
    assert container.alert_engine is not None
