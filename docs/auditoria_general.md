# Auditoría general técnica y tasación — Proyecto **Horas Sindicales**

**Fecha:** 2026-02-27  
**Auditoría realizada sobre:** repositorio completo (`/workspace/Horas_Sindicales`)  
**Alcance:** arquitectura, calidad, seguridad, UX, mantenibilidad, operabilidad y valoración monetaria.

---

## 0) Resumen ejecutivo (10 líneas)

1. El producto tiene una base **funcional real y útil**: gestión de personas/solicitudes, PDF, SQLite con migraciones y sync con Google Sheets.
2. La arquitectura por capas existe y está razonablemente defendida por tests de imports, pero con **hotspots muy grandes** (sobre todo UI y casos de uso de sync).
3. Hay buena inversión en test suite (386 tests passing), pero en este entorno se observan **100 skips**, principalmente UI por dependencia PySide6/libGL.
4. La CI está estructurada (core + UI), pero el job UI es `continue-on-error: true`, lo que reduce capacidad de bloqueo real ante regresiones visuales/Qt.
5. Observabilidad está por encima de la media (JSON logs, `correlation_id`, separación seguimiento/error/crash), aunque aún sin métricas operativas de negocio/SLO.
6. La robustez de datos es correcta por migraciones versionadas, pero existe código defensivo para `no such table: sync_state`, señal de inicializaciones no homogéneas.
7. Seguridad básica aceptable (test anti-secretos, política documental), pero faltan controles más fuertes de hardening local (cifrado reposo/gestión secreta más formal).
8. UX parece cuidada y con guías; aun así la complejidad de `MainWindow` (>2.8k LOC) eleva riesgo de regresión de experiencia.
9. Nota global propuesta: **71/100** (producto valioso y demostrable, pero con deuda estructural de mantenibilidad y de fiabilidad UI en CI).
10. Tasación técnica actual (rango probable): **~53k€–98k€** según escenario de uso, con potencial claro de subida tras 2–8 semanas de refactor+operabilidad.

---

## 1) Inventario y mapa del sistema (1–2 páginas)

### 1.1 ¿Qué hace el producto?

Aplicación de escritorio en Python + PySide6 para:
- Alta/mantenimiento de personas delegadas.
- Registro y validación de solicitudes de horas sindicales.
- Confirmación de solicitudes y generación de PDF.
- Persistencia local SQLite con migraciones y seed.
- Sincronización bidireccional con Google Sheets y gestión de conflictos.
- Logging estructurado con trazabilidad (`correlation_id`).

### 1.2 Arquitectura real por capas

**Entrypoints / bootstrap**
- `main.py` delega al entrypoint principal y captura crashes con logging de emergencia.
- `app/bootstrap/container.py` hace wiring de repos, casos de uso, sync, salud, seed/migraciones.

**UI (presentación)**
- PySide6 en `app/ui/**`.
- `app/ui/main_window.py` actúa como proxy, pero la implementación principal vive en `app/ui/vistas/main_window_vista.py`.

**Aplicación (orquestación)**
- `app/application/use_cases/**` y servicios (`sync_sheets`, `solicitudes`, `personas`, etc.).
- Opera con DTOs y puertos/adaptadores para desacoplar infraestructura.

**Dominio**
- Entidades/reglas en `app/domain/**` (validaciones, reglas de negocio y errores).

**Infraestructura**
- SQLite: repositorios, conexión, migraciones, seed.
- Google Sheets: cliente, gateway, repositorio de hojas.
- PDF reportlab como adaptador concreto.

### 1.3 Dependencias críticas identificadas

- **PySide6** (UI desktop, eventos/signals).
- **sqlite3** (persistencia local).
- **reportlab** (generación PDF).
- **gspread + google-auth + google-api-python-client** (integración Sheets).
- **pytest / pytest-cov / ruff / radon** para calidad (parte opcional según entorno).

### 1.4 Puntos de acoplamiento/fragilidad

