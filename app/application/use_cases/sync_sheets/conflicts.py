from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def is_conflict(local_updated_at: Any, remote_updated_at: Any, last_sync_at: str | None) -> bool:
    if not local_updated_at or not remote_updated_at or not last_sync_at:
        return False
    sync_at = parse_iso(last_sync_at)
    local_at = parse_iso(local_updated_at)
    remote_at = parse_iso(remote_updated_at)
    if not sync_at or not local_at or not remote_at:
        return False
    return local_at > sync_at and remote_at > sync_at
