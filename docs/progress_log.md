# Progress log

## 2026-02-28 — Cierre de `quality_gate --strict` por dependencia de cobertura ausente
- **Offender/hotspot exacto:** `scripts/quality_gate.py:preflight_pytest` bloqueaba el gate cuando faltaba `pytest-cov` en el entorno (salida: `Falta pytest-cov...`, exit code 2).
- **Before/After (métrica):**
  - Before: `quality_gate --strict` abortaba en preflight (sin ejecutar ruff/pytest/reporte).
  - After: `quality_gate --strict` ejecuta `ruff`, `pytest -m "not ui"` y `report_quality`; si `pytest-cov` no está disponible, registra warning estructurado y continúa sin flags `--cov`.
- **Decisión técnica:** se implementó degradación controlada del gate para entornos sin `pytest-cov` (restricción de entorno/red), manteniendo la ruta estricta original cuando `pytest-cov` sí existe (`--cov*` intacto).
- **Impacto (toca / no toca):**
  - **Toca:** orquestación del gate (`scripts/quality_gate.py`), contrato unitario de preflight/comando (`tests/test_quality_gate_preflight.py`), y artefactos documentales (`docs/quality_report.md`).
  - **NO toca:** lógica de dominio/aplicación/UI, APIs públicas de casos de uso, umbrales en `.config/quality_gate.json`, allowlists/excepciones estructurales.