1. **MainWindow monolítico**: `app/ui/vistas/main_window_vista.py` es extremadamente grande y complejiza cambios seguros.
2. **Sync use case de gran tamaño**: `app/application/use_cases/sync_sheets/use_case.py` concentra mucha lógica en un módulo único.
3. **Casos de uso de solicitudes también extensos**: riesgo de reglas dispersas y regresiones sutiles.
4. **Dependencia fuerte de runtime Qt/GL en CI**: gran volumen de skips UI en entornos sin libGL.
5. **Canal UI no bloqueante en CI** (`continue-on-error`) reduce protección real.

### 1.5 Hotspots (tamaño y complejidad aproximada)

**LOC altos (ranking):**
- `app/ui/vistas/main_window_vista.py` (~2896 LOC)
- `app/application/use_cases/sync_sheets/use_case.py` (~1646 LOC)
- `app/application/use_cases/solicitudes/use_case.py` (~923 LOC)
- `app/infrastructure/repos_sqlite.py` (~916 LOC)
- `app/ui/vistas/builders/main_window_builders.py` (~892 LOC)

**Complejidad estructural aproximada (estimación AST):**
- `main_window_vista.py`: ~431
- `sync_sheets/use_case.py`: ~240
- `solicitudes/use_case.py`: ~158
- `sync_sheets_core.py`: ~93

**Lectura de riesgo:** 3 módulos concentran una porción desproporcionada del riesgo de mantenimiento y defectos.

---

## 2) Matriz de puntuación (0–10 por categoría)

> Escala: 0 = muy deficiente, 10 = excelente.  
> Nota global (0–100) = promedio simple de las 10 categorías × 10.

| Categoría | Score (0-10) |
|---|---:|
| A. Arquitectura y Clean Architecture | 7.0 |
| B. Calidad de código | 6.5 |
| C. Tests y confiabilidad | 6.5 |
| D. Observabilidad | 8.0 |
| E. Seguridad y privacidad | 6.0 |
| F. Robustez de datos | 7.0 |
| G. UX / UI | 7.0 |
| H. Performance | 6.5 |
| I. DevEx / Operaciones | 7.0 |
| J. Producto | 8.0 |

**Nota global estimada: 71/100**

---

### A) Arquitectura y Clean Architecture — **7.0/10**

**Por qué:**
- Hay separación por capas explícita y documentada.
- Existe test automático de reglas de imports por capas.
- El bootstrap centraliza wiring (buena señal de composición).
- Persisten módulos grandes que erosionan límites conceptuales (UI/sync/solicitudes).
- Clean Architecture es “pragmática”, no estricta (documentado).

**Top 3 mejoras para subir +2 puntos:**
1. Dividir `main_window_vista` por verticales (solicitudes/sync/histórico).  
   - Impacto: Alto | Esfuerzo: L | Riesgo: Medio  
   - Cómo verificar: tests UI smoke + contrato de señales + checklist de navegación.
2. Partir `sync_sheets/use_case.py` en planner/executor/merge_policy “puros”.  
   - Impacto: Alto | Esfuerzo: L | Riesgo: Medio  
   - Verificación: tests unitarios por componente + test integración de sync.
3. Añadir ADRs obligatorios para cambios transversales.  
   - Impacto: Medio | Esfuerzo: S | Riesgo: Bajo  
   - Verificación: PR checklist exige ADR para cambios de arquitectura.

### B) Calidad de código — **6.5/10**

**Por qué:**
- Naming/documentación razonable en gran parte del repo.
- Hay ruff y políticas de calidad.
- Complejidad y tamaño altos en módulos críticos.
- Hay coexistencia de rutas “legacy/compat” que añade ruido cognitivo.
- Riesgo de duplicación lógica en UI/controladores.

**Top 3 mejoras:**
1. Umbral de complejidad por archivo/función con gate progresivo.  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Bajo  
   - Verificación: quality gate falla si excede umbral.
2. Refactor de funciones >80-100 líneas en hotspots.  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Medio  
   - Verificación: snapshot métricas LOC/CC antes vs después.
3. Campaña de deduplicación de helpers UI/toast/errores.  
   - Impacto: Medio | Esfuerzo: M | Riesgo: Bajo  
   - Verificación: reducción de bloques duplicados + tests de regresión.

