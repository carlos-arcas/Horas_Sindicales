from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntradaEstadoAccionesMainWindow:
    persona_seleccionada: bool
    formulario_valido: bool
    hay_errores_bloqueantes: bool
    hay_pendientes_visibles: bool
    hay_conflictos_pendientes: bool
    ver_todas_delegadas: bool
    sync_en_progreso: bool
    cantidad_seleccion_pendientes: int
    cantidad_seleccion_historico: int
    cantidad_ids_historico_seleccionados: int
    cantidad_pendientes_otras_delegadas: int


@dataclass(frozen=True)
class EstadoAccionesMainWindow:
    agregar_habilitado: bool
    insertar_sin_pdf_habilitado: bool
    confirmar_habilitado: bool
    editar_persona_habilitado: bool
    eliminar_persona_habilitado: bool
    editar_grupo_habilitado: bool
    editar_pdf_habilitado: bool
    eliminar_historico_habilitado: bool
    generar_pdf_habilitado: bool
    eliminar_pendiente_habilitado: bool
    clear_habilitado: bool
    hay_pendientes: bool
    puede_confirmar: bool
    hay_pendientes_otras_delegadas: bool
    total_historico_seleccionado: int


def resolver_estado_acciones_main_window(
    entrada: EntradaEstadoAccionesMainWindow,
) -> EstadoAccionesMainWindow:
    seleccion_historico = max(
        entrada.cantidad_seleccion_historico,
        entrada.cantidad_ids_historico_seleccionados,
    )
    puede_operar = not entrada.sync_en_progreso
    puede_confirmar = (
        entrada.hay_pendientes_visibles
        and not entrada.hay_conflictos_pendientes
        and not entrada.hay_errores_bloqueantes
        and puede_operar
    )

    return EstadoAccionesMainWindow(
        agregar_habilitado=(
            entrada.persona_seleccionada
            and entrada.formulario_valido
            and not entrada.hay_errores_bloqueantes
            and puede_operar
        ),
        insertar_sin_pdf_habilitado=entrada.persona_seleccionada and puede_confirmar,
        confirmar_habilitado=entrada.persona_seleccionada and puede_confirmar,
        editar_persona_habilitado=entrada.persona_seleccionada,
        eliminar_persona_habilitado=entrada.persona_seleccionada,
        editar_grupo_habilitado=True,
        editar_pdf_habilitado=True,
        eliminar_historico_habilitado=(
            entrada.persona_seleccionada and seleccion_historico > 0 and puede_operar
        ),
        generar_pdf_habilitado=(
            entrada.persona_seleccionada and seleccion_historico > 0 and puede_operar
        ),
        eliminar_pendiente_habilitado=entrada.hay_pendientes_visibles,
        clear_habilitado=entrada.hay_pendientes_visibles and puede_operar,
        hay_pendientes=entrada.hay_pendientes_visibles,
        puede_confirmar=puede_confirmar,
        hay_pendientes_otras_delegadas=entrada.cantidad_pendientes_otras_delegadas > 0,
        total_historico_seleccionado=seleccion_historico,
    )
