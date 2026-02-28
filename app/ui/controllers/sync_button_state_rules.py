from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EstadoBotonSyncEntrada:
    """Señales necesarias para decidir el estado de los botones de sincronización."""

    sync_configurado: bool
    sync_en_progreso: bool
    hay_plan_pendiente: bool
    plan_tiene_cambios: bool
    plan_tiene_conflictos: bool
    ultimo_reporte_presente: bool
    ultimo_reporte_tiene_fallos: bool
    conflictos_pendientes_total: int
    texto_sync_actual: str
    tooltip_sync_actual: str


@dataclass(frozen=True)
class DecisionBotonSync:
    """Decisión inmutable para aplicar a un botón sin depender de Qt."""

    enabled: bool
    text: str
    tooltip: str | None
    severity: str | None
    reason_code: str


@dataclass(frozen=True)
class EstadoBotonesSyncDecision:
    """Conjunto de decisiones para todos los botones del panel de sincronización."""

    sync: DecisionBotonSync
    simulate_sync: DecisionBotonSync
    confirm_sync: DecisionBotonSync
    retry_failed: DecisionBotonSync
    review_conflicts: DecisionBotonSync
    sync_details: DecisionBotonSync
    copy_sync_report: DecisionBotonSync



def decidir_estado_botones_sync(entrada: EstadoBotonSyncEntrada) -> EstadoBotonesSyncDecision:
    """Calcula el estado visible de los botones de sincronización.

    Mantiene la UX previa: mismas reglas de enabled y texto para conflictos.
    """

    sync_habilitado = entrada.sync_configurado and not entrada.sync_en_progreso
    if not entrada.sync_configurado:
        razon_sync = "sync_no_configurado"
    elif entrada.sync_en_progreso:
        razon_sync = "sync_en_progreso"
    else:
        razon_sync = "sync_listo"

    decision_sync = DecisionBotonSync(
        enabled=sync_habilitado,
        text=entrada.texto_sync_actual,
        tooltip=entrada.tooltip_sync_actual,
        severity=None,
        reason_code=razon_sync,
    )

    if entrada.sync_en_progreso:
        razon_confirm = "confirm_sync_bloqueado_en_progreso"
    elif not entrada.sync_configurado:
        razon_confirm = "confirm_sync_no_configurado"
    elif not entrada.hay_plan_pendiente:
        razon_confirm = "confirm_sync_sin_plan"
    elif not entrada.plan_tiene_cambios:
        razon_confirm = "confirm_sync_sin_cambios"
    elif entrada.plan_tiene_conflictos:
        razon_confirm = "confirm_sync_conflictos"
    else:
        razon_confirm = "confirm_sync_listo"

    confirm_habilitado = (
        sync_habilitado
        and entrada.hay_plan_pendiente
        and entrada.plan_tiene_cambios
        and not entrada.plan_tiene_conflictos
    )

    retry_habilitado = not entrada.sync_en_progreso and entrada.ultimo_reporte_tiene_fallos
    if entrada.sync_en_progreso:
        razon_retry = "retry_bloqueado_en_progreso"
    elif entrada.ultimo_reporte_tiene_fallos:
        razon_retry = "retry_listo"
    else:
        razon_retry = "retry_sin_fallos"

    review_habilitado = not entrada.sync_en_progreso and entrada.conflictos_pendientes_total > 0
    if entrada.sync_en_progreso:
        razon_review = "review_conflictos_bloqueado_en_progreso"
    elif entrada.conflictos_pendientes_total > 0:
        razon_review = "review_conflictos_pendientes"
    else:
        razon_review = "review_conflictos_sin_pendientes"

    texto_review = (
        "Revisar conflictos"
        if entrada.conflictos_pendientes_total > 0
        else "Revisar conflictos (sin pendientes)"
    )

    detalles_habilitado = not entrada.sync_en_progreso and entrada.ultimo_reporte_presente
    if entrada.sync_en_progreso:
        razon_detalles = "reporte_bloqueado_en_progreso"
    elif entrada.ultimo_reporte_presente:
        razon_detalles = "reporte_listo"
    else:
        razon_detalles = "reporte_no_disponible"

    return EstadoBotonesSyncDecision(
        sync=decision_sync,
        simulate_sync=DecisionBotonSync(
            enabled=sync_habilitado,
            text="",
            tooltip=None,
            severity=None,
            reason_code=razon_sync,
        ),
        confirm_sync=DecisionBotonSync(
            enabled=confirm_habilitado,
            text="",
            tooltip=None,
            severity="warning" if entrada.plan_tiene_conflictos else None,
            reason_code=razon_confirm,
        ),
        retry_failed=DecisionBotonSync(
            enabled=retry_habilitado,
            text="",
            tooltip=None,
            severity=None,
            reason_code=razon_retry,
        ),
        review_conflicts=DecisionBotonSync(
            enabled=review_habilitado,
            text=texto_review,
            tooltip=None,
            severity="warning" if entrada.conflictos_pendientes_total > 0 else None,
            reason_code=razon_review,
        ),
        sync_details=DecisionBotonSync(
            enabled=detalles_habilitado,
            text="",
            tooltip=None,
            severity=None,
            reason_code=razon_detalles,
        ),
        copy_sync_report=DecisionBotonSync(
            enabled=detalles_habilitado,
            text="",
            tooltip=None,
            severity=None,
            reason_code=razon_detalles,
        ),
    )
