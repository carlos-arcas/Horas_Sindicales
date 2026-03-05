from __future__ import annotations

from scripts.diagnosticar_pytest import detectar_ultimo_test_visto


def test_detectar_ultimo_test_visto_desde_salida_verbose() -> None:
    salida_vv = [
        "============================= test session starts =============================",
        "tests/scripts/test_alpha.py::test_uno PASSED                               [ 25%]",
        "tests/scripts/test_beta.py::test_dos PASSED                                [ 50%]",
        "texto irrelevante",
        "tests/scripts/test_gamma.py::test_tres FAILED                              [ 75%]",
    ]

    ultimo = detectar_ultimo_test_visto(salida_vv)

    assert ultimo == "tests/scripts/test_gamma.py::test_tres"
