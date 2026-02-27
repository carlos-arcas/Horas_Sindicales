from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.domain.sync_models import SyncExecutionPlan
from app.infrastructure.sync_sheets_adapter_puros import (
    build_service_operation,
    ensure_execution_plan_shape,
    normalize_pdf_log_input,
    normalize_sync_config_input,
)


@dataclass
class _ServiceFake:
    called: list[tuple[str, tuple[object, ...]]]

    def pull(self):
        self.called.append(("pull", ()))
        return "ok"

    def guardar(self, a, b):
        self.called.append(("guardar", (a, b)))
        return a, b


def test_build_service_operation_ejecuta_metodo() -> None:
    service = _ServiceFake([])
    op = build_service_operation("pull")
    assert op(service) == "ok"
    assert service.called == [("pull", ())]


def test_build_service_operation_pasa_argumentos() -> None:
    service = _ServiceFake([])
    op = build_service_operation("guardar", "k", "v")
    assert op(service) == ("k", "v")


@pytest.mark.parametrize("name", ["", None, 123])
def test_build_service_operation_nombre_invalido(name) -> None:
    with pytest.raises(ValueError):
        build_service_operation(name)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        (" token ", " abc ", ("token", "abc")),
        ("activo", "", ("activo", "")),
        ("x", "  1", ("x", "1")),
    ],
)
def test_normalize_sync_config_input(key: str, value: str, expected: tuple[str, str]) -> None:
    assert normalize_sync_config_input(key, value) == expected


@pytest.mark.parametrize("key", ["", "   "])
def test_normalize_sync_config_input_rechaza_clave_vacia(key: str) -> None:
    with pytest.raises(ValueError):
        normalize_sync_config_input(key, "v")


@pytest.mark.parametrize(
    ("persona_id", "fechas", "pdf_hash", "expected"),
    [
        (1, [" 2025-01-01 ", "", "2025-01-02"], "  h1 ", (1, ["2025-01-01", "2025-01-02"], "h1")),
        (9, [], None, (9, [], None)),
        (2, ["   "], "", (2, [], None)),
    ],
)
def test_normalize_pdf_log_input(persona_id, fechas, pdf_hash, expected) -> None:
    assert normalize_pdf_log_input(persona_id, fechas, pdf_hash) == expected


@pytest.mark.parametrize("persona_id", [0, -1])
def test_normalize_pdf_log_input_persona_invalida(persona_id: int) -> None:
    with pytest.raises(ValueError):
        normalize_pdf_log_input(persona_id, ["2025-01-01"], None)


def test_ensure_execution_plan_shape_ok() -> None:
    plan = SyncExecutionPlan(generated_at="hoy", worksheet="solicitudes")
    assert ensure_execution_plan_shape(plan) is plan


@pytest.mark.parametrize("plan", [object(), {"worksheet": "x"}, type("X", (), {"worksheet": "x"})()])
def test_ensure_execution_plan_shape_error(plan) -> None:
    with pytest.raises(ValueError):
        ensure_execution_plan_shape(plan)
