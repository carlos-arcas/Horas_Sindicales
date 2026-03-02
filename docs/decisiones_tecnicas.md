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

- **2026-02-25 — Colisiones horarias de pendientes acotadas por delegada (`persona_id`) — Vigente**  
  Diagnóstico: la detección de solapes en pendientes agrupaba sólo por `fecha_pedida`, lo que marcaba falsos conflictos entre delegadas distintas. Se corrige para evaluar por `(persona_id, fecha_pedida)` y mantener el bloqueo sólo dentro de la misma delegada.

- **2026-03-01 — Reglas de filtrado de histórico movidas de UI a aplicación — Vigente**  
  Antes: `app/ui/vistas/historico_filter_rules.py` contenía lógica de aceptación/descartes por estado, rango y búsqueda. Después: reglas puras en `app/domain/services.py`, y el módulo UI queda como shim de compatibilidad sin negocio. Se refuerza con guard de imports entre capas.

- **2026-03-02 — Validación explícita de `action_callback` en `ToastManager` — Vigente**  
  Se endurece la compatibilidad de kwargs en toasts: `success/error` mantienen soporte para `action_label/action_callback`, pero ahora rechazan callbacks no invocables con `ValueError` y logging estructurado (`toast_action_callback_invalido`). Esto evita errores silenciosos y asegura contratos de firma con tests unitarios puros (`inspect.signature`).

## Procedimiento de actualización

1. Añadir una nueva entrada con fecha ISO (`YYYY-MM-DD`).
2. Indicar estado (`Vigente`, `Revisar`, `Deprecada`).
3. Resumir impacto técnico (build, runtime, calidad o trazabilidad).
4. Referenciar docs complementarias cuando aplique (`guia_pruebas`, `guia_logging`, arquitectura).

## Pendiente de completar

- Pendiente de completar un ADR formal por cada integración externa crítica si auditoría lo exige.

- **2026-03-01 — Wiring perezoso de preferencias con fallback INI headless — Vigente**  
  `build_container()` deja de importar `QSettings` en import-time y resuelve el adaptador en runtime para evitar fallos en colección de tests UI en CI sin backend Qt completo.  
  Si `infraestructura.repositorio_preferencias_qsettings` no está disponible, se registra `RepositorioPreferenciasIni` (sin PySide6) y se emite WARNING estructurado para trazabilidad operativa.  
  La aplicación sigue dependiendo del puerto `IRepositorioPreferencias`; las implementaciones concretas permanecen en infraestructura, preservando inversión de dependencias y compatibilidad Windows.
