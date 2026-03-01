# Auditoría refactor UI `MainWindow` (state_controller)

## Objetivo
Garantizar que el refactor de `MainWindow` mejora cohesión y mantenibilidad sin introducir regresiones de calidad en CI/local.

## Árbol de archivos auditados

```text
app/ui/vistas/main_window/
├── state_actions.py
├── state_bindings.py
├── state_controller.py
├── state_helpers.py
└── state_validations.py

tests/
├── test_quality_gate_metrics.py
├── test_quality_gate_metrics_guard.py
└── ui/test_state_helpers.py
```

## Responsabilidades por módulo

- `state_controller.py`: composición principal, wiring de servicios y estado compartido de la ventana.
- `state_actions.py`: acciones de UI y flujos de interacción (confirmación, modales, refresh).
- `state_bindings.py`: enlaces de señales/eventos y binding de acciones.
- `state_helpers.py`: utilidades puras de estado, priorización y normalización.
- `state_validations.py`: validaciones de estado/entrada para operaciones de la UI.

## Métricas LOC/CC y determinismo del gate

- Se mantiene el test contractual `tests/test_quality_gate_metrics.py::test_quality_gate_size_and_complexity`.
- El test de métricas ahora es **100% headless**:
  - lee fuentes con `Path`;
  - carga umbrales (`MAX_LOC_POR_ARCHIVO`, `MAX_CC_POR_FUNCION`, excepciones) por análisis estático (`ast`) de `app/configuracion/calidad.py`;
  - no importa módulos `app.*`, evitando side effects de Qt.
- `radon==6.0.1` continúa fijado en dependencias dev (`requirements-dev.txt`) para ejecución determinista en CI/local.
- `scripts/quality_gate.py` ahora falla en preflight si falta `radon`, evitando `SKIP` silencioso del gate LOC/CC.

## Riesgos detectados y mitigaciones

### 1) Side effects de Qt durante métricas
- **Riesgo:** import accidental de módulos UI al evaluar LOC/CC.
- **Mitigación:** guard dedicado `tests/test_quality_gate_metrics_guard.py` que falla si el test de métricas importa `app.*`.

### 2) `SKIP` en CI por dependencia faltante
- **Riesgo:** `pytest.importorskip("radon")` oculta fallo de preparación del entorno.
- **Mitigación:**
  - `quality_gate.py` valida `radon` en preflight y termina con error explícito si falta;
  - guard en CI (`test_radon_obligatorio_en_ci_para_quality_gate`) exige disponibilidad de `radon` cuando `CI=true`.

### 3) Imports circulares tras extracción de módulos
- **Riesgo:** dependencia circular entre `state_controller` y mixins auxiliares.
- **Mitigación:** validación por suite de arquitectura/imports y smoke tests de estructura de módulos UI.

## Estado

✅ Refactor consistente y gate de métricas reforzado para ejecución determinista en entornos headless.
