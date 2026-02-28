# Auditoría técnica v7 — Horas Sindicales

## 1) Resumen ejecutivo
Este repositorio implementa una aplicación de escritorio (PySide6) para gestión de horas sindicales, solicitudes y sincronización bidireccional con Google Sheets usando SQLite local como fuente de estado y buffer operativo. Evidencia: `README.md`, `app/application/use_cases/sync_sheets/use_case.py`, `app/infrastructure/repos_sqlite.py`.

A nivel técnico, el proyecto **sí demuestra señales de seniority real** en varias áreas: arquitectura por capas con tests de reglas de imports, separación de puertos/protocolos, planner puro de acciones para el pull, controles de conflicto explícitos, savepoints/rollback en sync, retries de lock/rate limit, y una batería de tests amplia (incluye E2E sync y fuzz determinista). Evidencia: `tests/test_architecture_imports.py`, `app/domain/ports.py`, `app/application/use_cases/sync_sheets/action_planning.py`, `tests/e2e_sync/test_sync_sheets_e2e.py`, `tests/e2e_sync/test_sync_sheets_fuzz_light.py`.

Como base de producto, es **vendible como MVP B2B vertical** para secciones sindicales/representación laboral con necesidad de trazabilidad y workflow operativo. Como SaaS multi-tenant aún está verde: falta estrategia clara de despliegue, modelo de tenants, seguridad avanzada, soporte offline robusto con reconciliación formal y automatización de packaging/release cross-platform más madura.

Veredicto ejecutivo:
- **Contratable**: sí, perfil Senior Backend/Application + Desktop Product Engineer (fuerte en diseño pragmático, calidad y robustez operativa local).
- **Vendible hoy**: sí, como producto de nicho “single-organization / desktop-managed sync”.
- **Vendible como SaaS escalable**: no todavía; requiere hardening de seguridad/operación/observabilidad y empaquetado comercial.

Prioridad estratégica: convertir la robustez interna ya existente en una propuesta comercial demostrable (demo reproducible + métricas + packaging + operación de incidencias).

---

## 2) Evaluación por ejes (0-10)

| Eje | Nota | Justificación técnica (resumen) |
|---|---:|---|
| Arquitectura | **8.5** | Capas bien delimitadas y testeadas por reglas AST/import; puertos en `domain`, adaptadores en `infrastructure`, casos de uso en `application`. Persisten módulos muy grandes que elevan coste de cambio. |
| Robustez del Sync | **8.0** | Idempotencia y conflictos cubiertos en unit+e2e+fuzz; uso de savepoints y rollback parcial; retries en rate-limit y lock. Falta formalizar estrategia de compensación/event sourcing para escenarios extremos. |
| Persistencia | **7.8** | Contratos SQLite con validación de placeholders, migraciones y backfills, índices de UUID, tests de orden de parámetros. Riesgos en SQL dinámico puntual (f-string tabla) y constraints insuficientes para algunas invariantes. |
| Observabilidad | **7.0** | Correlation/result IDs y logging estructurado operativo. Falta estandarizar incident_id en toda la superficie y métricas de negocio/latencia exportables. |
| Calidad | **8.3** | Suite extensa y diversa (unit, contract, integration, e2e sync, fuzz determinista, smoke UI, guardrails arquitectura). Quality gate local bloqueado por dependencia faltante en este entorno (`pytest-cov`). |
| DX/Operación | **7.5** | Makefile + scripts + CI por jobs (core/ui smoke/ui extended), release scripts Windows. Aún hay fricción para reproducir cobertura y ausencia de pipeline de distribución artefactada por canal. |
| Seguridad básica | **6.8** | Buenas prácticas base (parametrización SQL mayoritaria, test anti secretos). Faltan controles de secretos en runtime, hardening de entradas/sanitización más sistemática y threat model/documentación de riesgos de credenciales. |

### Evidencias por eje

#### Arquitectura
- Reglas explícitas de dependencia entre capas y prohibición de imports técnicos en `application`. Evidencia: `tests/test_architecture_imports.py`.
- Puertos/protocolos definidos de forma amplia en dominio (`PersonaRepository`, `SheetsSyncPort`, etc.). Evidencia: `app/domain/ports.py`.
- Wiring centralizado en container bootstrap. Evidencia: `app/bootstrap/container.py`.

