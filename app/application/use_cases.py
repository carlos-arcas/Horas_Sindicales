from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.application.base_cuadrantes_service import BaseCuadrantesService
from app.application.dto import (
    ConflictoDiaDTO,
    PeriodoFiltro,
    PersonaDTO,
    ResumenGlobalAnualDTO,
    ResumenGrupoAnualDTO,
    ResumenIndividualDTO,
    ResumenSaldosDTO,
    SaldosDTO,
    SolicitudDTO,
    TotalesGlobalesDTO,
    GrupoConfigDTO,
)
from app.domain.models import GrupoConfig, Persona, Solicitud
from app.domain.ports import GrupoConfigRepository, PersonaRepository, SolicitudRepository
from app.domain.services import (
    BusinessRuleError,
    ValidacionError,
    validar_persona,
    validar_solicitud,
)
from app.domain.time_utils import minutes_to_hhmm, parse_hhmm
from app.pdf import pdf_builder

logger = logging.getLogger(__name__)

MONTH_NAMES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}


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
    )


def _solicitud_to_dto(solicitud: Solicitud) -> SolicitudDTO:
    desde = minutes_to_hhmm(solicitud.desde_min) if solicitud.desde_min is not None else None
    hasta = minutes_to_hhmm(solicitud.hasta_min) if solicitud.hasta_min is not None else None
    notas = solicitud.notas if solicitud.notas is not None else solicitud.observaciones
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
        notas=notas,
        generated=solicitud.generated,
    )


def _dto_to_solicitud(dto: SolicitudDTO) -> Solicitud:
    desde_min = parse_hhmm(dto.desde) if dto.desde else None
    hasta_min = parse_hhmm(dto.hasta) if dto.hasta else None
    notas = dto.notas if dto.notas is not None else dto.observaciones
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
        notas=notas,
        pdf_path=dto.pdf_path,
        pdf_hash=dto.pdf_hash,
        generated=dto.generated,
    )


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


def _pdf_intro_text(config: GrupoConfig | None) -> str | None:
    if config is None:
        return None
    intro = (config.pdf_intro_text or "").strip()
    return intro or pdf_builder.INTRO_TEXT


class PersonaUseCases:
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
        logger.info("Creando persona %s", dto.nombre)
        persona = _dto_to_persona(dto)
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
        logger.info("Editando persona %s", dto.id)
        persona = _dto_to_persona(dto)
        validar_persona(persona)
        actualizada = self._repo.update(persona)
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


