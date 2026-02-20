import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
BASELINE_PATH = ROOT / "configuracion" / "baseline_naming.json"
PATRON_ARCHIVO_SNAKE_CASE = re.compile(r"[a-z0-9_]+\.py")


def _cargar_baseline() -> set[str]:
    if not BASELINE_PATH.exists():
        raise AssertionError(
            "Falta configuracion/baseline_naming.json. "
            "Debe existir para grandfathering controlado."
        )

    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    rutas = data.get("archivos_existentes_permitidos", [])

    if not isinstance(rutas, list):
        raise AssertionError(
            "configuracion/baseline_naming.json debe contener "
            "'archivos_existentes_permitidos' como lista."
        )

    return {str(ruta).replace("\\", "/") for ruta in rutas}


def test_guardarrail_naming_archivos_python_en_app() -> None:
    baseline = _cargar_baseline()
    rutas_invalidas: list[str] = []

    for ruta in sorted(APP_DIR.rglob("*.py")):
        ruta_relativa = ruta.relative_to(ROOT).as_posix()

        if ruta_relativa in baseline:
            continue

        nombre = ruta.name

        if nombre == "__init__.py":
            continue

        tiene_espacios = " " in nombre
        tiene_mayusculas = any(caracter.isupper() for caracter in nombre)
        cumple_snake_case = bool(PATRON_ARCHIVO_SNAKE_CASE.fullmatch(nombre))

        if tiene_espacios or tiene_mayusculas or not cumple_snake_case:
            rutas_invalidas.append(ruta_relativa)

    assert not rutas_invalidas, (
        "Se detectaron archivos nuevos fuera de convención de naming en app/:\n"
        + "\n".join(f"- {ruta}" for ruta in rutas_invalidas)
        + "\n\nResolución:\n"
        "1) Renombrar a snake_case ([a-z0-9_]+.py), sin espacios ni mayúsculas.\n"
        "2) Si es una excepción temporal justificada, agregar la ruta en "
        "configuracion/baseline_naming.json -> archivos_existentes_permitidos."
    )
