from __future__ import annotations

import logging
from dataclasses import replace
from typing import Iterable

from app.application.base_cuadrantes_service import BaseCuadrantesService
from app.application.dto import PersonaDTO
from app.domain.models import Persona
from app.domain.ports import PersonaRepository
from app.domain.services import BusinessRuleError, validar_persona

logger = logging.getLogger(__name__)

def _persona_to_dto(persona: Persona) -> PersonaDTO:
    return PersonaDTO(
        id=persona.id,
        nombre=persona.nombre,
        genero=persona.genero,
        horas_mes=persona.horas_mes_min,
        horas_ano=persona.horas_ano_min,
        is_active=persona.is_active,
        cuad_lun_man_min=persona.cuad_lun_man_min,
        cuad_lun_tar_min=persona.cuad_lun_tar_min,
        cuad_mar_man_min=persona.cuad_mar_man_min,
        cuad_mar_tar_min=persona.cuad_mar_tar_min,
        cuad_mie_man_min=persona.cuad_mie_man_min,
        cuad_mie_tar_min=persona.cuad_mie_tar_min,
        cuad_jue_man_min=persona.cuad_jue_man_min,
        cuad_jue_tar_min=persona.cuad_jue_tar_min,
        cuad_vie_man_min=persona.cuad_vie_man_min,
        cuad_vie_tar_min=persona.cuad_vie_tar_min,
        cuad_sab_man_min=persona.cuad_sab_man_min,
        cuad_sab_tar_min=persona.cuad_sab_tar_min,
        cuad_dom_man_min=persona.cuad_dom_man_min,
        cuad_dom_tar_min=persona.cuad_dom_tar_min,
        cuadrante_uniforme=persona.cuadrante_uniforme,
        trabaja_finde=persona.trabaja_finde,
    )


def _dto_to_persona(dto: PersonaDTO) -> Persona:
    return Persona(
        id=dto.id,
        nombre=dto.nombre,
        genero=dto.genero,
        horas_mes_min=dto.horas_mes,
        horas_ano_min=dto.horas_ano,
        is_active=dto.is_active,
        cuad_lun_man_min=dto.cuad_lun_man_min,
        cuad_lun_tar_min=dto.cuad_lun_tar_min,
        cuad_mar_man_min=dto.cuad_mar_man_min,
        cuad_mar_tar_min=dto.cuad_mar_tar_min,
        cuad_mie_man_min=dto.cuad_mie_man_min,
        cuad_mie_tar_min=dto.cuad_mie_tar_min,
        cuad_jue_man_min=dto.cuad_jue_man_min,
        cuad_jue_tar_min=dto.cuad_jue_tar_min,
        cuad_vie_man_min=dto.cuad_vie_man_min,
        cuad_vie_tar_min=dto.cuad_vie_tar_min,
        cuad_sab_man_min=dto.cuad_sab_man_min,
        cuad_sab_tar_min=dto.cuad_sab_tar_min,
        cuad_dom_man_min=dto.cuad_dom_man_min,
        cuad_dom_tar_min=dto.cuad_dom_tar_min,
        cuadrante_uniforme=dto.cuadrante_uniforme,
        trabaja_finde=dto.trabaja_finde,
    )




def _normalizar_cuadrante_persona(dto: PersonaDTO) -> PersonaDTO:
    dto_normalizado = dto
    if dto_normalizado.cuadrante_uniforme:
        dto_normalizado = replace(
            dto_normalizado,
            cuad_mar_man_min=dto_normalizado.cuad_lun_man_min,
            cuad_mar_tar_min=dto_normalizado.cuad_lun_tar_min,
            cuad_mie_man_min=dto_normalizado.cuad_lun_man_min,
            cuad_mie_tar_min=dto_normalizado.cuad_lun_tar_min,
            cuad_jue_man_min=dto_normalizado.cuad_lun_man_min,
            cuad_jue_tar_min=dto_normalizado.cuad_lun_tar_min,
            cuad_vie_man_min=dto_normalizado.cuad_lun_man_min,
            cuad_vie_tar_min=dto_normalizado.cuad_lun_tar_min,
        )
    if not dto_normalizado.trabaja_finde:
        return replace(
            dto_normalizado,
            cuad_sab_man_min=0,
            cuad_sab_tar_min=0,
            cuad_dom_man_min=0,
            cuad_dom_tar_min=0,
        )
    return dto_normalizado

