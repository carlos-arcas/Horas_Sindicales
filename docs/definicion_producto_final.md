# Definición de Producto Final

## Nivel declarado

**Nivel 4 — Producto profesional reproducible**.

Este documento define el criterio auditable de cierre para declarar que el producto está terminado en términos operativos, de calidad y de trazabilidad. La aprobación final no depende de opiniones: depende de evidencia verificable en el repositorio y de ejecución real en Windows.

## Entrypoints oficiales

Los siguientes entrypoints son la forma oficial de uso del producto y de su validación:

- **Lanzar app (Windows, doble clic):** `lanzar_app.bat`
- **Ejecutar tests (Windows):** `ejecutar_tests.bat`
- **Quality gate (Windows):** `quality_gate.bat`
- **Auditor E2E (CLI exacto):** `python -m app.entrypoints.cli_auditoria --dry-run`

Para ejecución de auditoría con escritura de evidencias (modo no simulación), el comando base es:

- `python -m app.entrypoints.cli_auditoria`

## Checklist auditable (PASS/FAIL manual)

> Marcar cada punto como **PASS** o **FAIL** con evidencia asociada (comando, archivo, captura o artefacto).

### A) Arquitectura Clean

- [ ] PASS / [ ] FAIL — La estructura mantiene capas separadas (`domain`, `application`, `infrastructure`, `entrypoints`, `ui`) sin mezclar reglas de negocio en infraestructura/UI.
- [ ] PASS / [ ] FAIL — Las dependencias entre capas respetan el diseño documentado.

### B) Testing (incluye cobertura >=85%)

- [ ] PASS / [ ] FAIL — `pytest -q` finaliza en verde.
- [ ] PASS / [ ] FAIL — Se ejecuta cobertura con `pytest --cov` y el resultado global es **>= 85%** según la política del proyecto.
- [ ] PASS / [ ] FAIL — Existen pruebas de regresión para funcionalidades críticas.

### C) Observabilidad (JSONL + rotación + crashes.log + correlation_id)

- [ ] PASS / [ ] FAIL — Se generan logs operativos en formato JSONL.
- [ ] PASS / [ ] FAIL — Existe rotación de logs configurada y validada.
- [ ] PASS / [ ] FAIL — Se registra error en `crashes.log` ante fallo controlado.
- [ ] PASS / [ ] FAIL — Se registra seguimiento en `seguimiento.log`.
- [ ] PASS / [ ] FAIL — Cada operación relevante incluye `correlation_id` para trazabilidad.

### D) Robustez UI/CLI (incidente con ID)

- [ ] PASS / [ ] FAIL — Ante error en UI o CLI, el sistema devuelve un incidente identificable con ID.
- [ ] PASS / [ ] FAIL — El incidente permite localizar evidencia en logs sin ambigüedad.

### E) Reproducibilidad Windows (doble clic)

- [ ] PASS / [ ] FAIL — `lanzar_app.bat` permite abrir la aplicación en Windows real.
- [ ] PASS / [ ] FAIL — `ejecutar_tests.bat` corre pruebas en Windows sin pasos manuales ocultos.
- [ ] PASS / [ ] FAIL — `quality_gate.bat` ejecuta los controles de calidad esperados.

### F) Auditoría E2E (dry-run + write + evidencias)

- [ ] PASS / [ ] FAIL — `Auditor E2E` en dry-run (`python -m app.entrypoints.cli_auditoria --dry-run`) no escribe artefactos de salida.
- [ ] PASS / [ ] FAIL — Auditoría E2E en modo escritura (`python -m app.entrypoints.cli_auditoria`) genera evidencias.
- [ ] PASS / [ ] FAIL — Las evidencias son rastreables y quedan disponibles para revisión.

### G) Docs mínimas

- [ ] PASS / [ ] FAIL — Existe documentación mínima de arquitectura, pruebas, logging y operación.
- [ ] PASS / [ ] FAIL — Este documento (`docs/definicion_producto_final.md`) está actualizado con el estado real.

### H) Versionado (VERSION + CHANGELOG)

- [ ] PASS / [ ] FAIL — `VERSION` refleja la versión candidata a cierre.
- [ ] PASS / [ ] FAIL — `CHANGELOG`/`CHANGELOG.md` contiene cambios verificables de la versión.

### I) Guardarraíles (prints, naming, métricas, secretos)

- [ ] PASS / [ ] FAIL — No se introducen `print` de depuración en código de producción.
- [ ] PASS / [ ] FAIL — Se respetan convenciones de naming del proyecto.
- [ ] PASS / [ ] FAIL — Se mantienen métricas y controles de calidad definidos.
- [ ] PASS / [ ] FAIL — No se exponen secretos en código, logs o configuración versionada.

## Criterio de realidad

**Si falla en Windows real, NO aprobado.**

No se acepta el cierre por “funciona en mi máquina Linux/macOS” ni por validación parcial en CI. El estado de producto final exige comportamiento reproducible en el entorno operativo objetivo.

## Cómo validar en una máquina limpia

1. Clonar el repositorio en una máquina Windows sin estado previo del proyecto.
2. Verificar que existen los entrypoints oficiales en raíz: `lanzar_app.bat`, `ejecutar_tests.bat`, `quality_gate.bat`.
3. Ejecutar `lanzar_app.bat` con doble clic y comprobar arranque de la app.
4. Ejecutar `ejecutar_tests.bat` y confirmar suite de pruebas sin fallos.
5. Ejecutar `quality_gate.bat` y confirmar que no reporta bloqueos.
6. Ejecutar auditoría E2E en simulación: `python -m app.entrypoints.cli_auditoria --dry-run`.
7. Ejecutar auditoría E2E en modo escritura: `python -m app.entrypoints.cli_auditoria`.
8. Revisar evidencias y logs (`seguimiento.log`, `crashes.log`) para confirmar trazabilidad.
9. Confirmar versionado: archivo `VERSION` y registro de cambios en `CHANGELOG`.
10. Marcar checklist A–I con evidencia adjunta y dictaminar PASS/FAIL final.

## Condición de cierre

Solo se puede declarar “Producto Final” cuando todos los puntos A–I estén en PASS con evidencia verificable y el criterio de realidad quede satisfecho en Windows real.
