from __future__ import annotations

import logging
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from app.application.dto import (
    ConflictoDiaDTO,
    PeriodoFiltro,
    ResumenGlobalAnualDTO,
    ResumenGrupoAnualDTO,
    ResumenIndividualDTO,
    ResumenSaldosDTO,
    ResultadoCrearSolicitudDTO,
    SaldosDTO,
    SolicitudDTO,
    TotalesGlobalesDTO,
)
from app.application.dtos.contexto_operacion import ContextoOperacion
from app.application.operaciones.exportacion_pdf_historico_operacion import (
    ExportacionPdfHistoricoOperacion,
    RequestExportacionPdfHistorico,
)
from app.application.operaciones.confirmacion_pdf_operacion import (
    ConfirmacionPdfOperacion,
    RequestConfirmacionPdf,
)
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto
from app.application.pending_conflicts import detect_pending_time_conflicts
from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.core.errors import InfraError, PersistenceError
from app.core.observability import log_event
from app.domain.models import Persona, Solicitud
from app.domain.ports import GrupoConfigRepository, PersonaRepository, SolicitudRepository
from app.domain.request_time import compute_request_minutes, minutes_to_hours_float
from app.domain.services import BusinessRuleError, ValidacionError, validar_solicitud
from app.domain.time_utils import parse_hhmm
from app.application.use_cases.solicitudes.validaciones import validar_solicitud_dto_declarativo
from app.application.use_cases.solicitudes.mapping_service import (
    solicitud_to_dto as _solicitud_to_dto,
)
from app.application.use_cases.solicitudes.confirmacion_pdf_service import (
    PathFileSystem,
    actualizar_pdf_en_repo as _actualizar_pdf_en_repo,
    generar_incident_id as _generar_incident_id,
    hash_file as _hash_file,
    pdf_intro_text as _pdf_intro_text,
)
from app.application.use_cases.solicitudes.validacion_service import (
    build_periodo_filtro as _build_periodo_filtro,
    calcular_minutos as _calcular_minutos,
    calcular_saldos as _calcular_saldos,
    normalize_date,
    normalize_time,
    parse_year_month as _parse_year_month,
    solapa_rango as _solapa_rango,
    solicitud_key,
    total_cuadrante_por_fecha as _total_cuadrante_por_fecha,
)

logger = logging.getLogger(__name__)


class ErrorAplicacionSolicitud(BusinessRuleError):
    def __init__(self, mensaje: str, *, incident_id: str) -> None:
        super().__init__(f"{mensaje}. ID de incidente: {incident_id}")
        self.incident_id = incident_id


def _resolver_correlation_id(
    correlation_id: str | None,
    contexto: ContextoOperacion | None,
) -> str | None:
    if contexto is not None:
        return contexto.correlation_id
    return correlation_id

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

