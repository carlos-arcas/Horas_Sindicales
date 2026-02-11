from __future__ import annotations

from app.infrastructure.local_config import SheetsConfigStore


class LocalConfigStore(SheetsConfigStore):
    """Adaptador nominal para inyección por puerto."""

