from __future__ import annotations

import logging
from dataclasses import replace

from app.domain.base_cuadrantes import DEFAULT_BASE_DIAS, default_base_minutes
from app.domain.ports import CuadranteRepository, PersonaRepository

logger = logging.getLogger(__name__)


class BaseCuadrantesService:
    def __init__(self, persona_repo: PersonaRepository, cuadrante_repo: CuadranteRepository) -> None:
        self._persona_repo = persona_repo
        self._cuadrante_repo = cuadrante_repo

    def ensure_for_all_personas(self) -> None:
        for persona in self._persona_repo.list_all(include_inactive=True):
            if persona.id is None:
                continue
            self.ensure_for_persona(persona.id)

    def ensure_for_persona(self, persona_id: int) -> None:
        persona = self._persona_repo.get_by_id(persona_id)
        if persona is None:
            logger.warning("Persona %s no encontrada al asegurar cuadrantes base.", persona_id)
            return
        persona_uuid = self._persona_repo.get_or_create_uuid(persona_id)
        if not persona_uuid:
            logger.warning("Persona %s sin uuid; no se crean cuadrantes base.", persona_id)
            return

        default_man_min, default_tar_min = default_base_minutes()
        updates: dict[str, int] = {}
        for dia in DEFAULT_BASE_DIAS:
            man_field = f"cuad_{dia}_man_min"
            tar_field = f"cuad_{dia}_tar_min"
            current_man = getattr(persona, man_field)
            current_tar = getattr(persona, tar_field)
            if current_man == 0 and current_tar == 0:
                updates[man_field] = default_man_min
                updates[tar_field] = default_tar_min

        if updates:
            persona = replace(persona, **updates)
            self._persona_repo.update(persona)

        for dia in DEFAULT_BASE_DIAS:
            if self._cuadrante_repo.exists_for_delegada(persona_uuid, dia):
                continue
            man_min = getattr(persona, f"cuad_{dia}_man_min")
            tar_min = getattr(persona, f"cuad_{dia}_tar_min")
            self._cuadrante_repo.create(persona_uuid, dia, man_min, tar_min)