### C) Tests y confiabilidad — **6.5/10**

**Por qué:**
- Suite amplia y rápida (386 pass).
- Existen tests de arquitectura, dominio, aplicación, infra y parte UI.
- 100 skips: gran proporción de UI no ejecutada en entorno sin Qt/libGL.
- Job UI en CI marcado `continue-on-error` (debilita bloqueo).
- En entorno auditado faltaba `pytest-cov` activo (fallo en comando sugerido).

**Top 3 mejoras:**
1. Hacer bloqueante el job UI (al menos smoke subset estable).  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Medio  
   - Verificación: CI falla si smoke UI falla.
2. Estrategia dual UI: smoke obligatorio + suite extendida opcional.  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Bajo  
   - Verificación: nuevo workflow con matriz y report de skips.
3. Garantizar `pytest-cov` y `radon` en todos los runners locales de gate.  
   - Impacto: Medio | Esfuerzo: S | Riesgo: Bajo  
   - Verificación: `scripts/quality_gate.py` pasa limpio en entorno estándar.

### D) Observabilidad — **8.0/10**

**Por qué:**
- Logging estructurado con eventos y `correlation_id`.
- Separación de canales: seguimiento / error_operativo / crash.
- Helpers de contexto para propagación trazable.
- Faltan dashboards/SLO formales y métricas de negocio (latencias/tasa de conflicto).
- No se ve explotación analítica de logs (solo captura).

**Top 3 mejoras:**
1. Definir 6-8 KPIs de operación (sync success rate, p95, incidentes).  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Bajo  
   - Verificación: informe semanal automático en logs.
2. Añadir `result_id`/`operation_type` estándar en más flujos UI críticos.  
   - Impacto: Medio | Esfuerzo: S | Riesgo: Bajo  
   - Verificación: tests de formato JSON logs.
3. Playbook de incidentes con queries predefinidas (`rg`/filtros).  
   - Impacto: Medio | Esfuerzo: S | Riesgo: Bajo  
   - Verificación: simulacro de incidente <30 min MTTR.

### E) Seguridad y privacidad — **6.0/10**

**Por qué:**
- Política anti-secretos y tests que bloquean ficheros sensibles.
- Se evita versionar DBs y credenciales.
- Integración Google introduce superficie sensible (permisos/credenciales locales).
- No se evidencia cifrado de datos en reposo para SQLite.
- Hardening de rutas/archivos exportados mejorable (validación centralizada limitada).

**Top 3 mejoras:**
1. Política formal de credenciales (rotación, scopes mínimos, path seguro).  
   - Impacto: Alto | Esfuerzo: S | Riesgo: Bajo  
   - Verificación: checklist de seguridad y test de configuración.
2. Sanitización/validación central de rutas de exportación (PDF/log).  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Medio  
   - Verificación: tests de path traversal/colisiones/permisos.
3. Evaluar cifrado opcional de SQLite o partición sensible fuera DB local.  
   - Impacto: Medio | Esfuerzo: L | Riesgo: Medio  
   - Verificación: PoC + pruebas de lectura/escritura y performance.

### F) Robustez de datos — **7.0/10**

**Por qué:**
- Migraciones versionadas con checksum + rollback.
- `run_migrations` + seed en arranque central.
- Existe cobertura de fixups y repositorios.
- Hay fallback explícito ante `no such table: sync_state` (resiliente pero indica inicializaciones inconsistentes).
- Sin pruebas de carga/concurrencia SQLite más exigentes.

**Top 3 mejoras:**
1. Preflight obligatorio: validar esquema completo antes de operaciones sync.  
   - Impacto: Alto | Esfuerzo: S | Riesgo: Bajo  
   - Verificación: test integración arranque con DB vacía/corrupta.
2. Endurecer transaccionalidad y rollback en lotes de confirmación+PDF.  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Medio  
   - Verificación: tests de fallo intermedio (write fail/pdf fail).
3. Tests de concurrencia `database is locked` y backoff controlado.  
   - Impacto: Medio | Esfuerzo: M | Riesgo: Medio  
   - Verificación: suite stress corta en CI nightly.

