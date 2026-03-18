from __future__ import annotations

from pathlib import Path

from app.ui.vistas.main_window.politica_solo_lectura import (
    ACCIONES_MUTANTES_AUDITADAS_UI,
    DescriptorAccionMutante,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CONTRATO_CONTROLES_MUTANTES_UI: tuple[dict[str, str], ...] = (
    {
        "nombre_control": "agregar_button",
        "object_name": "agregar_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_solicitud.py",
    },
    {
        "nombre_control": "insertar_sin_pdf_button",
        "object_name": "insertar_sin_pdf_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    },
    {
        "nombre_control": "confirmar_button",
        "object_name": "confirmar_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    },
    {
        "nombre_control": "eliminar_pendiente_button",
        "object_name": "eliminar_pendiente_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    },
    {
        "nombre_control": "eliminar_huerfana_button",
        "object_name": "eliminar_huerfana_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py",
    },
    {
        "nombre_control": "add_persona_button",
        "object_name": "add_persona_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "edit_persona_button",
        "object_name": "edit_persona_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "delete_persona_button",
        "object_name": "delete_persona_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "edit_grupo_button",
        "object_name": "edit_grupo_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "editar_pdf_button",
        "object_name": "editar_pdf_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "opciones_button",
        "object_name": "opciones_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "config_sync_button",
        "object_name": "config_sync_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "sync_button",
        "object_name": "sync_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "confirm_sync_button",
        "object_name": "confirm_sync_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "retry_failed_button",
        "object_name": "retry_failed_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/sync_panel/builders_secciones.py",
    },
    {
        "nombre_control": "accion_menu_cargar_demo",
        "object_name": "accion_menu_cargar_demo",
        "tipo_control": "action",
        "ruta_origen": "app/entrypoints/ui_main.py",
    },
    {
        "nombre_control": "eliminar_button",
        "object_name": "eliminar_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/builders_tablas.py",
    },
    {
        "nombre_control": "generar_pdf_button",
        "object_name": "generar_pdf_button",
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/builders_tablas.py",
    },
)

CAMPOS_RUNTIME_DESCRIPTORES = (
    "nombre_control",
    "object_name",
    "tipo_control",
    "pantalla",
    "accion",
)
FRAGMENTOS_PROHIBIDOS_EN_RUNTIME = (
    "import ast",
    "from pathlib import Path",
    "ruta_origen: str",
    "RUTAS_ORIGEN_CONTROLES_MUTANTES_UI",
    "validar_inventario_acciones_mutantes",
    "validar_contrato_inventario_con_fuentes",
    "_extraer_asignaciones_de_atributos",
    "_extraer_nombres_target",
)


def exportar_contrato_inventario_mutante() -> dict[str, dict[str, str]]:
    return {
        item["nombre_control"]: {
            "object_name": item["object_name"],
            "tipo_control": item["tipo_control"],
            "ruta_origen": item["ruta_origen"],
        }
        for item in CONTRATO_CONTROLES_MUTANTES_UI
    }


def validar_inventario_runtime_mutante(
    descriptores: tuple[DescriptorAccionMutante, ...] = ACCIONES_MUTANTES_AUDITADAS_UI,
) -> list[str]:
    incidencias: list[str] = []
    nombres_vistos: set[str] = set()
    object_names_vistos: set[str] = set()
    acciones_vistas: set[tuple[str, str]] = set()
    for descriptor in descriptores:
        if not descriptor.nombre_control.strip():
            incidencias.append("DESCRIPTOR_NOMBRE_CONTROL_VACIO")
        if not descriptor.object_name.strip():
            incidencias.append(
                f"DESCRIPTOR_OBJECT_NAME_VACIO:{descriptor.nombre_control}"
            )
        if descriptor.tipo_control not in ("widget", "action"):
            incidencias.append(
                f"DESCRIPTOR_TIPO_CONTROL_INVALIDO:{descriptor.nombre_control}"
            )
        if not descriptor.pantalla.strip():
            incidencias.append(f"DESCRIPTOR_PANTALLA_VACIA:{descriptor.nombre_control}")
        if not descriptor.accion.strip():
            incidencias.append(f"DESCRIPTOR_ACCION_VACIA:{descriptor.nombre_control}")
        if descriptor.nombre_control in nombres_vistos:
            incidencias.append(f"DESCRIPTOR_DUPLICADO:{descriptor.nombre_control}")
        if descriptor.object_name in object_names_vistos:
            incidencias.append(
                f"DESCRIPTOR_OBJECT_NAME_DUPLICADO:{descriptor.object_name}"
            )
        nombres_vistos.add(descriptor.nombre_control)
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
        descriptor.nombre_control: descriptor for descriptor in descriptores
    }
    contrato_por_nombre = {item["nombre_control"]: item for item in contrato}

    faltantes_runtime = sorted(contrato_por_nombre.keys() - inventario_runtime.keys())
    sobrantes_runtime = sorted(inventario_runtime.keys() - contrato_por_nombre.keys())
    incidencias.extend(
        f"CONTRATO_FALTANTE_EN_RUNTIME:{nombre}" for nombre in faltantes_runtime
    )
    incidencias.extend(
        f"CONTRATO_SOBRANTE_EN_RUNTIME:{nombre}" for nombre in sobrantes_runtime
    )

    for nombre_control, descriptor in inventario_runtime.items():
        contrato_item = contrato_por_nombre.get(nombre_control)
        if not contrato_item:
            continue
        if descriptor.object_name != contrato_item["object_name"]:
            incidencias.append(
                f"CONTRATO_OBJECT_NAME_DISTINTO:{nombre_control}:{descriptor.object_name}:{contrato_item['object_name']}"
            )
        if descriptor.tipo_control != contrato_item["tipo_control"]:
            incidencias.append(
                f"CONTRATO_TIPO_DISTINTO:{nombre_control}:{descriptor.tipo_control}:{contrato_item['tipo_control']}"
            )
        ruta_origen = contrato_item["ruta_origen"]
        ruta_fuente = root_path / ruta_origen
        if not ruta_fuente.exists():
            incidencias.append(
                f"CONTRATO_RUTA_ORIGEN_NO_EXISTE:{nombre_control}:{ruta_origen}"
            )
            continue
        contenido = ruta_fuente.read_text(encoding="utf-8")
        literal_object_name = f'"{descriptor.object_name}"'
        if literal_object_name not in contenido:
            incidencias.append(
                f"CONTRATO_OBJECT_NAME_NO_VISIBLE_EN_FUENTE:{nombre_control}:{ruta_origen}:{descriptor.object_name}"
            )
        if descriptor.tipo_control == "action":
            if f"setObjectName({literal_object_name})" not in contenido:
                incidencias.append(
                    f"CONTRATO_ACTION_SIN_SET_OBJECT_NAME:{nombre_control}:{ruta_origen}"
                )
        elif f"object_name={literal_object_name}" not in contenido and (
            f"setObjectName({literal_object_name})" not in contenido
        ):
            incidencias.append(
                f"CONTRATO_WIDGET_SIN_IDENTIDAD_ESTABLE:{nombre_control}:{ruta_origen}"
            )
    return incidencias
