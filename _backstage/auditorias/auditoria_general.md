# Auditoría general técnica y tasación — Proyecto **Horas Sindicales**

**Fecha:** 2026-02-27  
**Alcance:** arquitectura, calidad, seguridad, UX, mantenibilidad, operabilidad y señal de portfolio.

---

## 0) Resumen ejecutivo

1. El producto tiene valor funcional real (gestión de personas/solicitudes, PDF, SQLite, sincronización con Sheets).
2. La arquitectura por capas está implementada y tiene verificación automática de dependencias.
3. La base de calidad es sólida (lint + tests + CI por carriles), pero existe deuda en hotspots de tamaño/complejidad.
4. La observabilidad está por encima de la media de proyectos portfolio (eventos estructurados + `correlation_id`).
5. La fiabilidad UI en CI está parcialmente garantizada: `UI_SMOKE` bloqueante y `UI_EXTENDED` no bloqueante.
6. El proyecto está bien posicionado como “mid con potencial senior”, y la subida de valoración depende de reducir riesgo estructural.

**Nota global:** **71/100**  
**Tasación técnica orientativa:** **53k€–98k€** (rango dependiente de contexto de uso y madurez operativa).

---

## 1) Matriz de puntuación

| Categoría | Score (0–10) |
|---|---:|
| A. Arquitectura y modularidad | 7.0 |
| B. Calidad de código | 6.5 |
| C. Tests y confiabilidad | 6.5 |
| D. Observabilidad | 8.0 |
| E. Seguridad y privacidad | 6.0 |
| F. Robustez de datos | 7.0 |
| G. UX / UI | 7.0 |
| H. Performance | 6.5 |
| I. DevEx / Operaciones | 7.0 |
| J. Producto / valor | 8.0 |

**Resultado consolidado:** **71/100**.

---

## 2) Evidencias (rutas del repositorio)

> Regla de lectura: cada afirmación técnica de esta auditoría se ancla en código/config/documentación existente. Si no hay evidencia directa, se marca como **asunción**.

### Arquitectura y límites
- `app/domain/`, `app/application/`, `app/infrastructure/`, `app/ui/`.
- `docs/arquitectura.md`.
- `tests/test_architecture_imports.py`.

### Calidad y pipeline
- `.github/workflows/ci.yml` (carriles `core`, `ui_smoke`, `ui_extended`).
- `.config/quality_gate.json` (umbral de coverage CORE).
- `scripts/report_quality.py` (reporte de LOC/complejidad/cobertura por paquete).
- `docs/quality_gate.md`.

### Persistencia y migraciones
- `migrations/`.
- `app/infrastructure/migrations_cli.py`.
- `docs/base_datos_local.md`.

### Observabilidad y trazabilidad
- `app/core/logging/`.
- `docs/guia_logging.md`.
- `README.md` (sección de Correlation ID y comandos de búsqueda).

### Integración externa (Google Sheets)
- `app/infrastructure/google_sheets/`.
- `app/application/use_cases/sync_sheets/`.
- `docs/sincronizacion_google_sheets.md`.

### Hotspots técnicos (por tamaño/complejidad)
- `app/ui/vistas/main_window_vista.py`.
- `app/application/use_cases/sync_sheets/use_case.py`.
- `app/application/use_cases/solicitudes/use_case.py`.

### Asunciones explícitas
- Métricas operativas de producción (SLO, MTTR, conflict-rate real en explotación) no se encuentran instrumentadas como dashboard persistente en el repo; se consideran **asunción/no disponible** en esta auditoría.

---

## 3) Backlog accionable (priorizado)