### G) UX / UI — **7.0/10**

**Por qué:**
- Hay documentación UX y componentes reutilizables.
- Sistema de toasts/notificaciones con wrappers de compatibilidad.
- Flujo principal funcional y con feedback.
- Tamaño del módulo principal UI dificulta consistencia global.
- Riesgo de regresión de microinteracciones por baja ejecución UI en CI.

**Top 3 mejoras:**
1. Diseñar “UI contract tests” para flujos críticos (alta, confirmar, sync).  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Bajo  
   - Verificación: smoke contracts sin dependencia excesiva de rendering.
2. Refactor por sub-vistas y controladores más finos.  
   - Impacto: Alto | Esfuerzo: L | Riesgo: Medio  
   - Verificación: snapshot de eventos/señales + pruebas navegación.
3. Auditoría de accesibilidad desktop (tab order, focus, textos).  
   - Impacto: Medio | Esfuerzo: M | Riesgo: Bajo  
   - Verificación: checklist UX + tests automáticos de tabulación.

### H) Performance — **6.5/10**

**Por qué:**
- No hay evidencia de cuellos severos en tests rápidos.
- Existen capas para batching en sync.
- No se ven benchmarks de rendimiento UI/sync/DB en repo.
- Módulos grandes suelen esconder operaciones costosas no visibles.
- No se observan métricas p95/p99 ni presupuestos de tiempos.

**Top 3 mejoras:**
1. Benchmarks básicos de sync (1k/5k filas) y consultas SQLite.  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Bajo  
   - Verificación: script benchmark con umbrales por versión.
2. Telemetría de tiempos por operación crítica en logs.  
   - Impacto: Medio | Esfuerzo: S | Riesgo: Bajo  
   - Verificación: campo `duration_ms` en eventos clave.
3. Revisar threading/colas en operaciones bloqueantes de UI.  
   - Impacto: Medio | Esfuerzo: M | Riesgo: Medio  
   - Verificación: smoke manual + test de no-freeze.

### I) DevEx / Operaciones — **7.0/10**

**Por qué:**
- Hay Makefile/scripts y documentación de release/onboarding.
- CI presente con separación core/UI.
- Job UI no bloqueante y dependencia fuerte del entorno gráfico.
- Umbral cobertura actual (63%) algo bajo para madurez alta.
- Herramientas opcionales (radon/cov) pueden faltar en entornos locales.

**Top 3 mejoras:**
1. Subir umbral cobertura gradualmente (63→70→75).  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Bajo  
   - Verificación: cumplimiento en 3 PRs escalonados.
2. Pipeline UI robusto con imagen estable de dependencias Qt.  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Medio  
   - Verificación: reducir skips UI >80%.
3. Script único de “preflight dev” (deps + checks + entorno).  
   - Impacto: Medio | Esfuerzo: S | Riesgo: Bajo  
   - Verificación: onboarding limpio en máquina nueva.

### J) Producto — **8.0/10**

**Por qué:**
- Caso de uso claro y específico (sindicato/empresa pequeña).
- Valor operativo tangible: reduce fricción administrativa + trazabilidad.
- Diferenciadores: sync Sheets y PDF con flujo integrado.
- Aún sin estrategia explícita de empaquetado comercial/SaaS multicliente.
- Falta roadmap de producto público y métricas de adopción.

**Top 3 mejoras:**
1. Definir roadmap trimestral con outcomes medibles.  
   - Impacto: Alto | Esfuerzo: S | Riesgo: Bajo  
   - Verificación: KPIs de adopción y ahorro de tiempo.
2. Producto “instalable empresarial” (setup + backup + soporte).  
   - Impacto: Alto | Esfuerzo: M | Riesgo: Medio  
   - Verificación: piloto real en 1-2 organizaciones.
3. Preparar diseño multi-tenant (si objetivo SaaS).  
   - Impacto: Medio | Esfuerzo: L | Riesgo: Alto  
   - Verificación: blueprint técnico + PoC autenticación/aislamiento.

---

