from __future__ import annotations

import pytest

from app.ui.vistas.confirmacion_presenter import ConfirmacionEntrada, build_confirmacion_plan


@pytest.mark.parametrize(
    ("entrada", "expected_reason", "must_include", "must_exclude"),
    [
        (ConfirmacionEntrada(False, (1,), True, True, False), "ui_not_ready", {"LOG_EARLY_RETURN"}, {"CONFIRM"}),
        (ConfirmacionEntrada(False, (), False, False, True), "ui_not_ready", {"LOG_EARLY_RETURN"}, {"SHOW_ERROR", "CONFIRM"}),
        (ConfirmacionEntrada(True, (), True, True, False), "no_pending_rows", {"SHOW_ERROR", "LOG_EARLY_RETURN"}, {"CONFIRM"}),
        (ConfirmacionEntrada(True, (), False, False, True), "no_pending_rows", {"SHOW_ERROR"}, {"CONFIRM", "PROMPT_PDF"}),
        (ConfirmacionEntrada(True, (1,), False, True, False), "preconfirm_checks", {"LOG_EARLY_RETURN"}, {"CONFIRM", "PROMPT_PDF"}),
        (ConfirmacionEntrada(True, (1,), False, False, False), "preconfirm_checks", {"LOG_EARLY_RETURN"}, {"CONFIRM"}),
        (ConfirmacionEntrada(True, (1,), True, False, False), "no_persona", {"LOG_EARLY_RETURN"}, {"CONFIRM", "PROMPT_PDF"}),
        (ConfirmacionEntrada(True, (1,), True, False, True), "no_persona", {"LOG_EARLY_RETURN"}, {"SHOW_ERROR", "CONFIRM"}),
        (ConfirmacionEntrada(True, (1,), True, True, True), "conflictos_pendientes", {"SHOW_ERROR", "LOG_EARLY_RETURN"}, {"CONFIRM", "PROMPT_PDF"}),
        (ConfirmacionEntrada(True, (1,), True, True, True, pdf_prompted=True), "conflictos_pendientes", {"SHOW_ERROR"}, {"CONFIRM"}),
        (ConfirmacionEntrada(True, (1,), True, True, False), "ready_for_prompt", {"PROMPT_PDF"}, {"CONFIRM"}),
        (ConfirmacionEntrada(True, (1,), True, True, False, pdf_prompted=True, pdf_path=None), "pdf_path_cancelado", {"LOG_EARLY_RETURN"}, {"CONFIRM"}),
        (ConfirmacionEntrada(True, (1, 2), True, True, False, pdf_prompted=True, pdf_path="/tmp/a.pdf"), "ready_for_confirm", {"PREPARE_PAYLOAD", "CONFIRM"}, set()),
        (ConfirmacionEntrada(True, (1,), True, True, False, pdf_prompted=True, pdf_path="a.pdf", execute_attempted=True, execute_succeeded=False), "execute_confirm_none", {"LOG_EARLY_RETURN"}, {"FINALIZE_CONFIRMATION", "CONFIRM"}),
        (ConfirmacionEntrada(True, (1,), True, True, False, pdf_prompted=True, pdf_path="a.pdf", execute_attempted=True, execute_succeeded=None), "execute_confirm_none", {"LOG_EARLY_RETURN"}, {"FINALIZE_CONFIRMATION", "CONFIRM"}),
        (ConfirmacionEntrada(True, (1,), True, True, False, pdf_prompted=True, pdf_path="a.pdf", execute_attempted=True, execute_succeeded=True), "confirmed", {"FINALIZE_CONFIRMATION", "RESET_FORM", "REFRESH_TABLE", "SHOW_TOAST"}, {"PROMPT_PDF"}),
        (ConfirmacionEntrada(True, (None,), True, True, False), "ready_for_prompt", {"PROMPT_PDF"}, {"CONFIRM"}),
        (ConfirmacionEntrada(True, (None, 2), True, True, False, pdf_prompted=True, pdf_path="x.pdf"), "ready_for_confirm", {"CONFIRM"}, set()),
    ],
)
def test_build_confirmacion_plan_transitions(entrada, expected_reason, must_include, must_exclude):
    plan = build_confirmacion_plan(entrada)
    action_types = {action.action_type for action in plan.actions}

    assert plan.decision.reason_code == expected_reason
    assert must_include.issubset(action_types)
    assert action_types.isdisjoint(must_exclude)


@pytest.mark.parametrize(
    "entrada",
    [
        ConfirmacionEntrada(True, (), True, True, False),
        ConfirmacionEntrada(True, (1,), False, True, False),
        ConfirmacionEntrada(True, (1,), True, False, False),
        ConfirmacionEntrada(True, (1,), True, True, True),
        ConfirmacionEntrada(True, (1,), True, True, False, pdf_prompted=True, pdf_path=None),
        ConfirmacionEntrada(True, (1,), True, True, False, pdf_prompted=True, pdf_path="a.pdf", execute_attempted=True, execute_succeeded=False),
    ],
)
def test_invalid_scenarios_never_include_confirm(entrada):
    plan = build_confirmacion_plan(entrada)
    assert "CONFIRM" not in {action.action_type for action in plan.actions}


def test_contract_text_no_pending_message():
    plan = build_confirmacion_plan(ConfirmacionEntrada(True, (), True, True, False))
    show_error = next(action for action in plan.actions if action.action_type == "SHOW_ERROR")
    assert show_error.message == "No hay pendientes"


def test_contract_text_no_pending_title():
    plan = build_confirmacion_plan(ConfirmacionEntrada(True, (), True, True, False))
    show_error = next(action for action in plan.actions if action.action_type == "SHOW_ERROR")
    assert show_error.title == "Sin pendientes"


def test_contract_text_conflict_message():
    plan = build_confirmacion_plan(ConfirmacionEntrada(True, (1,), True, True, True))
    show_error = next(action for action in plan.actions if action.action_type == "SHOW_ERROR")
    assert show_error.message == "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar."
