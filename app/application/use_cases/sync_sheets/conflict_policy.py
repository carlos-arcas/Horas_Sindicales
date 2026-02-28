from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.application.use_cases.sync_sheets import conflicts


class ConflictOutcome(str, Enum):
    NO_CONFLICT = "no_conflict"
    DIVERGENT_CONFLICT = "divergent_conflict"


@dataclass(frozen=True)
class ConflictDecision:
    outcome: ConflictOutcome
    allow_overwrite_local: bool
    should_register_conflict: bool


def evaluate_conflict_policy(
    local_updated_at: Any,
    remote_updated_at: datetime | None,
    last_sync_at: str | None,
) -> ConflictDecision:
    """Evalúa la política de conflictos para pull remoto -> local.

    Reglas:
    - Hay conflicto sólo cuando local y remoto cambiaron después de ``last_sync_at``.
    - Si hay conflicto divergente, NO se permite pisar local y se debe registrar conflicto.
    - Si no hay conflicto, se permite continuar con la política normal (overwrite/skip según recencia).
    """

    remote_value = remote_updated_at.isoformat() if remote_updated_at else None
    has_conflict = conflicts.is_conflict(local_updated_at, remote_value, last_sync_at)
    if has_conflict:
        return ConflictDecision(
            outcome=ConflictOutcome.DIVERGENT_CONFLICT,
            allow_overwrite_local=False,
            should_register_conflict=True,
        )
    return ConflictDecision(
        outcome=ConflictOutcome.NO_CONFLICT,
        allow_overwrite_local=True,
        should_register_conflict=False,
    )


def is_conflict(local_updated_at: Any, remote_updated_at: datetime | None, last_sync_at: str | None) -> bool:
    return evaluate_conflict_policy(local_updated_at, remote_updated_at, last_sync_at).should_register_conflict
