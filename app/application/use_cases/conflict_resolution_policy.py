from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.domain.sync_models import SyncExecutionPlan, SyncPlanItem


ConflictDecision = str


@dataclass(frozen=True)
class ConflictDecisionRecord:
    item_uuid: str
    decision: ConflictDecision
    decided_at: str


class ConflictResolutionPolicy:
    """Aplica decisiones de conflicto sin ejecutar escritura remota."""

    def __init__(self, log_root: Path) -> None:
        self._log_root = log_root

    def apply(self, plan: SyncExecutionPlan, decisions: dict[str, ConflictDecision]) -> tuple[SyncExecutionPlan, tuple[str, ...]]:
        promote_to_update: list[SyncPlanItem] = []
        keep_remote: list[SyncPlanItem] = []
        unresolved: list[str] = []

        for item in plan.conflicts:
            decision = decisions.get(item.uuid)
            if decision == "keep_local":
                promote_to_update.append(item)
            elif decision == "keep_remote":
                keep_remote.append(item)
            else:
                unresolved.append(item.uuid)

        adjusted = SyncExecutionPlan(
            generated_at=plan.generated_at,
            worksheet=plan.worksheet,
            to_create=plan.to_create,
            to_update=tuple([*plan.to_update, *promote_to_update]),
            unchanged=tuple([*plan.unchanged, *keep_remote]),
            conflicts=tuple(item for item in plan.conflicts if item.uuid in unresolved),
            potential_errors=plan.potential_errors,
            values_matrix=plan.values_matrix,
        )
        self._persist_decisions(decisions)
        return adjusted, tuple(unresolved)

    def _persist_decisions(self, decisions: dict[str, ConflictDecision]) -> None:
        now = datetime.now().strftime("%Y%m%d")
        log_dir = self._log_root / "logs" / "sync_history"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"conflict_decisions_{now}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            for item_uuid, decision in decisions.items():
                payload = ConflictDecisionRecord(item_uuid=item_uuid, decision=decision, decided_at=datetime.now().isoformat())
                fh.write(json.dumps(payload.__dict__, ensure_ascii=False) + "\n")
