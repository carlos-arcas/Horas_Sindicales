# Decisiones técnicas

## Registro de decisiones relevantes

> Formato: `Fecha — Decisión — Estado — Justificación`.

- **2026-02-20 — Lockfiles pinneados (`requirements.txt` y `requirements-dev.txt`) — Vigente**  
  Se mantiene instalación reproducible entre local, CI y scripts de Windows.

- **2026-02-20 — Fuentes editables separadas (`requirements.in` / `requirements-dev.in`) — Vigente**  
  La edición se hace en `.in`; los `.txt` se regeneran con `pip-compile`.

- **2026-02-20 — Logging estructurado JSONL con trazabilidad (`correlation_id`) — Vigente**  
  Facilita auditoría y seguimiento extremo a extremo de operaciones críticas.

- **2026-02-20 — Estrategia de pruebas con `pytest` y cobertura (`--cov`) — Vigente**  
  Se estandariza ejecución local, en Windows y en pipelines con umbral de cobertura.

- **2026-02-20 — Normalización documental: canonical en `/docs` para arquitectura — Vigente**  
  `arquitectura.md` de raíz pasa a stub de redirección para evitar duplicidad confusa.

- **2026-02-20 — Duplicidad de changelog: canonical en raíz (`CHANGELOG.md`) — Vigente**  
  `docs/CHANGELOG.md` queda como stub/enlace de compatibilidad para consulta rápida.

## Procedimiento de actualización

1. Añadir una nueva entrada con fecha ISO (`YYYY-MM-DD`).
2. Indicar estado (`Vigente`, `Revisar`, `Deprecada`).
3. Resumir impacto técnico (build, runtime, calidad o trazabilidad).
4. Referenciar docs complementarias cuando aplique (`guia_pruebas`, `guia_logging`, arquitectura).

## Pendiente de completar

- Pendiente de completar un ADR formal por cada integración externa crítica si auditoría lo exige.
