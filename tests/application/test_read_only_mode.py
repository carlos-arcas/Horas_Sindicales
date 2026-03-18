from __future__ import annotations

import pytest

from app.application.dto import PersonaDTO
from app.application.use_cases import politica_modo_solo_lectura as modulo_politica
from app.application.use_cases.politica_modo_solo_lectura import (
    crear_estado_modo_solo_lectura,
    MENSAJE_MODO_SOLO_LECTURA,
    crear_politica_modo_solo_lectura,
)
from app.domain.services import BusinessRuleError


def _politica(activo: bool):
    return crear_politica_modo_solo_lectura(crear_estado_modo_solo_lectura(lambda: activo))


def test_politica_explicita_bloquea_con_provider_activo() -> None:
    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        _politica(True).verificar()


def test_politica_explicita_no_bloquea_con_provider_inactivo() -> None:
    _politica(False).verificar()


def test_politica_no_expone_setters_ni_resets_globales() -> None:
    assert not hasattr(modulo_politica, 'configurar_proveedor_modo_solo_lectura')
    assert not hasattr(modulo_politica, 'restablecer_proveedor_modo_solo_lectura')
    assert not hasattr(modulo_politica, 'verificar_modo_solo_lectura')
    assert not hasattr(modulo_politica, '_proveedor_modo_solo_lectura')


def test_eliminar_solicitud_bloqueada_en_read_only(
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    creada = solicitud_use_cases.crear(solicitud_dto)
    solicitud_use_cases._politica_modo_solo_lectura = _politica(True)

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.eliminar_solicitud(int(creada.id or 0))


def test_eliminar_solicitud_read_only_sin_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    creada = solicitud_use_cases.crear(solicitud_dto)
    solicitud_use_cases._politica_modo_solo_lectura = _politica(True)

    def _no_deberia_llamarse(_: int) -> None:
        raise AssertionError('No debe consultar repositorio en modo solo lectura')

    monkeypatch.setattr(solicitud_use_cases._repo, 'get_by_id', _no_deberia_llamarse)

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.eliminar_solicitud(int(creada.id or 0))


def test_confirmar_sin_pdf_bloqueado_en_read_only(
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    solicitud_use_cases._politica_modo_solo_lectura = _politica(True)

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.confirmar_sin_pdf([solicitud_dto])


def test_confirmar_sin_pdf_read_only_sin_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    solicitud_use_cases._politica_modo_solo_lectura = _politica(True)

    def _no_deberia_llamarse(*_args, **_kwargs) -> None:
        raise AssertionError('No debe marcar elementos en modo solo lectura')

    monkeypatch.setattr(
        solicitud_use_cases._repo, 'mark_generated', _no_deberia_llamarse
    )

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.confirmar_sin_pdf([solicitud_dto])


def test_excepcion_y_mensaje_read_only_consistentes_en_mutaciones_principales(
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    creada = solicitud_use_cases.crear(solicitud_dto)
    solicitud_use_cases._politica_modo_solo_lectura = _politica(True)

    for operacion in (
        lambda: solicitud_use_cases.eliminar_solicitud(int(creada.id or 0)),
        lambda: solicitud_use_cases.confirmar_sin_pdf([solicitud_dto]),
        solicitud_use_cases._politica_modo_solo_lectura.verificar,
    ):
        with pytest.raises(BusinessRuleError) as error:
            operacion()
        assert str(error.value) == MENSAJE_MODO_SOLO_LECTURA


def test_solicitud_use_cases_no_expone_confirmar_lote_con_pdf_legacy(
    solicitud_use_cases,
) -> None:
    assert not hasattr(solicitud_use_cases, 'confirmar_lote_y_generar_pdf')


def _persona_dto_base() -> PersonaDTO:
    return PersonaDTO(
        id=None,
        nombre='Delegada Read Only',
        genero='F',
        horas_mes=600,
        horas_ano=7200,
        is_active=True,
        cuad_lun_man_min=240,
        cuad_lun_tar_min=240,
        cuad_mar_man_min=240,
        cuad_mar_tar_min=240,
        cuad_mie_man_min=240,
        cuad_mie_tar_min=240,
        cuad_jue_man_min=240,
        cuad_jue_tar_min=240,
        cuad_vie_man_min=240,
        cuad_vie_tar_min=240,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
        cuadrante_uniforme=False,
        trabaja_finde=False,
    )


def test_agregar_solicitud_bloqueada_en_read_only_sin_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    solicitud_use_cases._politica_modo_solo_lectura = _politica(True)

    def _no_deberia_llamarse(_dto):
        raise AssertionError('No debe validar ni persistir en modo solo lectura')

    monkeypatch.setattr(
        solicitud_use_cases, '_validar_y_normalizar_dto', _no_deberia_llamarse
    )

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.agregar_solicitud(solicitud_dto)


def test_sustituir_por_completo_bloqueado_en_read_only_sin_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    solicitud_use_cases._politica_modo_solo_lectura = _politica(True)

    def _no_deberia_llamarse(*_args, **_kwargs):
        raise AssertionError('No debe eliminar solicitudes en modo solo lectura')

    monkeypatch.setattr(
        solicitud_use_cases._repo, 'delete_by_ids', _no_deberia_llamarse
    )

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.sustituir_por_completo(
            solicitud_dto.persona_id,
            solicitud_dto.fecha_pedida,
            solicitud_dto,
        )


def test_sustituir_por_parcial_bloqueado_en_read_only_sin_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    solicitud_use_cases._politica_modo_solo_lectura = _politica(True)

    def _no_deberia_llamarse(*_args, **_kwargs):
        raise AssertionError('No debe eliminar solicitudes en modo solo lectura')

    monkeypatch.setattr(
        solicitud_use_cases._repo, 'delete_by_ids', _no_deberia_llamarse
    )

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.sustituir_por_parcial(
            solicitud_dto.persona_id,
            solicitud_dto.fecha_pedida,
            solicitud_dto,
        )


def test_personas_mutantes_bloqueados_en_read_only_sin_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    persona_use_cases,
) -> None:
    persona_use_cases._politica_modo_solo_lectura = _politica(True)

    def _no_deberia_llamarse(*_args, **_kwargs):
        raise AssertionError(
            'No debe mutar repositorio de personas en modo solo lectura'
        )

    monkeypatch.setattr(persona_use_cases._repo, 'create', _no_deberia_llamarse)
    monkeypatch.setattr(persona_use_cases._repo, 'update', _no_deberia_llamarse)

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        persona_use_cases.crear_persona(_persona_dto_base())

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        persona_use_cases.editar_persona(_persona_dto_base())

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        persona_use_cases.desactivar_persona(1)
