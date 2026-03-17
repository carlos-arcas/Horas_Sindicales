from __future__ import annotations

import pytest

from app.configuracion.settings import is_read_only_enabled
from app.domain.services import BusinessRuleError
from app.application.use_cases.politica_modo_solo_lectura import (
    MENSAJE_MODO_SOLO_LECTURA,
    verificar_modo_solo_lectura,
)


def test_settings_read_only_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("READ_ONLY", "1")
    assert is_read_only_enabled() is True


def test_politica_read_only_bloquea_con_mensaje_canonico(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("READ_ONLY", "1")

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        verificar_modo_solo_lectura()


def test_politica_read_only_no_bloquea_si_esta_desactivado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("READ_ONLY", "0")

    verificar_modo_solo_lectura()


def test_eliminar_solicitud_bloqueada_en_read_only(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    creada = solicitud_use_cases.crear(solicitud_dto)
    monkeypatch.setenv("READ_ONLY", "1")

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.eliminar_solicitud(int(creada.id or 0))


def test_eliminar_solicitud_read_only_sin_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    creada = solicitud_use_cases.crear(solicitud_dto)
    monkeypatch.setenv("READ_ONLY", "1")

    def _no_deberia_llamarse(_: int) -> None:
        raise AssertionError("No debe consultar repositorio en modo solo lectura")

    monkeypatch.setattr(solicitud_use_cases._repo, "get_by_id", _no_deberia_llamarse)

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.eliminar_solicitud(int(creada.id or 0))


def test_confirmar_sin_pdf_bloqueado_en_read_only(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    monkeypatch.setenv("READ_ONLY", "1")

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.confirmar_sin_pdf([solicitud_dto])


def test_confirmar_sin_pdf_read_only_sin_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    monkeypatch.setenv("READ_ONLY", "1")

    def _no_deberia_llamarse(*_args, **_kwargs) -> None:
        raise AssertionError("No debe marcar elementos en modo solo lectura")

    monkeypatch.setattr(solicitud_use_cases._repo, "mark_generated", _no_deberia_llamarse)

    with pytest.raises(BusinessRuleError, match=MENSAJE_MODO_SOLO_LECTURA):
        solicitud_use_cases.confirmar_sin_pdf([solicitud_dto])


def test_excepcion_y_mensaje_read_only_consistentes_en_mutaciones_principales(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    creada = solicitud_use_cases.crear(solicitud_dto)
    monkeypatch.setenv("READ_ONLY", "1")

    for operacion in (
        lambda: solicitud_use_cases.eliminar_solicitud(int(creada.id or 0)),
        lambda: solicitud_use_cases.confirmar_sin_pdf([solicitud_dto]),
        verificar_modo_solo_lectura,
    ):
        with pytest.raises(BusinessRuleError) as error:
            operacion()
        assert str(error.value) == MENSAJE_MODO_SOLO_LECTURA


def test_solicitud_use_cases_no_expone_confirmar_lote_con_pdf_legacy(
    solicitud_use_cases,
) -> None:
    assert not hasattr(solicitud_use_cases, "confirmar_lote_y_generar_pdf")
