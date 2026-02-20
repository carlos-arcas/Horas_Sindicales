from __future__ import annotations

from app.application.dto import GrupoConfigDTO
from app.domain.models import GrupoConfig
from app.domain.ports import GrupoConfigRepository
from app.domain.services import BusinessRuleError

def _grupo_config_to_dto(config: GrupoConfig) -> GrupoConfigDTO:
    return GrupoConfigDTO(
        id=config.id,
        nombre_grupo=config.nombre_grupo,
        bolsa_anual_grupo_min=config.bolsa_anual_grupo_min,
        pdf_logo_path=config.pdf_logo_path,
        pdf_intro_text=config.pdf_intro_text,
        pdf_include_hours_in_horario=config.pdf_include_hours_in_horario,
    )


def _dto_to_grupo_config(dto: GrupoConfigDTO) -> GrupoConfig:
    return GrupoConfig(
        id=dto.id,
        nombre_grupo=dto.nombre_grupo,
        bolsa_anual_grupo_min=dto.bolsa_anual_grupo_min,
        pdf_logo_path=dto.pdf_logo_path,
        pdf_intro_text=dto.pdf_intro_text,
        pdf_include_hours_in_horario=dto.pdf_include_hours_in_horario,
    )

class GrupoConfigUseCases:
    def __init__(self, repo: GrupoConfigRepository) -> None:
        self._repo = repo

    def get_grupo_config(self) -> GrupoConfigDTO:
        config = self._repo.get()
        if config is None:
            raise BusinessRuleError("Configuración de grupo no encontrada.")
        return _grupo_config_to_dto(config)

    def update_grupo_config(self, dto: GrupoConfigDTO) -> GrupoConfigDTO:
        config = _dto_to_grupo_config(dto)
        updated = self._repo.upsert(config)
        return _grupo_config_to_dto(updated)
