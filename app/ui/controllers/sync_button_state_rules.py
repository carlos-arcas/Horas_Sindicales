from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


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


ReglaReasonCode = tuple[Callable[[EstadoBotonSyncEntrada], bool], str]


def _first_matching_reason(
    entrada: EstadoBotonSyncEntrada,
    reglas: tuple[ReglaReasonCode, ...],
    default: str,
) -> str:
    """Devuelve el primer reason_code cuya regla aplique, respetando precedencia."""

    for predicado, reason_code in reglas:
        if predicado(entrada):
            return reason_code
    return default


def _razon_sync(entrada: EstadoBotonSyncEntrada) -> str:
    """Decide el reason_code de sync principal según configuración y progreso."""

    reglas: tuple[ReglaReasonCode, ...] = (
        (lambda e: not e.sync_configurado, "sync_no_configurado"),
        (lambda e: e.sync_en_progreso, "sync_en_progreso"),
    )
    return _first_matching_reason(entrada, reglas, "sync_listo")


def _razon_confirm_sync(entrada: EstadoBotonSyncEntrada) -> str:
    """Decide el reason_code de confirmación respetando el orden histórico."""

    reglas: tuple[ReglaReasonCode, ...] = (
        (lambda e: e.sync_en_progreso, "confirm_sync_bloqueado_en_progreso"),
        (lambda e: not e.sync_configurado, "confirm_sync_no_configurado"),
        (lambda e: not e.hay_plan_pendiente, "confirm_sync_sin_plan"),
        (lambda e: not e.plan_tiene_cambios, "confirm_sync_sin_cambios"),
        (lambda e: e.plan_tiene_conflictos, "confirm_sync_conflictos"),
    )
    return _first_matching_reason(entrada, reglas, "confirm_sync_listo")


def _razon_retry(entrada: EstadoBotonSyncEntrada) -> str:
    """Decide el reason_code de reintento en base a progreso y fallos previos."""

    reglas: tuple[ReglaReasonCode, ...] = (
        (lambda e: e.sync_en_progreso, "retry_bloqueado_en_progreso"),
        (lambda e: e.ultimo_reporte_tiene_fallos, "retry_listo"),
    )
    return _first_matching_reason(entrada, reglas, "retry_sin_fallos")


def _razon_review_conflictos(entrada: EstadoBotonSyncEntrada) -> str:
    """Decide el reason_code de revisión de conflictos por bloqueo y pendientes."""

    reglas: tuple[ReglaReasonCode, ...] = (
        (lambda e: e.sync_en_progreso, "review_conflictos_bloqueado_en_progreso"),
        (lambda e: e.conflictos_pendientes_total > 0, "review_conflictos_pendientes"),
    )
    return _first_matching_reason(entrada, reglas, "review_conflictos_sin_pendientes")


def _razon_reportes(entrada: EstadoBotonSyncEntrada) -> str:
    """Decide el reason_code de acciones de reporte."""

    reglas: tuple[ReglaReasonCode, ...] = (
        (lambda e: e.sync_en_progreso, "reporte_bloqueado_en_progreso"),
        (lambda e: e.ultimo_reporte_presente, "reporte_listo"),
    )
    return _first_matching_reason(entrada, reglas, "reporte_no_disponible")


def _texto_review_conflictos(entrada: EstadoBotonSyncEntrada) -> str:
    """Devuelve el texto visible del botón de conflictos según pendientes."""

    if entrada.conflictos_pendientes_total > 0:
        return "Revisar conflictos"
    return "Revisar conflictos (sin pendientes)"



def decidir_estado_botones_sync(entrada: EstadoBotonSyncEntrada) -> EstadoBotonesSyncDecision:
    """Calcula el estado visible de los botones de sincronización.

    Mantiene la UX previa: mismas reglas de enabled y texto para conflictos.
    """

    sync_habilitado = entrada.sync_configurado and not entrada.sync_en_progreso
    razon_sync = _razon_sync(entrada)

    decision_sync = DecisionBotonSync(
        enabled=sync_habilitado,
        text=entrada.texto_sync_actual,
        tooltip=entrada.tooltip_sync_actual,
        severity=None,
        reason_code=razon_sync,
    )

    razon_confirm = _razon_confirm_sync(entrada)

    confirm_habilitado = (
        sync_habilitado
        and entrada.hay_plan_pendiente
        and entrada.plan_tiene_cambios
        and not entrada.plan_tiene_conflictos
    )

    retry_habilitado = not entrada.sync_en_progreso and entrada.ultimo_reporte_tiene_fallos
    razon_retry = _razon_retry(entrada)

    review_habilitado = not entrada.sync_en_progreso and entrada.conflictos_pendientes_total > 0
    razon_review = _razon_review_conflictos(entrada)
    texto_review = _texto_review_conflictos(entrada)

    detalles_habilitado = not entrada.sync_en_progreso and entrada.ultimo_reporte_presente
    razon_detalles = _razon_reportes(entrada)

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
