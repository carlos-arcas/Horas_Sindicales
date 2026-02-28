from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.use_cases.sync_sheets.pull_planner import PullAction


ActionHandler = Callable[[PullAction], None]


def run_pull_actions(
    actions: tuple[PullAction, ...] | list[PullAction],
    *,
    on_skip: ActionHandler,
    on_backfill_uuid: ActionHandler,
    on_insert_solicitud: ActionHandler,
    on_update_solicitud: ActionHandler,
    on_register_conflict: ActionHandler,
) -> None:
    handlers: dict[str, ActionHandler] = {
        "SKIP": on_skip,
        "BACKFILL_UUID": on_backfill_uuid,
        "INSERT_SOLICITUD": on_insert_solicitud,
        "UPDATE_SOLICITUD": on_update_solicitud,
        "REGISTER_CONFLICT": on_register_conflict,
    }
    for action in actions:
        handler = handlers.get(action.command)
        if handler is None:
            continue
        handler(action)


def run_with_savepoint(connection: Any, name: str, fn: Callable[[], None]) -> None:
    cursor = connection.cursor()
    cursor.execute(f"SAVEPOINT {name}")
    try:
        fn()
        cursor.execute(f"RELEASE SAVEPOINT {name}")
    except Exception:
        cursor.execute(f"ROLLBACK TO SAVEPOINT {name}")
        cursor.execute(f"RELEASE SAVEPOINT {name}")
        raise