#### Robustez del Sync
- Política de conflictos explícita (`evaluate_conflict_policy`, outcomes). Evidencia: `app/application/use_cases/sync_sheets/conflict_policy.py`.
- Motor de conflicto temporal (`is_conflict`) con `last_sync_at` y timestamps locales/remotos. Evidencia: `app/application/use_cases/sync_sheets/conflicts.py`.
- Savepoint/rollback en pull de solicitudes para evitar corrupción parcial. Evidencia: `app/application/use_cases/sync_sheets/use_case.py` (bloque `SAVEPOINT pull_solicitudes_worksheet`).
- Planner puro de acciones (`PullAction`) + handlers explícitos por comando. Evidencia: `app/application/use_cases/sync_sheets/action_planning.py`, `app/application/use_cases/sync_sheets/use_case.py` (`_apply_action` y handlers).
- E2E de idempotencia/conflicto/retry/rollback y fuzz determinista. Evidencia: `tests/e2e_sync/test_sync_sheets_e2e.py`, `tests/e2e_sync/test_sync_sheets_fuzz_light.py`.

#### Persistencia
- Contratos de operaciones SQL críticas aisladas en `persistence_ops`. Evidencia: `app/application/use_cases/sync_sheets/persistence_ops.py`.
- Tests de contrato de orden de placeholders/parámetros y dedupe local. Evidencia: `tests/application/use_cases/sync_sheets/test_persistence_ops_sqlite_contract.py`.
- Builders SQL/params desacoplados con tests dedicados. Evidencia: `app/infrastructure/repos_sqlite_builders.py`, `tests/infrastructure/test_repos_sqlite_builders.py`.
- Migraciones con índices únicos de UUID y script Python de backfill legacy. Evidencia: `migrations/002_sync_indexes.up.sql`, `migrations/003_data_backfill.up.py`.

#### Observabilidad
- Contextvars para `correlation_id` y `result_id`, helper de `log_event`. Evidencia: `app/core/observability.py`.
- Logging operativo en bootstrap/smoke scripts y quality gate con mensajes accionables. Evidencia: `scripts/preflight_tests.py`, `scripts/quality_gate.py`.

#### Calidad
- Reglas de arquitectura, smoke UI, test de secretos, contracts de scripts y múltiples suites funcionales. Evidencia: carpeta `tests/`.
- En este entorno, `quality_gate.py` falla por prerequisito faltante (`pytest-cov`), pero de forma controlada/documentada. Evidencia: salida de comando ejecutado + `scripts/quality_gate.py` + `docs/quality_gate_evidencia.md`.

#### DX/Operación
- CI multi-job con matrix Python, artefactos de quality report, smoke UI y extended UI. Evidencia: `.github/workflows/ci.yml`.
- Make targets y scripts de release/validación. Evidencia: `Makefile`, `scripts/release/*`, `menu_validacion.bat`.

#### Seguridad básica
- Guardrail de secretos en tests. Evidencia: `tests/test_no_secrets_committed.py`.
- Parametrización SQL predominante + validación de placeholders en repos/ops. Evidencia: `app/infrastructure/repos_sqlite.py` (`_execute_with_validation`), `app/application/use_cases/sync_sheets/persistence_ops.py`.
- Riesgo residual: SQL dinámico de nombre de tabla (controlado por allowlist) en `backfill_uuid`; si la allowlist derivara de entrada no confiable, habría vector. Evidencia: `app/application/use_cases/sync_sheets/persistence_ops.py`.

---

## 3) “Pruebas” de madurez

