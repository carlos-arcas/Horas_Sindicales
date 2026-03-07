from app.ui.vistas.main_window.estado_acciones import (
    EntradaEstadoAccionesMainWindow,
    resolver_estado_acciones_main_window,
)


def _entrada_base(**overrides: object) -> EntradaEstadoAccionesMainWindow:
    base = dict(
        persona_seleccionada=True,
        formulario_valido=True,
        hay_errores_bloqueantes=False,
        hay_pendientes_visibles=False,
        hay_conflictos_pendientes=False,
        ver_todas_delegadas=False,
        sync_en_progreso=False,
        cantidad_seleccion_pendientes=0,
        cantidad_seleccion_historico=0,
        cantidad_ids_historico_seleccionados=0,
        cantidad_pendientes_otras_delegadas=0,
    )
    base.update(overrides)
    return EntradaEstadoAccionesMainWindow(**base)


def test_estado_acciones_sin_persona_deshabilita_acciones_dependientes_de_contexto() -> None:
    estado = resolver_estado_acciones_main_window(_entrada_base(persona_seleccionada=False, hay_pendientes_visibles=True))

    assert estado.agregar_habilitado is False
    assert estado.insertar_sin_pdf_habilitado is False
    assert estado.confirmar_habilitado is False
    assert estado.editar_persona_habilitado is False
    assert estado.generar_pdf_habilitado is False


def test_estado_acciones_con_contexto_valido_sin_pendientes_ni_seleccion_mantiene_coherencia() -> None:
    estado = resolver_estado_acciones_main_window(_entrada_base())

    assert estado.agregar_habilitado is True
    assert estado.insertar_sin_pdf_habilitado is False
    assert estado.confirmar_habilitado is False
    assert estado.eliminar_historico_habilitado is False
    assert estado.eliminar_pendiente_habilitado is False


def test_estado_acciones_con_pendientes_y_seleccion_habilita_confirmar_y_acciones_historico() -> None:
    estado = resolver_estado_acciones_main_window(
        _entrada_base(
            hay_pendientes_visibles=True,
            cantidad_seleccion_pendientes=2,
            cantidad_seleccion_historico=1,
        )
    )

    assert estado.insertar_sin_pdf_habilitado is True
    assert estado.confirmar_habilitado is True
    assert estado.eliminar_historico_habilitado is True
    assert estado.generar_pdf_habilitado is True
    assert estado.total_historico_seleccionado == 1


def test_estado_acciones_con_pendientes_de_otras_delegadas_no_contradice_confirmacion_visible() -> None:
    estado = resolver_estado_acciones_main_window(
        _entrada_base(
            hay_pendientes_visibles=False,
            cantidad_pendientes_otras_delegadas=3,
            cantidad_seleccion_pendientes=1,
        )
    )

    assert estado.hay_pendientes_otras_delegadas is True
    assert estado.puede_confirmar is False
    assert estado.confirmar_habilitado is False
