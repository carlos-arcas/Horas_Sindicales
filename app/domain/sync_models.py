from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, init=False)
class SyncSummary:
    inserted_local: int = 0
    updated_local: int = 0
    inserted_remote: int = 0
    updated_remote: int = 0
    duplicates_skipped: int = 0
    conflicts_detected: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)

    def __init__(
        self,
        *,
        inserted_local: int = 0,
        updated_local: int = 0,
        inserted_remote: int = 0,
        updated_remote: int = 0,
        duplicates_skipped: int = 0,
        conflicts_detected: int = 0,
        errors: tuple[str, ...] = (),
        downloaded: int | None = None,
        uploaded: int | None = None,
        conflicts: int | None = None,
        omitted_duplicates: int | None = None,
    ) -> None:
        if downloaded is not None:
            inserted_local = downloaded
        if uploaded is not None:
            inserted_remote = uploaded
        if omitted_duplicates is not None:
            duplicates_skipped = omitted_duplicates
        if conflicts is not None:
            conflicts_detected = conflicts
        object.__setattr__(self, "inserted_local", inserted_local)
        object.__setattr__(self, "updated_local", updated_local)
        object.__setattr__(self, "inserted_remote", inserted_remote)
        object.__setattr__(self, "updated_remote", updated_remote)
        object.__setattr__(self, "duplicates_skipped", duplicates_skipped)
        object.__setattr__(self, "conflicts_detected", conflicts_detected)
        object.__setattr__(self, "errors", errors)

    @property
    def downloaded(self) -> int:
        return self.inserted_local + self.updated_local

    @property
    def uploaded(self) -> int:
        return self.inserted_remote + self.updated_remote

    @property
    def conflicts(self) -> int:
        return self.conflicts_detected + len(self.errors)

    @property
    def omitted_duplicates(self) -> int:
        return self.duplicates_skipped
