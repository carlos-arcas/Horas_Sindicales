from __future__ import annotations

from pathlib import Path

from app.ui.vistas.main_window.politica_solo_lectura import (
    ACCIONES_MUTANTES_AUDITADAS_UI,
    DescriptorAccionMutante,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CONTRATO_CONTROLES_MUTANTES_UI: tuple[dict[str, str], ...] = (
    {
        "object_name": "agregar_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_solicitud.py",
    },
    {
        "object_name": "insertar_sin_pdf_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    },
    {
        "object_name": "confirmar_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    },
    {
        "object_name": "eliminar_pendiente_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    },
    {
        "object_name": "eliminar_huerfana_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    },
    {
        "object_name": "add_persona_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "edit_persona_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "delete_persona_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "edit_grupo_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "editar_pdf_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "opciones_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "config_sync_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "sync_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "confirm_sync_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "retry_failed_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "object_name": "accion_menu_cargar_demo",
        "tipo_control": "action",
        "ruta_origen": "app/entrypoints/ui_main.py",
    },
    {
        "object_name": "eliminar_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/builders_tablas.py",
    },
    {
        "object_name": "generar_pdf_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/builders_tablas.py",
    },
)

CAMPOS_RUNTIME_DESCRIPTORES = (
    "object_name",
    "tipo_control",
    "pantalla",
    "accion",
)
FRAGMENTOS_PROHIBIDOS_EN_RUNTIME = (
    "import ast",
    "from pathlib import Path",
    "nombre_control: str",
    "ruta_origen: str",
    "RUTAS_ORIGEN_CONTROLES_MUTANTES_UI",
    "validar_inventario_acciones_mutantes",
    "validar_contrato_inventario_con_fuentes",
    "_extraer_asignaciones_de_atributos",
    "_extraer_nombres_target",
)


def exportar_contrato_inventario_mutante() -> dict[str, dict[str, str]]:
    return {
        item["object_name"]: {
            "tipo_control": item["tipo_control"],
            "ruta_origen": item["ruta_origen"],
        }
        for item in CONTRATO_CONTROLES_MUTANTES_UI
    }



def validar_inventario_runtime_mutante(
    descriptores: tuple[DescriptorAccionMutante, ...] = ACCIONES_MUTANTES_AUDITADAS_UI,
) -> list[str]:
    incidencias: list[str] = []
    object_names_vistos: set[str] = set()
    acciones_vistas: set[tuple[str, str]] = set()
    for descriptor in descriptores:
        if not descriptor.object_name.strip():
            incidencias.append("DESCRIPTOR_OBJECT_NAME_VACIO")
        if descriptor.tipo_control not in ("widget", "action"):
            incidencias.append(
                f"DESCRIPTOR_TIPO_CONTROL_INVALIDO:{descriptor.object_name}"
            )
        if not descriptor.pantalla.strip():
            incidencias.append(f"DESCRIPTOR_PANTALLA_VACIA:{descriptor.object_name}")
        if not descriptor.accion.strip():
            incidencias.append(f"DESCRIPTOR_ACCION_VACIA:{descriptor.object_name}")
        if descriptor.object_name in object_names_vistos:
            incidencias.append(
                f"DESCRIPTOR_OBJECT_NAME_DUPLICADO:{descriptor.object_name}"
            )
        object_names_vistos.add(descriptor.object_name)
        clave_accion = (descriptor.pantalla, descriptor.accion)
        if clave_accion in acciones_vistas:
            incidencias.append(
                f"DESCRIPTOR_ACCION_DUPLICADA:{descriptor.pantalla}:{descriptor.accion}"
            )
        acciones_vistas.add(clave_accion)
    return incidencias



def validar_contrato_inventario_con_fuentes(
    *,
    root_path: Path = PROJECT_ROOT,
    descriptores: tuple[DescriptorAccionMutante, ...] = ACCIONES_MUTANTES_AUDITADAS_UI,
    contrato: tuple[dict[str, str], ...] = CONTRATO_CONTROLES_MUTANTES_UI,
) -> list[str]:
    incidencias = list(validar_inventario_runtime_mutante(descriptores))
    inventario_runtime = {
        descriptor.object_name: descriptor for descriptor in descriptores
    }
    contrato_por_object_name = {item["object_name"]: item for item in contrato}

    faltantes_runtime = sorted(
        contrato_por_object_name.keys() - inventario_runtime.keys()
    )
    sobrantes_runtime = sorted(
        inventario_runtime.keys() - contrato_por_object_name.keys()
    )
    incidencias.extend(
        f"CONTRATO_FALTANTE_EN_RUNTIME:{object_name}"
        for object_name in faltantes_runtime
    )
    incidencias.extend(
        f"CONTRATO_SOBRANTE_EN_RUNTIME:{object_name}"
        for object_name in sobrantes_runtime
    )

    for object_name, descriptor in inventario_runtime.items():
        contrato_item = contrato_por_object_name.get(object_name)
        if not contrato_item:
            continue
        if descriptor.tipo_control != contrato_item["tipo_control"]:
            incidencias.append(
                f"CONTRATO_TIPO_DISTINTO:{object_name}:{descriptor.tipo_control}:{contrato_item['tipo_control']}"
            )
        ruta_origen = contrato_item["ruta_origen"]
        ruta_fuente = root_path / ruta_origen
        if not ruta_fuente.exists():
            incidencias.append(
                f"CONTRATO_RUTA_ORIGEN_NO_EXISTE:{object_name}:{ruta_origen}"
            )
            continue
        contenido = ruta_fuente.read_text(encoding="utf-8")
        literal_object_name = f'"{descriptor.object_name}"'
        if literal_object_name not in contenido:
            incidencias.append(
                f"CONTRATO_OBJECT_NAME_NO_VISIBLE_EN_FUENTE:{object_name}:{ruta_origen}:{descriptor.object_name}"
            )
        if descriptor.tipo_control == "action":
            if f"setObjectName({literal_object_name})" not in contenido:
                incidencias.append(
                    f"CONTRATO_ACTION_SIN_SET_OBJECT_NAME:{object_name}:{ruta_origen}"
                )
        elif f"object_name={literal_object_name}" not in contenido and (
            f"setObjectName({literal_object_name})" not in contenido
        ):
            incidencias.append(
                f"CONTRATO_WIDGET_SIN_IDENTIDAD_ESTABLE:{object_name}:{ruta_origen}"
            )
    return incidencias
