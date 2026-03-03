# agents.md — Contrato de trabajo para agentes (genérico)

Este documento define reglas y guardarraíles para diseñar, implementar y mantener “agentes”
(casos de uso, controladores, handlers, jobs, pantallas) con:
- Clean Architecture estricta
- cobertura alta y verificable
- i18n sin hardcodeos
- tests deterministas (incluyendo golden gate para UI)
- flujo de trabajo óptimo para Codex (prompts atómicos)

---

## 0) La decisión clave (la mejor para Codex y para acotar trabajo)

**Se adopta un único comando canónico y versionado como “fuente de verdad” del gate:**

- Gate rápido: `python -m scripts.gate_rapido`
- Gate PR (completo): `python -m scripts.gate_pr`

¿Por qué es lo mejor?
- Un solo comando evita divergencias entre “lo que creías que era CI” y lo que realmente ejecuta CI.
- Codex funciona mejor con contratos simples: **ejecuta gate → arregla → re-ejecuta**.
- Puedes cambiar internamente herramientas/comandos sin reescribir docs ni prompts.

**Regla:** CI debe ejecutar exactamente `python -m scripts.gate_pr`.

---

## 1) Principios NO negociables

- **Clean Architecture 100%** (límites duros entre capas; dependencias correctas).
- **Cobertura mínima > 85%** (y el CORE debe ser el más cubierto).
- **Golden Gate UI** (si hay UI): toda interacción relevante y toda apertura de ventana/modal debe estar cubierta por tests deterministas.
- **Cero hardcodeo de textos visibles**: todo texto va a i18n y es fácil de traducir.
- **Sin deuda técnica**: si aparece, se paga en el mismo ciclo/PR.
- **Pytest** como estándar (`pytest -q`) y suite reproducible.
- **Naming en español** (permitidos términos técnicos internacionales: UI, UX, helper, debug, token, payload, cache, hash…).
- **Inventario de features + pendientes auto-actualizado** desde una fuente única.
- **Flujo Codex**: prompts atómicos, uno a uno; normalmente 1 de lógica, 1 de UI y 1 de seguridad (si aplica).

---

## 2) Arquitectura: estructura y reglas de dependencia

### 2.1 Estructura recomendada (genérica)

- `dominio/`
  - Entidades, Value Objects, invariantes, políticas de negocio puras.
- `aplicacion/`
  - Casos de uso, orquestación, DTOs, puertos (interfaces), validaciones de aplicación.
- `infraestructura/`
  - Implementaciones concretas: BD/ORM, FS, HTTP, colas, integraciones externas.
- `presentacion/`
  - UI / API / CLI: controladores, vistas, serialización entrada/salida; sin negocio.

Extras recomendados:
- `tests/`, `docs/`, `scripts/`, `configuracion/`, `logs/`

### 2.2 Reglas duras de dependencia

- `dominio` **no** depende de `aplicacion`, `infraestructura` ni `presentacion`.
- `aplicacion` depende de `dominio` y define **puertos**; no conoce detalles concretos.
- `infraestructura` implementa puertos; puede depender de `dominio/aplicacion`, pero **no** impone reglas de negocio.
- `presentacion` depende de `aplicacion` (y DTOs); evita depender directamente de infraestructura.

### 2.3 Guardarraíl de arquitectura (obligatorio)

Debe existir un “architecture gate” que falle si alguien rompe estas reglas.
Debe formar parte de `scripts.gate_pr` y `scripts.gate_rapido`.

---

## 3) Definition of Done (DoD) verificable

No se considera “hecho” hasta cumplir TODO (y el gate lo valida):

### 3.1 Calidad y estilo
- Lint en verde (ej. ruff/flake8).
- Formato aplicado (ej. ruff format/black).
- Tipado (si aplica): mypy/pyright en los módulos objetivo.

### 3.2 Tests y cobertura
- Suite rápida: `pytest -q`
- Suite con cobertura: `pytest -q --cov=... --cov-report=term-missing --cov-fail-under=85`

Reglas:
- El **CORE** (dominio + aplicación) debe ser lo más cubierto.
- Tests deterministas (sin sleeps arbitrarios; sin reloj real sin inyección; sin random sin semilla).
- Si hay UI, debe haber golden/smoke aunque no se mida por cobertura de líneas.

### 3.3 Complejidad y tamaño (anti-deuda)
Umbrales recomendados:
- Funciones: ≤ 40 líneas (sin contar docstring).
- Complejidad ciclomática: CC ≤ 10.
- Archivos: ≤ 300 líneas salvo excepción justificada.

---

## 4) Golden Gate UI (botones y apertura de ventanas)

### 4.1 Objetivo
Probar comportamiento y contratos, no píxeles.

### 4.2 Requisitos de instrumentación
- Cada elemento interactivo importante tiene identificador estable:
  `automation_id`, `objectName`, `data-testid`, etc.
- La UI delega acciones a handlers/controladores testables sin render real.

### 4.3 Qué verifica un golden test
- Secuencia de eventos:
  - `CLICK(boton_x)`
  - `DISPATCH(accion_y, payload_minimo)`
  - `OPEN_WINDOW(ventana_z, args_minimos)`
  - `SHOW_TOAST(tipo, clave_i18n, params)`
- Invocación del caso de uso correcto.
- Manejo de errores estable (mensaje i18n + logging).

### 4.4 Política de actualización de golden
- Por defecto, golden compara contra snapshots existentes.
- Actualizar snapshots requiere flag explícito:
  - `UPDATE_GOLDEN=1 pytest -q tests/golden`

---

## 5) i18n y “cero hardcodeo de texto visible”

### 5.1 Regla principal
Todo texto visible proviene de i18n:
- `t("CLAVE", **params)` o equivalente.

