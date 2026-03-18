from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ui.copy_catalog import copy_text


@dataclass(frozen=True, slots=True)
class DescriptorAccionMutante:
    nombre_control: str
    pantalla: str
    accion: str


ACCIONES_MUTANTES_AUDITADAS_UI: tuple[DescriptorAccionMutante, ...] = (
    DescriptorAccionMutante("agregar_button", "solicitudes", "agregar_pendiente"),
    DescriptorAccionMutante(
        "insertar_sin_pdf_button", "solicitudes", "confirmar_sin_pdf"
    ),
    DescriptorAccionMutante("confirmar_button", "solicitudes", "confirmar_con_pdf"),
    DescriptorAccionMutante(
        "eliminar_pendiente_button", "solicitudes", "eliminar_solicitud_pendiente"
    ),
    DescriptorAccionMutante(
        "eliminar_huerfana_button", "solicitudes", "eliminar_solicitud_huerfana"
    ),
    DescriptorAccionMutante("add_persona_button", "configuracion", "crear_persona"),
    DescriptorAccionMutante(
        "edit_persona_button", "configuracion", "editar_persona"
    ),
    DescriptorAccionMutante(
        "delete_persona_button", "configuracion", "desactivar_persona"
    ),
    DescriptorAccionMutante(
        "edit_grupo_button", "configuracion", "actualizar_configuracion_grupo"
    ),
    DescriptorAccionMutante(
        "editar_pdf_button", "configuracion", "actualizar_configuracion_pdf"
    ),
    DescriptorAccionMutante(
        "opciones_button", "sincronizacion", "actualizar_configuracion_sync"
    ),
    DescriptorAccionMutante(
        "config_sync_button", "sincronizacion", "sincronizar_desde_configuracion"
    ),
    DescriptorAccionMutante("sync_button", "sincronizacion", "sincronizar_ahora"),
    DescriptorAccionMutante(
        "confirm_sync_button", "sincronizacion", "confirmar_sincronizacion"
    ),
    DescriptorAccionMutante(
        "retry_failed_button",
        "sincronizacion",
        "reintentar_sincronizacion_fallida",
    ),
    DescriptorAccionMutante(
        "accion_menu_cargar_demo", "menu_ayuda", "cargar_datos_demo"
    ),
    DescriptorAccionMutante(
        "eliminar_button", "historico", "eliminar_solicitud_historica"
    ),
    DescriptorAccionMutante(
        "generar_pdf_button", "historico", "exportar_historico_pdf"
    ),
)

NOMBRES_CONTROLES_MUTANTES_UI: tuple[str, ...] = tuple(
    descriptor.nombre_control for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
)

TOOLTIP_MUTACION_BLOQUEADA = "ui.read_only.tooltip_mutacion_bloqueada"
ERROR_PROVEEDOR_NO_INYECTADO = "ui.read_only.error_proveedor_no_inyectado"


def aplicar_politica_solo_lectura(window: Any) -> None:
    proveedor = getattr(window, "_proveedor_ui_solo_lectura", None)
    if not callable(proveedor):
        raise TypeError(copy_text(ERROR_PROVEEDOR_NO_INYECTADO))
    if not proveedor():
        return
    tooltip = copy_text(TOOLTIP_MUTACION_BLOQUEADA)
    for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI:
        control = getattr(window, descriptor.nombre_control, None)
        if control is None:
            continue
        if hasattr(control, "setEnabled"):
            control.setEnabled(False)
        if hasattr(control, "setToolTip"):
            control.setToolTip(tooltip)


def exportar_inventario_acciones_mutantes() -> dict[str, dict[str, str]]:
    return {
        descriptor.nombre_control: {
            "pantalla": descriptor.pantalla,
            "accion": descriptor.accion,
        }
        for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
    }
