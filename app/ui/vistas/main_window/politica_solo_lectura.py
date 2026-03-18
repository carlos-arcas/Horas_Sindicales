from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.application.modo_solo_lectura import EstadoModoSoloLectura
from app.ui.copy_catalog import copy_text

TipoControlMutante = Literal["widget", "action"]


@dataclass(frozen=True, slots=True)
class DescriptorAccionMutante:
    nombre_control: str
    object_name: str
    tipo_control: TipoControlMutante
    pantalla: str
    accion: str


ACCIONES_MUTANTES_AUDITADAS_UI: tuple[DescriptorAccionMutante, ...] = (
    DescriptorAccionMutante(
        "agregar_button",
        "agregar_button",
        "widget",
        "solicitudes",
        "agregar_pendiente",
    ),
    DescriptorAccionMutante(
        "insertar_sin_pdf_button",
        "insertar_sin_pdf_button",
        "widget",
        "solicitudes",
        "confirmar_sin_pdf",
    ),
    DescriptorAccionMutante(
        "confirmar_button",
        "confirmar_button",
        "widget",
        "solicitudes",
        "confirmar_con_pdf",
    ),
    DescriptorAccionMutante(
        "eliminar_pendiente_button",
        "eliminar_pendiente_button",
        "widget",
        "solicitudes",
        "eliminar_solicitud_pendiente",
    ),
    DescriptorAccionMutante(
        "eliminar_huerfana_button",
        "eliminar_huerfana_button",
        "widget",
        "solicitudes",
        "eliminar_solicitud_huerfana",
    ),
    DescriptorAccionMutante(
        "add_persona_button",
        "add_persona_button",
        "widget",
        "configuracion",
        "crear_persona",
    ),
    DescriptorAccionMutante(
        "edit_persona_button",
        "edit_persona_button",
        "widget",
        "configuracion",
        "editar_persona",
    ),
    DescriptorAccionMutante(
        "delete_persona_button",
        "delete_persona_button",
        "widget",
        "configuracion",
        "desactivar_persona",
    ),
    DescriptorAccionMutante(
        "edit_grupo_button",
        "edit_grupo_button",
        "widget",
        "configuracion",
        "actualizar_configuracion_grupo",
    ),
    DescriptorAccionMutante(
        "editar_pdf_button",
        "editar_pdf_button",
        "widget",
        "configuracion",
        "actualizar_configuracion_pdf",
    ),
    DescriptorAccionMutante(
        "opciones_button",
        "opciones_button",
        "widget",
        "sincronizacion",
        "actualizar_configuracion_sync",
    ),
    DescriptorAccionMutante(
        "config_sync_button",
        "config_sync_button",
        "widget",
        "sincronizacion",
        "sincronizar_desde_configuracion",
    ),
    DescriptorAccionMutante(
        "sync_button",
        "sync_button",
        "widget",
        "sincronizacion",
        "sincronizar_ahora",
    ),
    DescriptorAccionMutante(
        "confirm_sync_button",
        "confirm_sync_button",
        "widget",
        "sincronizacion",
        "confirmar_sincronizacion",
    ),
    DescriptorAccionMutante(
        "retry_failed_button",
        "retry_failed_button",
        "widget",
        "sincronizacion",
        "reintentar_sincronizacion_fallida",
    ),
    DescriptorAccionMutante(
        "accion_menu_cargar_demo",
        "accion_menu_cargar_demo",
        "action",
        "menu_ayuda",
        "cargar_datos_demo",
    ),
    DescriptorAccionMutante(
        "eliminar_button",
        "eliminar_button",
        "widget",
        "historico",
        "eliminar_solicitud_historica",
    ),
    DescriptorAccionMutante(
        "generar_pdf_button",
        "generar_pdf_button",
        "widget",
        "historico",
        "exportar_historico_pdf",
    ),
)

NOMBRES_CONTROLES_MUTANTES_UI: tuple[str, ...] = tuple(
    descriptor.nombre_control for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
)

TOOLTIP_MUTACION_BLOQUEADA = "ui.read_only.tooltip_mutacion_bloqueada"
ERROR_ESTADO_NO_INYECTADO = "ui.read_only.error_estado_no_inyectado"


def aplicar_politica_solo_lectura(window: Any) -> None:
    estado = getattr(window, "_estado_modo_solo_lectura", None)
    if not isinstance(estado, EstadoModoSoloLectura):
        raise TypeError(copy_text(ERROR_ESTADO_NO_INYECTADO))
    if not estado.esta_activo():
        return
    tooltip = copy_text(TOOLTIP_MUTACION_BLOQUEADA)
    for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI:
        control = resolver_control_mutante(window, descriptor)
        if control is None:
            continue
        if hasattr(control, "setEnabled"):
            control.setEnabled(False)
        if hasattr(control, "setToolTip"):
            control.setToolTip(tooltip)


def resolver_control_mutante(
    window: Any, descriptor: DescriptorAccionMutante
) -> Any | None:
    control = getattr(window, descriptor.nombre_control, None)
    if _coincide_object_name(control, descriptor.object_name):
        return control
    return _buscar_control_por_object_name(window, descriptor.object_name)


def _coincide_object_name(control: Any | None, object_name: str) -> bool:
    if control is None:
        return False
    obtener_object_name = getattr(control, "objectName", None)
    if callable(obtener_object_name):
        return obtener_object_name() == object_name
    return False


def _buscar_control_por_object_name(window: Any, object_name: str) -> Any | None:
    buscar_varios = getattr(window, "findChildren", None)
    if not callable(buscar_varios):
        return None
    try:
        controles = buscar_varios(object, object_name)
    except TypeError:
        controles = buscar_varios(object)
    for control in controles:
        if _coincide_object_name(control, object_name):
            return control
    return None


def exportar_inventario_acciones_mutantes() -> dict[str, dict[str, str]]:
    return {
        descriptor.nombre_control: {
            "object_name": descriptor.object_name,
            "tipo_control": descriptor.tipo_control,
            "pantalla": descriptor.pantalla,
            "accion": descriptor.accion,
        }
        for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
    }


__all__ = [
    "ACCIONES_MUTANTES_AUDITADAS_UI",
    "DescriptorAccionMutante",
    "ERROR_ESTADO_NO_INYECTADO",
    "NOMBRES_CONTROLES_MUTANTES_UI",
    "TOOLTIP_MUTACION_BLOQUEADA",
    "TipoControlMutante",
    "aplicar_politica_solo_lectura",
    "exportar_inventario_acciones_mutantes",
    "resolver_control_mutante",
]
