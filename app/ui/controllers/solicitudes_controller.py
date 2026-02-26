from __future__ import annotations

from dataclasses import replace
import logging
from pathlib import Path

from app.application.dto import SolicitudDTO

from app.application.dtos.contexto_operacion import ContextoOperacion
from app.core.observability import OperationContext, log_event
from app.domain.services import BusinessRuleError, ValidacionError

logger = logging.getLogger(__name__)


class SolicitudesController:
    def __init__(self, window) -> None:
        self.window = window

    def on_add_pendiente(self) -> None:
        w = self.window
        logger.info("Botón Agregar pulsado en pantalla de Peticiones")
        solicitud = w._build_preview_solicitud()
        if solicitud is None:
            w.notifications.notify_validation_error(
                what="No se puede añadir la solicitud.",
                why="Falta seleccionar una delegada.",
                how="Selecciona una delegada en Configuración y vuelve a intentarlo.",
            )
            return

        pendiente_en_edicion = w._selected_pending_for_editing()

        duplicate = w._solicitud_use_cases.buscar_duplicado(solicitud)
        if duplicate is not None and (pendiente_en_edicion is None or duplicate.id != pendiente_en_edicion.id):
            if not w._handle_duplicate_detected(duplicate):
                return

        try:
            minutos = w._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
        except (ValidacionError, BusinessRuleError) as exc:
            w.notifications.notify_validation_error(
                what="No se puede añadir la solicitud.",
                why=f"{str(exc)}.",
                how="Revisa fecha/tramo y corrige los campos marcados.",
            )
            if not solicitud.completo:
                w.desde_input.setFocus()
            return
        except Exception as exc:  # pragma: no cover - fallback
            logger.error("Error calculando minutos de la petición", exc_info=True)
            w._show_critical_error(exc)
            return

        notas_text = w.notas_input.toPlainText().strip()
        solicitud = replace(
            solicitud,
            horas=w._solicitud_use_cases.minutes_to_hours_float(minutos),
            notas=notas_text or None,
        )

        if not w._resolve_backend_conflict(solicitud.persona_id, solicitud):
            return

        try:
            w._set_processing_state(True)
            build_context = getattr(w.notifications, "build_operation_context", None)
            operation_ctx = build_context() if callable(build_context) else ContextoOperacion.nuevo()
            if not isinstance(operation_ctx, ContextoOperacion):
                operation_ctx = ContextoOperacion.nuevo()
            with OperationContext(
                "agregar_pendiente",
                correlation_id=operation_ctx.correlation_id,
                result_id=operation_ctx.result_id,
            ) as operation:
                log_event(
                    logger,
                    "agregar_pendiente_started",
                    {"persona_id": solicitud.persona_id, "fecha_pedida": solicitud.fecha_pedida},
                    operation.correlation_id,
                )
                if pendiente_en_edicion is not None and pendiente_en_edicion.id is not None:
                    w._solicitud_use_cases.eliminar_solicitud(
                        pendiente_en_edicion.id,
                        correlation_id=operation.correlation_id,
                    )
                resultado = w._solicitud_use_cases.crear_resultado(
                    solicitud,
                    correlation_id=operation.correlation_id,
                    contexto=operation_ctx,
                )
                if not resultado.success:
                    raise BusinessRuleError(resultado.errores[0] if resultado.errores else "No se pudo guardar la solicitud.")
                creada = resultado.entidad
                if creada is None:
                    raise BusinessRuleError("No se pudo guardar la solicitud.")
                if resultado.warnings:
                    w.toast.info("\n".join(resultado.warnings), title="Solicitud registrada con advertencias")
                log_event(logger, "agregar_pendiente_succeeded", {}, operation.correlation_id)
            w._reload_pending_views()
        except (ValidacionError, BusinessRuleError) as exc:
            w.notifications.notify_validation_error(
                what="No se guardó la solicitud.",
                why=f"{str(exc)}.",
                how="Corrige el formulario y vuelve a pulsar 'Añadir pendiente'.",
            )
            return
        except Exception as exc:  # pragma: no cover - fallback
            log_event(logger, "agregar_pendiente_failed", {"error": str(exc)}, operation.correlation_id)
            logger.error("Error insertando petición en base de datos", exc_info=True)
            w._show_critical_error(exc)
            return
        finally:
            w._set_processing_state(False)

        w.notas_input.setPlainText("")
        w._refresh_historico()
        w._refresh_saldos()
        w._update_action_state()
        w.notifications.notify_added_pending(creada, on_undo=lambda: w._undo_last_added_pending(creada.id))
        if pendiente_en_edicion is not None:
            w.toast.success("Pendiente actualizada", title="Operación completada")

    def refresh_historico(self) -> list[SolicitudDTO]:
        return list(self.window._solicitud_use_cases.listar_historico())

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
                raise ValueError("pdf_path es obligatorio cuando generar_pdf=True")
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
