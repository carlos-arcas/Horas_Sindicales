from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


def _load_module(rel_path: str, module_name: str):
    path = Path(rel_path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"No se pudo cargar {rel_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reservado_calculo = _load_module(
    "app/ui/vistas/reservado_calculo.py",
    "reservado_calculo_contract",
)
form_handlers = _load_module(
    "app/ui/vistas/main_window/form_handlers.py",
    "form_handlers_contract",
)
solicitudes_controller_mod = _load_module(
    "app/ui/controllers/solicitudes_controller.py",
    "solicitudes_controller_contract",
)


on_completo_changed = form_handlers.on_completo_changed
SolicitudesController = solicitudes_controller_mod.SolicitudesController


def test_calcular_minutos_reservados_periodo_filtra_por_periodo() -> None:
    sumar = Mock(return_value=75)
    pendientes = [
        SimpleNamespace(fecha_pedida="2026-02-15"),
        SimpleNamespace(fecha_pedida="2026-02-20"),
        SimpleNamespace(fecha_pedida="2026-03-01"),
    ]

    total = reservado_calculo.calcular_minutos_reservados_periodo(
        persona_id=7,
        pendientes=pendientes,
        year=2026,
        month=2,
        sumar_pendientes_min=sumar,
    )

    assert total == 75
    sumar.assert_called_once()
    _, pendientes_filtrados = sumar.call_args.args
    assert len(pendientes_filtrados) == 2


def test_on_completo_changed_refresca_estado_operativa() -> None:
    completo_check = SimpleNamespace(
        isChecked=lambda: False,
        setChecked=lambda _value: None,
    )
    window = SimpleNamespace(
        completo_check=completo_check,
        _mark_field_touched=Mock(),
        _run_preventive_validation=Mock(),
        _refrescar_estado_operativa=Mock(),
    )

    on_completo_changed(window, True)

    window._refrescar_estado_operativa.assert_called_once_with("completo_changed")


def test_solicitudes_controller_refresca_reservado_al_aniadir() -> None:
    window = SimpleNamespace(
        notas_input=SimpleNamespace(setPlainText=lambda _texto: None),
        _solicitudes_last_action_saved=False,
        _solicitudes_runtime_error=True,
        _refresh_historico=Mock(),
        _refrescar_estado_operativa=Mock(),
        notifications=SimpleNamespace(notify_added_pending=Mock()),
        _undo_last_added_pending=Mock(),
        toast=SimpleNamespace(),
    )
    controller = SolicitudesController(window)

    creada = SimpleNamespace(id=44)
    controller._update_ui_after_add(creada, pendiente_en_edicion=None)

    window._refrescar_estado_operativa.assert_called_once_with("pendiente_added")
