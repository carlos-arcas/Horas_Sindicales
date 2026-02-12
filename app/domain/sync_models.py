from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncSummary:
    inserted_local: int = 0
    updated_local: int = 0
    inserted_remote: int = 0
    updated_remote: int = 0
    duplicates_skipped: int = 0
    conflicts_detected: int = 0
    errors: int = 0
    omitted_by_delegada: int = 0

    def __init__(
        self,
        inserted_local: int = 0,
        updated_local: int = 0,
        inserted_remote: int = 0,
        updated_remote: int = 0,
        duplicates_skipped: int = 0,
        conflicts_detected: int = 0,
        errors: int = 0,
        omitted_by_delegada: int = 0,
        omitidas_por_delegada: int | None = None,
        downloaded: int | None = None,
        uploaded: int | None = None,
        conflicts: int | None = None,
        omitted_duplicates: int | None = None,
    ) -> None:
        if downloaded is not None:
            inserted_local = downloaded
        if uploaded is not None:
            inserted_remote = uploaded
        if conflicts is not None:
            conflicts_detected = conflicts
        if omitted_duplicates is not None:
            duplicates_skipped = omitted_duplicates
        if omitidas_por_delegada is not None:
            omitted_by_delegada = omitidas_por_delegada
        object.__setattr__(self, "inserted_local", inserted_local)
        object.__setattr__(self, "updated_local", updated_local)
        object.__setattr__(self, "inserted_remote", inserted_remote)
        object.__setattr__(self, "updated_remote", updated_remote)
        object.__setattr__(self, "duplicates_skipped", duplicates_skipped)
        object.__setattr__(self, "conflicts_detected", conflicts_detected)
        object.__setattr__(self, "errors", errors)
        object.__setattr__(self, "omitted_by_delegada", omitted_by_delegada)

    @property
    def downloaded(self) -> int:
        return self.inserted_local + self.updated_local

    @property
    def uploaded(self) -> int:
        return self.inserted_remote + self.updated_remote

    @property
    def conflicts(self) -> int:
        return self.conflicts_detected + self.errors

    @property
    def omitted_duplicates(self) -> int:
        return self.duplicates_skipped

    @property
    def omitidas_por_delegada(self) -> int:
        return self.omitted_by_delegada
