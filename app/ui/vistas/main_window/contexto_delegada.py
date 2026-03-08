from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntradaEstadoContextoDelegada:
    delegada_actual_id: int | None
    persona_combo_current_data: object
    config_combo_current_data: object
    formulario_sucio: bool


@dataclass(frozen=True)
class SalidaEstadoContextoDelegada:
    delegada_destino_id: int | None
    contexto_combo_valido: bool
    cambio_delegada: bool
    requiere_confirmacion: bool
    puede_aplicar_cambio_directo: bool
    configuracion_combo_valida: bool
    habilitar_acciones_configuracion: bool


def _normalizar_delegada_id(valor: object) -> int | None:
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int) and valor > 0:
        return valor
    return None


def resolver_estado_contexto_delegada(
    entrada: EntradaEstadoContextoDelegada,
) -> SalidaEstadoContextoDelegada:
    delegada_destino_id = _normalizar_delegada_id(entrada.persona_combo_current_data)
    configuracion_delegada_id = _normalizar_delegada_id(entrada.config_combo_current_data)
    cambio_delegada = entrada.delegada_actual_id != delegada_destino_id
    contexto_combo_valido = delegada_destino_id is not None
    requiere_confirmacion = (
        cambio_delegada and contexto_combo_valido and entrada.formulario_sucio
    )
    puede_aplicar_cambio_directo = cambio_delegada and not requiere_confirmacion
    configuracion_combo_valida = configuracion_delegada_id is not None
    return SalidaEstadoContextoDelegada(
        delegada_destino_id=delegada_destino_id,
        contexto_combo_valido=contexto_combo_valido,
        cambio_delegada=cambio_delegada,
        requiere_confirmacion=requiere_confirmacion,
        puede_aplicar_cambio_directo=puede_aplicar_cambio_directo,
        configuracion_combo_valida=configuracion_combo_valida,
        habilitar_acciones_configuracion=configuracion_combo_valida,
    )

