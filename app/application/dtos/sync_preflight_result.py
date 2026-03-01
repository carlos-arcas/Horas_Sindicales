from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SyncPreflightIssue:
    tipo: str
    mensaje: str
    accion_sugerida: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SyncPreflightResult:
    ok: bool
    issues: tuple[SyncPreflightIssue, ...] = ()

    @classmethod
    def ok_result(cls) -> "SyncPreflightResult":
        return cls(ok=True)

    @classmethod
    def permission_denied(
        cls,
        *,
        mensaje: str,
        accion_sugerida: str,
        metadata: dict[str, str] | None = None,
    ) -> "SyncPreflightResult":
        issue = SyncPreflightIssue(
            tipo="PERMISSION_DENIED",
            mensaje=mensaje,
            accion_sugerida=accion_sugerida,
            metadata=metadata or {},
        )
        return cls(ok=False, issues=(issue,))