### 3.1 Señales de seniority presentes (12)
1. **Arquitectura verificada automáticamente** (no solo documentada). Evidencia: `tests/test_architecture_imports.py`.
2. **Puertos/protocolos explícitos para inversión de dependencias**. Evidencia: `app/domain/ports.py`.
3. **Wiring centralizado y reproducible** en container bootstrap. Evidencia: `app/bootstrap/container.py`.
4. **Planner puro (`PullAction`)** separando decisión de ejecución. Evidencia: `app/application/use_cases/sync_sheets/action_planning.py`.
5. **Handlers por acción** en pull con dispatch explícito. Evidencia: `app/application/use_cases/sync_sheets/use_case.py` (`_apply_action`).
6. **Control transaccional fino con SAVEPOINT/ROLLBACK** en sincronización parcial. Evidencia: `app/application/use_cases/sync_sheets/use_case.py`.
7. **Política de conflictos formalizada** con resultado tipado (`ConflictOutcome`). Evidencia: `app/application/use_cases/sync_sheets/conflict_policy.py`.
8. **Retries frente a lock SQLite** con backoff incremental. Evidencia: `app/infrastructure/repos_sqlite.py` (`_run_with_locked_retry`).
9. **Retries frente a rate-limit de Sheets** en cliente infra. Evidencia: `app/infrastructure/sheets_client.py`.
10. **Contratos de persistencia con foco en orden de parámetros** para evitar bugs silenciosos. Evidencia: `tests/application/use_cases/sync_sheets/test_persistence_ops_sqlite_contract.py`.
11. **Fuzz ligero determinista** para robustez de sync con seed fija. Evidencia: `tests/e2e_sync/test_sync_sheets_fuzz_light.py`.
12. **Quality reports automatizados (LOC/complejidad/cobertura por paquete)**. Evidencia: `scripts/report_quality.py`, `logs/quality_report.txt`.

### 3.2 Señales de deuda o “aún no senior” (12)
1. **Módulos demasiado grandes** (p.ej. UI principal >2600 LOC). Evidencia: `logs/quality_report.txt`.
2. **Fallback de complejidad por falta de `radon`** (no hay métrica CC real en este entorno). Evidencia: salida `python scripts/report_quality.py`.
3. **Quality gate no ejecutable completo localmente sin deps dev**. Evidencia: salida `python scripts/quality_gate.py`.
4. **Cobertura por paquete no disponible en entorno actual (.coverage ausente)**. Evidencia: `logs/quality_report.txt`.
5. **Acoplamiento operativo a desktop + Sheets**; falta estrategia server/SaaS multi-tenant.
6. **Observabilidad incompleta en incident response** (README marca `incident_id` como pendiente). Evidencia: `README.md`.
7. **Riesgo de deuda por duplicación de módulos/aliases legacy** (`dominio`, `aplicacion`, `presentacion`). Evidencia: árbol repo + `tests/test_spanish_layer_packages_are_thin.py`.
8. **Falta de métricas de rendimiento end-to-end persistidas** (latencias por fase, throughput por sync).
9. **No hay evidencia de pruebas de carga/concurrencia reales** más allá de lock retry.
10. **No hay estrategia formal de backup/restore y migración de cliente en campo** documentada a nivel operación comercial.
11. **UI test strategy sigue muy orientada a smoke/unit**; sin automatización visual/regresión de interacción completa.
12. **No se observa pipeline de release firmada/notarizada** para distribución empresarial masiva.

---

## 4) Top 12 riesgos actuales (severidad x probabilidad)

