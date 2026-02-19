from __future__ import annotations

from dataclasses import replace
import logging

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
            w.toast.warning("Selecciona una delegada antes de agregar una petición.", title="Validación")
            return

        try:
            minutos = w._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
        except (ValidacionError, BusinessRuleError) as exc:
            w.toast.warning(str(exc), title="Validación")
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
            with OperationContext("agregar_pendiente") as operation:
                log_event(
                    logger,
                    "agregar_pendiente_started",
                    {"persona_id": solicitud.persona_id, "fecha_pedida": solicitud.fecha_pedida},
                    operation.correlation_id,
                )
                w._solicitud_use_cases.agregar_solicitud(solicitud, correlation_id=operation.correlation_id)
                log_event(logger, "agregar_pendiente_succeeded", {}, operation.correlation_id)
            w._reload_pending_views()
        except (ValidacionError, BusinessRuleError) as exc:
            w.toast.warning(str(exc), title="Validación")
            return
        except Exception as exc:  # pragma: no cover - fallback
            log_event(logger, "agregar_pendiente_failed", {"error": str(exc)}, operation.correlation_id)
            logger.error("Error insertando petición en base de datos", exc_info=True)
            w._show_critical_error(exc)
            return

        w.notas_input.setPlainText("")
        w._refresh_historico()
        w._refresh_saldos()
        w._update_action_state()
        w.toast.success("Petición añadida a pendientes")
