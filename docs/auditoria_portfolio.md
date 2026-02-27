# Auditoría de portfolio técnico — Proyecto **Horas Sindicales**

## Resumen ejecutivo (recruiter/hiring manager, sin filtro)
Este repositorio **no parece un toy**, pero tampoco transmite senioridad plena en 5 minutos. El volumen de código, la cantidad de tests y la existencia de CI/quality gate elevan claramente el nivel por encima de junior básico. A la vez, la primera impresión deja señales de **complejidad no domada**: clase UI principal gigante, caso de uso de sync enorme, mezcla de capas de compatibilidad legacy y umbral de cobertura bajo (63%).

Como pieza de portfolio para España (30k–45k), hoy te posiciona más cerca de **Mid- / Mid técnico** que de Senior. Un recruiter técnico verá “persona trabajadora con ambición arquitectónica real”, pero también “aún en transición hacia rigor senior de producto en producción”.

Lo más fuerte: arquitectura por capas declarada y parcialmente forzada por tests, trazabilidad/observabilidad básica, dominio no trivial (sync bidireccional + conflictos + deduplicación + PDF + SQLite).

Lo más débil: monolitos internos, deuda de mantenibilidad, señales de fragilidad en UI cross-platform, y narrativa de valor demasiado centrada en “complejidad implementada” en lugar de “complejidad controlada”.

Veredicto corto: **te sube valor profesional**, sí; pero hoy te vende como **mid con potencial senior**, no como senior consolidado.

---

## Tabla de puntuaciones

| Dimensión | Puntuación (0–10) | Lectura rápida |
|---|---:|---|
| 1) Impacto visual y profesional (5 min) | **7.0** | Repositorio serio, pero con ruido/legacy visible |
| 2) Madurez arquitectónica | **6.5** | Buen diseño por capas, ejecución parcial |
| 3) Calidad profesional de código | **6.0** | Mucho esfuerzo, pero deuda estructural clara |
| 4) Confiabilidad real | **5.5** | Soporta uso controlado; riesgo al escalar uso real |
| 5) Valor diferencial portfolio | **7.0** | Diferencia más que CRUD típico, pero foco difuso |
| **Score global portfolio** | **6.4 / 10** | **Mid- / Mid** |

---

## 1) Primera impresión (simulación recruiter en 5 minutos)

### Lo que se ve rápido
- Repo grande, con estructura de capas (`app/application`, `app/domain`, `app/infrastructure`, `app/ui`) y documentación extensa: esto **sí comunica profesionalidad** inicial.
- README completo y operativo (instalación, tests, migraciones, quality gate, observabilidad): positivo para perfil backend/fullstack técnico.
- Hay batería de tests muy amplia (muchos directorios, unit/integration/e2e/ui), y CI con separación core/UI.
- También aparecen señales de transición/arrastre: paquetes puente (`dominio`, `aplicacion`, `infraestructura`, `presentacion`) y artefactos legacy de compatibilidad.

### Juicio recruiter
- **¿Proyecto serio o experimento?** → Serio, pero con olor a “producto en construcción prolongada” más que “sistema industrializado”.
- **¿Nivel que transmite?** → **Mid- / Mid**.
- **Red flags en 5 minutos:**
  1. Umbral de cobertura en 63% (bajo para vender senior).
  2. Clase `MainWindow` de casi 3000 LOC (acoplamiento y mantenibilidad).
  3. Use case de sync de >1600 LOC (núcleo crítico demasiado concentrado).
  4. CI de UI tolerante a error (`continue-on-error: true`), que baja confianza.
- **Puntos diferenciales:**
  1. Dominio no trivial (sync bidireccional, deduplicación, conflictos).
  2. Migraciones SQLite versionadas.
  3. Logging estructurado + correlation_id.

**Impacto visual y profesional: 7.0/10**

---

## 2) Arquitectura real vs arquitectura declarada

