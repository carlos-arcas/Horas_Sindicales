from __future__ import annotations

import pytest

from app.application.use_cases.sync_sheets.push_builder import build_push_solicitudes_payloads


HEADER = ("uuid", "payload")


def _local_payload(row: dict[str, str]) -> tuple[str, str]:
    return (row["uuid"], f"L-{row['uuid']}")


def _remote_payload(row: dict[str, str]) -> tuple[str, str]:
    return (str(row.get("uuid", "")), f"R-{row.get('uuid', '')}")


@pytest.mark.parametrize(
    ("local_rows", "remote_rows", "last_sync", "expected_values", "uploaded", "omitted", "conflicts"),
    [
        ([], [], None, [HEADER], 0, 0, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-01T00:00:00+00:00"}], [], None, [HEADER, ("u1", "L-u1")], 1, 0, 0),
        ([], [(2, {"uuid": "r1"})], None, [HEADER, ("r1", "R-r1")], 0, 1, 0),
        ([], [(2, {"uuid": ""})], None, [HEADER], 0, 0, 0),
        ([], [(2, {"uuid": "  "})], None, [HEADER], 0, 0, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-02T00:00:00+00:00"}], [(2, {"uuid": "u1", "updated_at": "2024-01-01T00:00:00+00:00"})], None, [HEADER, ("u1", "L-u1")], 1, 0, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-01T00:00:00+00:00"}], [(2, {"uuid": "x"})], "2024-01-02T00:00:00+00:00", [HEADER, ("x", "R-x")], 0, 1, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-03T00:00:00+00:00"}], [(2, {"uuid": "x"})], "2024-01-02T00:00:00+00:00", [HEADER, ("u1", "L-u1"), ("x", "R-x")], 1, 1, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-03T00:00:00+00:00"}], [(2, {"uuid": "u1"}), (3, {"uuid": "r2"})], "2024-01-02T00:00:00+00:00", [HEADER, ("u1", "L-u1"), ("r2", "R-r2")], 1, 1, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-03T00:00:00+00:00"}, {"uuid": "u2", "updated_at": "2024-01-03T00:00:00+00:00"}], [], None, [HEADER, ("u1", "L-u1"), ("u2", "L-u2")], 2, 0, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-01T00:00:00+00:00"}, {"uuid": "u2", "updated_at": "2024-01-03T00:00:00+00:00"}], [], "2024-01-02T00:00:00+00:00", [HEADER, ("u2", "L-u2")], 1, 0, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-03T00:00:00+00:00"}], [(2, {"uuid": "r1"}), (3, {"uuid": "r2"})], None, [HEADER, ("u1", "L-u1"), ("r1", "R-r1"), ("r2", "R-r2")], 1, 2, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-03T00:00:00+00:00"}], [(2, {"uuid": "u1"}), (3, {"uuid": "u1"}), (4, {"uuid": "r2"})], None, [HEADER, ("u1", "L-u1"), ("r2", "R-r2")], 1, 1, 0),
        ([{"uuid": "a", "updated_at": "2024-01-03T00:00:00+00:00"}, {"uuid": "b", "updated_at": "2024-01-03T00:00:00+00:00"}], [(2, {"uuid": "c"}), (3, {"uuid": "d"})], None, [HEADER, ("a", "L-a"), ("b", "L-b"), ("c", "R-c"), ("d", "R-d")], 2, 2, 0),
        ([{"uuid": "a", "updated_at": "2024-01-03T00:00:00+00:00"}], [(2, {"uuid": "c"}), (3, {"uuid": ""}), (4, {"uuid": "d"})], None, [HEADER, ("a", "L-a"), ("c", "R-c"), ("d", "R-d")], 1, 2, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-02T00:00:00+00:00"}], [(2, {"uuid": "u1", "updated_at": "2024-01-03T00:00:00+00:00"})], "2024-01-01T00:00:00+00:00", [HEADER], 0, 0, 1),
        ([{"uuid": "u1", "updated_at": "2024-01-02T00:00:00+00:00"}], [(2, {"uuid": "u1", "updated_at": "2024-01-03T00:00:00+00:00"})], None, [HEADER, ("u1", "L-u1")], 1, 0, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-05T00:00:00+00:00"}], [(2, {"uuid": "u1", "updated_at": "2024-01-03T00:00:00+00:00"})], "2024-01-01T00:00:00+00:00", [HEADER], 0, 0, 1),
        ([{"uuid": "u1", "updated_at": "2024-01-05T00:00:00+00:00"}], [(2, {"uuid": "u1", "updated_at": None})], "2024-01-01T00:00:00+00:00", [HEADER, ("u1", "L-u1")], 1, 0, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-05T00:00:00+00:00"}, {"uuid": "u2", "updated_at": "2024-01-05T00:00:00+00:00"}], [(2, {"uuid": "u2", "updated_at": "2024-01-06T00:00:00+00:00"})], "2024-01-01T00:00:00+00:00", [HEADER, ("u1", "L-u1")], 1, 0, 1),
        ([{"uuid": "u1", "updated_at": "2024-01-05T00:00:00+00:00"}], [(2, {"uuid": "r1"}), (3, {"uuid": "r2"}), (4, {"uuid": "r3"})], None, [HEADER, ("u1", "L-u1"), ("r1", "R-r1"), ("r2", "R-r2"), ("r3", "R-r3")], 1, 3, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-01T00:00:00+00:00"}, {"uuid": "u2", "updated_at": "2024-02-01T00:00:00+00:00"}], [(2, {"uuid": "r1"})], "2024-01-15T00:00:00+00:00", [HEADER, ("u2", "L-u2"), ("r1", "R-r1")], 1, 1, 0),
        ([{"uuid": "u1", "updated_at": "2024-01-01T00:00:00+00:00"}], [(2, {"uuid": "r1"}), (3, {"uuid": "u1"})], "2024-02-01T00:00:00+00:00", [HEADER, ("r1", "R-r1"), ("u1", "R-u1")], 0, 2, 0),
        ([{"uuid": "a", "updated_at": "2024-01-05T00:00:00+00:00"}], [(2, {"uuid": "b"}), (3, {"uuid": "b"})], None, [HEADER, ("a", "L-a"), ("b", "R-b"), ("b", "R-b")], 1, 2, 0),
        ([{"uuid": "alpha", "updated_at": "2024-02-05T00:00:00+00:00"}], [(2, {"uuid": "beta"})], None, [HEADER, ("alpha", "L-alpha"), ("beta", "R-beta")], 1, 1, 0),
    ],
)
def test_build_push_solicitudes_payloads_contract(
    local_rows: list[dict[str, str]],
    remote_rows: list[tuple[int, dict[str, str]]],
    last_sync: str | None,
    expected_values: list[tuple[str, str]],
    uploaded: int,
    omitted: int,
    conflicts: int,
) -> None:
    remote_index = {str(row.get("uuid", "")).strip(): row for _, row in remote_rows if str(row.get("uuid", "")).strip()}
    result = build_push_solicitudes_payloads(
        header=HEADER,
        local_rows=local_rows,
        remote_rows=remote_rows,
        remote_index=remote_index,
        last_sync_at=last_sync,
        local_payload_builder=_local_payload,
        remote_payload_builder=_remote_payload,
    )

    assert list(result.values) == expected_values
    assert result.uploaded == uploaded
    assert result.omitted_duplicates == omitted
    assert len(result.conflicts) == conflicts
    for conflict in result.conflicts:
        assert conflict.reason_code == "conflict_divergent"
