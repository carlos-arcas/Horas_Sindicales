from __future__ import annotations

from dataclasses import dataclass

from app.core.observability import generate_correlation_id


@dataclass(frozen=True, slots=True)
class ContextoOperacion:
    correlation_id: str
    result_id: str | None = None

    @classmethod
    def nuevo(cls, result_id: str | None = None) -> "ContextoOperacion":
        return cls(correlation_id=generate_correlation_id(), result_id=result_id)