| # | Riesgo | Severidad | Prob. | Impacto | Causa raíz | Evidencia | Solución concreta |
|---:|---|---|---|---|---|---|---|
| 1 | Complejidad/cambio riesgoso en módulos gigantes | Alta | Alta | Bugs de regresión y baja velocidad | Concentración de lógica en pocos archivos | `logs/quality_report.txt` (top LOC) | Refactor por bounded contexts + extraer servicios puros + límites de LOC por PR |
| 2 | Gate de cobertura no reproducible en entornos sin deps dev | Alta | Media | Falsos bloqueos y fricción CI/local | Dependencia explícita de `pytest-cov`/`coverage` | salida `quality_gate.py`, `scripts/preflight_tests.py` | Añadir bootstrap one-command (`make bootstrap-dev`) + validación temprana en onboarding |
| 3 | Cobertura de UI no contractual | Media | Alta | Riesgo de regresiones UX no detectadas por línea | Scope CORE excluye `app/ui` | `docs/coverage_policy.md`, `docs/coverage_scope.md` | Mantener exclusión de línea pero añadir smoke E2E guiados + test plan manual versionado |
| 4 | SQL dinámico puntual en backfill | Media | Baja | Potencial inyección si allowlist se degrada | f-string con tabla dinámica | `persistence_ops.backfill_uuid` | Mantener allowlist cerrada + test de seguridad específico + encapsular por enum |
| 5 | Invariantes DB incompletas (más checks/foreign keys/unique funcionales) | Alta | Media | Datos inconsistentes en edge cases | Esquema inicial permisivo | `migrations/001_initial_schema.up.sql` | Fortalecer constraints gradualmente + migraciones seguras con data fixups |
| 6 | Observabilidad parcial para soporte productivo | Media | Media | MTTR alto ante incidencias reales | No hay incident_id transversal y métricas de negocio limitadas | `README.md`, `app/core/observability.py` | Añadir incident_id, códigos de error estables, dashboards básicos |
| 7 | Falta de pruebas de estrés de sincronización | Media | Media | Riesgo en clientes con alto volumen | Foco en unit/e2e funcional, no perf/load | suites existentes | Introducir benchmark/smoke de volumen + budgets de tiempo |
| 8 | Dependencia fuerte de Google Sheets API | Media | Media | Caídas externas afectan operación | Arquitectura centrada en gateway Sheets | `app/infrastructure/sheets_client.py` | Modo degradado offline + colas de reintento persistente + alertas operativas |
| 9 | Superficie extensa de scripts .bat/Windows | Media | Media | Mantenimiento y divergencia de flujo | Multiplicidad de entrypoints | raíz + `scripts/release/*.bat` | Consolidar scripts y generar desde plantilla única |
| 10 | Riesgo de drift entre documentación y estado real | Baja | Media | Decisiones equivocadas en due diligence | Mucha documentación y varias auditorías históricas | carpeta `docs/` | Política de docs vivas (check en CI que valide referencias clave) |
| 11 | Falta de empaquetado comercial “listo para venta” | Alta | Media | Dificulta monetización inmediata | MVP técnico > producto comercial | `packaging/HorasSindicales.spec`, docs release | Definir canales (instalador, auto-update, soporte) + pricing/SLAs |
| 12 | Gestión de secretos/config en cliente | Alta | Baja-Media | Riesgo seguridad/compliance | Credenciales locales y setup manual | `app/infrastructure/local_config_store.py`, `docs/politica_secretos.md` | Cifrado en reposo de credenciales + rotación + guía operativa de seguridad |

---

## 5) Análisis de valor monetario (aprox.)

### 5.1 Valor como producto B2B
**Qué puede venderse ya**
- Solución desktop para gestión de horas sindicales, solicitud, PDF justificativo y sync con Sheets.
- Buyer típico: secciones sindicales medianas, federaciones locales, gestorías laborales especializadas.

**Qué falta para escalar comercialmente**
- Multi-tenant real + administración centralizada.
- Onboarding/autoconfiguración de credenciales más seguro.
- Panel de operación (errores sync, conflictos pendientes, métricas de uso).
- Estrategia de soporte y actualización automática.

### 5.2 Valor como portfolio para reclutador
Cuenta historias fuertes:
- Arquitectura por capas con enforcement por tests.
- Diseño robusto de sincronización (idempotencia, conflicto, rollback, dedupe).
- Quality mindset con gates/scripts/CI y foco en mantenibilidad.

Demuestra:
- Seniority técnico real en backend/application design.
- Buena capacidad de producto técnico, aunque aún con deuda de go-to-market SaaS.

### 5.3 Rangos orientativos (supuestos explícitos)
**Supuestos**
- Cliente tipo: 30-200 personas gestionadas.
- Pricing nicho SaaS-like (soporte incluido): 150-900 €/mes por organización según soporte/volumen.
- Coste soporte inicial: 4-12 h/mes/cliente en fase temprana.

**Rango**
- (a) **Proyecto portfolio**: valor reputacional alto; monetización directa baja (0-8k € equivalente como activo demostrativo).
- (b) **MVP vendible**: 10k-60k € de valor inicial (pilotos + adaptación + soporte primer año).
- (c) **Base de producto para empresa**: 60k-250k € como base técnica si se ejecuta roadmap de hardening/comercialización 6-12 meses.

> Nota: rangos orientativos de due diligence técnica/comercial temprana, no valoración financiera formal.

---

## 6) Roadmap 30-60-90 días (máx. impacto / mínimo esfuerzo)

### 30 días
1. Refactor quirúrgico de `sync_sheets/use_case.py` en submódulos (pull, push, conflict-handling).
2. Instalar/estandarizar entorno dev (`requirements-dev`) y cerrar gap `pytest-cov` en onboarding.
3. Introducir reporte CC real con `radon` en CI (sin fallback LOC).
4. Definir indicadores operativos mínimos: tasa conflicto, retries, tiempo de sync.
5. Añadir tests de seguridad básicos sobre entradas conflictivas y SQL allowlists.
6. Documentar runbook de incidencias (errores típicos de sync + recuperación).

