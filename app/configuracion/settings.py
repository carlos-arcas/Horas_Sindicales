from __future__ import annotations

import os


STARTUP_TIMEOUT_MS_POR_DEFECTO = 30_000
ENV_STARTUP_TIMEOUT_MS = "HORAS_SINDICALES_STARTUP_TIMEOUT_MS"


def is_read_only_enabled() -> bool:
    """Indica si la app está en modo solo lectura según la variable READ_ONLY."""
    value = os.environ.get("READ_ONLY", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def resolver_startup_timeout_ms() -> int:
    """Resuelve timeout de arranque desde entorno con fallback seguro."""
    raw = os.environ.get(ENV_STARTUP_TIMEOUT_MS)
    if raw is None:
        raw = os.environ.get("HORAS_STARTUP_TIMEOUT_MS", str(STARTUP_TIMEOUT_MS_POR_DEFECTO))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return STARTUP_TIMEOUT_MS_POR_DEFECTO
