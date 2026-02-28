import json
from pathlib import Path

from scripts.auditar_naming import construir_reporte


RAIZ = Path(__file__).resolve().parents[1]
BASELINE = RAIZ / ".config" / "naming_baseline.json"


def _cargar_baseline() -> dict[str, set[str]]:
    if not BASELINE.exists():
        raise AssertionError("Falta .config/naming_baseline.json para controlar regresión.")

    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    archivos = data.get("archivos_con_naming_ingles", [])
    simbolos = data.get("simbolos_publicos_en_ingles", [])

    if not isinstance(archivos, list) or not isinstance(simbolos, list):
        raise AssertionError("La baseline debe contener listas válidas de offenders.")

    return {
        "archivos": set(archivos),
        "simbolos": set(simbolos),
    }


def test_no_hay_nuevos_offenders_de_naming() -> None:
    baseline = _cargar_baseline()
    reporte = construir_reporte(raiz=RAIZ, umbral_offenders=10**9)

    archivos_actuales = set(reporte["archivos_con_naming_ingles"])
    simbolos_actuales = {
        f"{item['archivo']}::{item['simbolo']}"
        for item in reporte["simbolos_publicos_en_ingles"]
    }

    nuevos_archivos = sorted(archivos_actuales - baseline["archivos"])
    nuevos_simbolos = sorted(simbolos_actuales - baseline["simbolos"])

    assert not nuevos_archivos and not nuevos_simbolos, (
        "Se detectó regresión de naming debt.\n"
        "Nuevos archivos offenders:\n"
        + "\n".join(f"- {item}" for item in nuevos_archivos)
        + "\nNuevos símbolos offenders:\n"
        + "\n".join(f"- {item}" for item in nuevos_simbolos)
        + "\n\nSi la deuda nueva es intencional, actualizar .config/naming_baseline.json "
        "en el mismo PR con justificación explícita."
    )
