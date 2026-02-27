# Guía de estilo documental — `Horas_Sindicales`

## 1) Objetivo

Estandarizar la documentación del repositorio para que sea:
- verificable (claims con evidencia),
- mantenible (estructura estable),
- útil para producto, ingeniería y portfolio.

---

## 2) Tono y nivel de detalle

- **Tono:** profesional, directo, sin marketing vacío.
- **Lenguaje:** concreto y accionable; evitar “parece”, “probablemente” cuando hay evidencia.
- **Regla de verdad:** toda afirmación técnica debe incluir evidencia (`ruta de archivo`) o marcarse como **asunción**.

---

## 3) Estructura mínima obligatoria de cualquier doc técnico

1. **Título y alcance** (qué cubre y qué no cubre).
2. **Resumen ejecutivo** (5–10 bullets).
3. **Evidencias** (lista de rutas relevantes en repo).
4. **Contenido principal** (diagnóstico/diseño/proceso).
5. **Acciones o decisiones** (backlog, ADR, siguientes pasos).
6. **Verificación** (cómo se valida con comandos/criterios).
7. **Changelog de edición** (3–8 bullets al final).

---

## 4) Formato de comandos

- Usar bloques con lenguaje explícito:
  - `bash` para Linux/macOS/CI.
  - `bat` o `powershell` para Windows.
- Comandos deben ser ejecutables tal cual (sin placeholders ambiguos salvo que se indique).
- Si un comando requiere precondiciones, documentarlas justo encima.

Ejemplo:

```bash
# Requiere venv activo y dependencias instaladas
PYTHONPATH=. pytest -q -m "not ui"
```

---

## 5) Cómo citar evidencia

### En documentos Markdown del repo
- Citar rutas internas, sin URLs externas, por ejemplo:
  - `.github/workflows/ci.yml`
  - `.config/quality_gate.json`
  - `app/application/use_cases/sync_sheets/use_case.py`

### Buenas prácticas
- Si la afirmación es numérica (coverage, umbral, score), incluir fuente exacta del número.
- Si la evidencia no existe en repo, etiquetar como **asunción** y añadir “cómo obtenerla”.

---

## 6) Plantilla base — Auditoría técnica

```md
# <Nombre de auditoría>

**Fecha:** YYYY-MM-DD  
**Alcance:** ...

## Resumen ejecutivo
- ...

## Matriz de puntuación
| Categoría | Score |
|---|---:|
| ... | ... |

## Evidencias
- ruta/archivo_1
- ruta/archivo_2

## Diagnóstico
### Fortalezas
- ...
### Riesgos
- ...

## Backlog accionable
| ID | Acción | Impacto | Esfuerzo | Verificación |
|---|---|---|---|---|
| HS-A01 | ... | ... | ... | ... |

## Mapa de riesgos
| Riesgo | Severidad | Probabilidad | Mitigación | Verificación |
|---|---|---|---|---|

## Conclusión
- ...

## Changelog de edición
- ...
```

---

## 7) Plantilla base — ADR (Architecture Decision Record)

```md
# ADR-XXX: <Título>

## Estado
Propuesto | Aprobado | Reemplazado

## Contexto
- Problema a resolver
- Restricciones
- Alternativas consideradas

## Decisión
- Decisión final
- Alcance

## Consecuencias
### Positivas
- ...
### Negativas / trade-offs
- ...

## Evidencias
- ruta/archivo_que_motiva
- ruta/archivo_afectado

## Verificación
- Test/command/check que demuestra que la decisión funciona

## Changelog de edición
- ...
```

---

## 8) Criterios de calidad documental (checklist rápido)

- [ ] ¿Tiene alcance explícito?
- [ ] ¿Tiene sección de evidencias?
- [ ] ¿Hay asunciones marcadas?
- [ ] ¿Incluye verificación reproducible?
- [ ] ¿Cierra con changelog de edición?

---

## Changelog de edición

- Se creó una guía única para homogenizar estructura, tono y trazabilidad de documentación.
- Se definieron secciones mínimas obligatorias para docs técnicos.
- Se normalizó el formato de comandos y el criterio de reproducibilidad.
- Se incluyeron plantillas base para auditorías y ADRs.
- Se añadió checklist de calidad documental para revisión rápida en PR.
