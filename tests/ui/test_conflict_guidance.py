from app.application.conflicts_service import ConflictRecord
from app.ui.conflict_guidance import build_what_happened, classify_conflict


def _record(local: dict, remote: dict) -> ConflictRecord:
    return ConflictRecord(
        id=1,
        uuid="uuid-1",
        entity_type="delegadas",
        local_snapshot=local,
        remote_snapshot=remote,
        detected_at="2026-01-01T10:00:00Z",
    )


def test_classify_conflict_access_error() -> None:
    conflict = _record({"error": "permiso denegado"}, {})
    assert classify_conflict(conflict) == "Error de acceso"


def test_classify_conflict_balance_difference() -> None:
    conflict = _record({"horas_mes_min": 600}, {"horas_mes_min": 500})
    assert classify_conflict(conflict) == "Diferencia de saldo"


def test_classify_conflict_duplicate_remote() -> None:
    conflict = _record({"duplicate_of": "abc"}, {})
    assert classify_conflict(conflict) == "Duplicado remoto"


def test_build_what_happened_includes_guidance_without_raw_json() -> None:
    conflict = _record({"nombre": "Ana", "horas_mes_min": 600}, {"horas_mes_min": 500})
    message = build_what_happened(conflict)
    assert "Delegada afectada: Ana" in message
    assert "Acción recomendada:" in message
    assert "{" not in message
