from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def _load_state_historico_module():
    module_path = Path(__file__).resolve().parents[2] / "app/ui/vistas/main_window/state_historico.py"
    spec = importlib.util.spec_from_file_location("state_historico_test_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


state_historico = _load_state_historico_module()

pytestmark = pytest.mark.headless_safe


class _Index:
    def __init__(self, row: int, valid: bool = True) -> None:
        self._row = row
        self._valid = valid

    def row(self) -> int:
        return self._row

    def isValid(self) -> bool:  # noqa: N802
        return self._valid


class _SelectionModel:
    def __init__(self, rows: list[int]) -> None:
        self._rows = rows

    def selectedRows(self):  # noqa: N802
        return [_Index(row) for row in self._rows]


class _TableStub:
    def __init__(self, rows: list[int]) -> None:
        self._selection_model = _SelectionModel(rows)
        self.clearSelection = Mock()

    def selectionModel(self):  # noqa: N802
        return self._selection_model


class _ProxyStub:
    def mapToSource(self, index: _Index) -> _Index:  # noqa: N802
        return index


class _ModelStub:
    def __init__(self, ids_by_row: dict[int, int | None]) -> None:
        self._ids_by_row = ids_by_row

    def solicitud_at(self, row: int):
        return SimpleNamespace(id=self._ids_by_row.get(row))


class _ButtonStub:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, text: str) -> None:  # noqa: N802
        self.text = text


def test_seleccion_historico_actualiza_contador() -> None:
    window = SimpleNamespace(
        historico_table=_TableStub([0, 1]),
        historico_proxy_model=_ProxyStub(),
        historico_model=_ModelStub({0: 11, 1: 12}),
        eliminar_button=_ButtonStub(),
        _historico_ids_seleccionados=set(),
    )

    state_historico.actualizar_estado_seleccion_historico(window)

    assert window._historico_ids_seleccionados == {11, 12}
    assert window.eliminar_button.text == "Eliminar (2)"


def test_eliminar_historico_con_ids_llama_use_case_y_limpia_estado() -> None:
    use_case = Mock()
    window = SimpleNamespace(
        _historico_ids_seleccionados={11, 12},
        _solicitud_use_cases=SimpleNamespace(eliminar_solicitud=use_case),
        historico_table=_TableStub([]),
        eliminar_button=_ButtonStub(),
    )

    eliminadas = state_historico.eliminar_historico_seleccionado(window)

    assert eliminadas == 2
    assert use_case.call_count == 2
    assert {call.args[0] for call in use_case.call_args_list} == {11, 12}
    assert window._historico_ids_seleccionados == set()
    assert window.eliminar_button.text == "Eliminar (0)"


def test_eliminar_historico_sin_ids_no_llama_use_case() -> None:
    use_case = Mock()
    window = SimpleNamespace(
        _historico_ids_seleccionados=set(),
        _solicitud_use_cases=SimpleNamespace(eliminar_solicitud=use_case),
        historico_table=_TableStub([]),
        eliminar_button=_ButtonStub(),
    )

    eliminadas = state_historico.eliminar_historico_seleccionado(window)

    assert eliminadas == 0
    use_case.assert_not_called()