class PersonaUseCases:
    """Orquesta operaciones de ciclo de vida de delegadas.

    Centraliza normalización y validaciones para que la UI y los adaptadores no
    repliquen reglas que afectan saldos y conflictos posteriores.
    """
    def __init__(self, repo: PersonaRepository, base_cuadrantes_service: BaseCuadrantesService | None = None) -> None:
        self._repo = repo
        self._base_cuadrantes_service = base_cuadrantes_service

    def listar(self) -> Iterable[PersonaDTO]:
        return self.listar_personas()

    def crear(self, dto: PersonaDTO) -> PersonaDTO:
        return self.crear_persona(dto)

    def listar_personas(self) -> Iterable[PersonaDTO]:
        logger.info("Listando personas")
        return [_persona_to_dto(p) for p in self._repo.list_all()]

    def crear_persona(self, dto: PersonaDTO) -> PersonaDTO:
        """Crea una persona aplicando reglas de consistencia de cuadrante.

        La normalización previa evita persistir estados mixtos (uniforme vs.
        personalizado) que producirían cálculos diarios contradictorios.
        """
        logger.info("Creando persona %s", dto.nombre)
        dto_normalizado = _normalizar_cuadrante_persona(dto)
        persona = _dto_to_persona(dto_normalizado)
        validar_persona(persona)
        creada = self._repo.create(persona)
        if self._base_cuadrantes_service and creada.id is not None:
            self._base_cuadrantes_service.ensure_for_persona(creada.id)
            refrescada = self._repo.get_by_id(creada.id)
            if refrescada is not None:
                creada = refrescada
        return _persona_to_dto(creada)

    def editar_persona(self, dto: PersonaDTO) -> PersonaDTO:
        if dto.id is None:
            raise BusinessRuleError("La persona debe tener id para editar.")
        uuid_antes = self._repo.get_or_create_uuid(dto.id)
        logger.info("Editando persona id=%s uuid_antes=%s", dto.id, uuid_antes)
        dto_normalizado = _normalizar_cuadrante_persona(dto)
        if not dto_normalizado.trabaja_finde:
            actual = self._repo.get_by_id(dto_normalizado.id)
            if actual is None:
                raise BusinessRuleError("Persona no encontrada.")
            dto_normalizado = replace(
                dto_normalizado,
                cuad_sab_man_min=actual.cuad_sab_man_min,
                cuad_sab_tar_min=actual.cuad_sab_tar_min,
                cuad_dom_man_min=actual.cuad_dom_man_min,
                cuad_dom_tar_min=actual.cuad_dom_tar_min,
            )
        persona = _dto_to_persona(dto_normalizado)
        validar_persona(persona)
        actualizada = self._repo.update(persona)
        uuid_despues = self._repo.get_or_create_uuid(dto.id)
        logger.info("Edición persona id=%s uuid_despues=%s", dto.id, uuid_despues)
        if uuid_antes and uuid_despues and uuid_antes != uuid_despues:
            raise BusinessRuleError("El UUID de delegada no puede cambiar al editar.")
        return _persona_to_dto(actualizada)

    def desactivar_persona(self, persona_id: int) -> PersonaDTO:
        persona = self._repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        if not persona.is_active:
            return _persona_to_dto(persona)
        personas = list(self._repo.list_all(include_inactive=True))
        activas = [p for p in personas if p.is_active]
        if len(activas) <= 1:
            raise BusinessRuleError("Debe existir al menos un delegado activo.")
        persona_actualizada = replace(persona, is_active=False)
        actualizada = self._repo.update(persona_actualizada)
        return _persona_to_dto(actualizada)

    def obtener_persona(self, persona_id: int) -> PersonaDTO:
        persona = self._repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        return _persona_to_dto(persona)

class PersonaFactory:
    @staticmethod
    def desde_formulario(
        nombre: str,
        genero: str,
        horas_mes: int,
        horas_ano: int,
        is_active: bool,
        cuad_lun_man_min: int,
        cuad_lun_tar_min: int,
        cuad_mar_man_min: int,
        cuad_mar_tar_min: int,
        cuad_mie_man_min: int,
        cuad_mie_tar_min: int,
        cuad_jue_man_min: int,
        cuad_jue_tar_min: int,
        cuad_vie_man_min: int,
        cuad_vie_tar_min: int,
        cuad_sab_man_min: int,
        cuad_sab_tar_min: int,
        cuad_dom_man_min: int,
        cuad_dom_tar_min: int,
    ) -> PersonaDTO:
        return PersonaDTO(
            id=None,
            nombre=nombre,
            genero=genero,
            horas_mes=horas_mes,
            horas_ano=horas_ano,
            is_active=is_active,
            cuad_lun_man_min=cuad_lun_man_min,
            cuad_lun_tar_min=cuad_lun_tar_min,
            cuad_mar_man_min=cuad_mar_man_min,
            cuad_mar_tar_min=cuad_mar_tar_min,
            cuad_mie_man_min=cuad_mie_man_min,
            cuad_mie_tar_min=cuad_mie_tar_min,
            cuad_jue_man_min=cuad_jue_man_min,
            cuad_jue_tar_min=cuad_jue_tar_min,
            cuad_vie_man_min=cuad_vie_man_min,
            cuad_vie_tar_min=cuad_vie_tar_min,
            cuad_sab_man_min=cuad_sab_man_min,
            cuad_sab_tar_min=cuad_sab_tar_min,
            cuad_dom_man_min=cuad_dom_man_min,
            cuad_dom_tar_min=cuad_dom_tar_min,
            trabaja_finde=False,
        )