### Diagnóstico
- **No es Clean Architecture estricta**; es arquitectura por capas pragmática (el propio repo lo admite). Eso es correcto si lo explicas bien.
- Hay **inversión de dependencias parcial real** (puertos y tests de imports), pero convive con zonas de alta concentración de orquestación.
- UI: aunque existen controllers/helpers/mixins, `main_window_vista.py` sigue siendo un **macro-componente** (monolito funcional parcialmente modularizado).
- Sync Sheets: funcionalmente rico, pero el tamaño del caso de uso sugiere riesgo de “god object” en evolución y regresiones.

### ¿Qué falta para que un Senior diga “entiende arquitectura”?
1. Extraer el sync en submódulos por bounded context (pull/push/conflicts/dedupe/schema-sync) con contratos explícitos.
2. Reducir `MainWindow` a shell + coordinadores, llevando lógica de estado/flujo a presenters/controllers testeables.
3. Definir ADRs de decisiones duras (conflict policy, eventual consistency, criterios dedupe).
4. Endurecer reglas de arquitectura con métricas (máximo LOC por archivo crítico, máximo complejidad por función).
5. Mostrar trade-offs con métricas de operación (no solo estructura de carpetas).

**Madurez arquitectónica: 6.5/10**

---

## 3) Calidad técnica

### Evaluación franca
- **Complejidad ciclomática**: funciones de sync y UI con ramas altas; hay hotspots claros.
- **Tamaño de clases/módulos**: `MainWindow` y caso de uso de sync están sobredimensionados.
- **Separación de responsabilidades**: buena intención global; ejecución desigual en módulos críticos.
- **Errores y logging**: bien orientado (taxonomía + observabilidad), por encima de la media de portfolio junior.
- **Tests**: cantidad alta y cobertura temática amplia, pero calidad percibida se degrada por señal de umbral bajo y skips condicionales en UI.
- **CI**: correcta separación de jobs, pero UI no bloqueante resta credibilidad de robustez.

### 5 mejoras que te suben +3 puntos en calidad
1. Particionar `sync_sheets/use_case.py` en servicios pequeños con tests de contrato por componente.
2. Reducir `main_window_vista.py` a <1000 LOC con arquitectura MVP/MVVM ligera.
3. Subir cobertura mínima progresiva (63→70→75) con foco en caminos de error y conflictos.
4. Hacer UI tests críticos bloqueantes en CI (al menos smoke de arranque + flujo principal).
5. Definir presupuesto de complejidad (por ejemplo, no funciones >10–12 en núcleos críticos) y fallar CI cuando se exceda.

**Calidad profesional: 6.0/10**

---

## 4) Robustez y confiabilidad

### Qué veo
- El sistema contempla conflictos, dedupe y reintentos, lo cual suma.
- Pero la propia documentación de sync enumera riesgos operativos relevantes (cambios parciales sin transacción global, timestamps inválidos, conflictos acumulados, dependencia fuerte de UUID y edición manual en Sheets).
- En UI, la cantidad de lógica en la ventana principal incrementa probabilidad de regresiones de flujo (confirmación, estados pendientes, toasts, refresh de vistas).

### Si lo usa un sindicato real mañana
- Probablemente **funcionará en escenarios nominales** y piloto controlado.
- En uso real continuado (varios operadores, errores de red, datos sucios, conflictos recurrentes), esperaría incidencias operativas y necesidad de soporte cercano.

**Confiabilidad real: 5.5/10**

---

## 5) Diferenciación en el mercado laboral

### Señal para recruiter técnico
- **Backend real**: sí, hay lógica sustancial de aplicación/infra.
- **Arquitectura**: sí, pero más “en transición madura” que “senior consolidada”.
- **Diseño de dominio**: sí, especialmente en sincronización y reglas.
- **Testing serio**: parcial; fuerte en volumen, menos fuerte en señal de rigor final.
- **Errores/observabilidad**: razonablemente profesional.
- **Pensamiento sistémico**: sí, por el modelado de conflictos y consistencia.

