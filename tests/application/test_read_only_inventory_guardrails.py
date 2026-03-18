from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ARCHIVOS_MUTANTES_NEGOCIO = {
    "app/application/use_cases/cargar_datos_demo_caso_uso.py",
    "app/application/use_cases/confirmacion_pdf/caso_uso.py",
    "app/application/use_cases/exportar_compartir_periodo.py",
    "app/application/use_cases/grupos_config/use_case.py",
    "app/application/use_cases/personas/use_case.py",
    "app/application/use_cases/solicitudes/crear_pendiente_caso_uso.py",
    "app/application/use_cases/solicitudes/use_case.py",
}

ARCHIVOS_SOLO_LECTURA = {
    "app/application/use_cases/alert_engine.py",
    "app/application/use_cases/health_check.py",
    "app/application/use_cases/retry_sync_use_case.py",
}

ARCHIVOS_DUDOSOS = {
    "app/application/use_cases/validacion_preventiva_lock_use_case.py": (
        "Ejecuta callbacks potencialmente mutantes, pero no define ni posee la mutación "
        "de negocio; solo clasifica errores de lock."
    ),
}


def _leer(relativo: str) -> str:
    return (PROJECT_ROOT / relativo).read_text(encoding="utf-8")


def _importa_politica(relativo: str) -> bool:
    tree = ast.parse(_leer(relativo), filename=relativo)
    for nodo in ast.walk(tree):
        if isinstance(nodo, ast.ImportFrom) and nodo.module == "app.application.use_cases.politica_modo_solo_lectura":
            return True
    return False


def test_inventario_repo_wide_de_owners_auditados_se_mantiene_estable() -> None:
    assert ARCHIVOS_MUTANTES_NEGOCIO == {
        "app/application/use_cases/cargar_datos_demo_caso_uso.py",
        "app/application/use_cases/confirmacion_pdf/caso_uso.py",
        "app/application/use_cases/exportar_compartir_periodo.py",
        "app/application/use_cases/grupos_config/use_case.py",
        "app/application/use_cases/personas/use_case.py",
        "app/application/use_cases/solicitudes/crear_pendiente_caso_uso.py",
        "app/application/use_cases/solicitudes/use_case.py",
    }
    assert ARCHIVOS_SOLO_LECTURA == {
        "app/application/use_cases/alert_engine.py",
        "app/application/use_cases/health_check.py",
        "app/application/use_cases/retry_sync_use_case.py",
    }
    assert set(ARCHIVOS_DUDOSOS) == {
        "app/application/use_cases/validacion_preventiva_lock_use_case.py"
    }


def test_mutantes_auditados_dependen_de_politica_modo_solo_lectura() -> None:
    faltantes = [relativo for relativo in sorted(ARCHIVOS_MUTANTES_NEGOCIO) if not _importa_politica(relativo)]
    assert not faltantes, "Todo owner mutante auditado debe importar e inyectar la política:\n" + "\n".join(faltantes)


def test_owners_solo_lectura_auditados_no_arrastran_politica() -> None:
    sobrantes = [relativo for relativo in sorted(ARCHIVOS_SOLO_LECTURA) if _importa_politica(relativo)]
    assert not sobrantes, "Los owners auditados como solo lectura deben permanecer limpios:\n" + "\n".join(sobrantes)


def test_owners_dudosos_quedan_documentados_con_justificacion() -> None:
    justificaciones_vacias = [relativo for relativo, justificacion in ARCHIVOS_DUDOSOS.items() if not justificacion.strip()]
    assert not justificaciones_vacias
