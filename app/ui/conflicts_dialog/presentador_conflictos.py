from __future__ import annotations

from app.application.conflicts_service import ConflictRecord
from app.ui.conflict_guidance import classify_conflict, delegada_name, recommended_action

from .contratos import ModeloVistaConflictoFila, ModeloVistaResumenResolucion


def construir_filas_conflicto(conflicts: list[ConflictRecord]) -> list[ModeloVistaConflictoFila]:
    return [construir_fila_conflicto(conflict) for conflict in conflicts]


def construir_fila_conflicto(conflict: ConflictRecord) -> ModeloVistaConflictoFila:
    return ModeloVistaConflictoFila(
        record=conflict,
        tipo=formatear_tipo(conflict.entity_type),
        fecha=extraer_fecha(conflict.local_snapshot, conflict.remote_snapshot),
        campo=extraer_campo(conflict),
        local_updated=str(conflict.local_snapshot.get("updated_at") or ""),
        remote_updated=str(conflict.remote_snapshot.get("updated_at") or ""),
    )


def formatear_tipo(entity_type: str) -> str:
    mapping = {
        "delegadas": "delegada",
        "solicitudes": "solicitud",
        "cuadrantes": "cuadrante",
    }
    return mapping.get(entity_type, entity_type)


def extraer_fecha(local_snapshot: dict, remote_snapshot: dict) -> str:
    for key in ("fecha_pedida", "fecha", "created_at"):
        if local_snapshot.get(key):
            return str(local_snapshot.get(key))
        if remote_snapshot.get(key):
            return str(remote_snapshot.get(key))
    return ""


def extraer_campo(conflict: ConflictRecord) -> str:
    ignored = {"id", "updated_at", "source_device", "deleted", "__row_number__"}
    local = conflict.local_snapshot
    remote = conflict.remote_snapshot
    for key in sorted(set(local.keys()) | set(remote.keys())):
        if key in ignored:
            continue
        if str(local.get(key)) != str(remote.get(key)):
            return key
    if conflict.entity_type == "delegadas":
        return str(local.get("nombre") or remote.get("nombre") or "")
    if conflict.entity_type == "solicitudes":
        return str(local.get("fecha_pedida") or remote.get("fecha") or "")
    if conflict.entity_type == "cuadrantes":
        return str(local.get("dia_semana") or remote.get("dia_semana") or "")
    return ""


def construir_resumen_panel_inicial(filas: list[ModeloVistaConflictoFila], t) -> str:
    if not filas:
        return t("ui.conflictos.sin_conflictos")
    first = filas[0].record
    tipo_conflicto = classify_conflict(first)
    linea_titulo = f"{chr(91)}{t('ui.conflictos.conflictos_detectados')}{chr(93)}"
    lineas = (
        linea_titulo,
        f"{t('ui.conflictos.item_total')}{chr(32)}{len(filas)}",
        f"{t('ui.conflictos.item_tipo_conflicto')}{chr(32)}{tipo_conflicto}",
        f"{t('ui.conflictos.item_delegada_afectada')}{chr(32)}{delegada_name(first)}",
        f"{t('ui.conflictos.item_accion_recomendada')}{chr(32)}{recommended_action(tipo_conflicto)}",
    )
    return chr(10).join(lineas)


def construir_resumen_resolucion(
    filas: list[ModeloVistaConflictoFila],
    ids_revision_manual: set[int],
    total_resueltos: int,
) -> ModeloVistaResumenResolucion:
    pending_ids = {fila.record.id for fila in filas}
    manual_pending = len(ids_revision_manual & pending_ids)
    return ModeloVistaResumenResolucion(
        resueltos=total_resueltos,
        pendientes=len(filas),
        revision_manual=manual_pending,
    )


def siguiente_indice(fila_actual: int | None, total_filas: int) -> int | None:
    if total_filas <= 0:
        return None
    if fila_actual is None:
        return 0
    nueva_fila = fila_actual + 1
    if nueva_fila >= total_filas:
        return 0
    return nueva_fila
