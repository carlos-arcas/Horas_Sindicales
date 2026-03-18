from __future__ import annotations

from app.application.dto import GrupoConfigDTO
from app.application.use_cases.politica_modo_solo_lectura import PoliticaModoSoloLectura
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
    def __init__(
        self,
        repo: GrupoConfigRepository,
        *,
        politica_modo_solo_lectura: PoliticaModoSoloLectura,
    ) -> None:
        self._repo = repo
        self._politica_modo_solo_lectura = politica_modo_solo_lectura

    def get_grupo_config(self) -> GrupoConfigDTO:
        config = self._repo.get()
        if config is None:
            raise BusinessRuleError("Configuración de grupo no encontrada.")
        return _grupo_config_to_dto(config)

    def update_grupo_config(self, dto: GrupoConfigDTO) -> GrupoConfigDTO:
        self._politica_modo_solo_lectura.verificar()
        config = _dto_to_grupo_config(dto)
        updated = self._repo.upsert(config)
        return _grupo_config_to_dto(updated)
