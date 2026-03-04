from __future__ import annotations

import logging
from dataclasses import replace
from app.domain.base_cuadrantes import DEFAULT_BASE_DIAS, default_base_minutes
from app.domain.models import Persona
from app.domain.ports import CuadranteRepository, PersonaRepository

logger = logging.getLogger(__name__)

def _actualizar_dia(persona: Persona, dia: str, man_min: int, tar_min: int) -> Persona:
    if dia == "lun":
        return replace(persona, cuad_lun_man_min=man_min, cuad_lun_tar_min=tar_min)
    if dia == "mar":
        return replace(persona, cuad_mar_man_min=man_min, cuad_mar_tar_min=tar_min)
    if dia == "mie":
        return replace(persona, cuad_mie_man_min=man_min, cuad_mie_tar_min=tar_min)
    if dia == "jue":
        return replace(persona, cuad_jue_man_min=man_min, cuad_jue_tar_min=tar_min)
    if dia == "vie":
        return replace(persona, cuad_vie_man_min=man_min, cuad_vie_tar_min=tar_min)
    if dia == "sab":
        return replace(persona, cuad_sab_man_min=man_min, cuad_sab_tar_min=tar_min)
    return replace(persona, cuad_dom_man_min=man_min, cuad_dom_tar_min=tar_min)


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
        persona_actualizada = persona
        cambios = False
        for dia in DEFAULT_BASE_DIAS:
            current_man = getattr(persona_actualizada, f"cuad_{dia}_man_min")
            current_tar = getattr(persona_actualizada, f"cuad_{dia}_tar_min")
            if current_man != 0 or current_tar != 0:
                continue
            persona_actualizada = _actualizar_dia(persona_actualizada, dia, default_man_min, default_tar_min)
            cambios = True

        if cambios:
            persona = self._persona_repo.update(persona_actualizada)

        for dia in DEFAULT_BASE_DIAS:
            if self._cuadrante_repo.exists_for_delegada(persona_uuid, dia):
                continue
            man_min = getattr(persona, f"cuad_{dia}_man_min")
            tar_min = getattr(persona, f"cuad_{dia}_tar_min")
            self._cuadrante_repo.create(persona_uuid, dia, man_min, tar_min)