### 5.2 Catálogo recomendado
- `i18n/es.json`, `i18n/en.json` (o `.po`, `.yml`…)
- Claves semánticas y estables.

### 5.3 Gate anti-hardcode
Debe existir script/test que:
- escanee `presentacion/` (y UI),
- compare contra baseline si existe,
- falle ante **nuevos** hardcodes.

---

## 6) Inventario de features (auto-actualizado)

### 6.1 Fuente única (obligatoria)
`docs/features.yml` (o JSON) como verdad única.

Campos mínimos:
- `id` (ej. `FTR-001`)
- `nombre`
- `estado` (`DONE | TODO | WIP | BLOCKED`)
- `tipo` (`LOGICA | UI | SEGURIDAD | INFRA`)
- `tests` (rutas relevantes)
- `notas` (opcional)

### 6.2 Generación automática
Un script genera:
- `docs/features.md`
- `docs/features_pendientes.md`

### 6.3 Gate documental
El gate falla si:
- los docs generados no coinciden con la fuente única, o
- hay cambios sin regenerar.

---

## 7) Seguridad (mínimo profesional)

- Validación/sanitización antes de llegar a dominio.
- Secret scanning (pre-commit + CI).
- Escaneo de dependencias (ej. pip-audit) con política clara.
- No PII en logs. Mensajes al usuario sin stacktrace.

---

## 8) Logging y observabilidad

- Logging estructurado (JSONL recomendado).
- `correlation_id` por operación.
- Canales separados recomendados:
  - seguimiento (INFO/DEBUG)
  - error_operativo (ERROR manejado)
  - crash (CRITICAL/no controlado)
- Los logs operativos/crash deben reiniciarse en cada arranque (evita ruido).

---

## 9) PR Gate (Opción A) — Política obligatoria “no PR si no pasa”

### 9.1 Regla de oro
**NO crear PR** hasta que pase el gate local completo.

### 9.2 Protocolo obligatorio antes de abrir PR
1) Ejecutar: `python -m scripts.gate_pr`
2) Si falla:
   - corregir lo mínimo necesario,
   - re-ejecutar `python -m scripts.gate_pr`,
   - repetir hasta PASS.
3) Límite:
   - máximo 3 ciclos “arreglo → gate”.
   - si tras 3 intentos no pasa: **parar**, reportar el fallo y **NO** abrir PR.
4) Prohibiciones:
   - no bajar umbrales,
   - no desactivar checks,
   - no tocar baselines (i18n/golden) salvo cambio intencional y justificado.

### 9.3 Si el agente no puede ejecutar comandos
Si el entorno no permite correr el gate:
- se considera **FAIL**,
- **NO** se abre PR,
- se entrega:
  - lista exacta de comandos,
  - hipótesis del fallo,
  - plan mínimo de corrección.

---

## 10) Flujo Codex óptimo (prompts atómicos)

### 10.1 Reglas del prompt (obligatorias)
Todo prompt incluye:
- Objetivo exacto
- Alcance (qué toca y qué NO)
- Contratos (inputs/outputs/DTOs/puertos)
- Criterios de aceptación (tests + gates)
- Restricciones (arquitectura, i18n, naming, cobertura, no deuda)
- Plan corto por pasos
- Entregables (archivos/rutas)

### 10.2 Patrón de prompts (uno a uno)
1) Prompt de Lógica: caso de uso + tests unitarios.
2) Prompt de UI: wiring + i18n + golden tests.
3) Prompt de Seguridad: validación + tests de abuso.

Si una capa no aporta en un ciclo:
- escribir: “No necesario en este ciclo”.

---

## 11) Mejoras potentes para acotar trabajo (recomendadas)

### 11.1 Change Budget por prompt
Cada prompt debe declarar:
- máximo 10 archivos tocados (o el número que definas),
- máximo 300 LOC netos,
- prohibido refactor masivo fuera del alcance.

Si se supera:
- dividir en prompts más pequeños.

### 11.2 “No nueva API pública sin test”
Si se expone símbolo/endpoint/acción nueva:
- test obligatorio,
- doc mínima,
- i18n si es UI.

### 11.3 Determinismo por contrato (core)
Inyectar en CORE:
- reloj (`Clock`) y
- random (`RandomProvider`).
Prohibido depender de hora real o random sin semilla.

### 11.4 Pirámide de tests + gates separados
- `python -m scripts.gate_rapido`: feedback rápido (lint + unit core).
- `python -m scripts.gate_pr`: completo (coverage + golden + i18n + docs).

---

## 12) Especificación mínima de los gates (lo que deben ejecutar)

### 12.1 `python -m scripts.gate_rapido` (rápido)
Debe ejecutar, en orden:
1) lint
2) formato (o “check format”)
3) tests unitarios del CORE (rápidos)
4) architecture gate (imports/capas)
5) i18n hardcode check (si es rápido y existe)

### 12.2 `python -m scripts.gate_pr` (completo)
Debe ejecutar, en orden:
1) lint
2) formato
3) typecheck (si aplica)
4) tests rápidos (`pytest -q`)
5) tests con cobertura (`--cov-fail-under=85`)
6) golden UI (`pytest -q tests/golden`) si aplica
7) i18n hardcode check (con baseline si existe)
8) regeneración features docs (y verificación de limpieza de working tree)
9) security checks (secret scan y dependencias) según política definida

---

## Changelog
- v1: Contrato genérico para agentes: arquitectura, DoD, golden UI, i18n, seguridad, logging y flujo Codex.
- v1.1: Se adopta enfoque “un comando canónico” (gate_rapido/gate_pr) y PR Gate (Opción A).
