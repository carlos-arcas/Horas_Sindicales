# Auditoría de portfolio técnico — Proyecto **Horas Sindicales**

## Resumen ejecutivo (recruiter-friendly con evidencia técnica)

Este repositorio comunica claramente que no es un proyecto de práctica básica: hay dominio real (solicitudes, sincronización, conflictos, PDF, persistencia), pipeline CI por carriles y documentación operativa consistente.

**Posicionamiento actual:** **Mid / Mid+ con trayectoria a Senior-**.  
**Score portfolio alineado con auditoría general:** **7.1/10** (equivalente a 71/100).  

> Justificación de alineación: la evaluación general puntúa madurez técnica global; la lectura recruiter penaliza menos el detalle interno y prioriza claridad de narrativa + evidencia de execution. No hay contradicción, solo distinto ángulo de lectura.

---

## 1) Scorecard de portfolio (alineada con `auditoria_general.md`)

| Dimensión | Puntuación (0–10) | Evidencia principal |
|---|---:|---|
| Impacto profesional en 5 minutos | 7.5 | `README.md`, `docs/arquitectura.md`, `.github/workflows/ci.yml` |
| Madurez arquitectónica | 7.0 | `app/*` por capas, `tests/test_architecture_imports.py` |
| Calidad de ingeniería | 6.8 | `.config/quality_gate.json`, `scripts/report_quality.py`, `docs/quality_gate.md` |
| Confiabilidad demostrable | 6.8 | CI por carriles + smoke UI bloqueante en workflow |
| Diferenciación portfolio | 7.4 | `app/application/use_cases/sync_sheets/`, `docs/sincronizacion_google_sheets.md` |
| **Global** | **7.1 / 10** | Alineado con auditoría general |

---

## 2) Lo que un recruiter técnico entiende rápido

### Señales fuertes
- Proyecto con alcance no trivial y valor funcional reconocible.
- Stack y CI con decisiones razonadas (core bloqueante, smoke UI bloqueante, extended opcional).
- Evidencia de disciplina de ingeniería: quality gate, migraciones versionadas, logging estructurado.

### Riesgos de percepción (si no guías bien la demo)
- Hotspots grandes (`main_window_vista`, `sync_sheets/use_case`) pueden parecer falta de control si no explicas plan de reducción.
- Mucha documentación sin hilo conductor puede diluir mensaje de impacto.
- Si la demo entra en detalles prematuros de implementación, pierdes narrativa de negocio.

---

## 3) Demo script (5 minutos, pasos exactos)

> Objetivo: enseñar valor + rigor técnico sin entrar en over-detail.

1. **(30s) Contexto y problema**  
   “Esta app resuelve gestión de horas sindicales con persistencia local y sincronización con Google Sheets, incluyendo conflictos y trazabilidad.”

2. **(45s) Mapa de arquitectura**  
   Abrir `docs/arquitectura.md` y señalar capas `domain/application/infrastructure/ui` + test que valida imports (`tests/test_architecture_imports.py`).

3. **(45s) Calidad y CI**  
   Abrir `.github/workflows/ci.yml` y explicar carriles `core`, `ui_smoke`, `ui_extended`, destacando qué bloquea release y qué no.

4. **(45s) Evidencia de quality gate**  
   Mostrar `.config/quality_gate.json` (coverage CORE >= 70) y `docs/quality_gate.md` (cómo se interpreta el gate).

5. **(60s) Dominio diferencial**  
   Navegar por `app/application/use_cases/sync_sheets/` y `docs/sincronizacion_google_sheets.md`, explicando trade-offs de sincronización y conflictos.

6. **(45s) Operabilidad y trazabilidad**  
   Enseñar `docs/guia_logging.md` y cómo se sigue un `correlation_id` (comando documentado en README).

7. **(30s) Cierre con plan senior**  
   Abrir `docs/roadmap_senior.md` y explicar en 2 frases: qué deuda existe y cómo la estás cerrando con hitos medibles.

---

## 4) Talking points para entrevista

### Arquitectura
- “Arquitectura por capas pragmática: prioricé separación verificable por tests antes que pureza académica.”
- “Uso tests de import para evitar erosión silenciosa de límites entre capas.”

### Trade-offs y decisiones
- “Dividí CI en carriles para balancear señal de calidad y estabilidad de ejecución en entorno gráfico.”
- “Acepté deuda táctica en hotspots para sostener entrega funcional, con plan explícito de refactor incremental.”

### Decisiones operativas
- “No vendo robustez como opinión: la anclo en quality gate, smoke tests y trazabilidad por `correlation_id`.”
- “Cuando una métrica no existe en repo, la marco como asunción y propongo cómo instrumentarla.”

### Métricas (sin inventar)
- Coverage CORE: fuente en `.config/quality_gate.json`.
- Estado y estrategia de CI: fuente en `.github/workflows/ci.yml`.
- Hotspots: fuente en módulos de mayor tamaño/complejidad (`app/ui/vistas/main_window_vista.py`, `app/application/use_cases/sync_sheets/use_case.py`).

---

## 5) Mensaje final para hiring manager

Este proyecto ya demuestra capacidad de construir producto real con criterios de ingeniería. El salto a senioridad consolidada depende de completar la reducción de deuda en hotspots y acompañar esa ejecución con métricas operativas estables.

---

## Changelog de edición

- Se reescribió el documento con enfoque recruiter-friendly sin perder trazabilidad técnica.
- Se incorporó un **Demo script de 5 minutos** con secuencia exacta y artefactos concretos a mostrar.
- Se añadieron **Talking points** para arquitectura, trade-offs, decisiones y métricas.
- Se alineó el score global con `auditoria_general.md` (7.1/10) y se explicó el criterio de lectura.
- Se eliminaron afirmaciones ambiguas no ancladas y se reforzó el uso de evidencias del repositorio.
