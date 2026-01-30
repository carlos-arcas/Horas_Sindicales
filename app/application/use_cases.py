from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from app.application.dto import (
    PeriodoFiltro,
    PersonaDTO,
    SaldosDTO,
    SolicitudDTO,
    TotalesGlobalesDTO,
)
from app.domain.models import Persona, Solicitud
from app.domain.ports import PersonaRepository, SolicitudRepository
from app.domain.services import BusinessRuleError, validar_persona, validar_solicitud
from app.domain.time_utils import minutes_to_hhmm, parse_hhmm

logger = logging.getLogger(__name__)


def _minutes_to_hours(minutos: int) -> float:
    return minutos / 60.0


def _hours_to_minutes(horas: float) -> int:
    return int(round(horas * 60))


def _total_cuadrante_min(persona: Persona, dia_prefix: str) -> int:
    man = getattr(persona, f"{dia_prefix}_man_min")
    tar = getattr(persona, f"{dia_prefix}_tar_min")
    return man + tar


def _persona_to_dto(persona: Persona) -> PersonaDTO:
    return PersonaDTO(
        id=persona.id,
        nombre=persona.nombre,
        genero=persona.genero,
        horas_mes=_minutes_to_hours(persona.horas_mes_min),
        horas_ano=_minutes_to_hours(persona.horas_ano_min),
        horas_jornada_defecto=_minutes_to_hours(persona.horas_jornada_defecto_min),
        cuad_lun=_minutes_to_hours(_total_cuadrante_min(persona, "cuad_lun")),
        cuad_mar=_minutes_to_hours(_total_cuadrante_min(persona, "cuad_mar")),
        cuad_mie=_minutes_to_hours(_total_cuadrante_min(persona, "cuad_mie")),
        cuad_jue=_minutes_to_hours(_total_cuadrante_min(persona, "cuad_jue")),
        cuad_vie=_minutes_to_hours(_total_cuadrante_min(persona, "cuad_vie")),
        cuad_sab=_minutes_to_hours(_total_cuadrante_min(persona, "cuad_sab")),
        cuad_dom=_minutes_to_hours(_total_cuadrante_min(persona, "cuad_dom")),
    )


def _dto_to_persona(dto: PersonaDTO) -> Persona:
    return Persona(
        id=dto.id,
        nombre=dto.nombre,
        genero=dto.genero,
        horas_mes_min=_hours_to_minutes(dto.horas_mes),
        horas_ano_min=_hours_to_minutes(dto.horas_ano),
        horas_jornada_defecto_min=_hours_to_minutes(dto.horas_jornada_defecto),
        cuad_lun_man_min=_hours_to_minutes(dto.cuad_lun),
        cuad_lun_tar_min=0,
        cuad_mar_man_min=_hours_to_minutes(dto.cuad_mar),
        cuad_mar_tar_min=0,
        cuad_mie_man_min=_hours_to_minutes(dto.cuad_mie),
        cuad_mie_tar_min=0,
        cuad_jue_man_min=_hours_to_minutes(dto.cuad_jue),
        cuad_jue_tar_min=0,
        cuad_vie_man_min=_hours_to_minutes(dto.cuad_vie),
        cuad_vie_tar_min=0,
        cuad_sab_man_min=_hours_to_minutes(dto.cuad_sab),
        cuad_sab_tar_min=0,
        cuad_dom_man_min=_hours_to_minutes(dto.cuad_dom),
        cuad_dom_tar_min=0,
    )


def _solicitud_to_dto(solicitud: Solicitud) -> SolicitudDTO:
    desde = minutes_to_hhmm(solicitud.desde_min) if solicitud.desde_min is not None else None
    hasta = minutes_to_hhmm(solicitud.hasta_min) if solicitud.hasta_min is not None else None
    return SolicitudDTO(
        id=solicitud.id,
        persona_id=solicitud.persona_id,
        fecha_solicitud=solicitud.fecha_solicitud,
        fecha_pedida=solicitud.fecha_pedida,
        desde=desde,
        hasta=hasta,
        completo=solicitud.completo,
        horas=_minutes_to_hours(solicitud.horas_solicitadas_min),
        observaciones=solicitud.observaciones,
        pdf_path=solicitud.pdf_path,
        pdf_hash=solicitud.pdf_hash,
    )


