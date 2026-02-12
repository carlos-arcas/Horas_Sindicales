from __future__ import annotations

from app.domain.ports import SheetsConfigStorePort
from app.infrastructure.local_config import SheetsConfigStore


class LocalConfigStore(SheetsConfigStore, SheetsConfigStorePort):
    """Adaptador nominal para inyección por puerto."""
