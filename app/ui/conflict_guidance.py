from __future__ import annotations

from app.application.conflicts_service import ConflictRecord
from app.ui.copy_catalog import copy_text


def classify_conflict(conflict: ConflictRecord) -> str:
    local = {str(k).lower(): str(v).lower() for k, v in conflict.local_snapshot.items()}
    remote = {str(k).lower(): str(v).lower() for k, v in conflict.remote_snapshot.items()}
    keys = set(local.keys()) | set(remote.keys())
    values_joined = " ".join(list(local.values()) + list(remote.values()))
    if any(token in values_joined for token in ("permiso", "acceso", "credential", "forbidden", "unauthorized")):
        return copy_text("ui.conflictos.tipo_error_acceso")
    if any(token in keys for token in ("horas_mes_min", "horas_ano_min", "saldo_min", "saldo")):
        return copy_text("ui.conflictos.tipo_diferencia_saldo")
    if any(token in keys for token in ("duplicate_of", "duplicado", "is_duplicate", "dup_uuid")):
        return copy_text("ui.conflictos.tipo_duplicado_remoto")
    return copy_text("ui.conflictos.tipo_solicitud_ya_modificada")


def delegada_name(conflict: ConflictRecord) -> str:
    for payload in (conflict.local_snapshot, conflict.remote_snapshot):
        for key in ("nombre", "delegada_nombre", "persona_nombre"):
            value = payload.get(key)
            if value:
                return str(value)
    return copy_text("ui.comun.no_disponible")


def recommended_action(conflict_type: str) -> str:
    if conflict_type == copy_text("ui.conflictos.tipo_error_acceso"):
        return copy_text("ui.comun.reintentar")
    if conflict_type == copy_text("ui.conflictos.tipo_diferencia_saldo"):
        return copy_text("ui.conflictos.revisar_manualmente")
    return copy_text("ui.conflictos.mantener_local")


def build_what_happened(conflict: ConflictRecord) -> str:
    conflict_type = classify_conflict(conflict)
    return (
        f"{copy_text('ui.conflictos.tipo_label')} {conflict_type}\n"
        f"{copy_text('ui.conflictos.delegada_afectada_label')} {delegada_name(conflict)}\n"
        f"{copy_text('ui.conflictos.solicitud_label')} {conflict.uuid}\n"
        f"{copy_text('ui.conflictos.accion_recomendada_label')} {recommended_action(conflict_type)}"
    )


def build_why_happened(conflict: ConflictRecord) -> str:
    conflict_type = classify_conflict(conflict)
    mapping = {
        copy_text("ui.conflictos.tipo_duplicado_remoto"): copy_text("ui.conflictos.why_duplicado_remoto"),
        copy_text("ui.conflictos.tipo_diferencia_saldo"): copy_text("ui.conflictos.why_diferencia_saldo"),
        copy_text("ui.conflictos.tipo_solicitud_ya_modificada"): copy_text("ui.conflictos.why_solicitud_ya_modificada"),
        copy_text("ui.conflictos.tipo_error_acceso"): copy_text("ui.conflictos.why_error_acceso"),
    }
    return mapping.get(conflict_type, copy_text("ui.conflictos.why_por_defecto"))