| ID | Acción | Impacto | Esfuerzo | Evidencia asociada | Criterio de verificación |
|---|---|---|---|---|---|
| HS-A01 | Particionar `sync_sheets/use_case.py` en submódulos por responsabilidad (pull/push/conflicts/dedupe) | Alto | Alto | `app/application/use_cases/sync_sheets/use_case.py` | Reducción de tamaño por archivo + tests de contrato por submódulo |
| HS-A02 | Reducir `main_window_vista.py` a shell de composición y mover lógica a controladores/presenters | Alto | Alto | `app/ui/vistas/main_window_vista.py` | Menor acoplamiento + UI smoke estable sin regresiones |
| HS-A03 | Definir presupuesto de complejidad/LOC y hacerlo fallar en CI si se excede | Alto | Medio | `.github/workflows/ci.yml`, `scripts/report_quality.py` | Gate automático con umbrales documentados |
| HS-A04 | Mantener cobertura CORE >=70 y plan progresivo a 75 en rutas críticas | Medio | Medio | `.config/quality_gate.json`, `docs/roadmap_senior.md` | Cobertura CORE >= objetivo en CI durante 3 sprints |
| HS-A05 | Endurecer pruebas UI bloqueantes para flujos críticos de negocio (no solo arranque/sanidad) | Medio | Medio | `.github/workflows/ci.yml`, `tests/ui/` | Nuevo subset bloqueante estable (flakiness acotada) |
| HS-A06 | Formalizar ADRs de decisiones clave de sincronización y resolución de conflictos | Medio | Bajo | `docs/decisiones.md`, `docs/decisiones_tecnicas.md` | ADRs publicados con contexto, decisión y trade-offs |
| HS-A07 | Definir métricas operativas (éxito sync, conflictos, tiempo de resolución) y extracción reproducible | Alto | Medio | `docs/sincronizacion_google_sheets.md` | Script/consulta documentada para obtener métricas |
| HS-A08 | Consolidar narrativa portfolio en README + auditorías + roadmap con un único set de scores | Medio | Bajo | `README.md`, `docs/auditoria_general.md`, `docs/auditoria_portfolio.md`, `docs/roadmap_senior.md` | Consistencia explícita entre documentos |

---

## 4) Mapa de riesgos

| Riesgo | Severidad | Probabilidad | Mitigación propuesta | Verificación |
|---|---|---|---|---|
| Deuda estructural en sync (archivo de gran tamaño) | Alta | Alta | Ejecutar HS-A01 con refactor incremental y tests de caracterización | Comparar complejidad/LOC antes-después + verde en CI |
| Deuda estructural en UI principal | Alta | Alta | Ejecutar HS-A02 y ampliar smoke de UI crítica | Suite UI bloqueante estable + menor tamaño módulo |
| Falsa sensación de seguridad por UI_EXTENDED no bloqueante | Media | Media | Fortalecer `UI_SMOKE` con flujos de negocio críticos (HS-A05) | Fallo real de CI ante regresión en flujo clave |
| Calidad heterogénea entre módulos | Media | Alta | Presupuesto de complejidad y gate automático (HS-A03) | Pipeline falla al superar umbral |
| Falta de métricas operativas de negocio | Media | Alta | Instrumentar métricas mínimas de sync y conflictos (HS-A07) | Reporte periódico reproducible |
| Dependencia de entorno gráfico para ciertas pruebas UI | Media | Media | Mantener separación smoke/extended + documentación de entorno | Tasa de éxito estable en `ui_smoke` |

---

## 5) Qué demostrar en entrevista

- Cómo se valida arquitectura por capas con tests automáticos (no solo con diagrama).
- Por qué existe separación `CORE` / `UI_SMOKE` / `UI_EXTENDED` en CI y qué riesgo cubre cada carril.
- Cómo se rastrea una operación completa con `correlation_id` en logs.
- Qué trade-off asumiste al priorizar entrega funcional frente a refactor estructural.
- Qué plan concreto tienes para reducir hotspots sin “big bang refactor”.

---

## 6) Conclusión

El proyecto ya supera el estándar de “demo CRUD”, muestra criterio de arquitectura y disciplina operativa básica, pero mantiene deuda en módulos críticos que hoy limita la señal de senioridad plena. La prioridad no es añadir más features, sino reducir concentración de riesgo y demostrar control operativo con métricas reproducibles.

---

## Changelog de edición

- Se reorganizó la auditoría a formato ejecutivo + secciones verificables para lectura técnica y de hiring.
- Se añadió sección de **Evidencias** con rutas concretas para sostener afirmaciones técnicas.
- Se convirtió la lista de recomendaciones en backlog accionable con IDs `HS-A01...HS-A08`.
- Se añadió **Mapa de riesgos** (severidad/probabilidad/mitigación/verificación) para priorización objetiva.
- Se incorporó sección **Qué demostrar en entrevista** para reforzar señal de portfolio.
- Se eliminaron formulaciones vagas y se marcaron explícitamente las asunciones no demostrables con evidencia del repo.
