from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SolicitudesFocusInput:
    blocking_errors: dict[str, str]
    field_order: tuple[str, ...] = ("delegada", "fecha", "tramo")


@dataclass(frozen=True)
class SolicitudesStatusInput:
    delegada_actual: str | None
    pendientes_visibles: int
    pendientes_seleccionadas: int
    saldo_reservado: str
    has_blocking_errors: bool
    has_runtime_error: bool
    hay_conflictos_pendientes: bool
    puede_confirmar_pdf: bool


@dataclass(frozen=True)
class SolicitudesStatusOutput:
    label_key: str
    label_params: dict[str, str | int] = field(default_factory=dict)
    action_key: str = ""
    help_key: str | None = None


def resolve_first_invalid_field(data: SolicitudesFocusInput) -> str | None:
    for field_name in data.field_order:
        if field_name in data.blocking_errors:
            return field_name
    if data.blocking_errors:
        return next(iter(data.blocking_errors.keys()))
    return None


def _seleccion_key(pendientes_seleccionadas: int) -> str:
    if pendientes_seleccionadas <= 0:
        return "solicitudes.resumen_operativo.seleccion_ninguna"
    if pendientes_seleccionadas == 1:
        return "solicitudes.resumen_operativo.seleccion_una"
    return "solicitudes.resumen_operativo.seleccion_varias"


def build_solicitudes_status(data: SolicitudesStatusInput) -> SolicitudesStatusOutput:
    delegada_actual = data.delegada_actual or "—"
    label_params: dict[str, str | int] = {
        "delegada": delegada_actual,
        "pendientes": max(0, data.pendientes_visibles),
        "saldo_reservado": data.saldo_reservado,
        "seleccion_key": _seleccion_key(data.pendientes_seleccionadas),
    }
    if data.has_runtime_error or data.has_blocking_errors:
        return SolicitudesStatusOutput(
            label_key="solicitudes.resumen_operativo.estado_validacion",
            label_params=label_params,
            action_key="solicitudes.resumen_operativo.accion_corregir_validacion",
            help_key="solicitudes.resumen_operativo.ayuda_corregir_validacion",
        )
    if not data.delegada_actual:
        return SolicitudesStatusOutput(
            label_key="solicitudes.resumen_operativo.estado_sin_delegada",
            label_params=label_params,
            action_key="solicitudes.resumen_operativo.accion_seleccionar_delegada",
            help_key="solicitudes.resumen_operativo.ayuda_seleccionar_delegada",
        )
    if data.hay_conflictos_pendientes:
        return SolicitudesStatusOutput(
            label_key="solicitudes.resumen_operativo.estado_con_conflictos",
            label_params=label_params,
            action_key="solicitudes.resumen_operativo.accion_corregir_conflictos",
            help_key="solicitudes.resumen_operativo.ayuda_conflictos",
        )
    if data.pendientes_visibles <= 0:
        return SolicitudesStatusOutput(
            label_key="solicitudes.resumen_operativo.estado_sin_pendientes",
            label_params=label_params,
            action_key="solicitudes.resumen_operativo.accion_anadir_pendiente",
            help_key="solicitudes.resumen_operativo.ayuda_anadir_pendiente",
        )
    if data.puede_confirmar_pdf and data.pendientes_seleccionadas > 0:
        return SolicitudesStatusOutput(
            label_key="solicitudes.resumen_operativo.estado_lista_para_confirmar",
            label_params=label_params,
            action_key="solicitudes.resumen_operativo.accion_confirmar_generar_pdf",
            help_key=None,
        )
    if data.pendientes_seleccionadas <= 0:
        return SolicitudesStatusOutput(
            label_key="solicitudes.resumen_operativo.estado_pendientes_sin_seleccion",
            label_params=label_params,
            action_key="solicitudes.resumen_operativo.accion_seleccionar_pendiente",
            help_key="solicitudes.resumen_operativo.ayuda_seleccionar_pendiente",
        )
    return SolicitudesStatusOutput(
        label_key="solicitudes.resumen_operativo.estado_preparando_confirmacion",
        label_params=label_params,
        action_key="solicitudes.resumen_operativo.accion_revisar_antes_confirmar",
        help_key="solicitudes.resumen_operativo.ayuda_revisar_antes_confirmar",
    )
