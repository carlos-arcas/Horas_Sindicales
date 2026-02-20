from __future__ import annotations

from app.application.conflicts_service import ConflictRecord


def classify_conflict(conflict: ConflictRecord) -> str:
    local = {str(k).lower(): str(v).lower() for k, v in conflict.local_snapshot.items()}
    remote = {str(k).lower(): str(v).lower() for k, v in conflict.remote_snapshot.items()}
    keys = set(local.keys()) | set(remote.keys())
    values_joined = " ".join(list(local.values()) + list(remote.values()))
    if any(token in values_joined for token in ("permiso", "acceso", "credential", "forbidden", "unauthorized")):
        return "Error de acceso"
    if any(token in keys for token in ("horas_mes_min", "horas_ano_min", "saldo_min", "saldo")):
        return "Diferencia de saldo"
    if any(token in keys for token in ("duplicate_of", "duplicado", "is_duplicate", "dup_uuid")):
        return "Duplicado remoto"
    return "Registro ya modificado"


def delegada_name(conflict: ConflictRecord) -> str:
    for payload in (conflict.local_snapshot, conflict.remote_snapshot):
        for key in ("nombre", "delegada_nombre", "persona_nombre"):
            value = payload.get(key)
            if value:
                return str(value)
    return "No disponible"


def recommended_action(conflict_type: str) -> str:
    if conflict_type == "Error de acceso":
        return "Reintentar"
    if conflict_type == "Diferencia de saldo":
        return "Revisar manualmente"
    return "Mantener local"


def build_what_happened(conflict: ConflictRecord) -> str:
    conflict_type = classify_conflict(conflict)
    return (
        f"Tipo: {conflict_type}\n"
        f"Delegada afectada: {delegada_name(conflict)}\n"
        f"Registro: {conflict.uuid}\n"
        f"Acción recomendada: {recommended_action(conflict_type)}"
    )


def build_why_happened(conflict: ConflictRecord) -> str:
    conflict_type = classify_conflict(conflict)
    mapping = {
        "Duplicado remoto": "El mismo registro llegó dos veces desde la nube o se repitió durante un reintento.",
        "Diferencia de saldo": "Los minutos u horas disponibles no coinciden entre este equipo y la nube.",
        "Registro ya modificado": "El registro cambió en ambos lados antes de terminar la sincronización.",
        "Error de acceso": "No fue posible validar correctamente un dato remoto por permisos o acceso.",
    }
    return mapping.get(conflict_type, "El registro se modificó en distintos momentos y necesita una decisión.")
