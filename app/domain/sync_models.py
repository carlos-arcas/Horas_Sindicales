from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncSummary:
    downloaded: int
    uploaded: int
    conflicts: int
    omitted_duplicates: int
