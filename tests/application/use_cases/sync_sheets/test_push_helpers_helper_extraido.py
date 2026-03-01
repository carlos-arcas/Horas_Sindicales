from __future__ import annotations

from types import SimpleNamespace

from app.application.use_cases.sync_sheets.push_helpers import push_config


class _StubService:
    def __init__(self, connection) -> None:
        self._connection = connection
        self._enable_backfill = False
        self.appended: list[tuple[object, list[str], dict[str, object]]] = []
        self.updated: list[tuple[object, int, list[str], dict[str, object]]] = []
        self.flush_calls = 0

    def _get_worksheet(self, spreadsheet, worksheet_name: str):
        return SimpleNamespace(title=worksheet_name)

    def _rows_with_index(self, _worksheet):
        return ["key", "value", "updated_at", "source_device"], self.remote_rows

    def _header_map(self, headers, _expected):
        return headers

    def _append_row(self, worksheet, header_map, payload):
        self.appended.append((worksheet, header_map, payload))

    def _update_row(self, worksheet, row_number, header_map, payload):
        self.updated.append((worksheet, row_number, header_map, payload))

    def _flush_write_batches(self, _spreadsheet, _worksheet):
        self.flush_calls += 1

    def _device_id(self) -> str:
        return "device-fallback"


def test_push_config_helper_extraido_appends_local_row_when_remote_missing(connection) -> None:
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO sync_config (key, value, updated_at, source_device) VALUES (?, ?, ?, ?)",
        ("k1", "v1", "2026-01-01T10:00:00Z", None),
    )
    connection.commit()

    service = _StubService(connection)
    service.remote_rows = []

    uploaded = push_config(service, spreadsheet=object(), last_sync_at="2025-01-01T00:00:00Z")

    assert uploaded == 1
    assert len(service.appended) == 1
    assert service.appended[0][2]["source_device"] == "device-fallback"
    assert service.flush_calls == 1


def test_push_config_helper_extraido_skips_when_remote_is_newer(connection) -> None:
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO sync_config (key, value, updated_at, source_device) VALUES (?, ?, ?, ?)",
        ("k2", "v2", "2026-01-01T10:00:00Z", "local-device"),
    )
    connection.commit()

    service = _StubService(connection)
    service.remote_rows = [
        (
            2,
            {
                "key": "k2",
                "value": "remote-v2",
                "updated_at": "2026-01-01T10:01:00Z",
                "source_device": "remote-device",
                "__row_number__": 2,
            },
        )
    ]

    uploaded = push_config(service, spreadsheet=object(), last_sync_at="2025-01-01T00:00:00Z")

    assert uploaded == 0
    assert service.appended == []
    assert service.updated == []
    assert service.flush_calls == 1
