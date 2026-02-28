from __future__ import annotations

import pytest

from app.application.use_cases.sync_sheets.pull_planner import PullPlannerSignals, plan_pull_actions


@pytest.mark.parametrize(
    ("signals", "expected_commands", "expected_reason_codes"),
    [
        (PullPlannerSignals(False, False, False, False, False, False, False, None), ["INSERT_SOLICITUD"], ["insert_missing_uuid"]),
        (PullPlannerSignals(False, True, False, False, False, False, False, "u1"), ["SKIP"], ["duplicate_without_uuid"]),
        (PullPlannerSignals(False, True, False, False, False, False, True, "u1"), ["SKIP", "BACKFILL_UUID"], ["duplicate_without_uuid", "backfill_existing_uuid"]),
        (PullPlannerSignals(False, True, False, False, False, False, True, None), ["SKIP"], ["duplicate_without_uuid"]),
        (PullPlannerSignals(True, False, False, False, False, False, False, None), ["INSERT_SOLICITUD"], ["insert_new_uuid"]),
        (PullPlannerSignals(True, False, False, True, False, False, False, None), ["SKIP"], ["duplicate_with_uuid"]),
        (PullPlannerSignals(True, False, True, False, True, True, False, None), ["REGISTER_CONFLICT"], ["conflict_divergent"]),
        (PullPlannerSignals(True, False, True, False, False, True, False, None), ["UPDATE_SOLICITUD"], ["remote_newer"]),
        (PullPlannerSignals(True, False, True, False, False, False, False, None), ["SKIP"], ["local_is_newer_or_equal"]),
        (PullPlannerSignals(True, True, False, False, False, False, True, "z"), ["INSERT_SOLICITUD"], ["insert_new_uuid"]),
        (PullPlannerSignals(True, True, False, True, False, False, True, "z"), ["SKIP"], ["duplicate_with_uuid"]),
        (PullPlannerSignals(True, True, True, False, True, False, True, "z"), ["REGISTER_CONFLICT"], ["conflict_divergent"]),
        (PullPlannerSignals(True, True, True, False, False, True, True, "z"), ["UPDATE_SOLICITUD"], ["remote_newer"]),
        (PullPlannerSignals(True, True, True, False, False, False, True, "z"), ["SKIP"], ["local_is_newer_or_equal"]),
        (PullPlannerSignals(False, False, True, False, False, False, False, None), ["INSERT_SOLICITUD"], ["insert_missing_uuid"]),
        (PullPlannerSignals(False, True, True, False, False, False, False, "u2"), ["SKIP"], ["duplicate_without_uuid"]),
        (PullPlannerSignals(False, True, True, False, False, False, True, "u2"), ["SKIP", "BACKFILL_UUID"], ["duplicate_without_uuid", "backfill_existing_uuid"]),
        (PullPlannerSignals(False, False, False, True, False, False, False, None), ["INSERT_SOLICITUD"], ["insert_missing_uuid"]),
        (PullPlannerSignals(False, True, False, True, False, False, True, "x"), ["SKIP", "BACKFILL_UUID"], ["duplicate_without_uuid", "backfill_existing_uuid"]),
        (PullPlannerSignals(True, False, False, False, True, True, False, None), ["INSERT_SOLICITUD"], ["insert_new_uuid"]),
        (PullPlannerSignals(True, False, False, True, True, True, False, None), ["SKIP"], ["duplicate_with_uuid"]),
        (PullPlannerSignals(True, False, True, True, True, True, False, None), ["REGISTER_CONFLICT"], ["conflict_divergent"]),
        (PullPlannerSignals(True, False, True, True, False, True, False, None), ["UPDATE_SOLICITUD"], ["remote_newer"]),
        (PullPlannerSignals(True, False, True, True, False, False, False, None), ["SKIP"], ["local_is_newer_or_equal"]),
        (PullPlannerSignals(False, True, False, False, True, True, True, "uuid-z"), ["SKIP", "BACKFILL_UUID"], ["duplicate_without_uuid", "backfill_existing_uuid"]),
    ],
)
def test_plan_pull_actions_contract(signals: PullPlannerSignals, expected_commands: list[str], expected_reason_codes: list[str]) -> None:
    actions = plan_pull_actions(signals)
    assert [action.command for action in actions] == expected_commands
    assert [action.reason_code for action in actions] == expected_reason_codes


def test_plan_pull_actions_backfill_payload_stable() -> None:
    actions = plan_pull_actions(PullPlannerSignals(False, True, False, False, False, False, True, "abc-123"))
    assert actions[1].payload == {"uuid": "abc-123"}
    assert actions[0].payload == {"counter": "omitted_duplicates"}
