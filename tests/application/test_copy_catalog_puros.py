from __future__ import annotations

from app.ui.copy_catalog import (
    calcular_diff_catalogos,
    fusionar_catalogos,
    parsear_catalogo_crudo,
    seleccionar_claves,
)


def test_parsear_catalogo_normaliza_y_filtra_entradas_invalidas() -> None:
    raw = {
        " ui.clave ": " Texto ",
        None: "ignorar",
        "": "ignorar",
        123: b"bytes\r\ncon salto",
        "ui.none": None,
    }

    resultado = parsear_catalogo_crudo(raw)

    assert resultado == {
        "ui.clave": "Texto",
        "123": "bytes\ncon salto",
        "ui.none": "",
    }


def test_calcular_diff_catalogos_es_determinista() -> None:
    base = {"a": "1", "b": "2", "solo_base": "x"}
    objetivo = {"a": "1", "b": "3", "solo_objetivo": "y"}

    diff = calcular_diff_catalogos(base, objetivo)

    assert [item.clave for item in diff.missing] == ["solo_objetivo"]
    assert [item.clave for item in diff.extra] == ["solo_base"]
    assert [item.clave for item in diff.changed] == ["b"]
    assert diff.changed[0].texto_base == "2"
    assert diff.changed[0].texto_objetivo == "3"


def test_fusionar_catalogos_y_seleccionar_claves() -> None:
    base = {"a": "1", "b": "2"}
    sobreescrituras = {"b": "dos", "c": "3"}

    fusionado = fusionar_catalogos(base, sobreescrituras)
    seleccion = seleccionar_claves(fusionado, ("c", "a", "inexistente"))

    assert fusionado == {"a": "1", "b": "dos", "c": "3"}
    assert seleccion == {"c": "3", "a": "1"}
