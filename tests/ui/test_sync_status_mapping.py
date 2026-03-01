from __future__ import annotations

import pytest

from app.ui.vistas.sync_status_mapping import status_to_label


@pytest.mark.parametrize("status", ["IDLE", "ERROR", "CONFIG_INCOMPLETE"])
def test_status_to_label_known_statuses_return_non_empty_string(status: str) -> None:
    label = status_to_label(status)

    assert isinstance(label, str)
    assert label.strip()


def test_status_to_label_unknown_status_falls_back_to_status_code() -> None:
    status = "UNKNOWN"

    assert status_to_label(status) == status
