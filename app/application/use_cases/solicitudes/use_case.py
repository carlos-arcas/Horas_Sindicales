from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Iterable

from app.application.dto import (
    ConflictoDiaDTO,
    PeriodoFiltro,
    ResumenSaldosDTO,
    ResultadoCrearSolicitudDTO,
    SaldosDTO,
    SolicitudDTO,
    TotalesGlobalesDTO,
)
from app.application.dtos.contexto_operacion import ContextoOperacion
from app.application.ports.sistema_archivos_puerto import SistemaArchivosPuerto
from app.application.ports.pdf_puerto import GeneradorPdfPuerto
from app.core.errors import InfraError, PersistenceError
from app.core.metrics import metrics_registry
from app.core.observability import log_event
from app.configuracion.settings import is_read_only_enabled
from app.domain.models import ConflictoSolicitud, Persona, Solicitud
from app.domain.ports import (
    GrupoConfigRepository,
    PersonaRepository,
    SolicitudRepository,
)
from app.domain.request_time import minutes_to_hours_float
from app.domain.services import BusinessRuleError, ValidacionError, validar_solicitud
from app.domain.time_range import normalize_range, overlaps
from app.domain.time_utils import parse_hhmm
from app.application.use_cases.solicitudes.validaciones import (
    validar_solicitud_dto_declarativo,
)
from app.application.use_cases.solicitudes.mapping_service import (
    solicitud_to_dto as _solicitud_to_dto,
)
from app.application.use_cases.solicitudes.helpers_puros import (
    mensaje_conflicto,
    mensaje_duplicado,
    mensaje_persona_invalida,
    mensaje_warning_saldo_insuficiente,
    normalizar_dto_para_creacion,
    resultado_error_creacion,
    saldo_insuficiente,
)
from app.application.use_cases.solicitudes.helpers_puros_2 import (
    correlation_id_or_new,
    debe_emitir_evento,
    mensaje_duplicado_desde_estado,
    payload_evento_exito,
    payload_evento_inicio,
    rango_en_minutos,
    solicitud_desde_dto,
)
from app.application.use_cases.solicitudes.confirmacion_pdf_service import (
    PathFileSystem,
    generar_incident_id as _generar_incident_id,
    hash_file as _hash_file,
    pdf_intro_text as _pdf_intro_text,
)
from app.application.use_cases.solicitudes.confirmar_sin_pdf_planner import (
    plan_confirmar_sin_pdf,
)
from app.application.use_cases.solicitudes.pdf_confirmadas_builder import (
    plan_pdf_confirmadas,
)
from app.application.use_cases.solicitudes.pdf_confirmadas_runner import (
    run_pdf_confirmadas_plan,
)
from app.application.use_cases.solicitudes.pdf_destino_policy import (
    resolver_colision_pdf,
    resolver_ruta_sin_colision,
)
from app.application.use_cases.solicitudes.servicio_preflight_pdf import (
    EntradaNombrePdf,
    ServicioPreflightPdf,
)
from app.application.use_cases.solicitudes.servicio_saldos import (
    acumular_consumo_anual_por_personas as _acumular_consumo_anual_por_personas,
    calcular_totales_globales as _calcular_totales_globales,
    construir_resumen_saldos as _construir_resumen_saldos,
    sumar_consumo_solicitudes as _sumar_consumo_solicitudes,
    sugerir_nombre_pdf_historico as _sugerir_nombre_pdf_historico,
)
from app.application.use_cases.solicitudes.auxiliares_caso_uso import (
    NOMBRE_PDF_POR_DEFECTO,
    ResolucionDestinoPdf,
    calcular_totales_globales_desde_fuentes,
    calcular_resumen_saldos_desde_fuentes,
    construir_conflicto_dia,
    detectar_conflictos_pendientes_con_resolutor,
    ejecutar_exportacion_pdf_historico,
    ids_para_sustitucion,
    obtener_persona_o_error,
    resolver_destino_pdf as resolver_destino_pdf_helper,
    resumen_confirmacion_pdf,
    resolver_correlation_id,
    seleccionar_solicitudes_por_filtro,
    sugerir_completo_minutos,
    sumar_pendientes_minutos,
    validar_tipo_para_sustitucion,
    confirmar_solicitudes_lote_con_manejador,
    confirmar_sin_pdf_con_manejador,
    ejecutar_confirmar_sin_pdf_action,
)
from app.application.use_cases.solicitudes.orquestacion_confirmacion import (
    confirmar_lote_y_generar_pdf as confirmar_lote_y_generar_pdf_orquestado,
    confirmar_sin_pdf as confirmar_sin_pdf_orquestado,
    confirmar_solicitudes_lote as confirmar_solicitudes_lote_orquestado,
    generar_pdf_confirmadas as generar_pdf_confirmadas_orquestado,
    resolver_o_crear_solicitud as resolver_o_crear_solicitud_orquestado,
    run_confirmar_sin_pdf_action as run_confirmar_sin_pdf_action_orquestado,
)
from app.application.use_cases.solicitudes.orquestacion_exportaciones import (
    exportar_historico_pdf as exportar_historico_pdf_orquestado,
    generar_pdf_historico as generar_pdf_historico_orquestado,
    personas_por_solicitudes,
)
from app.application.use_cases.solicitudes.orquestacion_pendientes import (
    listar_pendientes_all as listar_pendientes_all_orquestado,
    listar_pendientes_huerfanas as listar_pendientes_huerfanas_orquestado,
    listar_pendientes_por_persona as listar_pendientes_por_persona_orquestado,
)
from app.application.use_cases.solicitudes.validacion_service import (
    build_periodo_filtro as _build_periodo_filtro,
    calcular_minutos as _calcular_minutos,
    calcular_saldos as _calcular_saldos,
    normalize_date,
    parse_year_month as _parse_year_month,
    solicitud_key,
    total_cuadrante_por_fecha as _total_cuadrante_por_fecha,
)

