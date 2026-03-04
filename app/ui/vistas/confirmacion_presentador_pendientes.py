from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.ui.vistas.pendientes_iter_presenter import IterAction, IterPendientesEntrada, PendienteRowSnapshot, plan_iter_pendientes

if TYPE_CHECKING:
    from app.application.dto import SolicitudDTO


def iterar_pendientes_en_tabla(
    *,
    model: Any,
    pendientes_model: Any,
    qt_horizontal: object,
    qt_display_role: object,
) -> list[dict[str, object]]:
    snapshots = build_pendientes_snapshots(model, pendientes_model, qt_horizontal, qt_display_role)
    plan = plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=tuple(snapshots)))
    return apply_iter_pendientes_actions(plan.actions)


def build_pendientes_snapshots(
    model: Any,
    pendientes_model: Any,
    qt_horizontal: object,
    qt_display_role: object,
) -> list[PendienteRowSnapshot]:
    total_rows = model.rowCount()
    total_cols = model.columnCount()
    delegada_col = find_delegada_col(model, total_cols, qt_horizontal, qt_display_role)
    snapshots: list[PendienteRowSnapshot] = []
    for row in range(total_rows):
        solicitud = pendientes_model.solicitud_at(row) if pendientes_model is not None else None
        snapshots.append(
            PendienteRowSnapshot(
                row=row,
                solicitud_id=solicitud.id if solicitud is not None else None,
                persona_id=solicitud.persona_id if solicitud is not None else None,
                fecha_raw=model.index(row, 0).data() if total_cols > 0 else "",
                desde_raw=model.index(row, 1).data() if total_cols > 1 else "",
                hasta_raw=model.index(row, 2).data() if total_cols > 2 else "",
                delegada_raw=model.index(row, delegada_col).data() if delegada_col is not None else None,
            )
        )
    return snapshots


def find_delegada_col(model: Any, total_cols: int, qt_horizontal: object, qt_display_role: object) -> int | None:
    for col in range(total_cols):
        header = model.headerData(col, qt_horizontal, qt_display_role)
        if str(header).strip().lower() == "delegada":
            return col
    return None


def apply_iter_pendientes_actions(actions: tuple[IterAction, ...]) -> list[dict[str, object]]:
    pendientes: list[dict[str, object]] = []
    for action in actions:
        if action.action_type == "APPEND_PENDING":
            pendientes.append(dict(action.payload))
    return pendientes


def calcular_filtro_delegada_para_confirmacion(pending_view_all: bool, persona_id: int | None) -> int | None:
    if pending_view_all:
        return None
    return persona_id


def seleccionar_creadas_por_ids(selected: list[SolicitudDTO], confirmadas_ids: list[int]) -> list[SolicitudDTO]:
    confirmadas_ids_set = set(confirmadas_ids)
    return [solicitud for solicitud in selected if solicitud.id in confirmadas_ids_set]


def filtrar_pendientes_restantes(
    pendientes: list[SolicitudDTO],
    pendientes_restantes_ids: list[int] | None,
) -> list[SolicitudDTO] | None:
    if pendientes_restantes_ids is None:
        return None
    pendientes_ids = set(pendientes_restantes_ids)
    return [solicitud for solicitud in pendientes if solicitud.id is None or solicitud.id in pendientes_ids]


def contar_pendientes_restantes(pendientes_restantes: list[SolicitudDTO] | None) -> int:
    if pendientes_restantes is None:
        return 0
    return len(pendientes_restantes)