### 60 días
1. Endurecer esquema DB con nuevas constraints e índices funcionales tras análisis de datos.
2. Añadir suite de carga ligera (volumen filas + latencias máximas aceptables).
3. UI smoke E2E guiado (flujo creación solicitud->PDF->sync) en CI opcional/nightly.
4. Implementar `incident_id` transversal y taxonomía de errores operativos.
5. Consolidar scripts Windows/Linux en comandos uniformes.
6. Publicar demo dataset reproducible y script de reseteo.

### 90 días
1. Packaging comercial: instalador estable + mecanismo de actualización.
2. Hardening de secretos (cifrado local/rotación) y guía compliance básica.
3. Panel de salud de sincronización (CLI o vista dedicada en UI).
4. Definir edición “single-org” vs “multi-org managed”.
5. Ejecutar 2-3 pilotos reales con métricas de adopción y feedback estructurado.
6. Recalibrar pricing/soporte con datos reales de operación.

---

## 7) Recomendación de packaging de presentación

### 7.1 README “cara a reclutador”
- Problema concreto y público objetivo en 5 líneas.
- Arquitectura en capas + diagrama + 3 decisiones técnicas no triviales.
- “Robustez sync” en bullets: idempotencia, conflictos, rollback, retries.
- “Calidad” en números: tamaño suite, tipos de tests, quality gate.
- “Cómo correr demo en 3 comandos”.
- “Qué queda por hacer” (honesto, priorizado).

### 7.2 Demo reproducible
- Script único para levantar entorno y dataset fake.
- Escenario guiado: alta solicitud, generar PDF, sync, conflicto, resolución.
- Capturas o screencast corto de 2-3 minutos.
- Reporte final autogenerado (estado DB + resumen sync).

### 7.3 Qué enseñar en entrevista (guion 5 minutos)
1. Problema de negocio y por qué desktop+Sheets al inicio.
2. Arquitectura y enforcement (tests de imports).
3. Sync engine: planner (`PullAction`) + handlers + policy conflictos.
4. Robustez: savepoint/rollback, retries, dedupe, fuzz determinista.
5. Deuda conocida y plan 90 días (criterio de producto, no solo código).

---

## 8) Apéndice técnico

### 8.1 Comandos ejecutados para esta auditoría
- `python scripts/report_quality.py`
- `python scripts/quality_gate.py`
- `pytest -q tests/application/use_cases/test_conflict_policy.py tests/application/use_cases/sync_sheets/test_sync_sheets_use_case_planning.py tests/application/use_cases/sync_sheets/test_persistence_ops_sqlite_contract.py tests/infrastructure/test_repos_sqlite_builders.py tests/e2e_sync/test_sync_sheets_e2e.py tests/e2e_sync/test_sync_sheets_fuzz_light.py`

### 8.2 Top 20 archivos por LOC y complejidad (salida actual)
Fuente: `logs/quality_report.txt` generado por `scripts/report_quality.py`.

| Rank | Archivo | LOC |
|---:|---|---:|
| 1 | app/ui/vistas/main_window_vista.py | 2633 |
| 2 | app/application/use_cases/sync_sheets/use_case.py | 1373 |
| 3 | app/application/use_cases/solicitudes/use_case.py | 826 |
| 4 | app/ui/vistas/builders/main_window_builders.py | 764 |
| 5 | app/infrastructure/repos_sqlite.py | 617 |
| 6 | app/ui/sync_reporting.py | 444 |
| 7 | app/ui/widgets/toast.py | 436 |
| 8 | app/ui/vistas/confirmacion_actions.py | 379 |
| 9 | app/infrastructure/repos_conflicts_sqlite.py | 343 |
| 10 | app/ui/conflicts_dialog.py | 331 |
| 11 | app/application/use_cases/sync_sheets_core.py | 271 |
| 12 | app/infrastructure/sheets_client.py | 271 |
| 13 | app/ui/person_dialog.py | 258 |
| 14 | app/pdf/pdf_builder.py | 254 |
| 15 | app/ui/historico_view.py | 253 |
| 16 | app/ui/notification_service.py | 245 |
| 17 | app/application/use_cases/sync_sheets/helpers.py | 243 |
| 18 | app/infrastructure/migrations.py | 237 |
| 19 | app/ui/vistas/main_window_helpers.py | 236 |
| 20 | app/application/auditoria_e2e/caso_uso.py | 234 |

