from __future__ import annotations

from pathlib import Path

import pytest

from app.configuracion.settings import is_read_only_enabled
from app.domain.services import BusinessRuleError


def test_settings_read_only_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("READ_ONLY", "1")
    assert is_read_only_enabled() is True


def test_eliminar_solicitud_bloqueada_en_read_only(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    creada = solicitud_use_cases.crear(solicitud_dto)
    monkeypatch.setenv("READ_ONLY", "1")

    with pytest.raises(BusinessRuleError, match="Modo solo lectura activado"):
        solicitud_use_cases.eliminar_solicitud(int(creada.id or 0))


def test_confirmar_sin_pdf_bloqueado_en_read_only(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
) -> None:
    monkeypatch.setenv("READ_ONLY", "1")

    with pytest.raises(BusinessRuleError, match="Modo solo lectura activado"):
        solicitud_use_cases.confirmar_sin_pdf([solicitud_dto])


def test_confirmar_lote_con_pdf_bloqueado_en_read_only(
    monkeypatch: pytest.MonkeyPatch,
    solicitud_use_cases,
    solicitud_dto,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("READ_ONLY", "1")

    with pytest.raises(BusinessRuleError, match="Modo solo lectura activado"):
        solicitud_use_cases.confirmar_lote_y_generar_pdf(
            [solicitud_dto],
            tmp_path / "confirmadas.pdf",
        )
