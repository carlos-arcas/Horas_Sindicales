from __future__ import annotations

from dataclasses import replace
import logging
from pathlib import Path
from time import monotonic

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.crear_pendiente_caso_uso import (
    SolicitudCrearPendientePeticion,
)

from app.application.dtos.contexto_operacion import ContextoOperacion
from app.core.observability import OperationContext, log_event
from app.domain.services import BusinessRuleError, ValidacionError
from app.ui.toast_helpers import toast_success

logger = logging.getLogger(__name__)


def _normalizar_inputs_pendiente(
    solicitud: SolicitudDTO,
    *,
    horas: float,
    notas_texto: str | None,
) -> SolicitudDTO:
    notas_limpias = (notas_texto or "").strip() or None
    return replace(solicitud, horas=horas, notas=notas_limpias)


def _construir_peticion_crear_pendiente(
    solicitud: SolicitudDTO,
    correlation_id: str,
) -> SolicitudCrearPendientePeticion:
    return SolicitudCrearPendientePeticion(
        solicitud=solicitud,
        correlation_id=correlation_id,
    )


def _mapear_error_persistencia_a_feedback(exc: Exception) -> tuple[str, str, str]:
    return (
        "ui.solicitudes.no_se_guardo",
        f"{str(exc)}.",
        "ui.solicitudes.corrige_formulario",
    )