def _dto_to_solicitud(dto: SolicitudDTO) -> Solicitud:
    desde_min = parse_hhmm(dto.desde) if dto.desde else None
    hasta_min = parse_hhmm(dto.hasta) if dto.hasta else None
    return Solicitud(
        id=dto.id,
        persona_id=dto.persona_id,
        fecha_solicitud=dto.fecha_solicitud,
        fecha_pedida=dto.fecha_pedida,
        desde_min=desde_min,
        hasta_min=hasta_min,
        completo=dto.completo,
        horas_solicitadas_min=_hours_to_minutes(dto.horas),
        observaciones=dto.observaciones,
        pdf_path=dto.pdf_path,
        pdf_hash=dto.pdf_hash,
    )


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

        desde_min = parse_hhmm(dto.desde) if dto.desde else None
        hasta_min = parse_hhmm(dto.hasta) if dto.hasta else None
        if self._repo.exists_duplicate(
            dto.persona_id, dto.fecha_pedida, desde_min, hasta_min, dto.completo
        ):
            raise BusinessRuleError("Duplicado")

        minutos = _calcular_minutos(dto, persona)
        solicitud = Solicitud(
            id=None,
            persona_id=dto.persona_id,
            fecha_solicitud=dto.fecha_solicitud,
            fecha_pedida=dto.fecha_pedida,
            desde_min=desde_min,
            hasta_min=hasta_min,
            completo=dto.completo,
            horas_solicitadas_min=minutos,
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
            filtro = _build_periodo_filtro(year, month)
            solicitudes = self._repo.list_by_persona_and_period(
                persona_id, filtro.year, filtro.month
            )
        return [_solicitud_to_dto(s) for s in solicitudes]

    def calcular_saldos(self, persona_id: int, year: int, month: int) -> SaldosDTO:
        filtro = _build_periodo_filtro(year, month)
        return self.calcular_saldos_por_periodo(persona_id, filtro)

    def calcular_saldos_por_periodo(
        self, persona_id: int, filtro: PeriodoFiltro
    ) -> SaldosDTO:
        persona = self._persona_repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        solicitudes_mes = self._repo.list_by_persona_and_period(
            persona_id, filtro.year, filtro.month
        )
        solicitudes_ano = self._repo.list_by_persona_and_period(
            persona_id, filtro.year, None
        )
        return _calcular_saldos(persona, solicitudes_mes, solicitudes_ano)

    def eliminar_solicitud(self, solicitud_id: int) -> SaldosDTO:
        solicitud = self._repo.get_by_id(solicitud_id)
        if solicitud is None:
            raise BusinessRuleError("Solicitud no encontrada.")
        self._repo.delete(solicitud_id)
        year, month = _parse_year_month(solicitud.fecha_pedida)
        return self.calcular_saldos(solicitud.persona_id, year, month)

    def sugerir_completo_min(self, persona_id: int, fecha: str) -> int:
        persona = self._persona_repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        total_dia = _total_cuadrante_por_fecha(persona, fecha)
        return total_dia if total_dia > 0 else persona.horas_jornada_defecto_min

    def sumar_pendientes_min(self, persona_id: int, solicitudes: Iterable[SolicitudDTO]) -> int:
        persona = self._persona_repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        total = 0
        for solicitud in solicitudes:
            total += _calcular_minutos(solicitud, persona)
        return total

    def calcular_totales_globales(self, filtro: PeriodoFiltro) -> TotalesGlobalesDTO:
        personas = list(self._persona_repo.list_all())
        total_bolsa = 0
        total_consumidas = 0
        for persona in personas:
            total_bolsa += (
                persona.horas_mes_min if filtro.modo == "MENSUAL" else persona.horas_ano_min
            )
            solicitudes = self._repo.list_by_persona_and_period(
                persona.id or 0, filtro.year, filtro.month if filtro.modo == "MENSUAL" else None
            )
            total_consumidas += sum(s.horas_solicitadas_min for s in solicitudes)
        total_restantes = total_bolsa - total_consumidas
        return TotalesGlobalesDTO(
            total_consumidas_min=total_consumidas,
            total_bolsa_min=total_bolsa,
            total_restantes_min=total_restantes,
        )


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


def _build_periodo_filtro(year: int, month: int | None) -> PeriodoFiltro:
    return PeriodoFiltro.anual(year) if month is None else PeriodoFiltro.mensual(year, month)


def _total_cuadrante_por_fecha(persona: Persona, fecha: str) -> int:
    weekday = datetime.strptime(fecha, "%Y-%m-%d").weekday()
    dia_map = {
        0: "cuad_lun",
        1: "cuad_mar",
        2: "cuad_mie",
        3: "cuad_jue",
        4: "cuad_vie",
        5: "cuad_sab",
        6: "cuad_dom",
    }
    dia_prefix = dia_map[weekday]
    return _total_cuadrante_min(persona, dia_prefix)


def _calcular_minutos(dto: SolicitudDTO, persona: Persona | None) -> int:
    if dto.horas < 0:
        raise BusinessRuleError("Las horas deben ser mayores a cero.")
    if dto.completo:
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        total_dia = _total_cuadrante_por_fecha(persona, dto.fecha_pedida)
        minutos = _hours_to_minutes(dto.horas) if dto.horas > 0 else total_dia
        if minutos <= 0:
            minutos = persona.horas_jornada_defecto_min
        if minutos <= 0:
            raise BusinessRuleError("Las horas deben ser mayores a cero.")
        return minutos

    if not dto.desde or not dto.hasta:
        raise BusinessRuleError("Desde y hasta son obligatorios para solicitudes parciales.")
    desde_min = parse_hhmm(dto.desde)
    hasta_min = parse_hhmm(dto.hasta)
    if hasta_min <= desde_min:
        raise BusinessRuleError("La hora hasta debe ser mayor que desde.")
    minutos_calculados = hasta_min - desde_min
    minutos = _hours_to_minutes(dto.horas) if dto.horas > 0 else minutos_calculados
    if minutos <= 0:
        raise BusinessRuleError("Las horas deben ser mayores a cero.")
    return minutos


def _calcular_saldos(
    persona: Persona,
    solicitudes_mes: Iterable[Solicitud],
    solicitudes_ano: Iterable[Solicitud],
) -> SaldosDTO:
    consumidas_mes = sum(s.horas_solicitadas_min for s in solicitudes_mes)
    consumidas_ano = sum(s.horas_solicitadas_min for s in solicitudes_ano)
    restantes_mes = persona.horas_mes_min - consumidas_mes
    restantes_ano = persona.horas_ano_min - consumidas_ano
    exceso_mes = abs(restantes_mes) if restantes_mes < 0 else 0
    exceso_ano = abs(restantes_ano) if restantes_ano < 0 else 0
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