class SolicitudUseCases:
    """Casos de uso para altas, sustituciones y saldos de solicitudes.

    Esta capa protege invariantes del dominio antes de persistir: conflicto
    completo/parcial, deduplicación y cálculo en minutos como unidad canónica.
    """
    def __init__(
        self,
        repo: SolicitudRepository,
        persona_repo: PersonaRepository,
        config_repo: GrupoConfigRepository | None = None,
        generador_pdf: GeneradorPdfPuerto | None = None,
        fs: SistemaArchivosPuerto | None = None,
    ) -> None:
        self._repo = repo
        self._persona_repo = persona_repo
        self._config_repo = config_repo
        self._generador_pdf = generador_pdf
        self._fs = fs or PathFileSystem()

    def listar_por_persona(self, persona_id: int) -> Iterable[SolicitudDTO]:
        return self.listar_solicitudes_por_persona_y_periodo(persona_id, None, None)

    def listar_solicitudes_por_persona(self, persona_id: int) -> Iterable[SolicitudDTO]:
        """Lista todas las solicitudes de una persona sin filtrar por periodo."""
        return [_solicitud_to_dto(s) for s in self._repo.list_by_persona(persona_id)]

    def listar_pendientes_por_persona(self, persona_id: int) -> Iterable[SolicitudDTO]:
        return [_solicitud_to_dto(s) for s in self._repo.list_pendientes_by_persona(persona_id)]

    def listar_pendientes_all(self) -> Iterable[SolicitudDTO]:
        return [_solicitud_to_dto(s) for s in self._repo.list_pendientes_all()]

    def listar_pendientes_huerfanas(self) -> Iterable[SolicitudDTO]:
        return [_solicitud_to_dto(s) for s in self._repo.list_pendientes_huerfanas()]

    def crear(
        self,
        dto: SolicitudDTO,
        correlation_id: str | None = None,
        contexto: ContextoOperacion | None = None,
    ) -> SolicitudDTO:
        solicitud, _ = self.agregar_solicitud(dto, correlation_id=correlation_id, contexto=contexto)
        return solicitud

    def crear_resultado(
        self,
        dto: SolicitudDTO,
        correlation_id: str | None = None,
        contexto: ContextoOperacion | None = None,
    ) -> ResultadoCrearSolicitudDTO:
        correlation_id = _resolver_correlation_id(correlation_id, contexto)
        errores: list[str] = []
        warnings: list[str] = []

        if dto.persona_id <= 0:
            errores.append("Selecciona una delegada válida antes de guardar la solicitud.")
            return ResultadoCrearSolicitudDTO(success=False, warnings=warnings, errores=errores, entidad=None)

        try:
            validar_solicitud_dto_declarativo(dto)
        except (ValidacionError, BusinessRuleError) as exc:
            errores.append(str(exc))
            return ResultadoCrearSolicitudDTO(success=False, warnings=warnings, errores=errores, entidad=None)

        persona = self._persona_repo.get_by_id(dto.persona_id)
        if persona is None:
            errores.append("Persona no encontrada.")
            return ResultadoCrearSolicitudDTO(success=False, warnings=warnings, errores=errores, entidad=None)

        dto_normalizado = replace(
            dto,
            fecha_pedida=normalize_date(dto.fecha_pedida),
            fecha_solicitud=normalize_date(dto.fecha_solicitud),
            desde=None if dto.desde is None else normalize_time(dto.desde),
            hasta=None if dto.hasta is None else normalize_time(dto.hasta),
        )

        conflicto = self.validar_conflicto_dia(dto_normalizado.persona_id, dto_normalizado.fecha_pedida, dto_normalizado.completo)
        if not conflicto.ok:
            errores.append(
                "Conflicto completo/parcial en la misma fecha. "
                f"Acción sugerida: {conflicto.accion_sugerida}."
            )
            return ResultadoCrearSolicitudDTO(success=False, warnings=warnings, errores=errores, entidad=None)

        duplicate = self.buscar_duplicado(dto_normalizado)
        if duplicate is not None:
            errores.append("Duplicado confirmado" if duplicate.generated else "Duplicado pendiente")
            return ResultadoCrearSolicitudDTO(success=False, warnings=warnings, errores=errores, entidad=None)

        try:
            minutos = _calcular_minutos(dto_normalizado, persona)
            year, month = _parse_year_month(dto_normalizado.fecha_pedida)
            saldos_previos = self.calcular_saldos(dto_normalizado.persona_id, year, month)
            if saldos_previos.restantes_mes < minutos or saldos_previos.restantes_ano < minutos:
                warning_msg = "Saldo insuficiente. La petición se ha registrado igualmente."
                warnings.append(warning_msg)
                logger.warning(
                    warning_msg,
                    extra={
                        "extra": {
                            "operation": "crear_solicitud",
                            "persona_id": dto_normalizado.persona_id,
                            "fecha_pedida": dto_normalizado.fecha_pedida,
                            "minutos_solicitados": minutos,
                            "restantes_mes": saldos_previos.restantes_mes,
                            "restantes_ano": saldos_previos.restantes_ano,
                        }
                    },
                )

            creada, saldos = self.agregar_solicitud(
                dto_normalizado,
                correlation_id=correlation_id,
                contexto=contexto,
            )
        except (ValidacionError, BusinessRuleError) as exc:
            errores.append(str(exc))
            return ResultadoCrearSolicitudDTO(success=False, warnings=warnings, errores=errores, entidad=None)
        except (InfraError, PersistenceError) as exc:
            errores.append(str(exc))
            return ResultadoCrearSolicitudDTO(success=False, warnings=warnings, errores=errores, entidad=None)

        return ResultadoCrearSolicitudDTO(
            success=True,
            warnings=warnings,
            errores=errores,
            entidad=creada,
            saldos=saldos,
        )

    def agregar_solicitud(
        self,
        dto: SolicitudDTO,
        correlation_id: str | None = None,
        contexto: ContextoOperacion | None = None,
    ) -> tuple[SolicitudDTO, SaldosDTO]:
        """Registra una solicitud nueva y devuelve el saldo recalculado.

        Se devuelve saldo en la misma operación para que el cliente trabaje con
        una vista consistente después de validar duplicados y conflictos del día.
        """
        correlation_id = _resolver_correlation_id(correlation_id, contexto)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        logger.info(
            "Creando solicitud persona_id=%s fecha_pedida=%s completo=%s desde=%s hasta=%s",
            dto.persona_id,
            dto.fecha_pedida,
            dto.completo,
            dto.desde,
            dto.hasta,
        )
        if correlation_id:
            log_event(
                logger,
                "solicitud_create_started",
                {"persona_id": dto.persona_id, "fecha_pedida": dto.fecha_pedida},
                correlation_id,
            )
        if dto.persona_id <= 0:
            raise BusinessRuleError("Selecciona una delegada válida antes de guardar la solicitud.")
        validar_solicitud_dto_declarativo(dto)
        persona = self._persona_repo.get_by_id(dto.persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")

        dto = replace(
            dto,
            fecha_pedida=normalize_date(dto.fecha_pedida),
            fecha_solicitud=normalize_date(dto.fecha_solicitud),
            desde=None if dto.desde is None else normalize_time(dto.desde),
            hasta=None if dto.hasta is None else normalize_time(dto.hasta),
        )

        conflicto = self.validar_conflicto_dia(dto.persona_id, dto.fecha_pedida, dto.completo)
        if not conflicto.ok:
            raise BusinessRuleError(
                "Conflicto completo/parcial en la misma fecha. "
                f"Acción sugerida: {conflicto.accion_sugerida}."
            )

        desde_min = parse_hhmm(dto.desde) if dto.desde else None
        hasta_min = parse_hhmm(dto.hasta) if dto.hasta else None
        duplicate_key = solicitud_key(dto, persona=persona, delegada_uuid=self._delegada_uuid(dto.persona_id))
        duplicate = self.buscar_duplicado(dto)
        if duplicate is not None:
            logger.debug("Duplicado detectado al agregar solicitud. nueva=%s existente_id=%s", duplicate_key, duplicate.id)
            if duplicate.generated:
                raise BusinessRuleError("Duplicado confirmado")
            raise BusinessRuleError("Duplicado pendiente")

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
        logger.info(
            "Pendiente creada id=%s delegada_id=%s fecha=%s tramo=%s-%s",
            creada.id,
            creada.persona_id,
            creada.fecha_pedida,
            dto.desde,
            dto.hasta,
        )
        year, month = _parse_year_month(dto.fecha_pedida)
        saldos = self.calcular_saldos(dto.persona_id, year, month)
        if correlation_id:
            log_event(
                logger,
                "solicitud_create_succeeded",
                {"solicitud_id": creada.id, "persona_id": creada.persona_id},
                correlation_id,
            )
        return _solicitud_to_dto(creada), saldos

    def _delegada_uuid(self, persona_id: int) -> str:
        delegada_uuid = self._persona_repo.get_or_create_uuid(persona_id)
        if not delegada_uuid:
            raise BusinessRuleError("No se pudo resolver el uuid de la delegada.")
        return delegada_uuid

    def buscar_duplicado(self, dto: SolicitudDTO) -> SolicitudDTO | None:
        _, fecha, completo, desde, hasta = solicitud_key(
            dto,
            persona=self._persona_repo.get_by_id(dto.persona_id),
            delegada_uuid=self._delegada_uuid(dto.persona_id),
        )
        desde_min = None if completo else parse_hhmm(str(desde))
        hasta_min = None if completo else parse_hhmm(str(hasta))
        duplicate = self._repo.find_duplicate(dto.persona_id, str(fecha), desde_min, hasta_min, completo)
        if duplicate is None:
            return None
        return _solicitud_to_dto(duplicate)

    def buscar_similares(self, dto: SolicitudDTO) -> list[SolicitudDTO]:
        """Devuelve posibles solicitudes similares de la misma delegada y fecha.

        Similaridad operativa: misma persona y fecha con solape de tramo horario.
        En solicitudes completas se considera similar cualquier solicitud del mismo día.
        """
        if dto.persona_id <= 0:
            return []
        fecha = normalize_date(dto.fecha_pedida)
        existentes = list(self._repo.list_by_persona_and_fecha(dto.persona_id, fecha))
        if not existentes:
            return []

        if dto.completo:
            return [_solicitud_to_dto(item) for item in existentes]

        nuevo_desde = parse_hhmm(dto.desde or "00:00")
        nuevo_hasta = parse_hhmm(dto.hasta or "00:00")
        similares: list[SolicitudDTO] = []
        for existente in existentes:
            if existente.completo:
                similares.append(_solicitud_to_dto(existente))
                continue
            if existente.desde_min is None or existente.hasta_min is None:
                continue
            if _solapa_rango(nuevo_desde, nuevo_hasta, existente.desde_min, existente.hasta_min):
                similares.append(_solicitud_to_dto(existente))
        return similares

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

    def eliminar_solicitud(
        self,
        solicitud_id: int,
        correlation_id: str | None = None,
        contexto: ContextoOperacion | None = None,
    ) -> SaldosDTO:
        correlation_id = _resolver_correlation_id(correlation_id, contexto)
        if correlation_id:
            log_event(logger, "solicitud_delete_started", {"solicitud_id": solicitud_id}, correlation_id)
        solicitud = self._repo.get_by_id(solicitud_id)
        if solicitud is None:
            raise BusinessRuleError("Solicitud no encontrada.")
        self._repo.delete(solicitud_id)
        year, month = _parse_year_month(solicitud.fecha_pedida)
        if correlation_id:
            log_event(logger, "solicitud_delete_succeeded", {"solicitud_id": solicitud_id}, correlation_id)
        return self.calcular_saldos(solicitud.persona_id, year, month)

    def validar_conflicto_dia(
        self, persona_id: int, fecha_pedida: str, tipo_nuevo: bool
    ) -> ConflictoDiaDTO:
        """Impide mezclar solicitudes completas y parciales en la misma fecha.

        La regla existe para mantener una semántica única de consumo diario y
        evitar dobles cómputos cuando se sustituyen solicitudes existentes.
        """
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
        self,
        persona_id: int,
        fecha_pedida: str,
        nueva_solicitud: SolicitudDTO,
        correlation_id: str | None = None,
    ) -> tuple[SolicitudDTO, SaldosDTO]:
        if not nueva_solicitud.completo:
            raise BusinessRuleError("La solicitud debe ser completa para esta sustitución.")
        existentes = list(self._repo.list_by_persona_and_fecha(persona_id, fecha_pedida))
        ids = [s.id for s in existentes if s.id is not None and not s.completo]
        self._repo.delete_by_ids(ids)
        return self.agregar_solicitud(nueva_solicitud, correlation_id=correlation_id)

    def sustituir_por_parcial(
        self,
        persona_id: int,
        fecha_pedida: str,
        nueva_solicitud: SolicitudDTO,
        correlation_id: str | None = None,
    ) -> tuple[SolicitudDTO, SaldosDTO]:
        if nueva_solicitud.completo:
            raise BusinessRuleError("La solicitud debe ser parcial para esta sustitución.")
        existentes = list(self._repo.list_by_persona_and_fecha(persona_id, fecha_pedida))
        ids = [s.id for s in existentes if s.id is not None and s.completo]
        self._repo.delete_by_ids(ids)
        return self.agregar_solicitud(nueva_solicitud, correlation_id=correlation_id)

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

    def minutes_to_hours_float(self, minutos: int) -> float:
        return minutes_to_hours_float(minutos)

    def detectar_conflictos_pendientes(self, solicitudes: Iterable[SolicitudDTO]) -> set[int]:
        solicitudes_list = list(solicitudes)
        if not solicitudes_list:
            return set()

        persona_cache: dict[int, Persona] = {}

        def _resolve_interval(dto: SolicitudDTO) -> tuple[int, int]:
            persona = persona_cache.get(dto.persona_id)
            if persona is None:
                persona = self._persona_repo.get_by_id(dto.persona_id)
                if persona is None:
                    raise BusinessRuleError("Persona no encontrada.")
                persona_cache[dto.persona_id] = persona

            if dto.completo:
                total_dia = _total_cuadrante_por_fecha(persona, dto.fecha_pedida)
                compute_request_minutes(
                    dto.desde,
                    dto.hasta,
                    dto.completo,
                    cuadrante_base=total_dia,
                )
                return 0, 24 * 60

            if not dto.desde or not dto.hasta:
                raise BusinessRuleError("Desde y hasta son obligatorios para solicitudes parciales.")
            return parse_hhmm(dto.desde), parse_hhmm(dto.hasta)

        return detect_pending_time_conflicts(solicitudes_list, _resolve_interval)

    def sugerir_nombre_pdf(self, solicitudes: Iterable[SolicitudDTO]) -> str:
        solicitudes_list = list(solicitudes)
        if not solicitudes_list:
            return "A_Coordinadora_Solicitud_Horas_Sindicales.pdf"
        persona = self._persona_repo.get_by_id(solicitudes_list[0].persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        fechas = [solicitud.fecha_pedida for solicitud in solicitudes_list]
        if self._generador_pdf is None:
            raise BusinessRuleError("No hay generador PDF configurado.")
        return self._generador_pdf.construir_nombre_archivo(persona.nombre, fechas)

    def confirmar_lote_y_generar_pdf(
        self,
        solicitudes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str], Path | None]:
        solicitudes_list = list(solicitudes)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        if correlation_id:
            log_event(logger, "confirmar_lote_pdf_started", {"count": len(solicitudes_list)}, correlation_id)

        for solicitud in solicitudes_list:
            validar_solicitud_dto_declarativo(solicitud)

        preflight = ConfirmacionPdfOperacion(fs=self._fs, generador_pdf=self._generador_pdf).ejecutar(
            RequestConfirmacionPdf(
                solicitudes=solicitudes_list,
                destino=destino,
                dry_run=True,
                overwrite=False,
            )
        )
        if preflight.conflictos.no_ejecutable:
            raise BusinessRuleError("; ".join(preflight.conflictos.conflictos))

        creadas: list[SolicitudDTO] = []
        pendientes: list[SolicitudDTO] = []
        errores: list[str] = []
        for solicitud in solicitudes_list:
            try:
                if solicitud.id is not None:
                    existente = self._repo.get_by_id(solicitud.id)
                    if existente is None:
                        raise BusinessRuleError("La solicitud pendiente ya no existe.")
                    creada = _solicitud_to_dto(existente)
                else:
                    creada, _ = self.agregar_solicitud(solicitud, correlation_id=correlation_id)
                creadas.append(creada)
            except (ValidacionError, BusinessRuleError) as exc:
                errores.append(str(exc))
                pendientes.append(solicitud)
            except PersistenceError:
                raise
            except InfraError:  # pragma: no cover - fallback
                incident_id = _generar_incident_id()
                logger.exception("Error técnico creando solicitud")
                if correlation_id:
                    log_event(
                        logger,
                        "confirmar_lote_pdf_failed",
                        {"error": "crear_solicitud", "incident_id": incident_id},
                        correlation_id,
                    )
                errores.append(f"Se produjo un error técnico al guardar la solicitud. ID de incidente: {incident_id}")
                pendientes.append(solicitud)

        pdf_path: Path | None = None
        if creadas:
            try:
                persona = self._persona_repo.get_by_id(creadas[0].persona_id)
                if persona is None:
                    raise BusinessRuleError("Persona no encontrada.")
                pdf_options = self._config_repo.get() if self._config_repo else None
                if self._generador_pdf is None:
                    raise BusinessRuleError("No hay generador PDF configurado.")
                pdf_path = self._generador_pdf.generar_pdf_solicitudes(
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
            except PersistenceError:
                raise
            except InfraError:  # pragma: no cover - fallback
                incident_id = _generar_incident_id()
                logger.exception("Error técnico generando PDF")
                if correlation_id:
                    log_event(
                        logger,
                        "confirmar_lote_pdf_failed",
                        {"error": "generar_pdf", "incident_id": incident_id},
                        correlation_id,
                    )
                raise ErrorAplicacionSolicitud(
                    "No se pudo generar el PDF por un error técnico",
                    incident_id=incident_id,
                )

        if correlation_id:
            log_event(
                logger,
                "confirmar_lote_pdf_succeeded",
                {"creadas": len(creadas), "pendientes": len(pendientes), "errores": len(errores)},
                correlation_id,
            )
        return creadas, pendientes, errores, pdf_path

    def confirmar_sin_pdf(
        self,
        solicitudes: Iterable[SolicitudDTO],
        correlation_id: str | None = None,
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]:
        solicitudes_list = list(solicitudes)
        if correlation_id:
            log_event(logger, "confirmar_sin_pdf_started", {"count": len(solicitudes_list)}, correlation_id)
        creadas_confirmadas: list[SolicitudDTO] = []
        pendientes_restantes: list[SolicitudDTO] = []
        errores: list[str] = []
        for solicitud in solicitudes_list:
            try:
                if solicitud.id is not None:
                    existente = self._repo.get_by_id(solicitud.id)
                    if existente is None:
                        raise BusinessRuleError("La solicitud pendiente ya no existe.")
                    creada = _solicitud_to_dto(existente)
                else:
                    creada, _ = self.agregar_solicitud(solicitud, correlation_id=correlation_id)

                if creada.id is None:
                    raise BusinessRuleError("No se pudo confirmar la solicitud sin id.")
                self._repo.mark_generated(creada.id, True)
                creadas_confirmadas.append(replace(creada, generated=True))
            except (ValidacionError, BusinessRuleError) as exc:
                errores.append(str(exc))
                pendientes_restantes.append(solicitud)
            except PersistenceError:
                raise
            except InfraError as exc:  # pragma: no cover - fallback
                logger.exception("Error técnico confirmando solicitud sin PDF")
                if correlation_id:
                    log_event(logger, "confirmar_sin_pdf_failed", {"error": str(exc)}, correlation_id)
                errores.append("Se produjo un error técnico al confirmar la solicitud.")
                pendientes_restantes.append(solicitud)

        if correlation_id:
            log_event(
                logger,
                "confirmar_sin_pdf_succeeded",
                {"creadas": len(creadas_confirmadas), "pendientes": len(pendientes_restantes), "errores": len(errores)},
                correlation_id,
            )
        return creadas_confirmadas, pendientes_restantes, errores

    def confirmar_y_generar_pdf(
        self,
        solicitudes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str], Path | None]:
        return self.confirmar_lote_y_generar_pdf(solicitudes, destino, correlation_id=correlation_id)

    def confirmar_y_generar_pdf_por_filtro(
        self,
        *,
        filtro_delegada: int | None,
        pendientes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> tuple[Path | None, list[int], str]:
        pendientes_lista = list(pendientes)
        if filtro_delegada is None:
            seleccionadas = pendientes_lista
            modo = "todas"
        else:
            seleccionadas = [sol for sol in pendientes_lista if sol.persona_id == filtro_delegada]
            modo = f"delegada:{filtro_delegada}"
        if not seleccionadas:
            return None, [], f"Sin pendientes para confirmar ({modo})."

        creadas, _pendientes, errores, ruta = self.confirmar_lote_y_generar_pdf(
            seleccionadas,
            destino,
            correlation_id=correlation_id,
        )
        if ruta is None:
            return None, [], "No se generó el PDF."
        ids_confirmadas = [sol.id for sol in creadas if sol.id is not None]
        resumen = f"Confirmadas: {len(ids_confirmadas)} · Errores: {len(errores)} · Modo: {modo}"
        return ruta, ids_confirmadas, resumen

    def generar_pdf_historico(
        self,
        solicitudes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> Path:
        solicitudes_list = list(solicitudes)
        if correlation_id:
            log_event(logger, "generar_pdf_historico_started", {"count": len(solicitudes_list)}, correlation_id)
        if not solicitudes_list:
            raise BusinessRuleError("No hay solicitudes para generar el PDF.")
        persona = self._persona_repo.get_by_id(solicitudes_list[0].persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        pdf_options = self._config_repo.get() if self._config_repo else None
        operacion = ExportacionPdfHistoricoOperacion(fs=self._fs, generador_pdf=self._generador_pdf)
        resultado = operacion.ejecutar(
            RequestExportacionPdfHistorico(
                solicitudes=solicitudes_list,
                persona=persona,
                destino=destino,
                dry_run=False,
                overwrite=True,
                intro_text=_pdf_intro_text(pdf_options),
                logo_path=pdf_options.pdf_logo_path if pdf_options else None,
            )
        )
        if resultado.conflictos.no_ejecutable:
            raise BusinessRuleError("; ".join(resultado.conflictos.conflictos))
        pdf_path = Path(resultado.artefactos_generados[0])
        if correlation_id:
            log_event(logger, "generar_pdf_historico_succeeded", {"path": str(pdf_path)}, correlation_id)
        return pdf_path

    def exportar_historico_pdf(
        self,
        persona_id: int,
        filtro: PeriodoFiltro,
        destino: Path,
        correlation_id: str | None = None,
    ) -> Path:
        if correlation_id:
            log_event(logger, "exportar_historico_pdf_started", {"persona_id": persona_id}, correlation_id)
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
        operacion = ExportacionPdfHistoricoOperacion(fs=self._fs, generador_pdf=self._generador_pdf)
        resultado = operacion.ejecutar(
            RequestExportacionPdfHistorico(
                solicitudes=solicitudes_list,
                persona=persona,
                destino=destino,
                dry_run=False,
                overwrite=True,
                intro_text=_pdf_intro_text(pdf_options),
                logo_path=pdf_options.pdf_logo_path if pdf_options else None,
            )
        )
        if resultado.conflictos.no_ejecutable:
            raise BusinessRuleError("; ".join(resultado.conflictos.conflictos))
        pdf_path = Path(resultado.artefactos_generados[0])
        if correlation_id:
            log_event(logger, "exportar_historico_pdf_succeeded", {"path": str(pdf_path)}, correlation_id)
        return pdf_path

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
