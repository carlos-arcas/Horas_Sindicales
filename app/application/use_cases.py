from __future__ import annotations

import logging
from typing import Iterable

from app.application.dto import PersonaDTO, SolicitudDTO
from app.domain.models import Persona, Solicitud
from app.domain.ports import PersonaRepository, SolicitudRepository
from app.domain.services import validar_persona, validar_solicitud

logger = logging.getLogger(__name__)


def _persona_to_dto(persona: Persona) -> PersonaDTO:
    return PersonaDTO(**persona.__dict__)


def _dto_to_persona(dto: PersonaDTO) -> Persona:
    return Persona(**dto.__dict__)


def _solicitud_to_dto(solicitud: Solicitud) -> SolicitudDTO:
    return SolicitudDTO(**solicitud.__dict__)


def _dto_to_solicitud(dto: SolicitudDTO) -> Solicitud:
    return Solicitud(**dto.__dict__)


class PersonaUseCases:
    def __init__(self, repo: PersonaRepository) -> None:
        self._repo = repo

    def listar(self) -> Iterable[PersonaDTO]:
        logger.info("Listando personas")
        return [_persona_to_dto(p) for p in self._repo.list_all()]

    def crear(self, dto: PersonaDTO) -> PersonaDTO:
        logger.info("Creando persona %s", dto.nombre)
        persona = _dto_to_persona(dto)
        validar_persona(persona)
        creada = self._repo.create(persona)
        return _persona_to_dto(creada)


class SolicitudUseCases:
    def __init__(self, repo: SolicitudRepository) -> None:
        self._repo = repo

    def listar_por_persona(self, persona_id: int) -> Iterable[SolicitudDTO]:
        logger.info("Listando solicitudes para persona %s", persona_id)
        return [_solicitud_to_dto(s) for s in self._repo.list_by_persona(persona_id)]

    def crear(self, dto: SolicitudDTO) -> SolicitudDTO:
        logger.info("Creando solicitud para persona %s", dto.persona_id)
        solicitud = _dto_to_solicitud(dto)
        validar_solicitud(solicitud)
        creada = self._repo.create(solicitud)
        return _solicitud_to_dto(creada)


class PersonaFactory:
    @staticmethod
    def desde_formulario(
        nombre: str,
        genero: str,
        horas_mes: float,
        horas_ano: float,
        horas_jornada_defecto: float,
        cuad_lun: float,
        cuad_mar: float,
        cuad_mie: float,
        cuad_jue: float,
        cuad_vie: float,
        cuad_sab: float,
        cuad_dom: float,
    ) -> PersonaDTO:
        return PersonaDTO(
            id=None,
            nombre=nombre,
            genero=genero,
            horas_mes=horas_mes,
            horas_ano=horas_ano,
            horas_jornada_defecto=horas_jornada_defecto,
            cuad_lun=cuad_lun,
            cuad_mar=cuad_mar,
            cuad_mie=cuad_mie,
            cuad_jue=cuad_jue,
            cuad_vie=cuad_vie,
            cuad_sab=cuad_sab,
            cuad_dom=cuad_dom,
        )
