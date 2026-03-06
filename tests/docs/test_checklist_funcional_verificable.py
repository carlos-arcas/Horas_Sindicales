from __future__ import annotations

import json
from pathlib import Path

ESTADOS_PERMITIDOS = {"Verificada", "Parcial", "No verificada", "No implementada"}
PRIORIDADES_PERMITIDAS = {"Alta", "Media", "Baja"}


def test_checklist_funcional_verificable_json_tiene_estructura_valida() -> None:
    ruta = Path("docs/checklist_funcional_verificable.json")
    assert ruta.exists(), "Debe existir docs/checklist_funcional_verificable.json"

    contenido = json.loads(ruta.read_text(encoding="utf-8"))

    assert "funciones" in contenido
    assert isinstance(contenido["funciones"], list)
    assert contenido["funciones"], "La lista de funciones no puede ser vacía"

    ids_funciones: set[str] = set()

    for funcion in contenido["funciones"]:
        assert "id" in funcion
        assert "descripcion" in funcion
        assert "prioridad" in funcion
        assert "estado_global" in funcion
        assert "logica" in funcion
        assert "ui" in funcion
        assert "validaciones" in funcion
        assert "e2e" in funcion

        assert isinstance(funcion["id"], str)
        assert isinstance(funcion["descripcion"], str)
        assert funcion["id"].strip()
        assert funcion["descripcion"].strip()

        assert funcion["prioridad"] in PRIORIDADES_PERMITIDAS
        assert funcion["estado_global"] in ESTADOS_PERMITIDOS
        assert funcion["logica"] in ESTADOS_PERMITIDOS
        assert funcion["ui"] in ESTADOS_PERMITIDOS
        assert funcion["validaciones"] in ESTADOS_PERMITIDOS
        assert funcion["e2e"] in ESTADOS_PERMITIDOS

        ids_funciones.add(funcion["id"])

    assert "ruta_critica" in contenido
    assert isinstance(contenido["ruta_critica"], list)
    assert contenido["ruta_critica"], "ruta_critica no puede estar vacía"

    for funcion_id in contenido["ruta_critica"]:
        assert funcion_id in ids_funciones, f"ID de ruta_critica inexistente: {funcion_id}"
