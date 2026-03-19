from __future__ import annotations

import json
from pathlib import Path


DOC = Path("docs/validacion_windows_real.md")
SCRIPT = Path("scripts/validar_windows_real.bat")
CHECKLIST = Path("docs/checklist_funcional.json")
DEFINICION = Path("docs/definicion_producto_final.md")


def test_paquete_validacion_windows_real_existe() -> None:
    assert DOC.exists(), "Debe existir docs/validacion_windows_real.md como guía auditable."
    assert SCRIPT.exists(), "Debe existir scripts/validar_windows_real.bat para preparar evidencia en Windows real."


def test_guia_windows_real_incluye_pasos_comandos_y_dictamen() -> None:
    contenido = DOC.read_text(encoding="utf-8")

    referencias_obligatorias = [
        "scripts\\validar_windows_real.bat",
        "setup.bat",
        "lanzar_app.bat",
        "ejecutar_tests.bat",
        "quality_gate.bat",
        "auditar_e2e.bat --dry-run",
        "auditar_e2e.bat --write",
        "launcher.bat",
        "logs\\windows_real\\<run_id>",
        "logs\\seguimiento.log",
        "PASS",
        "FAIL",
        "WARNING",
        "PRODUCTO CERRADO",
        "PRODUCTO CANDIDATO A CIERRE",
        "PRODUCTO NO CERRADO",
        "Qué revisar visualmente",
        "Evidencia auditable mínima",
    ]

    faltantes = [ref for ref in referencias_obligatorias if ref not in contenido]
    assert not faltantes, (
        "La guía de Windows real no cumple el contrato mínimo; faltan referencias: "
        + ", ".join(faltantes)
    )


def test_script_validacion_windows_real_crea_run_dir_y_plantilla() -> None:
    contenido = SCRIPT.read_text(encoding="utf-8", errors="ignore").lower()

    for token in (
        "%~dp0",
        "logs\\windows_real",
        "resumen_validacion_windows_real.txt",
        "entorno.txt",
        "pasos_ejecutados.txt",
        "setup.bat",
        "lanzar_app.bat",
        "ejecutar_tests.bat",
        "quality_gate.bat",
        "auditar_e2e.bat --dry-run",
        "auditar_e2e.bat --write",
        "launcher.bat",
    ):
        assert token in contenido, f"scripts/validar_windows_real.bat debe incluir '{token}'."


def test_estado_windows_pendiente_queda_alineado_en_docs() -> None:
    definicion = DEFINICION.read_text(encoding="utf-8")
    assert "PRODUCTO CANDIDATO A CIERRE" in definicion
    assert "validación manual final en una máquina Windows real" in definicion
    assert "docs/validacion_windows_real.md" in definicion

    data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    fun_001 = next(func for func in data["funciones"] if func["id"] == "FUN-001")
    assert fun_001["estado_global"] == "Parcial", (
        "FUN-001 no debe marcarse como completada mientras Windows real siga pendiente."
    )
    assert "Windows sigue pendiente" in fun_001["observaciones"] or "Windows sigue pendiente".lower() in fun_001["observaciones"].lower()