class SolicitudUseCases:
    def __init__(
        self,
        repo: SolicitudRepository,
        persona_repo: PersonaRepository,
        config_repo: GrupoConfigRepository | None = None,
    ) -> None:
        self._repo = repo
        self._persona_repo = persona_repo
        self._config_repo = config_repo

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

        conflicto = self.validar_conflicto_dia(dto.persona_id, dto.fecha_pedida, dto.completo)
        if not conflicto.ok:
            raise BusinessRuleError(
                "Conflicto completo/parcial en la misma fecha. "
                f"Acción sugerida: {conflicto.accion_sugerida}."
            )

        desde_min = parse_hhmm(dto.desde) if dto.desde else None
        hasta_min = parse_hhmm(dto.hasta) if dto.hasta else None
        if self._repo.exists_duplicate(
            dto.persona_id, dto.fecha_pedida, desde_min, hasta_min, dto.completo
        ):
            raise BusinessRuleError("Duplicado")

        minutos = _calcular_minutos(dto, persona)
        notas = dto.notas if dto.notas is not None else dto.observaciones
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
            notas=notas,
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

    def validar_conflicto_dia(
        self, persona_id: int, fecha_pedida: str, tipo_nuevo: bool
    ) -> ConflictoDiaDTO:
        existentes = list(self._repo.list_by_persona_and_fecha(persona_id, fecha_pedida))
        if tipo_nuevo:
            conflictos = [s for s in existentes if not s.completo]
        else:
            conflictos = [s for s in existentes if s.completo]
        ids = [s.id for s in conflictos if s.id is not None]
        if not ids:
            return ConflictoDiaDTO(ok=True, ids_existentes=[], accion_sugerida=None)
        return ConflictoDiaDTO(
            ok=False,
            ids_existentes=ids,
            accion_sugerida="sustituir",
        )

    def sustituir_por_completo(
        self, persona_id: int, fecha_pedida: str, nueva_solicitud: SolicitudDTO
    ) -> tuple[SolicitudDTO, SaldosDTO]:
        if not nueva_solicitud.completo:
            raise BusinessRuleError("La solicitud debe ser completa para esta sustitución.")
        existentes = list(self._repo.list_by_persona_and_fecha(persona_id, fecha_pedida))
        ids = [s.id for s in existentes if s.id is not None and not s.completo]
        self._repo.delete_by_ids(ids)
        return self.agregar_solicitud(nueva_solicitud)

    def sustituir_por_parcial(
        self, persona_id: int, fecha_pedida: str, nueva_solicitud: SolicitudDTO
    ) -> tuple[SolicitudDTO, SaldosDTO]:
        if nueva_solicitud.completo:
            raise BusinessRuleError("La solicitud debe ser parcial para esta sustitución.")
        existentes = list(self._repo.list_by_persona_and_fecha(persona_id, fecha_pedida))
        ids = [s.id for s in existentes if s.id is not None and s.completo]
        self._repo.delete_by_ids(ids)
        return self.agregar_solicitud(nueva_solicitud)

    def sugerir_completo_min(self, persona_id: int, fecha: str) -> int:
        persona = self._persona_repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        total_dia = _total_cuadrante_por_fecha(persona, fecha)
        return total_dia if total_dia > 0 else 0

    def sumar_pendientes_min(self, persona_id: int, solicitudes: Iterable[SolicitudDTO]) -> int:
        persona = self._persona_repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        total = 0
        for solicitud in solicitudes:
            total += _calcular_minutos(solicitud, persona)
        return total

    def calcular_minutos_solicitud(self, dto: SolicitudDTO) -> int:
        persona = self._persona_repo.get_by_id(dto.persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        return _calcular_minutos(dto, persona)

    def sugerir_nombre_pdf(self, solicitudes: Iterable[SolicitudDTO]) -> str:
        solicitudes_list = list(solicitudes)
        if not solicitudes_list:
            return "A_Coordinadora_Solicitud_Horas_Sindicales.pdf"
        persona = self._persona_repo.get_by_id(solicitudes_list[0].persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        fechas = [solicitud.fecha_pedida for solicitud in solicitudes_list]
        return pdf_builder.build_nombre_archivo(persona.nombre, fechas)

    def confirmar_lote_y_generar_pdf(
        self, solicitudes: Iterable[SolicitudDTO], destino: Path
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str], Path | None]:
        solicitudes_list = list(solicitudes)
        creadas: list[SolicitudDTO] = []
        pendientes: list[SolicitudDTO] = []
        errores: list[str] = []
        for solicitud in solicitudes_list:
            try:
                creada, _ = self.agregar_solicitud(solicitud)
                creadas.append(creada)
            except (ValidacionError, BusinessRuleError) as exc:
                errores.append(str(exc))
                pendientes.append(solicitud)
            except Exception as exc:  # pragma: no cover - fallback
                logger.exception("Error creando solicitud")
                errores.append(str(exc))
                pendientes.append(solicitud)

        pdf_path: Path | None = None
        if creadas:
            try:
                persona = self._persona_repo.get_by_id(creadas[0].persona_id)
                if persona is None:
                    raise BusinessRuleError("Persona no encontrada.")
                pdf_options = self._config_repo.get() if self._config_repo else None
                pdf_path = pdf_builder.construir_pdf_solicitudes(
                    creadas,
                    persona,
                    destino,
                    intro_text=_pdf_intro_text(pdf_options),
                    logo_path=pdf_options.pdf_logo_path if pdf_options else None,
                    include_hours_in_horario=(
                        pdf_options.pdf_include_hours_in_horario if pdf_options else None
                    ),
                )
                pdf_hash = _hash_file(pdf_path)
                creadas = [
                    _actualizar_pdf_en_repo(self._repo, solicitud, pdf_path, pdf_hash)
                    for solicitud in creadas
                ]
            except Exception as exc:  # pragma: no cover - fallback
                logger.exception("Error generando PDF")
                errores.append(f"No se pudo generar el PDF: {exc}")
                pdf_path = None

        return creadas, pendientes, errores, pdf_path

    def confirmar_y_generar_pdf(
        self, solicitudes: Iterable[SolicitudDTO], destino: Path
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str], Path | None]:
        return self.confirmar_lote_y_generar_pdf(solicitudes, destino)

    def generar_pdf_historico(
        self, solicitudes: Iterable[SolicitudDTO], destino: Path
    ) -> Path:
        solicitudes_list = list(solicitudes)
        if not solicitudes_list:
            raise BusinessRuleError("No hay solicitudes para generar el PDF.")
        persona = self._persona_repo.get_by_id(solicitudes_list[0].persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        pdf_options = self._config_repo.get() if self._config_repo else None
        return pdf_builder.construir_pdf_historico(
            solicitudes_list,
            persona,
            destino,
            intro_text=_pdf_intro_text(pdf_options),
            logo_path=pdf_options.pdf_logo_path if pdf_options else None,
        )

    def exportar_historico_pdf(
        self, persona_id: int, filtro: PeriodoFiltro, destino: Path
    ) -> Path:
        persona = self._persona_repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        solicitudes = self._repo.list_by_persona_and_period(
            persona_id,
            filtro.year,
            filtro.month if filtro.modo == "MENSUAL" else None,
        )
        solicitudes_list = [_solicitud_to_dto(s) for s in solicitudes]
        if not solicitudes_list:
            raise BusinessRuleError("No hay solicitudes para generar el PDF.")
        pdf_options = self._config_repo.get() if self._config_repo else None
        return pdf_builder.construir_pdf_historico(
            solicitudes_list,
            persona,
            destino,
            intro_text=_pdf_intro_text(pdf_options),
            logo_path=pdf_options.pdf_logo_path if pdf_options else None,
        )

    def sugerir_nombre_pdf_historico(self, filtro: PeriodoFiltro) -> str:
        if filtro.modo == "ANUAL":
            return f"Historico_Horas_Sindicales_(AÑO {filtro.year}).pdf"
        month_name = MONTH_NAMES.get(filtro.month or 0, "")
        return f"Historico_Horas_Sindicales_({month_name} {filtro.year}).pdf"

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

    def calcular_resumen_saldos(
        self, persona_id: int, filtro: PeriodoFiltro
    ) -> ResumenSaldosDTO:
        persona = self._persona_repo.get_by_id(persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        solicitudes_periodo = self._repo.list_by_persona_and_period(
            persona_id, filtro.year, filtro.month if filtro.modo == "MENSUAL" else None
        )
        solicitudes_ano = self._repo.list_by_persona_and_period(
            persona_id, filtro.year, None
        )
        consumidas_periodo = sum(s.horas_solicitadas_min for s in solicitudes_periodo)
        consumidas_anual = sum(s.horas_solicitadas_min for s in solicitudes_ano)
        bolsa_periodo = (
            persona.horas_mes_min if filtro.modo == "MENSUAL" else persona.horas_ano_min
        )
        bolsa_anual = persona.horas_ano_min
        individuales = ResumenIndividualDTO(
            consumidas_periodo_min=consumidas_periodo,
            bolsa_periodo_min=bolsa_periodo,
            restantes_periodo_min=bolsa_periodo - consumidas_periodo,
            consumidas_anual_min=consumidas_anual,
            bolsa_anual_min=bolsa_anual,
            restantes_anual_min=bolsa_anual - consumidas_anual,
        )

        personas = list(self._persona_repo.list_all())
        total_bolsa_anual = sum(p.horas_ano_min for p in personas)
        total_consumidas_anual = 0
        for persona_item in personas:
            solicitudes_persona = self._repo.list_by_persona_and_period(
                persona_item.id or 0, filtro.year, None
            )
            total_consumidas_anual += sum(s.horas_solicitadas_min for s in solicitudes_persona)
        global_anual = ResumenGlobalAnualDTO(
            consumidas_anual_min=total_consumidas_anual,
            bolsa_anual_min=total_bolsa_anual,
            restantes_anual_min=total_bolsa_anual - total_consumidas_anual,
        )

        config = self._config_repo.get() if self._config_repo else None
        bolsa_grupo = config.bolsa_anual_grupo_min if config else 0
        grupo_anual = ResumenGrupoAnualDTO(
            consumidas_anual_min=total_consumidas_anual,
            bolsa_anual_grupo_min=bolsa_grupo,
            restantes_anual_grupo_min=bolsa_grupo - total_consumidas_anual,
        )
        return ResumenSaldosDTO(
            individual=individuales, global_anual=global_anual, grupo_anual=grupo_anual
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
            raise BusinessRuleError(
                "Las horas deben ser mayores a cero. "
                "Configura el cuadrante o introduce las horas."
            )
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


def _hash_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _actualizar_pdf_en_repo(
    repo: SolicitudRepository, solicitud: SolicitudDTO, pdf_path: Path, pdf_hash: str | None
) -> SolicitudDTO:
    if solicitud.id is None:
        return solicitud
    repo.update_pdf_info(solicitud.id, str(pdf_path), pdf_hash)
    return replace(solicitud, pdf_path=str(pdf_path), pdf_hash=pdf_hash)
