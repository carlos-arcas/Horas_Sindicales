from __future__ import annotations

from dataclasses import replace
import logging

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

        duplicate = w._solicitud_use_cases.buscar_duplicado(solicitud)
        if duplicate is not None and not w._handle_duplicate_detected(duplicate):
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
                creada, _ = w._solicitud_use_cases.agregar_solicitud(
                    solicitud,
                    correlation_id=operation.correlation_id,
                    contexto=operation_ctx,
                )
                log_event(logger, "agregar_pendiente_succeeded", {}, operation.correlation_id)
            w._reload_pending_views()
        except (ValidacionError, BusinessRuleError) as exc:
            w.notifications.notify_validation_error(
                what="No se guardó la solicitud.",
                why=f"{str(exc)}.",
                how="Corrige el formulario y vuelve a pulsar 'Añadir a pendientes'.",
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
