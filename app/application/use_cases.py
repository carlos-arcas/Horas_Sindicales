from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from app.application.dto import PersonaDTO, SaldosDTO, SolicitudDTO
from app.domain.models import Persona, Solicitud
from app.domain.ports import PersonaRepository, SolicitudRepository
from app.domain.services import BusinessRuleError, validar_persona, validar_solicitud

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
        return self.listar_personas()

    def crear(self, dto: PersonaDTO) -> PersonaDTO:
        return self.crear_persona(dto)

    def listar_personas(self) -> Iterable[PersonaDTO]:
        logger.info("Listando personas")
        return [_persona_to_dto(p) for p in self._repo.list_all()]

    def crear_persona(self, dto: PersonaDTO) -> PersonaDTO:
        logger.info("Creando persona %s", dto.nombre)
        persona = _dto_to_persona(dto)
        validar_persona(persona)
        creada = self._repo.create(persona)
        return _persona_to_dto(creada)

    def editar_persona(self, dto: PersonaDTO) -> PersonaDTO:
        if dto.id is None:
            raise BusinessRuleError("La persona debe tener id para editar.")
        logger.info("Editando persona %s", dto.id)
        persona = _dto_to_persona(dto)
        validar_persona(persona)
        actualizada = self._repo.update(persona)
        return _persona_to_dto(actualizada)

    def obtener_persona(self, persona_id: int) -> PersonaDTO:
        persona = self._repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        return _persona_to_dto(persona)


class SolicitudUseCases:
    def __init__(
        self, repo: SolicitudRepository, persona_repo: PersonaRepository
    ) -> None:
        self._repo = repo
        self._persona_repo = persona_repo

    def listar_por_persona(self, persona_id: int) -> Iterable[SolicitudDTO]:
        return self.listar_solicitudes_por_persona_y_periodo(persona_id, None, None)

    def crear(self, dto: SolicitudDTO) -> SolicitudDTO:
        solicitud, _ = self.agregar_solicitud(dto)
        return solicitud

    def agregar_solicitud(self, dto: SolicitudDTO) -> tuple[SolicitudDTO, SaldosDTO]:
        logger.info("Creando solicitud para persona %s", dto.persona_id)
        persona = self._persona_repo.get_by_id(dto.persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")

        if self._repo.exists_duplicate(
            dto.persona_id, dto.fecha_pedida, dto.desde, dto.hasta, dto.completo
        ):
            raise BusinessRuleError("Duplicado")

        horas = _calcular_horas(dto, persona)
        solicitud = Solicitud(
            id=None,
            persona_id=dto.persona_id,
            fecha_solicitud=dto.fecha_solicitud,
            fecha_pedida=dto.fecha_pedida,
            desde=dto.desde,
            hasta=dto.hasta,
            completo=dto.completo,
            horas=horas,
            observaciones=dto.observaciones,
            pdf_path=dto.pdf_path,
            pdf_hash=dto.pdf_hash,
        )
        validar_solicitud(solicitud)
        creada = self._repo.create(solicitud)
        year, month = _parse_year_month(dto.fecha_pedida)
        saldos = self.calcular_saldos(dto.persona_id, year, month)
        return _solicitud_to_dto(creada), saldos

    def listar_solicitudes_por_persona_y_periodo(
        self, persona_id: int, year: int | None, month: int | None
    ) -> Iterable[SolicitudDTO]:
        logger.info(
            "Listando solicitudes para persona %s en periodo %s-%s",
            persona_id,
            year,
            month,
        )
        if year is None:
            solicitudes = self._repo.list_by_persona(persona_id)
        else:
            solicitudes = self._repo.list_by_persona_and_period(persona_id, year, month)
        return [_solicitud_to_dto(s) for s in solicitudes]

    def calcular_saldos(self, persona_id: int, year: int, month: int) -> SaldosDTO:
        persona = self._persona_repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        solicitudes_mes = self._repo.list_by_persona_and_period(persona_id, year, month)
        solicitudes_ano = self._repo.list_by_persona_and_period(persona_id, year, None)
        return _calcular_saldos(persona, solicitudes_mes, solicitudes_ano)

    def eliminar_solicitud(self, solicitud_id: int) -> SaldosDTO:
        solicitud = self._repo.get_by_id(solicitud_id)
        if solicitud is None:
            raise BusinessRuleError("Solicitud no encontrada.")
        self._repo.delete(solicitud_id)
        year, month = _parse_year_month(solicitud.fecha_pedida)
        return self.calcular_saldos(solicitud.persona_id, year, month)


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


def _parse_year_month(fecha: str) -> tuple[int, int]:
    parsed = datetime.strptime(fecha, "%Y-%m-%d")
    return parsed.year, parsed.month


def _parse_time_to_minutes(hora: str) -> int:
    parsed = datetime.strptime(hora, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _calcular_horas(dto: SolicitudDTO, persona: Persona) -> float:
    if dto.horas < 0:
        raise BusinessRuleError("Las horas deben ser mayores a cero.")
    if dto.completo:
        horas = dto.horas if dto.horas > 0 else persona.horas_jornada_defecto
        if horas <= 0:
            raise BusinessRuleError("Las horas deben ser mayores a cero.")
        return horas

    if not dto.desde or not dto.hasta:
        raise BusinessRuleError("Desde y hasta son obligatorios para solicitudes parciales.")
    desde_min = _parse_time_to_minutes(dto.desde)
    hasta_min = _parse_time_to_minutes(dto.hasta)
    if hasta_min <= desde_min:
        raise BusinessRuleError("La hora hasta debe ser mayor que desde.")
    horas_calculadas = (hasta_min - desde_min) / 60.0
    horas = dto.horas if dto.horas > 0 else horas_calculadas
    if horas <= 0:
        raise BusinessRuleError("Las horas deben ser mayores a cero.")
    return horas


def _calcular_saldos(
    persona: Persona,
    solicitudes_mes: Iterable[Solicitud],
    solicitudes_ano: Iterable[Solicitud],
) -> SaldosDTO:
    consumidas_mes = sum(s.horas for s in solicitudes_mes)
    consumidas_ano = sum(s.horas for s in solicitudes_ano)
    restantes_mes = max(0.0, persona.horas_mes - consumidas_mes)
    restantes_ano = max(0.0, persona.horas_ano - consumidas_ano)
    exceso_mes = max(0.0, consumidas_mes - persona.horas_mes)
    exceso_ano = max(0.0, consumidas_ano - persona.horas_ano)
    return SaldosDTO(
        consumidas_mes=consumidas_mes,
        restantes_mes=restantes_mes,
        consumidas_ano=consumidas_ano,
        restantes_ano=restantes_ano,
        exceso_mes=exceso_mes,
        exceso_ano=exceso_ano,
        excedido_mes=exceso_mes > 0,
        excedido_ano=exceso_ano > 0,
    )