logger = logging.getLogger(__name__)


class SolicitudUseCases:
    """Casos de uso para solicitudes."""

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
        self._servicio_preflight_pdf = ServicioPreflightPdf(
            fs=self._fs,
            generador_pdf=self._generador_pdf,
        )

    def listar_por_persona(self, persona_id: int) -> Iterable[SolicitudDTO]:
        return self.listar_solicitudes_por_persona_y_periodo(persona_id, None, None)

    def listar_solicitudes_por_persona(self, persona_id: int) -> Iterable[SolicitudDTO]:
        """Lista todas las solicitudes de una persona sin filtrar por periodo."""
        return [_solicitud_to_dto(s) for s in self._repo.list_by_persona(persona_id)]

    def listar_historico(self) -> Iterable[SolicitudDTO]:
        """Lista el histórico consolidado con paginación defensiva y sin consultas N+1."""
        limite = 500
        offset = 0
        solicitudes: list[SolicitudDTO] = []

        while True:
            lote = list(self._repo.list_historico_batch(limit=limite, offset=offset))
            if not lote:
                break
            solicitudes.extend(_solicitud_to_dto(solicitud) for solicitud in lote)
            if len(lote) < limite:
                break
            offset += limite

        return solicitudes

    def _personas_por_solicitudes(
        self, solicitudes: list[SolicitudDTO]
    ) -> dict[int, Persona]:
        return personas_por_solicitudes(
            solicitudes=solicitudes, persona_repo=self._persona_repo
        )

    def listar_pendientes_por_persona(self, persona_id: int) -> Iterable[SolicitudDTO]:
        return listar_pendientes_por_persona_orquestado(
            self._repo,
            persona_id,
            solicitud_to_dto=_solicitud_to_dto,
        )

    def listar_pendientes_all(self) -> Iterable[SolicitudDTO]:
        return listar_pendientes_all_orquestado(
            self._repo, solicitud_to_dto=_solicitud_to_dto
        )

    def listar_pendientes_huerfanas(self) -> Iterable[SolicitudDTO]:
        return listar_pendientes_huerfanas_orquestado(
            self._repo, solicitud_to_dto=_solicitud_to_dto
        )

    def crear(
        self,
        dto: SolicitudDTO,
        correlation_id: str | None = None,
        contexto: ContextoOperacion | None = None,
    ) -> SolicitudDTO:
        solicitud, _ = self.agregar_solicitud(
            dto, correlation_id=correlation_id, contexto=contexto
        )
        return solicitud

    def crear_resultado(
        self,
        dto: SolicitudDTO,
        correlation_id: str | None = None,
        contexto: ContextoOperacion | None = None,
    ) -> ResultadoCrearSolicitudDTO:
        correlation_id = resolver_correlation_id(correlation_id, contexto)
        errores: list[str] = []
        warnings: list[str] = []

        try:
            dto_normalizado, persona = self._resolver_peticion_y_persona_para_creacion(
                dto
            )
            self._agregar_warning_saldo_si_aplica(dto_normalizado, persona, warnings)
            creada, saldos = self.agregar_solicitud(
                dto_normalizado,
                correlation_id=correlation_id,
                contexto=contexto,
            )
        except (
            ValidacionError,
            BusinessRuleError,
            InfraError,
            PersistenceError,
        ) as exc:
            errores.append(str(exc))
            return resultado_error_creacion(errores=errores, warnings=warnings)

        return ResultadoCrearSolicitudDTO(
            success=True,
            warnings=warnings,
            errores=errores,
            entidad=creada,
            saldos=saldos,
        )

    def _resolver_peticion_y_persona_para_creacion(
        self, dto: SolicitudDTO
    ) -> tuple[SolicitudDTO, Persona]:
        mensaje_error = mensaje_persona_invalida(dto.persona_id)
        if mensaje_error is not None:
            raise BusinessRuleError(mensaje_error)
        validar_solicitud_dto_declarativo(dto)
        persona = self._persona_repo.get_by_id(dto.persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")

        dto_normalizado = normalizar_dto_para_creacion(dto)
        conflicto = self.validar_conflicto_dia(
            dto_normalizado.persona_id,
            dto_normalizado.fecha_pedida,
            dto_normalizado.completo,
        )
        if not conflicto.ok:
            raise BusinessRuleError(mensaje_conflicto(conflicto.accion_sugerida))
        duplicate = self.buscar_duplicado(dto_normalizado)
        if duplicate is not None:
            raise BusinessRuleError(mensaje_duplicado(duplicate.generated))
        return dto_normalizado, persona

    def _agregar_warning_saldo_si_aplica(
        self, dto: SolicitudDTO, persona: Persona, warnings: list[str]
    ) -> None:
        minutos = _calcular_minutos(dto, persona)
        year, month = _parse_year_month(dto.fecha_pedida)
        saldos_previos = self.calcular_saldos(dto.persona_id, year, month)
        if not saldo_insuficiente(
            saldos_previos.restantes_mes, saldos_previos.restantes_ano, minutos
        ):
            return
        warning_msg = mensaje_warning_saldo_insuficiente()
        warnings.append(warning_msg)
        logger.warning(
            warning_msg,
            extra={
                "extra": {
                    "operation": "crear_solicitud",
                    "persona_id": dto.persona_id,
                    "fecha_pedida": dto.fecha_pedida,
                    "minutos_solicitados": minutos,
                    "restantes_mes": saldos_previos.restantes_mes,
                    "restantes_ano": saldos_previos.restantes_ano,
                }
            },
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
        correlation_id = resolver_correlation_id(correlation_id, contexto)
        correlation_id = correlation_id_or_new(correlation_id, str(uuid.uuid4()))
        self._log_inicio_agregar_solicitud(dto, correlation_id)
        dto_normalizado, persona = self._validar_y_normalizar_dto(dto)
        self._validar_conflicto_y_duplicado(dto_normalizado, persona)
        creada, saldos = self._crear_solicitud_y_saldos(dto_normalizado, persona)
        metrics_registry.incrementar("solicitudes_creadas")
        if debe_emitir_evento(correlation_id):
            log_event(
                logger,
                "solicitud_create_succeeded",
                payload_evento_exito(creada.id, creada.persona_id),
                correlation_id,
            )
        return _solicitud_to_dto(creada), saldos

    def _log_inicio_agregar_solicitud(
        self, dto: SolicitudDTO, correlation_id: str
    ) -> None:
        logger.info(
            "Creando solicitud persona_id=%s fecha_pedida=%s completo=%s desde=%s hasta=%s",
            dto.persona_id,
            dto.fecha_pedida,
            dto.completo,
            dto.desde,
            dto.hasta,
        )
        if debe_emitir_evento(correlation_id):
            log_event(
                logger,
                "solicitud_create_started",
                payload_evento_inicio(dto),
                correlation_id,
            )

    def _validar_y_normalizar_dto(
        self, dto: SolicitudDTO
    ) -> tuple[SolicitudDTO, Persona]:
        mensaje_persona = mensaje_persona_invalida(dto.persona_id)
        if mensaje_persona is not None:
            raise BusinessRuleError(mensaje_persona)
        validar_solicitud_dto_declarativo(dto)
        persona = self._persona_repo.get_by_id(dto.persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        return normalizar_dto_para_creacion(dto), persona

    def _validar_conflicto_y_duplicado(
        self, dto: SolicitudDTO, persona: Persona
    ) -> None:
        conflicto = self.validar_conflicto_dia(
            dto.persona_id, dto.fecha_pedida, dto.completo
        )
        if not conflicto.ok:
            raise BusinessRuleError(mensaje_conflicto(conflicto.accion_sugerida))

        duplicate_key = solicitud_key(
            dto, persona=persona, delegada_uuid=self._delegada_uuid(dto.persona_id)
        )
        conflicto_pendiente = self.buscar_conflicto_pendiente(dto)
        if conflicto_pendiente is None:
            return
        if conflicto_pendiente.tipo == "DUPLICADO":
            duplicate = self._repo.get_by_id(conflicto_pendiente.id_existente)
            logger.debug(
                "Duplicado detectado al agregar solicitud. nueva=%s existente_id=%s",
                duplicate_key,
                conflicto_pendiente.id_existente,
            )
            raise BusinessRuleError(
                mensaje_duplicado_desde_estado(bool(duplicate and duplicate.generated))
            )
        logger.debug(
            "Solape detectado al agregar solicitud. nueva=%s existente_id=%s",
            duplicate_key,
            conflicto_pendiente.id_existente,
        )
        raise BusinessRuleError(
            "Solape horario con una solicitud existente en la misma fecha."
        )

    def _crear_solicitud_y_saldos(
        self, dto: SolicitudDTO, persona: Persona
    ) -> tuple[Solicitud, SaldosDTO]:
        desde_min, hasta_min = rango_en_minutos(dto.desde, dto.hasta)
        minutos = _calcular_minutos(dto, persona)
        solicitud = solicitud_desde_dto(
            dto, minutos=minutos, desde_min=desde_min, hasta_min=hasta_min
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
        return creada, self.calcular_saldos(dto.persona_id, year, month)

    def _delegada_uuid(self, persona_id: int) -> str:
        delegada_uuid = self._persona_repo.get_or_create_uuid(persona_id)
        if not delegada_uuid:
            raise BusinessRuleError("No se pudo resolver el uuid de la delegada.")
        return delegada_uuid

    def buscar_conflicto_pendiente(
        self,
        dto: SolicitudDTO,
        *,
        excluir_solicitud_id: int | None = None,
    ) -> ConflictoSolicitud | None:
        persona = self._persona_repo.get_by_id(dto.persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        _, fecha, completo, desde, hasta = solicitud_key(
            dto,
            persona=persona,
            delegada_uuid=self._delegada_uuid(dto.persona_id),
        )
        desde_min = None if completo else parse_hhmm(str(desde))
        hasta_min = None if completo else parse_hhmm(str(hasta))
        return self._repo.detectar_conflicto_pendiente(
            dto.persona_id,
            str(fecha),
            desde_min,
            hasta_min,
            completo,
            excluir_solicitud_id=excluir_solicitud_id,
        )

    def buscar_duplicado(self, dto: SolicitudDTO) -> SolicitudDTO | None:
        persona = self._persona_repo.get_by_id(dto.persona_id)
        if persona is None:
            raise BusinessRuleError("Persona no encontrada.")
        _, fecha, completo, desde, hasta = solicitud_key(
            dto,
            persona=persona,
            delegada_uuid=self._delegada_uuid(dto.persona_id),
        )
        desde_min = None if completo else parse_hhmm(str(desde))
        hasta_min = None if completo else parse_hhmm(str(hasta))
        duplicate = self._repo.find_duplicate(
            dto.persona_id,
            str(fecha),
            desde_min,
            hasta_min,
            completo,
        )
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

        nuevo_inicio, nuevo_fin = normalize_range(
            completo=dto.completo,
            desde=dto.desde,
            hasta=dto.hasta,
        )
        similares: list[SolicitudDTO] = []
        for existente in existentes:
            try:
                existente_inicio, existente_fin = normalize_range(
                    completo=existente.completo,
                    desde_min=existente.desde_min,
                    hasta_min=existente.hasta_min,
                )
            except ValidacionError:
                continue
            if overlaps(nuevo_inicio, nuevo_fin, existente_inicio, existente_fin):
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
        if is_read_only_enabled():
            raise BusinessRuleError("Modo solo lectura activado")
        correlation_id = resolver_correlation_id(correlation_id, contexto)
        if correlation_id:
            log_event(
                logger,
                "solicitud_delete_started",
                {"solicitud_id": solicitud_id},
                correlation_id,
            )
        solicitud = self._repo.get_by_id(solicitud_id)
        if solicitud is None:
            raise BusinessRuleError("Solicitud no encontrada.")
        self._repo.delete(solicitud_id)
        year, month = _parse_year_month(solicitud.fecha_pedida)
        if correlation_id:
            log_event(
                logger,
                "solicitud_delete_succeeded",
                {"solicitud_id": solicitud_id},
                correlation_id,
            )
        return self.calcular_saldos(solicitud.persona_id, year, month)

    def validar_conflicto_dia(
        self, persona_id: int, fecha_pedida: str, tipo_nuevo: bool
    ) -> ConflictoDiaDTO:
        existentes = list(
            self._repo.list_by_persona_and_fecha(persona_id, fecha_pedida)
        )
        return construir_conflicto_dia(existentes, tipo_nuevo)

    def sustituir_por_completo(
        self,
        persona_id: int,
        fecha_pedida: str,
        nueva_solicitud: SolicitudDTO,
        correlation_id: str | None = None,
    ) -> tuple[SolicitudDTO, SaldosDTO]:
        validar_tipo_para_sustitucion(
            es_completa=nueva_solicitud.completo, requiere_completa=True
        )
        existentes = list(
            self._repo.list_by_persona_and_fecha(persona_id, fecha_pedida)
        )
        ids = ids_para_sustitucion(existentes, eliminar_completas=False)
        self._repo.delete_by_ids(ids)
        return self.agregar_solicitud(nueva_solicitud, correlation_id=correlation_id)

    def sustituir_por_parcial(
        self,
        persona_id: int,
        fecha_pedida: str,
        nueva_solicitud: SolicitudDTO,
        correlation_id: str | None = None,
    ) -> tuple[SolicitudDTO, SaldosDTO]:
        validar_tipo_para_sustitucion(
            es_completa=nueva_solicitud.completo, requiere_completa=False
        )
        existentes = list(
            self._repo.list_by_persona_and_fecha(persona_id, fecha_pedida)
        )
        ids = ids_para_sustitucion(existentes, eliminar_completas=True)
        self._repo.delete_by_ids(ids)
        return self.agregar_solicitud(nueva_solicitud, correlation_id=correlation_id)

    def sugerir_completo_min(self, persona_id: int, fecha: str) -> int:
        persona = obtener_persona_o_error(self._persona_repo.get_by_id(persona_id))
        total_dia = _total_cuadrante_por_fecha(persona, fecha)
        return sugerir_completo_minutos(total_dia)

    def sumar_pendientes_min(
        self, persona_id: int, solicitudes: Iterable[SolicitudDTO]
    ) -> int:
        persona = obtener_persona_o_error(self._persona_repo.get_by_id(persona_id))
        return sumar_pendientes_minutos(
            solicitudes,
            calcular_minutos=lambda solicitud: _calcular_minutos(solicitud, persona),
        )

    def calcular_minutos_solicitud(self, dto: SolicitudDTO) -> int:
        persona = obtener_persona_o_error(self._persona_repo.get_by_id(dto.persona_id))
        return _calcular_minutos(dto, persona)

    def minutes_to_hours_float(self, minutos: int) -> float:
        return minutes_to_hours_float(minutos)

    def detectar_conflictos_pendientes(
        self, solicitudes: Iterable[SolicitudDTO]
    ) -> set[int]:
        return detectar_conflictos_pendientes_con_resolutor(
            solicitudes,
            resolver_persona=lambda persona_id: obtener_persona_o_error(
                self._persona_repo.get_by_id(persona_id)
            ),
            total_cuadrante_por_fecha=_total_cuadrante_por_fecha,
        )

    def sugerir_nombre_pdf(self, solicitudes: Iterable[SolicitudDTO]) -> str:
        solicitudes_list = list(solicitudes)
        if not solicitudes_list:
            return NOMBRE_PDF_POR_DEFECTO
        persona = obtener_persona_o_error(
            self._persona_repo.get_by_id(solicitudes_list[0].persona_id)
        )
        fechas = [solicitud.fecha_pedida for solicitud in solicitudes_list]
        try:
            return self._servicio_preflight_pdf.construir_nombre_pdf(
                EntradaNombrePdf(nombre_persona=persona.nombre, fechas=tuple(fechas))
            )
        except ValueError as exc:
            raise BusinessRuleError(str(exc)) from exc

    def resolver_destino_pdf(
        self,
        destino: Path,
        *,
        overwrite: bool = False,
        auto_rename: bool = True,
    ) -> ResolucionDestinoPdf:
        if hasattr(self._fs, "resolver_colision_archivo"):
            resolver_colision = resolver_ruta_sin_colision
        else:

            def resolver_colision(ruta: Path) -> Path:
                return resolver_colision_pdf(ruta, self._fs)

        ruta_destino, colision_detectada, ruta_original, ruta_alternativa = (
            resolver_destino_pdf_helper(
                destino,
                overwrite=overwrite,
                auto_rename=auto_rename,
                resolver_ruta_colision=resolver_colision,
            )
        )

        return ResolucionDestinoPdf(
            ruta_destino=ruta_destino,
            colision_detectada=colision_detectada,
            ruta_original=ruta_original,
            ruta_alternativa=ruta_alternativa if colision_detectada else None,
        )

    def confirmar_lote_y_generar_pdf(
        self,
        solicitudes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str], Path | None]:
        if is_read_only_enabled():
            raise BusinessRuleError("Modo solo lectura activado")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        return confirmar_lote_y_generar_pdf_orquestado(
            solicitudes=solicitudes,
            destino=destino,
            resolver_destino_pdf=self.resolver_destino_pdf,
            fs=self._fs,
            generador_pdf=self._generador_pdf,
            validar_solicitud=validar_solicitud_dto_declarativo,
            confirmar_solicitudes_lote=self._confirmar_solicitudes_lote,
            generar_pdf_confirmadas=self._generar_pdf_confirmadas,
            logger=logger,
            correlation_id=correlation_id,
        )

    def _confirmar_solicitudes_lote(
        self, solicitudes: list[SolicitudDTO], *, correlation_id: str | None
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]:
        return confirmar_solicitudes_lote_orquestado(
            solicitudes=solicitudes,
            resolver_o_crear=self._resolver_o_crear_solicitud,
            confirmar_lote_con_manejador=confirmar_solicitudes_lote_con_manejador,
            generar_incident_id=_generar_incident_id,
            logger=logger,
            correlation_id=correlation_id,
        )

    def _resolver_o_crear_solicitud(
        self, solicitud: SolicitudDTO, *, correlation_id: str | None
    ) -> SolicitudDTO:
        return resolver_o_crear_solicitud_orquestado(
            solicitud,
            correlation_id=correlation_id,
            get_by_id=self._repo.get_by_id,
            solicitud_to_dto=_solicitud_to_dto,
            agregar_solicitud=self.agregar_solicitud,
        )

    def _generar_pdf_confirmadas(
        self, creadas: list[SolicitudDTO], destino: Path, *, correlation_id: str | None
    ) -> tuple[Path | None, list[SolicitudDTO]]:
        """Genera y persiste PDF de solicitudes confirmadas."""
        return generar_pdf_confirmadas_orquestado(
            creadas=creadas,
            destino=destino,
            config_repo=self._config_repo,
            persona_repo=self._persona_repo,
            generador_pdf=self._generador_pdf,
            repo=self._repo,
            pdf_intro_text=_pdf_intro_text,
            hash_file=_hash_file,
            generar_incident_id=_generar_incident_id,
            planificador_pdf=plan_pdf_confirmadas,
            runner_pdf=run_pdf_confirmadas_plan,
            logger=logger,
            correlation_id=correlation_id,
        )

    def confirmar_sin_pdf(
        self,
        solicitudes: Iterable[SolicitudDTO],
        correlation_id: str | None = None,
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str]]:
        if is_read_only_enabled():
            raise BusinessRuleError("Modo solo lectura activado")
        return confirmar_sin_pdf_orquestado(
            solicitudes=solicitudes,
            planner=plan_confirmar_sin_pdf,
            run_action=self._run_confirmar_sin_pdf_action,
            confirmar_sin_pdf_con_manejador=confirmar_sin_pdf_con_manejador,
            logger=logger,
            correlation_id=correlation_id,
        )

    def _run_confirmar_sin_pdf_action(
        self, action, *, correlation_id: str | None
    ) -> SolicitudDTO:
        return run_confirmar_sin_pdf_action_orquestado(
            action,
            correlation_id=correlation_id,
            ejecutar_confirmar_sin_pdf_action=ejecutar_confirmar_sin_pdf_action,
            get_by_id=self._repo.get_by_id,
            solicitud_to_dto=_solicitud_to_dto,
            agregar_solicitud=self.agregar_solicitud,
            marcar_generada=lambda solicitud_id: self._repo.mark_generated(
                solicitud_id, True
            ),
        )

    def confirmar_y_generar_pdf(
        self,
        solicitudes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> tuple[list[SolicitudDTO], list[SolicitudDTO], list[str], Path | None]:
        return self.confirmar_lote_y_generar_pdf(
            solicitudes, destino, correlation_id=correlation_id
        )

    def confirmar_y_generar_pdf_por_filtro(
        self,
        *,
        filtro_delegada: int | None,
        pendientes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> tuple[Path | None, list[int], str]:
        seleccionadas, modo = seleccionar_solicitudes_por_filtro(
            pendientes, filtro_delegada
        )
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
        resumen = resumen_confirmacion_pdf(creadas, errores, modo)
        return ruta, ids_confirmadas, resumen

    def generar_pdf_historico(
        self,
        solicitudes: Iterable[SolicitudDTO],
        destino: Path,
        correlation_id: str | None = None,
    ) -> Path:
        return generar_pdf_historico_orquestado(
            solicitudes=solicitudes,
            destino=destino,
            correlation_id=correlation_id,
            persona_repo=self._persona_repo,
            config_repo=self._config_repo,
            fs=self._fs,
            generador_pdf=self._generador_pdf,
            obtener_persona_o_error=obtener_persona_o_error,
            solicitud_to_dto=_solicitud_to_dto,
            ejecutar_exportacion_pdf_historico=ejecutar_exportacion_pdf_historico,
            pdf_intro_text=_pdf_intro_text,
            logger=logger,
        )

    def exportar_historico_pdf(
        self,
        persona_id: int,
        filtro: PeriodoFiltro,
        destino: Path,
        correlation_id: str | None = None,
    ) -> Path:
        return exportar_historico_pdf_orquestado(
            persona_id=persona_id,
            filtro=filtro,
            destino=destino,
            correlation_id=correlation_id,
            persona_repo=self._persona_repo,
            repo=self._repo,
            config_repo=self._config_repo,
            fs=self._fs,
            generador_pdf=self._generador_pdf,
            obtener_persona_o_error=obtener_persona_o_error,
            solicitud_to_dto=_solicitud_to_dto,
            ejecutar_exportacion_pdf_historico=ejecutar_exportacion_pdf_historico,
            pdf_intro_text=_pdf_intro_text,
            logger=logger,
        )

    def sugerir_nombre_pdf_historico(self, filtro: PeriodoFiltro) -> str:
        return _sugerir_nombre_pdf_historico(filtro)

    def calcular_totales_globales(self, filtro: PeriodoFiltro) -> TotalesGlobalesDTO:
        personas = list(self._persona_repo.list_all())
        return calcular_totales_globales_desde_fuentes(
            filtro=filtro,
            personas=personas,
            listar_consumos=lambda persona_id, year, month: [
                solicitud.horas_solicitadas_min
                for solicitud in self._repo.list_by_persona_and_period(
                    persona_id, year, month
                )
            ],
            sumar_consumo=_sumar_consumo_solicitudes,
            calcular_totales=_calcular_totales_globales,
        )

    def calcular_resumen_saldos(
        self, persona_id: int, filtro: PeriodoFiltro
    ) -> ResumenSaldosDTO:
        persona = obtener_persona_o_error(self._persona_repo.get_by_id(persona_id))
        personas = list(self._persona_repo.list_all())
        config = self._config_repo.get() if self._config_repo else None
        bolsa_grupo = config.bolsa_anual_grupo_min if config else 0
        return calcular_resumen_saldos_desde_fuentes(
            persona=persona,
            persona_id=persona_id,
            filtro=filtro,
            listar_periodo=self._repo.list_by_persona_and_period,
            sumar_consumo=_sumar_consumo_solicitudes,
            acumular_consumo_anual=_acumular_consumo_anual_por_personas,
            bolsa_grupo=bolsa_grupo,
            personas=personas,
            construir_resumen=_construir_resumen_saldos,
        )
