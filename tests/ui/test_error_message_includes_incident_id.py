from __future__ import annotations

from app.ui.error_mapping import map_error_to_user_message


def test_error_message_includes_incident_id() -> None:
    message = map_error_to_user_message(RuntimeError("fallo"), incident_id="cid-777")

    assert "ID de incidente: cid-777" in message