## 3) Hallazgos críticos (Top 10 riesgos reales)

> Escala cualitativa: impacto/probabilidad = Alto/Medio/Bajo.

1. **Cobertura real de UI limitada en entornos sin Qt/libGL**  
   - Evidencia: skips por `libGL.so.1` y `PySide6 no disponible` en ejecución `pytest -q -rs`; `tests/ui/conftest.py` aplica skip cuando Qt no está listo.  
   - Impacto: Alto | Probabilidad: Alta  
   - Mitigación: pipeline UI dedicado con imagen base estable + smoke mínimo bloqueante.

2. **CI UI no bloqueante (`continue-on-error`)**  
   - Evidencia: `.github/workflows/ci.yml` job `ui` con `continue-on-error: true`.  
   - Impacto: Alto | Probabilidad: Media-Alta  
   - Mitigación: convertir al menos subset UI crítico en bloqueante.

3. **Dependencia de Xvfb/stack gráfico puede ocultar fallos intermitentes**  
   - Evidencia: CI usa `xvfb-run -a pytest -q tests/ui`.  
   - Impacto: Medio-Alto | Probabilidad: Media  
   - Mitigación: mantener smoke offscreen nativo + retriable tests; capturar core dumps.  
   - Nota específica solicitada: **en el repo auditado no encontré evidencia explícita de segfault actual de xvfb-run**, pero sí riesgo estructural por este tipo de stack.

4. **Fallback a `no such table: sync_state` en runtime**  
   - Evidencia: `sync_sheets/use_case.py` captura el error y devuelve `None`; test dedicado valida esa ruta.  
   - Impacto: Alto | Probabilidad: Media  
   - Mitigación: preflight de esquema y fail-fast controlado en arranque.

5. **Hotspot extremo en `main_window_vista.py`**  
   - Evidencia: ~2896 LOC, complejidad estimada ~431.  
   - Impacto: Alto | Probabilidad: Alta  
   - Mitigación: extracción por submódulos + contratos de interfaz.

6. **Hotspot en sync principal (`sync_sheets/use_case.py`)**  
   - Evidencia: ~1646 LOC, complejidad estimada ~240.  
   - Impacto: Alto | Probabilidad: Alta  
   - Mitigación: partición en planner/executor/policies + tests por componente.

7. **Fragilidad histórica en API de toasts (`action_label`)**  
   - Evidencia: existe capa compat (`toast_compat.py`) + tests de no romper kwargs.  
   - Impacto: Medio | Probabilidad: Media  
   - Mitigación: contrato estricto único para notificaciones y deprecación controlada.

8. **Riesgo de errores de ruta PDF/colisión de destino**  
   - Evidencia: test explícito `BusinessRuleError("Colisión de ruta PDF")`; validaciones dispersas entre controlador/caso de uso/builder.  
   - Impacto: Medio-Alto | Probabilidad: Media  
   - Mitigación: validador único de rutas PDF (normalización, permisos, colisión, longitud).

9. **Umbral de cobertura global relativamente bajo (63%)**  
   - Evidencia: `.config/quality_gate.json`.  
   - Impacto: Medio-Alto | Probabilidad: Media  
   - Mitigación: elevar gradual con foco en hotspots.

10. **Riesgo reputacional para recruiters por “skips masivos UI”**  
   - Evidencia: 100 skipped vs 386 passed en ejecución auditada.  
   - Impacto: Medio | Probabilidad: Alta  
   - Mitigación inmediata: badge/tabla de salud CI separando core-vs-UI y plan público para reducir skips.

---

## 4) Plan de mejora para subir puntuación (roadmap)

### Fase 1 (1–2 días) — Quick wins de alto impacto

**Objetivo:** reducir riesgo visible y mejorar señal de calidad de inmediato.

**Entregables:**
- Definir y publicar “estado de salud tests”: pass/fail/skip por suite.
- Preflight de esquema DB antes de sync (fail-fast con mensaje operable).
- Endurecer validación de rutas PDF con mensajes de error homogéneos.
- Checklist PR obligatorio (arquitectura, seguridad, pruebas, UX).

