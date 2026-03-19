from pathlib import Path

from app.ui.vistas.main_window.politica_solo_lectura import (
    ACCIONES_MUTANTES_AUDITADAS_UI,
)
from tests.application.test_read_only_inventory_guardrails import (
    ARCHIVOS_DUDOSOS,
    ARCHIVOS_MUTANTES_NEGOCIO,
    ARCHIVOS_SOLO_LECTURA,
)


def test_readonly_done_checklist_cubre_inventario_backend_y_ui() -> None:
    ruta = Path("docs/readonly_done_checklist.md")
    assert ruta.exists(), (
        "Falta docs/readonly_done_checklist.md; no se puede declarar el cierre auditable de readonly."
    )

    contenido = ruta.read_text(encoding="utf-8")
    referencias_obligatorias = [
        "Estado final",
        "Backend blindado",
        "UI preventiva cerrada",
        "Contrato estable",
        "Tests suficientes",
        "Sin deuda estructural evidente",
        "Evidencia de cierre",
        "Windows real",
        "python -m scripts.gate_pr",
    ]
    faltantes = [ref for ref in referencias_obligatorias if ref not in contenido]
    assert not faltantes, (
        "docs/readonly_done_checklist.md no cumple el contrato mínimo; faltan referencias: "
        + ", ".join(faltantes)
    )

    for relativo in sorted(ARCHIVOS_MUTANTES_NEGOCIO):
        assert relativo in contenido, f"Falta owner mutante auditado en checklist readonly: {relativo}"

    for relativo in sorted(ARCHIVOS_SOLO_LECTURA):
        assert relativo in contenido, f"Falta owner solo lectura auditado en checklist readonly: {relativo}"

    for relativo in sorted(ARCHIVOS_DUDOSOS):
        assert relativo in contenido, f"Falta owner dudoso documentado en checklist readonly: {relativo}"

    for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI:
        assert descriptor.object_name in contenido, (
            "Falta acción UI auditada en checklist readonly: "
            f"{descriptor.object_name}"
        )
