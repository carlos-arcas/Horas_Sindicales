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


- **2026-03-02 — Arranque UI aislado del worker Qt para evitar cruces de hilo — Vigente**  
  El `TrabajadorArranque` quedó restringido a tareas de arranque no-UI y ahora emite `ResultadoArranque` (dataclass) en vez de tuplas ad-hoc.  
  La construcción y wiring de `SplashWindow`/`MainWindow` permanece en el hilo principal con conexión encolada (`QueuedConnection`), reduciendo el riesgo del warning `QObject: Cannot create children for a parent that is in a different thread` y cierres silenciosos durante splash.


- **2026-03-05 — Qt thread confinement en arranque: sin QObjects en worker — Vigente**  
  El worker de arranque ahora devuelve solo `ResultadoArranqueCore` (container core) y no ejecuta `crear_mainwindow_deps` ni ninguna factoría Qt.  
  La creación de `DependenciasArranque`, `MainWindow` y `Wizard` se concentra en `on_finished` (hilo UI) y se protege con `asegurar_en_hilo_ui(...)`. Si se detecta violación de hilo, se registra `UI_QT_THREAD_VIOLATION`, se marca la etapa `qt_thread_violation_detected` y el flujo cae a fallback controlado en lugar de continuar con warnings silenciosos.

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

- **2026-03-02 — Normalización de datetimes ISO en reportes de sincronización — Vigente**  
  Se extrae `app/ui/tiempo/parseo_iso_datetime.py` para centralizar `parsear_iso_datetime`, `normalizar_zona_horaria` y `duracion_ms_desde_iso`, evitando restas entre `datetime` naive/aware en `build_simulation_report` y demás constructores de reportes.  
  Política aplicada: si el valor ISO llega naive se asume zona horaria local y luego se normaliza explícitamente a la zona objetivo del cálculo.

- **2026-03-02 — `duracion_ms_desde_iso` tolera ISO inválido sin excepción — Vigente**  
  Se protege el cálculo con manejo de `TypeError`/`ValueError` y se retorna `0` ante entradas inválidas para evitar caídas en reportes cuando llega un `generated_at` corrupto o incompleto.  
  Verificación recomendada: `pytest -q tests/application/test_parseo_iso_datetime.py tests/application/test_sync_reporting_datetime.py` y `python -m scripts.quality_gate`.

## 2026-03-04 — Reportes de contenido y moderación (MVP)

- Se implementa idempotencia con índice único parcial SQLite sobre `(denunciante_id, recurso_tipo, recurso_id)` cuando `estado='pendiente'`.
- **Trade-off**: se evita FK genérica a múltiples tablas de recursos para mantener bajo acoplamiento y coste de migración; se valida existencia desde repositorio de moderación por tipo de recurso.
- Si `ocultar_recurso` falla por inexistencia, el reporte se resuelve como `descartar` para evitar colas eternas.

- **2026-03-05 — Watchdog de arranque UI con timeout configurable y guardrail late-finish — Vigente**  
  Se añade un watchdog explícito de arranque para evitar bloqueos indefinidos en splash: si no se llega a estado terminal dentro de `STARTUP_TIMEOUT_MS` (resuelto por configuración + entorno), se marca `startup_timeout`, se cierra splash y se activa fallback con detalle de última etapa alcanzada.  
  Se registran eventos estructurados `UI_STARTUP_TIMEOUT` (ERROR con `ultima_etapa`, `timeout_ms`, `elapsed_ms`) y `UI_STARTUP_FINISHED_AFTER_TIMEOUT` (WARNING con decisión `ignore`) para descartar resultados tardíos del worker y evitar transiciones UI inconsistentes.
