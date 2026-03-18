from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.application.modo_solo_lectura import EstadoModoSoloLectura
from app.ui.copy_catalog import copy_text

TipoControlMutante = Literal["widget", "action"]


@dataclass(frozen=True, slots=True)
class DescriptorAccionMutante:
    nombre_control: str
    tipo_control: TipoControlMutante
    pantalla: str
    accion: str
    ruta_origen: str


ACCIONES_MUTANTES_AUDITADAS_UI: tuple[DescriptorAccionMutante, ...] = (
    DescriptorAccionMutante(
        "agregar_button",
        "widget",
        "solicitudes",
        "agregar_pendiente",
        "app/ui/vistas/builders/formulario_solicitud/builders_solicitud.py",
    ),
    DescriptorAccionMutante(
        "insertar_sin_pdf_button",
        "widget",
        "solicitudes",
        "confirmar_sin_pdf",
        "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    ),
    DescriptorAccionMutante(
        "confirmar_button",
        "widget",
        "solicitudes",
        "confirmar_con_pdf",
        "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    ),
    DescriptorAccionMutante(
        "eliminar_pendiente_button",
        "widget",
        "solicitudes",
        "eliminar_solicitud_pendiente",
        "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    ),
    DescriptorAccionMutante(
        "eliminar_huerfana_button",
        "widget",
        "solicitudes",
        "eliminar_solicitud_huerfana",
        "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    ),
    DescriptorAccionMutante(
        "add_persona_button",
        "widget",
        "configuracion",
        "crear_persona",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "edit_persona_button",
        "widget",
        "configuracion",
        "editar_persona",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "delete_persona_button",
        "widget",
        "configuracion",
        "desactivar_persona",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "edit_grupo_button",
        "widget",
        "configuracion",
        "actualizar_configuracion_grupo",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "editar_pdf_button",
        "widget",
        "configuracion",
        "actualizar_configuracion_pdf",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "opciones_button",
        "widget",
        "sincronizacion",
        "actualizar_configuracion_sync",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "config_sync_button",
        "widget",
        "sincronizacion",
        "sincronizar_desde_configuracion",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "sync_button",
        "widget",
        "sincronizacion",
        "sincronizar_ahora",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "confirm_sync_button",
        "widget",
        "sincronizacion",
        "confirmar_sincronizacion",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "retry_failed_button",
        "widget",
        "sincronizacion",
        "reintentar_sincronizacion_fallida",
        "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    ),
    DescriptorAccionMutante(
        "accion_menu_cargar_demo",
        "action",
        "menu_ayuda",
        "cargar_datos_demo",
        "app/entrypoints/ui_main.py",
    ),
    DescriptorAccionMutante(
        "eliminar_button",
        "widget",
        "historico",
        "eliminar_solicitud_historica",
        "app/ui/vistas/builders/builders_tablas.py",
    ),
    DescriptorAccionMutante(
        "generar_pdf_button",
        "widget",
        "historico",
        "exportar_historico_pdf",
        "app/ui/vistas/builders/builders_tablas.py",
    ),
)

NOMBRES_CONTROLES_MUTANTES_UI: tuple[str, ...] = tuple(
    descriptor.nombre_control for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
)

RUTAS_ORIGEN_CONTROLES_MUTANTES_UI: tuple[str, ...] = tuple(
    dict.fromkeys(descriptor.ruta_origen for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI)
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


def resolver_control_mutante(window: Any, descriptor: DescriptorAccionMutante) -> Any | None:
    return getattr(window, descriptor.nombre_control, None)


def exportar_inventario_acciones_mutantes() -> dict[str, dict[str, str]]:
    return {
        descriptor.nombre_control: {
            "tipo_control": descriptor.tipo_control,
            "pantalla": descriptor.pantalla,
            "accion": descriptor.accion,
            "ruta_origen": descriptor.ruta_origen,
        }
        for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
    }


def validar_inventario_acciones_mutantes(
    descriptores: tuple[DescriptorAccionMutante, ...] = ACCIONES_MUTANTES_AUDITADAS_UI,
) -> list[str]:
    incidencias: list[str] = []
    nombres_vistos: set[str] = set()
    acciones_vistas: set[tuple[str, str]] = set()
    for descriptor in descriptores:
        if not descriptor.nombre_control.strip():
            incidencias.append("DESCRIPTOR_NOMBRE_CONTROL_VACIO")
        if descriptor.tipo_control not in ("widget", "action"):
            incidencias.append(
                f"DESCRIPTOR_TIPO_CONTROL_INVALIDO:{descriptor.nombre_control}"
            )
        if not descriptor.pantalla.strip():
            incidencias.append(
                f"DESCRIPTOR_PANTALLA_VACIA:{descriptor.nombre_control}"
            )
        if not descriptor.accion.strip():
            incidencias.append(f"DESCRIPTOR_ACCION_VACIA:{descriptor.nombre_control}")
        if not descriptor.ruta_origen.strip():
            incidencias.append(
                f"DESCRIPTOR_RUTA_ORIGEN_VACIA:{descriptor.nombre_control}"
            )
        if descriptor.nombre_control in nombres_vistos:
            incidencias.append(f"DESCRIPTOR_DUPLICADO:{descriptor.nombre_control}")
        nombres_vistos.add(descriptor.nombre_control)
        clave_accion = (descriptor.pantalla, descriptor.accion)
        if clave_accion in acciones_vistas:
            incidencias.append(
                f"DESCRIPTOR_ACCION_DUPLICADA:{descriptor.pantalla}:{descriptor.accion}"
            )
        acciones_vistas.add(clave_accion)
    return incidencias


def validar_contrato_inventario_con_fuentes(
    *,
    root_path: Path | None = None,
    descriptores: tuple[DescriptorAccionMutante, ...] = ACCIONES_MUTANTES_AUDITADAS_UI,
) -> list[str]:
    incidencias = list(validar_inventario_acciones_mutantes(descriptores))
    root = root_path or Path(__file__).resolve().parents[4]
    for descriptor in descriptores:
        ruta_fuente = root / descriptor.ruta_origen
        if not ruta_fuente.exists():
            incidencias.append(
                f"CONTRATO_RUTA_ORIGEN_NO_EXISTE:{descriptor.nombre_control}:{descriptor.ruta_origen}"
            )
            continue
        contenido = ruta_fuente.read_text(encoding="utf-8")
        nombres_asignados = _extraer_asignaciones_de_atributos(contenido)
        if descriptor.nombre_control not in nombres_asignados:
            incidencias.append(
                f"CONTRATO_CONTROL_NO_DECLARADO_EN_FUENTE:{descriptor.nombre_control}:{descriptor.ruta_origen}"
            )
    return incidencias


def _extraer_asignaciones_de_atributos(contenido: str) -> set[str]:
    modulo = ast.parse(contenido)
    nombres: set[str] = set()
    for nodo in ast.walk(modulo):
        if isinstance(nodo, ast.Assign):
            for target in nodo.targets:
                nombres.update(_extraer_nombres_target(target))
        elif isinstance(nodo, ast.AnnAssign):
            nombres.update(_extraer_nombres_target(nodo.target))
    return nombres


def _extraer_nombres_target(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
        if target.value.id in {"self", "window", "main_window"}:
            return {target.attr}
    if isinstance(target, ast.Tuple):
        nombres: set[str] = set()
        for elemento in target.elts:
            nombres.update(_extraer_nombres_target(elemento))
        return nombres
    return set()


__all__ = [
    "ACCIONES_MUTANTES_AUDITADAS_UI",
    "DescriptorAccionMutante",
    "ERROR_ESTADO_NO_INYECTADO",
    "NOMBRES_CONTROLES_MUTANTES_UI",
    "RUTAS_ORIGEN_CONTROLES_MUTANTES_UI",
    "TOOLTIP_MUTACION_BLOQUEADA",
    "TipoControlMutante",
    "aplicar_politica_solo_lectura",
    "exportar_inventario_acciones_mutantes",
    "resolver_control_mutante",
    "validar_contrato_inventario_con_fuentes",
    "validar_inventario_acciones_mutantes",
]
