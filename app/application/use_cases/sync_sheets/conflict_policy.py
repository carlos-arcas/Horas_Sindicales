from __future__ import annotations

from datetime import datetime
from typing import Any

from app.application.use_cases.sync_sheets import conflicts


# Política pura para decidir conflictos sin tocar infraestructura.
def is_conflict(local_updated_at: Any, remote_updated_at: datetime | None, last_sync_at: str | None) -> bool:
    remote_value = remote_updated_at.isoformat() if remote_updated_at else None
    return conflicts.is_conflict(local_updated_at, remote_value, last_sync_at)