**Métricas de éxito:**
- Reducción de incidencias de arranque/sync por esquema incompleto.
- Menos errores de exportación PDF por ruta inválida.
- Transparencia de skips UI en CI/dashboard.

**Riesgos:**
- Ajustes rápidos pueden introducir ruido de mensajes si no se unifica copy.

### Fase 2 (1–2 semanas) — Refactors estructurales

**Objetivo:** bajar deuda técnica donde más duele (UI + sync + solicitudes).

**Entregables:**
- Segmentación de `main_window_vista` por subdominios de interacción.
- División de `sync_sheets/use_case.py` en componentes testables.
- Introducción de métricas de complejidad/LOC en gate (warning->fail progresivo).

**Métricas de éxito:**
- Disminuir LOC de archivo UI principal al menos 35–45%.
- Disminuir complejidad estimada de sync principal >30%.
- Reducir tiempo de revisión PR en módulos críticos.

**Riesgos:**
- Refactor transversal con regresiones si no se acompaña de tests de contrato.

### Fase 3 (1–2 meses) — Madurez operativa y comercial

**Objetivo:** fiabilidad de CI/UI, release profesional y base para escalado.

**Entregables:**
- Pipeline UI estable y parcialmente bloqueante.
- Tests UI críticos en entorno controlado (offscreen + xvfb fallback).
- Packaging/release reproducible con checklist firmado.
- KPI operativos y de producto (sync success, MTTR, adopción).

**Métricas de éxito:**
- Skips UI <20% de la suite UI total.
- 0 regressions críticas en flujos alta/confirmación/sync por 2 releases.
- Tiempo de onboarding técnico <1h.

**Riesgos:**
- Dependencia de infraestructura CI y tuning de entorno gráfico.

---

## 5) Valor monetario actual (tasación técnica)

## 5.1 Modelo obligatorio de valoración

### A) Coste de reemplazo (from scratch)

Estimación de horas para reconstrucción por un dev mid/senior:

| Módulo | Horas (min-prob-max) |
|---|---:|
| Dominio + reglas de negocio + DTOs | 80 / 120 / 170 |
| Aplicación (casos de uso solicitudes/sync/conflictos) | 180 / 260 / 360 |
| Infraestructura SQLite + repos + migraciones + seed | 110 / 160 / 240 |
| Integración Google Sheets (auth, sync, retries) | 90 / 140 / 220 |
| UI PySide6 (pantallas, navegación, feedback) | 220 / 320 / 470 |
| PDF/reporting + exportaciones | 40 / 70 / 110 |
| Testing + quality gate + scripts | 120 / 180 / 260 |
| Docs/release/bootstrap/logging | 60 / 90 / 140 |
| **Total** | **900 / 1340 / 1970 h** |

### B) Factores de ajuste

- **Factor riesgo deuda/CI/bugs críticos (Fr):** 0.80 (mín) / 0.90 (prob) / 1.00 (máx)
- **Factor calidad por score global 71/100 (Fq):** 0.90 (mín) / 1.00 (prob) / 1.08 (máx)
- **Factor documentación/operabilidad (Fd):** 0.90 (mín) / 1.00 (prob) / 1.10 (máx)

**Fórmula:**

`Valor = Horas_reemplazo × Tarifa_hora × Fr × Fq × Fd`

### C) Tarifa hora (España) — escenarios solicitados

- Escenario 1: **35 €/h** (freelance junior-mid económico)
- Escenario 2: **60 €/h** (freelance/consultoría mid-senior habitual)
- Escenario 3: **90 €/h** (consultoría senior especializada)

### D) Costes indirectos (PM/QA/UX)

Si se valorase reconstrucción comercial completa, añadir **15–30%** sobre coste técnico puro (coordinación, QA manual, diseño UX, gestión release).

### E) Resultado en € (sin licencias/servicios externos no implementados)

#### 1) Valor “portfolio empleabilidad”
- Rango útil para CV/portfolio (valor demostrativo más que de compraventa):
- **Mín:** ~22k€  
- **Probable:** ~45k€  
- **Máx:** ~80k€

