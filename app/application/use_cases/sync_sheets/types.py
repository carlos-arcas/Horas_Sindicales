from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.sync_models import SyncExecutionPlan, SyncPlanItem, SyncSummary


@dataclass(frozen=True)
class Conflict:
    table_name: str
    record_uuid: str
    local_payload: dict[str, Any]
    remote_payload: dict[str, Any]


@dataclass(frozen=True)
class SyncItem:
    item: SyncPlanItem


@dataclass(frozen=True)
class SyncPlan:
    plan: SyncExecutionPlan


@dataclass(frozen=True)
class SyncReport:
    summary: SyncSummary
    metadata: dict[str, Any] = field(default_factory=dict)
