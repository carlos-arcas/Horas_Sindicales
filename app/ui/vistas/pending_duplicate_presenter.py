from __future__ import annotations

from dataclasses import dataclass

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import clave_duplicado_solicitud


@dataclass(frozen=True)
class PendingDuplicateEntrada:
    """Entrada pura para resolver foco de duplicados en pendientes.

    Precedencia (de mayor a menor):
    1) Si la solicitud objetivo no puede normalizarse, no hay duplicado enfocable.
    2) Si la clave objetivo no está en `duplicated_keys`, no se considera duplicado activo.
    3) Si hay matches válidos (excluyendo la fila/ID en edición), se elige el menor índice.
    4) Si no hay matches válidos pero sí hay pendientes y la clave está marcada como duplicada,
       aplicar fallback estable a la fila 0 (comportamiento legado).
    5) Si no hay pendientes, devolver `None`.
    """

    solicitud: SolicitudDTO
    pending_solicitudes: list[SolicitudDTO]
    editing_pending_id: int | None
    editing_row: int | None
    duplicated_keys: set[tuple[int, str, str, str, str]]


@dataclass(frozen=True)
class PendingDuplicateDecision:
    row_index: int | None
    row_id: int | None
    reason_code: str
    debug_evidence: tuple[str, ...] = ()


def resolve_pending_duplicate_row(entrada: PendingDuplicateEntrada) -> PendingDuplicateDecision:
    try:
        target_key = clave_duplicado_solicitud(entrada.solicitud)
    except Exception:
        return PendingDuplicateDecision(row_index=None, row_id=None, reason_code="target_key_invalid")

    duplicate_key = tuple(list(target_key) + ["COMPLETO" if entrada.solicitud.completo else "PARCIAL"])
    if duplicate_key not in entrada.duplicated_keys:
        return PendingDuplicateDecision(
            row_index=None,
            row_id=None,
            reason_code="key_not_marked_duplicated",
            debug_evidence=(f"duplicate_key={duplicate_key}",),
        )

    for row_index, pending in enumerate(entrada.pending_solicitudes):
        if (
            entrada.editing_pending_id is not None
            and pending.id is not None
            and str(pending.id) == str(entrada.editing_pending_id)
        ):
            continue
        if pending.id is None and entrada.editing_row is not None and row_index == entrada.editing_row:
            continue
        try:
            if clave_duplicado_solicitud(pending) == target_key:
                return PendingDuplicateDecision(
                    row_index=row_index,
                    row_id=pending.id,
                    reason_code="matched_duplicate_row",
                )
        except Exception:
            continue

    if entrada.pending_solicitudes:
        fallback = entrada.pending_solicitudes[0]
        return PendingDuplicateDecision(
            row_index=0,
            row_id=fallback.id,
            reason_code="fallback_first_row",
        )

    return PendingDuplicateDecision(row_index=None, row_id=None, reason_code="no_pending_rows")
