from app.ui.vistas.main_window.contexto_delegada import (
    EntradaEstadoContextoDelegada,
    resolver_estado_contexto_delegada,
)


def test_contexto_invalido_cuando_current_data_no_es_id_valido() -> None:
    estado = resolver_estado_contexto_delegada(
        EntradaEstadoContextoDelegada(
            delegada_actual_id=2,
            persona_combo_current_data="2",
            config_combo_current_data=None,
            formulario_sucio=False,
        )
    )

    assert estado.contexto_combo_valido is False
    assert estado.delegada_destino_id is None
    assert estado.cambio_delegada is True


def test_contexto_valido_formulario_limpio_permite_cambio_sin_confirmacion() -> None:
    estado = resolver_estado_contexto_delegada(
        EntradaEstadoContextoDelegada(
            delegada_actual_id=1,
            persona_combo_current_data=2,
            config_combo_current_data=2,
            formulario_sucio=False,
        )
    )

    assert estado.contexto_combo_valido is True
    assert estado.cambio_delegada is True
    assert estado.requiere_confirmacion is False
    assert estado.puede_aplicar_cambio_directo is True
    assert estado.habilitar_acciones_configuracion is True


def test_contexto_valido_formulario_sucio_exige_confirmacion() -> None:
    estado = resolver_estado_contexto_delegada(
        EntradaEstadoContextoDelegada(
            delegada_actual_id=1,
            persona_combo_current_data=2,
            config_combo_current_data=2,
            formulario_sucio=True,
        )
    )

    assert estado.requiere_confirmacion is True
    assert estado.puede_aplicar_cambio_directo is False