¿Parece app de escritorio compleja sin foco? **Parcialmente**. El valor backend está, pero queda eclipsado por el peso UI y por la narrativa del repositorio (mucho “cómo está montado”, menos “impacto medible”).

**Valor diferencial como portfolio: 7.0/10**

---

## 6) Clasificación final del nivel

- **Nivel proyectado hoy:** **Mid- / Mid**.
- **Rango salarial coherente (España, con este proyecto):** **32k–40k €** (según empresa/ciudad/stack exigido).
- **Qué falta para justificar 40k+:**
  - Evidencia fuerte de robustez operacional (incidentes, MTTR, SLO internos).
  - CI más estricta y métricas de calidad sostenidas.
  - Reducción visible de deuda en hotspots críticos.
- **Qué falta para justificar 50k+:**
  - Arquitectura modular del sync + UI desacoplada de verdad.
  - Pruebas de contrato/integración robustas sobre integraciones externas.
  - Señales claras de liderazgo técnico: ADRs, governance, decisiones con coste/beneficio.

---

## 7) Valor profesional del proyecto (impacto en € del candidato)

> Estimación orientativa para mercado español (no consultoría legal/salarial).

- **Sin este proyecto (perfil similar):** 28k–34k €.
- **Con este proyecto actual:** 32k–40k €.
- **Con mejoras sugeridas (ejecución real y demostrable):** 38k–46k € (tope superior si la narrativa en entrevistas está bien articulada).

Lectura directa: este proyecto hoy puede aportar **+4k a +8k €/año** de capacidad negociadora frente a un perfil sin pieza técnica comparable.

---

## 8) Plan estratégico para convertirlo en “proyecto senior”

## Fase 1 — Blindaje (2 semanas)
**Objetivo:** bajar riesgo inmediato y mejorar señal de rigor.

**Entregables**
1. Quality gate endurecido: cobertura mínima 70, UI smoke bloqueante en CI.
2. Dashboard mínimo de calidad: complejidad, archivos hotspot, test flakiness.
3. Documento de “riesgos operativos actuales” con mitigaciones y dueño.
4. Checklist de PR senior (arquitectura, tests de error, observabilidad, rollback).

## Fase 2 — Madurez real (1 mes)
**Objetivo:** reducir deuda estructural en núcleos críticos.

**Entregables**
1. Refactor de `sync_sheets` en módulos cohesionados con tests de contrato.
2. Refactor de `MainWindow` a shell + controllers/presenters.
3. ADRs para decisiones clave (conflictos, dedupe, transaccionalidad, retries).
4. Cobertura 75 con foco explícito en edge-cases y paths de error.

## Fase 3 — Proyecto impactante (2 meses)
**Objetivo:** convertirlo en historia de ingeniería senior vendible.

**Entregables**
1. Caso real de resiliencia: simulador de fallos de sync + reporte de recuperación.
2. Métricas de operación: tasa de conflictos, tiempo medio de resolución, tasa de éxito sync.
3. Demo técnica orientada a negocio: “qué problema resuelve, con qué garantías”.
4. Portfolio package: README ejecutivo + arquitectura C4 + postmortem de incidente simulado.

---

## Diagnóstico honesto (sin suavizar)
- Tienes un proyecto **trabajado y con ambición**.
- Pero hoy aún transmite “ingeniería intensa de una persona” más que “arquitectura senior sostenible por equipo”.
- Si no reduces hotspots (sync/UI) y no endureces CI/quality signals, te quedarás en techo **mid** aunque el esfuerzo sea enorme.

## Estimación salarial final
- **Hoy:** 32k–40k € realista.
- **Tras plan (bien ejecutado):** 38k–46k €.
- **Para 50k+:** necesitas demostrar impacto operativo y liderazgo arquitectónico, no solo complejidad técnica.

## Conclusión final
**Hoy este proyecto te posiciona como Mid- / Mid. Con blindaje de calidad + refactor de hotspots + narrativa de impacto operativo, te posicionaría como Mid+ / Senior-.**