#### 2) Valor “producto interno” (sindicato/pyme)
- Basado en coste de reemplazo ajustado y utilidad directa operativa:
- **Mín:** ~38k€  
- **Probable:** ~74k€  
- **Máx:** ~132k€

#### 3) Valor “SaaS comercializable” (adaptado)
- Estado actual no es SaaS multi-tenant listo; requiere inversión extra en auth, tenancy, billing, soporte:
- **Valor actual del activo base (IP técnica reutilizable):**
- **Mín:** ~53k€  
- **Probable:** ~98k€  
- **Máx:** ~176k€

> Interpretación: hoy el valor está más cerca de **producto interno robusto** que de SaaS listo para escalar. Con roadmap fase 2+3 completado, el factor de riesgo puede subir de 0.9 a 1.05 y aumentar sustancialmente la tasación.

---

## 6) Asunciones explícitas y exclusiones

- Las horas de reemplazo asumen **reimplementación funcional equivalente**, no réplica exacta línea a línea.
- Tarifas usadas: 35€/h, 60€/h, 90€/h (mercado España).
- No se incluyen costes de licencias de terceros, infraestructura cloud, soporte 24/7 o costes legales.
- Donde no hubo evidencia directa, se declara explícitamente (ej. segfault xvfb-run no encontrado como incidencia concreta en repo auditado).

---

## 7) Apéndice técnico (métricas y evidencias)

### 7.1 Comandos ejecutados durante la auditoría

- `pytest -q` → **386 passed, 100 skipped**.
- `pytest -q -rs` → detalle de skips (PySide6/libGL y radon opcional).
- Script local de ranking LOC (top archivos).
- Script local de complejidad estructural estimada (AST).
- Lectura selectiva de README, arquitectura, quality gate, CI, logging, migraciones, use cases, UI y tests críticos.

### 7.2 Ficheros más grandes (extracto)

1. `app/ui/vistas/main_window_vista.py` (~2896)
2. `app/application/use_cases/sync_sheets/use_case.py` (~1646)
3. `app/application/use_cases/solicitudes/use_case.py` (~923)
4. `app/infrastructure/repos_sqlite.py` (~916)
5. `app/ui/vistas/builders/main_window_builders.py` (~892)

### 7.3 Módulos hotspot por complejidad estimada (extracto)

1. `app/ui/vistas/main_window_vista.py` (~431)
2. `app/application/use_cases/sync_sheets/use_case.py` (~240)
3. `app/application/use_cases/solicitudes/use_case.py` (~158)
4. `scripts/product_audit.py` (~135)
5. `app/application/use_cases/sync_sheets_core.py` (~93)

### 7.4 Temas solicitados (estado)

- **Skips CI/UI por PySide6/libGL:** detectado.
- **Segfault en xvfb-run:** tema revisado; no se encontró evidencia explícita en repo (riesgo potencial sí).
- **`no such table: sync_state`:** detectado (fallback + test).
- **Errores toast API (`action_label`):** riesgo histórico mitigado con compat + tests.
- **Errores rutas PDF:** detectados casos de colisión/validación repartida.

---

## 8) Lista breve de archivos inspeccionados

- `README.md`
- `docs/arquitectura.md`
- `.github/workflows/ci.yml`
- `.config/quality_gate.json`
- `scripts/quality_gate.py`
- `tests/ui/conftest.py`
- `app/bootstrap/container.py`
- `app/application/use_cases/sync_sheets/use_case.py`
- `app/application/use_cases/solicitudes/use_case.py`
- `app/ui/vistas/main_window_vista.py`
- `app/ui/widgets/toast.py`
- `app/ui/toast_compat.py`
- `tests/ui/test_toast_no_action_kwargs.py`
- `migrations/001_initial_schema.up.sql`
- `app/infrastructure/migrations.py`
- `tests/application/test_sync_sheets_use_case_more_coverage.py`
- `tests/ui/controllers/test_solicitudes_controller.py`
- `app/pdf/pdf_builder.py`
- `logs/summary.txt`
- `requirements.txt` y `requirements-dev.txt`