**Complejidad:** `radon` no estuvo disponible en este entorno; el reporte usa fallback por LOC (deuda de entorno para medir CC real).

### 8.3 Cobertura por paquete y focos rojos
Salida actual de `report_quality.py`:
- domain: 0.00%
- application: 0.00%
- infrastructure: 0.00%
- ui: 0.00%

Interpretación: **no representa cobertura real del proyecto**; refleja ausencia de datos `.coverage` en este entorno. El `quality_gate` también falla por falta de `pytest-cov` con mensaje accionable.

Focos rojos reales de cobertura (independientes del 0.00% técnico del entorno):
1. UI fuera del umbral contractual CORE por diseño (`docs/coverage_policy.md`).
2. Módulos grandes en UI/sync requieren estrategia específica de pruebas de regresión funcional.

### 8.4 Suites de tests relevantes y qué cubren
- **Unitarios de política de conflictos**: `tests/application/use_cases/test_conflict_policy.py`.
- **Planificación pull (`PullAction`)**: `tests/application/use_cases/sync_sheets/test_sync_sheets_use_case_planning.py`.
- **Contrato SQLite de `persistence_ops`**: `tests/application/use_cases/sync_sheets/test_persistence_ops_sqlite_contract.py`.
- **Builders SQLite + soft delete SQL**: `tests/infrastructure/test_repos_sqlite_builders.py`.
- **E2E sync** (idempotencia, conflicto, retries, rollback): `tests/e2e_sync/test_sync_sheets_e2e.py`.
- **Fuzz light determinista** con seed fija: `tests/e2e_sync/test_sync_sheets_fuzz_light.py`.
- **Arquitectura/import boundaries**: `tests/test_architecture_imports.py`.
- **Smoke UI estrategia alternativa a cobertura lineal UI**: `tests/ui/test_qt_sanity.py`, `tests/ui/test_ui_smoke_startup.py`, `tests/ui/test_models_qt_smoke.py`, script `scripts/ui_main_window_smoke.py`.

### 8.5 Localizaciones explícitas solicitadas
- **Política de conflictos (módulo + API):** `app/application/use_cases/sync_sheets/conflict_policy.py` (`evaluate_conflict_policy`, `ConflictDecision`, `ConflictOutcome`).
- **Planner de pull solicitudes (`PullAction`, handlers):** `app/application/use_cases/sync_sheets/action_planning.py` + `app/application/use_cases/sync_sheets/use_case.py` (`_build_pull_solicitud_plan`, `_apply_action`, `_apply_*_action`).
- **`persistence_ops` y contratos sqlite:** `app/application/use_cases/sync_sheets/persistence_ops.py` + `tests/application/use_cases/sync_sheets/test_persistence_ops_sqlite_contract.py`.
- **Tests E2E de sync y fuzz determinista:** `tests/e2e_sync/test_sync_sheets_e2e.py` + `tests/e2e_sync/test_sync_sheets_fuzz_light.py`.
- **`repos_sqlite_builders` y tests:** `app/infrastructure/repos_sqlite_builders.py` + `tests/infrastructure/test_repos_sqlite_builders.py`.
- **Cobertura UI 0% y su implicación real:** `docs/coverage_policy.md`, `docs/coverage_scope.md`, `.github/workflows/ci.yml` (estrategia alternativa de smoke UI).

---

## Veredicto duro final
Esto demuestra **nivel Senior sólido (casi Staff en backend/aplicación)** por: (A) diseño por capas con enforcement real, (B) tratamiento serio de robustez sync (idempotencia/conflictos/rollback/retries), (C) disciplina de calidad con pruebas amplias y guardrails de arquitectura.

Para ser claramente vendible como producto/SaaS faltan: (D) hardening de operación/comercialización (packaging, soporte, métricas), (E) seguridad y gestión de secretos de nivel producto, (F) estrategia de test/regresión UI y performance más industrial.

**Prioridad #1:** reducir riesgo en el núcleo de sync/UI grande (modularización + métricas operativas + pipeline reproducible de calidad/cobertura). Esto maximiza valor comercial y reduce coste de mantenimiento al mismo tiempo.
