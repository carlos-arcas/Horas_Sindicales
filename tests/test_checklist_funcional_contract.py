import json
from pathlib import Path


ESTADOS_PERMITIDOS = {
    "Verificada",
    "Parcial",
    "No verificada",
    "No implementada",
}

PRIORIDADES_PERMITIDAS = {"Alta", "Media", "Baja"}


def test_checklist_funcional_contract() -> None:
    ruta = Path("docs/checklist_funcional.json")
    assert ruta.exists(), "Falta docs/checklist_funcional.json"

    data = json.loads(ruta.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "El checklist funcional debe ser un objeto JSON"

    funciones = data.get("funciones")
    assert isinstance(funciones, list) and funciones, "El checklist debe incluir una lista no vacía de funciones"

    ids = set()
    for funcion in funciones:
        assert isinstance(funcion, dict), "Cada función debe representarse como objeto"

        id_funcion = funcion.get("id")
        assert isinstance(id_funcion, str) and id_funcion.strip(), "Cada función necesita id"
        assert id_funcion not in ids, f"ID duplicado en checklist funcional: {id_funcion}"
        ids.add(id_funcion)

        descripcion = funcion.get("descripcion")
        assert isinstance(descripcion, str) and descripcion.strip(), f"{id_funcion} sin descripción humana"

        prioridad = funcion.get("prioridad")
        assert prioridad in PRIORIDADES_PERMITIDAS, f"{id_funcion} usa prioridad inválida: {prioridad}"

        estado_global = funcion.get("estado_global")
        assert estado_global in ESTADOS_PERMITIDOS, (
            f"{id_funcion} usa estado_global inválido: {estado_global}"
        )

        desglose = funcion.get("desglose")
        assert isinstance(desglose, dict), f"{id_funcion} debe incluir desglose por dimensión"

        for clave in ("logica", "ui", "validaciones_seguridad", "e2e"):
            assert clave in desglose, f"{id_funcion} no incluye desglose obligatorio: {clave}"
            assert desglose[clave] in ESTADOS_PERMITIDOS, (
                f"{id_funcion}/{clave} usa estado inválido: {desglose[clave]}"
            )

        evidencias = funcion.get("evidencias")
        assert isinstance(evidencias, list) and evidencias, f"{id_funcion} debe incluir evidencias"

    estados_catalogo = data.get("estados_permitidos")
    assert isinstance(estados_catalogo, list) and estados_catalogo, (
        "El checklist debe declarar estados_permitidos"
    )
    assert set(estados_catalogo) == ESTADOS_PERMITIDOS, (
        "estados_permitidos debe coincidir con el contrato esperado"
    )

    ruta_critica = data.get("ruta_critica_principal")
    assert isinstance(ruta_critica, list) and ruta_critica, "Debe existir ruta_critica_principal"

    invalidos = [id_funcion for id_funcion in ruta_critica if id_funcion not in ids]
    assert not invalidos, (
        "ruta_critica_principal referencia IDs inexistentes: " + ", ".join(invalidos)
    )
