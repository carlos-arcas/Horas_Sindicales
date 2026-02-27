from __future__ import annotations

import pytest

from app.application.dto import GrupoConfigDTO
from app.application.use_cases.grupos_config.use_case import (
    GrupoConfigUseCases,
    _dto_to_grupo_config,
    _grupo_config_to_dto,
)
from app.domain.models import GrupoConfig
from app.domain.services import BusinessRuleError


class _RepoGrupoFalso:
    def __init__(self, initial: GrupoConfig | None = None) -> None:
        self._current = initial

    def get(self) -> GrupoConfig | None:
        return self._current

    def upsert(self, config: GrupoConfig) -> GrupoConfig:
        self._current = config
        return config


def _dto_base() -> GrupoConfigDTO:
    return GrupoConfigDTO(
        id=7,
        nombre_grupo="Comité",
        bolsa_anual_grupo_min=1234,
        pdf_logo_path="logo.png",
        pdf_intro_text="Introducción",
        pdf_include_hours_in_horario=True,
    )


def test_get_grupo_config_devuelve_dto() -> None:
    repo = _RepoGrupoFalso(initial=_dto_to_grupo_config(_dto_base()))
    use_case = GrupoConfigUseCases(repo)

    resultado = use_case.get_grupo_config()

    assert resultado.nombre_grupo == "Comité"
    assert resultado.bolsa_anual_grupo_min == 1234


def test_get_grupo_config_lanza_error_si_no_existe() -> None:
    use_case = GrupoConfigUseCases(_RepoGrupoFalso(initial=None))

    with pytest.raises(BusinessRuleError, match="Configuración de grupo no encontrada"):
        use_case.get_grupo_config()


def test_update_grupo_config_persiste_en_repo() -> None:
    repo = _RepoGrupoFalso(initial=None)
    use_case = GrupoConfigUseCases(repo)

    actualizado = use_case.update_grupo_config(_dto_base())

    assert actualizado.id == 7
    assert repo.get() is not None
    assert repo.get().pdf_logo_path == "logo.png"


def test_mapeo_modelo_a_dto_y_dto_a_modelo_es_estable() -> None:
    dto_original = _dto_base()

    modelo = _dto_to_grupo_config(dto_original)
    dto_roundtrip = _grupo_config_to_dto(modelo)

    assert dto_roundtrip == dto_original