class SolicitudesController:
    _CONFLICT_DEBOUNCE_MS = 800

    def __init__(self, window) -> None:
        self.window = window
        self._last_conflict_toast: tuple[int, str, float] | None = None

    def on_add_pendiente(self) -> None:
        w = self.window
        logger.info("UI_ADD_PENDING_START")
        try:
            solicitud = w._build_preview_solicitud()
            solicitud, pendiente_en_edicion = self._validate_inputs(solicitud)
            if solicitud is None:
                return

            if not self._handle_duplicate(solicitud, pendiente_en_edicion):
                return

            solicitud = self._persist_pendiente(solicitud, pendiente_en_edicion)
            if solicitud is None:
                return

            self._update_ui_after_add(solicitud, pendiente_en_edicion)
            logger.info("UI_ADD_PENDING_OK", extra={"solicitud_id": solicitud.id})
        except Exception:
            logger.exception("UI_ADD_PENDING_EXCEPTION")
            raise

    def _validate_inputs(self, solicitud: SolicitudDTO | None) -> tuple[SolicitudDTO | None, SolicitudDTO | None]:
        w = self.window
        if solicitud is None:
            logger.info("UI_ADD_PENDING_VALIDATION_ERROR", extra={"motivo": "solicitud_preview_none"})
            w.notifications.notify_validation_error(
                what=self._copy("ui.solicitudes.no_puede_aniadir"),
                why=self._copy("ui.solicitudes.falta_delegada"),
                how=self._copy("ui.solicitudes.selecciona_delegada"),
            )
            return None, None
        return solicitud, w._selected_pending_for_editing()

    def _handle_duplicate(self, solicitud: SolicitudDTO, pendiente_en_edicion: SolicitudDTO | None) -> bool:
        w = self.window
        logger.info(
            "buscar_conflicto_pendiente_start",
            extra={
                "persona_id": solicitud.persona_id,
                "fecha_pedida": solicitud.fecha_pedida,
                "desde": solicitud.desde,
                "hasta": solicitud.hasta,
                "completo": solicitud.completo,
                "pendiente_edicion_id": getattr(pendiente_en_edicion, "id", None),
            },
        )
        conflicto = w._solicitud_use_cases.buscar_conflicto_pendiente(
            solicitud,
            excluir_solicitud_id=getattr(pendiente_en_edicion, "id", None),
        )
        if conflicto is not None:
            logger.info(
                "buscar_conflicto_pendiente_detectado",
                extra={
                    "tipo": getattr(conflicto, "tipo", None),
                    "id_existente": getattr(conflicto, "id_existente", None),
                    "fecha": getattr(conflicto, "fecha", None),
                    "desde": getattr(conflicto, "desde", None),
                    "hasta": getattr(conflicto, "hasta", None),
                    "completo": getattr(conflicto, "completo", None),
                },
            )
            return self._handle_conflict_detected(conflicto)
        return True

    def _handle_conflict_detected(self, conflicto: object) -> bool:
        tipo = str(getattr(conflicto, "tipo", "")).upper()
        id_existente = getattr(conflicto, "id_existente", None)
        if not isinstance(id_existente, int) or not tipo:
            logger.warning("conflict_toast_missing_payload", extra={"tipo": tipo, "id_existente": id_existente})
            return self.window._handle_duplicate_detected(conflicto)

        ahora_ms = monotonic() * 1000
        if self._is_debounced(id_existente=id_existente, tipo=tipo, timestamp_ms=ahora_ms):
            logger.info("conflict_toast_debounced", extra={"tipo": tipo, "id_existente": id_existente})
            return False

        title = self._copy("ui.conflictos.titulo_revisa_formulario", fallback="")
        message_key = "ui.conflictos.duplicado_mensaje" if tipo == "DUPLICADO" else "ui.conflictos.solape_mensaje"
        message_template = self._copy(message_key)
        message = message_template.format(
            id=id_existente,
            fecha=getattr(conflicto, "fecha", "-"),
            desde=getattr(conflicto, "desde", "-"),
            hasta=getattr(conflicto, "hasta", "-"),
            completo=getattr(conflicto, "completo", False),
        )
        action_label = self._copy("ui.conflictos.boton_ver_registro", fallback="")
        self.window.toast.warning(
            message,
            title=title,
            action_label=action_label,
            action_callback=lambda: self.window.ir_a_pendiente_existente(id_existente),
        )
        self._last_conflict_toast = (id_existente, tipo, ahora_ms)
        return False

    def _copy(self, key: str, fallback: str | None = None) -> str:
        translate = getattr(self.window, "_t", None)
        if callable(translate):
            translated = translate(key)
            if isinstance(translated, str) and translated.strip():
                return translated
        translated = getattr(self.window, "copy_text", None)
        if callable(translated):
            value = translated(key)
            if isinstance(value, str) and value.strip():
                return value
        try:
            from app.ui.copy_catalog import copy_text

            value = copy_text(key)
            if isinstance(value, str) and value.strip():
                return value
        except Exception:  # pragma: no cover - defensive
            logger.warning("copy_text_resolution_failed", extra={"key": key}, exc_info=True)
        return fallback if fallback is not None else key

    def _is_debounced(self, *, id_existente: int, tipo: str, timestamp_ms: float) -> bool:
        if self._last_conflict_toast is None:
            return False
        last_id, last_tipo, last_ts = self._last_conflict_toast
        return last_id == id_existente and last_tipo == tipo and (timestamp_ms - last_ts) < self._CONFLICT_DEBOUNCE_MS

    def _persist_pendiente(
        self,
        solicitud: SolicitudDTO,
        pendiente_en_edicion: SolicitudDTO | None,
    ) -> SolicitudDTO | None:
        w = self.window

        solicitud_normalizada = self._calcular_y_normalizar_pendiente(solicitud)
        if solicitud_normalizada is None:
            return None

        if not w._resolve_backend_conflict(solicitud_normalizada.persona_id, solicitud_normalizada):
            logger.info(
                "backend_conflict_abort",
                extra={
                    "persona_id": solicitud_normalizada.persona_id,
                    "fecha_pedida": solicitud_normalizada.fecha_pedida,
                },
            )
            return None

        operation_correlation_id = ContextoOperacion.nuevo().correlation_id
        try:
            w._set_processing_state(True)
            operation_ctx = self._crear_contexto_operacion()
            operation_correlation_id = operation_ctx.correlation_id
            with OperationContext(
                "agregar_pendiente",
                correlation_id=operation_ctx.correlation_id,
                result_id=operation_ctx.result_id,
            ) as operation:
                log_event(
                    logger,
                    "crear_pendiente_started",
                    {
                        "persona_id": solicitud_normalizada.persona_id,
                        "fecha_pedida": solicitud_normalizada.fecha_pedida,
                    },
                    operation.correlation_id,
                )
                creada, warnings = self._ejecutar_creacion_pendiente(
                    solicitud_normalizada,
                    pendiente_en_edicion,
                    operation_ctx,
                    operation.correlation_id,
                )
                if warnings:
                    w.toast.info(
                        "\n".join(warnings),
                        title=self._copy("ui.solicitudes.solicitud_con_advertencias"),
                    )
                log_event(
                    logger,
                    "crear_pendiente_finished",
                    {"solicitud_id": creada.id, "ok": True},
                    operation.correlation_id,
                )
        except (ValidacionError, BusinessRuleError) as exc:
            logger.info("UI_ADD_PENDING_VALIDATION_ERROR", extra={"motivo": str(exc)})
            what_key, why, how_key = _mapear_error_persistencia_a_feedback(exc)
            w.notifications.notify_validation_error(
                what=self._copy(what_key),
                why=why,
                how=self._copy(how_key),
            )
            return None
        except Exception as exc:  # pragma: no cover - fallback
            logger.error("UI_ADD_PENDING_EXCEPTION", extra={"error": str(exc)}, exc_info=True)
            log_event(
                logger,
                "crear_pendiente_finished",
                {"error": str(exc), "ok": False},
                operation_correlation_id,
            )
            logger.error("Error insertando petición en base de datos", exc_info=True)
            w._show_critical_error(exc)
            return None
        finally:
            w._set_processing_state(False)

        return creada

    def _calcular_y_normalizar_pendiente(self, solicitud: SolicitudDTO) -> SolicitudDTO | None:
        w = self.window
        try:
            minutos = w._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
        except (ValidacionError, BusinessRuleError) as exc:
            w.notifications.notify_validation_error(
                what=self._copy("ui.solicitudes.no_puede_aniadir"),
                why=f"{str(exc)}.",
                how=self._copy("ui.solicitudes.revisa_formulario"),
            )
            if not solicitud.completo:
                w.desde_input.setFocus()
            return None
        except Exception as exc:  # pragma: no cover - fallback
            logger.error("Error calculando minutos de la petición", exc_info=True)
            w._show_critical_error(exc)
            return None

        horas = w._solicitud_use_cases.minutes_to_hours_float(minutos)
        notas_texto = w.notas_input.toPlainText()
        return _normalizar_inputs_pendiente(solicitud, horas=horas, notas_texto=notas_texto)

    def _crear_contexto_operacion(self) -> ContextoOperacion:
        build_context = getattr(self.window.notifications, "build_operation_context", None)
        operation_ctx = build_context() if callable(build_context) else ContextoOperacion.nuevo()
        return operation_ctx if isinstance(operation_ctx, ContextoOperacion) else ContextoOperacion.nuevo()

    def _ejecutar_creacion_pendiente(
        self,
        solicitud: SolicitudDTO,
        pendiente_en_edicion: SolicitudDTO | None,
        operation_ctx: ContextoOperacion,
        correlation_id: str,
    ) -> tuple[SolicitudDTO, list[str]]:
        w = self.window
        if pendiente_en_edicion is not None and pendiente_en_edicion.id is not None:
            w._solicitud_use_cases.eliminar_solicitud(
                pendiente_en_edicion.id,
                correlation_id=correlation_id,
            )

        logger.info(
            "persist_start",
            extra={"persona_id": solicitud.persona_id, "fecha_pedida": solicitud.fecha_pedida},
        )
        crear_pendiente_caso_uso = getattr(w, "_crear_pendiente_caso_uso", None)
        if crear_pendiente_caso_uso is None:
            return self._crear_desde_use_case_legacy(solicitud, operation_ctx, correlation_id)
        return self._crear_desde_caso_uso_dedicado(solicitud, correlation_id)

    def _crear_desde_use_case_legacy(
        self,
        solicitud: SolicitudDTO,
        operation_ctx: ContextoOperacion,
        correlation_id: str,
    ) -> tuple[SolicitudDTO, list[str]]:
        resultado = self.window._solicitud_use_cases.crear_resultado(
            solicitud,
            correlation_id=correlation_id,
            contexto=operation_ctx,
        )
        if not resultado.success:
            logger.warning(
                "crear_resultado_failed",
                extra={
                    "reason_code": getattr(resultado, "reason_code", None),
                    "errores": list(getattr(resultado, "errores", []) or []),
                },
            )
            raise BusinessRuleError(resultado.errores[0] if resultado.errores else self._copy("ui.solicitudes.no_pudo_guardar"))
        if resultado.entidad is None:
            raise BusinessRuleError(self._copy("ui.solicitudes.no_pudo_guardar"))
        return resultado.entidad, resultado.warnings

    def _crear_desde_caso_uso_dedicado(
        self,
        solicitud: SolicitudDTO,
        correlation_id: str,
    ) -> tuple[SolicitudDTO, list[str]]:
        crear_pendiente_caso_uso = self.window._crear_pendiente_caso_uso
        resultado_creacion = crear_pendiente_caso_uso.execute(
            _construir_peticion_crear_pendiente(solicitud, correlation_id)
        )
        if resultado_creacion.errores:
            raise BusinessRuleError(resultado_creacion.errores[0])
        if resultado_creacion.solicitud_creada is None:
            raise BusinessRuleError(self._copy("ui.solicitudes.no_pudo_guardar"))
        return resultado_creacion.solicitud_creada, []

    def _update_ui_after_add(self, creada: SolicitudDTO, pendiente_en_edicion: SolicitudDTO | None) -> None:
        w = self.window
        w._reload_pending_views()
        actualizar_totales = getattr(w, "_update_pending_totals", None)
        if callable(actualizar_totales):
            actualizar_totales()
        refrescar_contexto_global = getattr(w, "_update_global_context", None)
        if callable(refrescar_contexto_global):
            refrescar_contexto_global()
        w.notas_input.setPlainText("")
        w._solicitudes_last_action_saved = True
        w._solicitudes_runtime_error = False
        w._refresh_historico()
        refrescar_operativa = getattr(w, "_refrescar_estado_operativa", None)
        if callable(refrescar_operativa):
            refrescar_operativa("pendiente_added")
        else:
            w._refresh_saldos()
            w._update_action_state()
        w.notifications.notify_added_pending(creada, on_undo=lambda: w._undo_last_added_pending(creada.id))
        if pendiente_en_edicion is not None:
            toast_success(
                w.toast,
                self._copy("ui.solicitudes.pendiente_actualizada"),
                title=self._copy("ui.solicitudes.operacion_completada"),
            )

    def refresh_historico(self) -> list[SolicitudDTO]:
        return list(self.window._solicitud_use_cases.listar_historico())


    def resolver_destino_pdf_confirmacion(
        self,
        pdf_path: str,
        *,
        overwrite: bool = False,
        auto_rename: bool = True,
    ) -> Path:
        resolucion = self.window._solicitud_use_cases.resolver_destino_pdf(
            Path(pdf_path),
            overwrite=overwrite,
            auto_rename=auto_rename,
        )
        return resolucion.ruta_destino

    def obtener_resolucion_destino_pdf(self, pdf_path: str):
        return self.window._solicitud_use_cases.resolver_destino_pdf(
            Path(pdf_path),
            overwrite=False,
            auto_rename=False,
        )

    def confirmar_lote(
        self,
        pendientes_actuales: list[SolicitudDTO],
        *,
        correlation_id: str | None,
        generar_pdf: bool,
        pdf_path: str | None = None,
        filtro_delegada: int | None = None,
    ) -> tuple[list[int], list[str], Path | None, list[SolicitudDTO], list[SolicitudDTO] | None]:
        if generar_pdf:
            if not pdf_path:
                raise ValueError(self._copy("ui.solicitudes.pdf_path_obligatorio"))
            ruta, confirmadas_ids, resumen = self.window._solicitud_use_cases.confirmar_y_generar_pdf_por_filtro(
                filtro_delegada=filtro_delegada,
                pendientes=pendientes_actuales,
                destino=Path(pdf_path),
                correlation_id=correlation_id,
            )
            errores = [] if confirmadas_ids else [resumen]
            confirmadas = [sol for sol in pendientes_actuales if sol.id in set(confirmadas_ids)]
            pendientes_restantes = aplicar_confirmacion(pendientes_actuales, confirmadas_ids)
            return confirmadas_ids, errores, ruta, confirmadas, pendientes_restantes

        creadas, _pendientes_restantes, errores = self.window._solicitud_use_cases.confirmar_sin_pdf(
            pendientes_actuales,
            correlation_id=correlation_id,
        )
        confirmadas_ids = [sol.id for sol in creadas if sol.id is not None]
        return confirmadas_ids, errores, None, creadas, _pendientes_restantes

    def aplicar_confirmacion(
        self,
        confirmadas_ids: list[int],
        pendientes_restantes: list[SolicitudDTO] | None,
    ) -> None:
        w = self.window
        if pendientes_restantes is not None:
            restantes_ids = {sol.id for sol in pendientes_restantes if sol.id is not None}
            w._pending_solicitudes = list(pendientes_restantes)
            w._pending_all_solicitudes = [
                sol for sol in w._pending_all_solicitudes if sol.id is None or sol.id in restantes_ids
            ]
            w._hidden_pendientes = [
                sol for sol in w._hidden_pendientes if sol.id is None or sol.id in restantes_ids
            ]
            w._orphan_pendientes = [
                sol for sol in w._orphan_pendientes if sol.id is None or sol.id in restantes_ids
            ]
            return

        w._pending_all_solicitudes = aplicar_confirmacion(w._pending_all_solicitudes, confirmadas_ids)
        w._pending_solicitudes = aplicar_confirmacion(w._pending_solicitudes, confirmadas_ids)
        w._hidden_pendientes = aplicar_confirmacion(w._hidden_pendientes, confirmadas_ids)
        w._orphan_pendientes = aplicar_confirmacion(w._orphan_pendientes, confirmadas_ids)


def aplicar_confirmacion(pendientes: list[SolicitudDTO], confirmadas_ids: list[int]) -> list[SolicitudDTO]:
    confirmadas_set = set(confirmadas_ids)
    return [solicitud for solicitud in pendientes if solicitud.id is None or solicitud.id not in confirmadas_set]
