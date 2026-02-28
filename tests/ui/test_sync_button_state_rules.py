from __future__ import annotations

import pytest

from app.ui.controllers.sync_button_state_rules import (
    EstadoBotonSyncEntrada,
    decidir_estado_botones_sync,
)


pytestmark = pytest.mark.headless_safe


def _entrada_base(**overrides) -> EstadoBotonSyncEntrada:
    base = dict(
        sync_configurado=True,
        sync_en_progreso=False,
        hay_plan_pendiente=True,
        plan_tiene_cambios=True,
        plan_tiene_conflictos=False,
        ultimo_reporte_presente=True,
        ultimo_reporte_tiene_fallos=False,
        conflictos_pendientes_total=0,
        texto_sync_actual="Sincronizar",
        tooltip_sync_actual="Listo para sincronizar",
    )
    base.update(overrides)
    return EstadoBotonSyncEntrada(**base)


@pytest.mark.parametrize(
    ("overrides", "enabled", "reason_code"),
    [
        ({}, True, "sync_listo"),
        ({"sync_configurado": False}, False, "sync_no_configurado"),
        ({"sync_en_progreso": True}, False, "sync_en_progreso"),
        ({"sync_configurado": False, "sync_en_progreso": True}, False, "sync_no_configurado"),
        ({"texto_sync_actual": "Actualizar"}, True, "sync_listo"),
        ({"tooltip_sync_actual": "Manual"}, True, "sync_listo"),
    ],
)
def test_decidir_estado_sync(overrides: dict, enabled: bool, reason_code: str) -> None:
    decision = decidir_estado_botones_sync(_entrada_base(**overrides))

    assert decision.sync.enabled is enabled
    assert decision.sync.reason_code == reason_code


@pytest.mark.parametrize(
    ("overrides", "enabled", "reason_code", "severity"),
    [
        ({}, True, "confirm_sync_listo", None),
        ({"sync_en_progreso": True}, False, "confirm_sync_bloqueado_en_progreso", None),
        ({"sync_configurado": False}, False, "confirm_sync_no_configurado", None),
        ({"hay_plan_pendiente": False}, False, "confirm_sync_sin_plan", None),
        ({"plan_tiene_cambios": False}, False, "confirm_sync_sin_cambios", None),
        ({"plan_tiene_conflictos": True}, False, "confirm_sync_conflictos", "warning"),
        (
            {
                "sync_configurado": False,
                "hay_plan_pendiente": False,
                "plan_tiene_cambios": False,
                "plan_tiene_conflictos": True,
            },
            False,
            "confirm_sync_no_configurado",
            "warning",
        ),
        (
            {
                "sync_en_progreso": True,
                "hay_plan_pendiente": False,
                "plan_tiene_cambios": False,
                "plan_tiene_conflictos": True,
            },
            False,
            "confirm_sync_bloqueado_en_progreso",
            "warning",
        ),
    ],
)
def test_decidir_estado_confirm_sync(
    overrides: dict,
    enabled: bool,
    reason_code: str,
    severity: str | None,
) -> None:
    decision = decidir_estado_botones_sync(_entrada_base(**overrides))

    assert decision.confirm_sync.enabled is enabled
    assert decision.confirm_sync.reason_code == reason_code
    assert decision.confirm_sync.severity == severity


@pytest.mark.parametrize(
    ("overrides", "retry_enabled", "retry_reason"),
    [
        ({}, False, "retry_sin_fallos"),
        ({"ultimo_reporte_tiene_fallos": True}, True, "retry_listo"),
        ({"ultimo_reporte_presente": False}, False, "retry_sin_fallos"),
        ({"sync_en_progreso": True, "ultimo_reporte_tiene_fallos": True}, False, "retry_bloqueado_en_progreso"),
        ({"sync_en_progreso": True, "ultimo_reporte_tiene_fallos": False}, False, "retry_bloqueado_en_progreso"),
        ({"sync_configurado": False, "ultimo_reporte_tiene_fallos": True}, True, "retry_listo"),
    ],
)
def test_decidir_estado_retry(overrides: dict, retry_enabled: bool, retry_reason: str) -> None:
    decision = decidir_estado_botones_sync(_entrada_base(**overrides))

    assert decision.retry_failed.enabled is retry_enabled
    assert decision.retry_failed.reason_code == retry_reason


@pytest.mark.parametrize(
    ("overrides", "review_enabled", "review_text", "review_reason", "review_severity"),
    [
        ({}, False, "Revisar conflictos (sin pendientes)", "review_conflictos_sin_pendientes", None),
        ({"conflictos_pendientes_total": 1}, True, "Revisar conflictos", "review_conflictos_pendientes", "warning"),
        ({"conflictos_pendientes_total": 5}, True, "Revisar conflictos", "review_conflictos_pendientes", "warning"),
        (
            {"sync_en_progreso": True, "conflictos_pendientes_total": 0},
            False,
            "Revisar conflictos (sin pendientes)",
            "review_conflictos_bloqueado_en_progreso",
            None,
        ),
        (
            {"sync_en_progreso": True, "conflictos_pendientes_total": 3},
            False,
            "Revisar conflictos",
            "review_conflictos_bloqueado_en_progreso",
            "warning",
        ),
    ],
)
def test_decidir_estado_conflictos(
    overrides: dict,
    review_enabled: bool,
    review_text: str,
    review_reason: str,
    review_severity: str | None,
) -> None:
    decision = decidir_estado_botones_sync(_entrada_base(**overrides))

    assert decision.review_conflicts.enabled is review_enabled
    assert decision.review_conflicts.text == review_text
    assert decision.review_conflicts.reason_code == review_reason
    assert decision.review_conflicts.severity == review_severity


@pytest.mark.parametrize(
    ("overrides", "enabled", "reason_code"),
    [
        ({}, True, "reporte_listo"),
        ({"ultimo_reporte_presente": False}, False, "reporte_no_disponible"),
        ({"sync_en_progreso": True, "ultimo_reporte_presente": True}, False, "reporte_bloqueado_en_progreso"),
        ({"sync_en_progreso": True, "ultimo_reporte_presente": False}, False, "reporte_bloqueado_en_progreso"),
        ({"sync_configurado": False, "ultimo_reporte_presente": True}, True, "reporte_listo"),
    ],
)
def test_decidir_estado_reportes(overrides: dict, enabled: bool, reason_code: str) -> None:
    decision = decidir_estado_botones_sync(_entrada_base(**overrides))

    assert decision.sync_details.enabled is enabled
    assert decision.copy_sync_report.enabled is enabled
    assert decision.sync_details.reason_code == reason_code
    assert decision.copy_sync_report.reason_code == reason_code
