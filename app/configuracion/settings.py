from __future__ import annotations

import os


def is_read_only_enabled() -> bool:
    """Indica si la app está en modo solo lectura según la variable READ_ONLY."""
    value = os.environ.get("READ_ONLY", "").strip().lower()
    return value in {"1", "true", "yes", "on"}
