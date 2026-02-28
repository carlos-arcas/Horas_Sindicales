from __future__ import annotations

import pytest

from app.ui.vistas.personas_presenter import (
    PersonaOption,
    PersonasLoadInput,
    build_personas_load_output,
    resolve_active_delegada_id,
)


def _entrada(personas: list[tuple[int | None, str]], *, select_id: int | None = None, saved: object = None) -> PersonasLoadInput:
    return PersonasLoadInput(
        personas=tuple(PersonaOption(id=persona_id, nombre=nombre) for persona_id, nombre in personas),
        select_id=select_id,
        saved_delegada_id=saved,
    )


@pytest.mark.parametrize(
    ("delegada_ids", "preferred", "expected"),
    [
        ([], None, None),
        ([4], None, 4),
        ([4, 8, 15], 8, 8),
        ([4, 8, 15], "8", 8),
        ([4, 8, 15], "15", 15),
        ([4, 8, 15], 99, 4),
        ([4, 8, 15], "99", 4),
    ],
)
def test_resolve_active_delegada_id_rules(delegada_ids, preferred, expected):
    assert resolve_active_delegada_id(delegada_ids, preferred) == expected


@pytest.mark.parametrize(
    ("personas", "select_id", "expected_selected"),
    [
        ([], None, None),
        ([(1, "Ana")], None, 1),
        ([(1, "Ana"), (2, "Berta")], None, 1),
        ([(1, "Ana"), (2, "Berta")], 2, 2),
        ([(1, "Ana"), (2, "Berta")], 99, 1),
        ([(None, "Sin ID"), (2, "Berta")], None, None),
        ([(None, "Sin ID"), (2, "Berta")], 2, 2),
    ],
)
def test_build_personas_load_output_selects_persona(personas, select_id, expected_selected):
    output = build_personas_load_output(_entrada(personas, select_id=select_id))
    assert output.selected_persona_id == expected_selected


@pytest.mark.parametrize(
    ("personas", "expected"),
    [
        ([], {}),
        ([(1, "Ana")], {1: "Ana"}),
        ([(1, "Ana"), (2, "Berta")], {1: "Ana", 2: "Berta"}),
        ([(None, "Sin ID"), (2, "Berta")], {2: "Berta"}),
        ([(3, "Zoe"), (3, "Zoe nueva")], {3: "Zoe nueva"}),
    ],
)
def test_build_personas_load_output_persona_nombres(personas, expected):
    output = build_personas_load_output(_entrada(personas))
    assert output.persona_nombres == expected


@pytest.mark.parametrize(
    ("personas", "expected_historico", "expected_config"),
    [
        ([], (("Todas", None),), ()),
        ([(2, "Berta"), (1, "Ana")], (("Todas", None), ("Ana", 1), ("Berta", 2)), (("Ana", 1), ("Berta", 2))),
        ([(2, "berta"), (1, "Ana")], (("Todas", None), ("Ana", 1), ("berta", 2)), (("Ana", 1), ("berta", 2))),
        ([(2, "Ángela"), (1, "ana")], (("Todas", None), ("ana", 1), ("Ángela", 2)), (("ana", 1), ("Ángela", 2))),
    ],
)
def test_build_personas_load_output_sorted_items(personas, expected_historico, expected_config):
    output = build_personas_load_output(_entrada(personas))
    assert output.historico_items == expected_historico
    assert output.config_items == expected_config


@pytest.mark.parametrize(
    ("personas", "select_id", "saved", "expected_active"),
    [
        ([], None, None, None),
        ([(1, "Ana")], None, None, 1),
        ([(1, "Ana"), (2, "Berta")], None, "2", 2),
        ([(1, "Ana"), (2, "Berta")], None, 99, 1),
        ([(1, "Ana"), (2, "Berta")], 2, 1, 2),
        ([(1, "Ana"), (2, "Berta")], 99, 2, 1),
    ],
)
def test_build_personas_load_output_active_config(personas, select_id, saved, expected_active):
    output = build_personas_load_output(_entrada(personas, select_id=select_id, saved=saved))
    assert output.active_config_id == expected_active


def test_contract_textos_criticos_se_mantienen() -> None:
    output = build_personas_load_output(_entrada([(2, "Berta"), (1, "Ana")]))
    assert output.historico_items[0][0] == "Todas"
    assert output.historico_items[1][0] == "Ana"
    assert output.historico_items[2][0] == "Berta"
    assert output.config_items[0][0] == "Ana"
    assert output.config_items[1][0] == "Berta"
