# AGENTS.md — Contrato operativo para agentes autónomos (Horas Sindicales)

## 1) Objetivo del documento

Este contrato regula la ejecución autónoma de agentes sobre este repositorio.
Aplica a cambios de lógica, UI, seguridad, documentación, scripts y pruebas.
Su objetivo es garantizar entregas pequeñas, verificables y alineadas con arquitectura, calidad y alcance.

Reglas de aplicación:
- Este archivo es vinculante para toda la raíz del repositorio.
- Si existe otra instrucción de mayor prioridad (sistema, developer, usuario), prevalece esa instrucción.
- Si una tarea entra en conflicto con este contrato, el agente debe detenerse y reportar bloqueo con evidencia.

---

## 2) Arquitectura (obligatoria)

### 2.1 Capas y límites
- `app/domain`: entidades, value objects, reglas de negocio puras.
- `app/application`: casos de uso, puertos, orquestación de dominio.
- `app/infrastructure`: adaptadores concretos, persistencia e integraciones.
- `app/ui`: presentación y wiring con casos de uso.

### 2.2 Dependencias permitidas
- `domain` no depende de `application`, `infrastructure` ni `ui`.
- `application` depende de `domain` y puertos propios.
- `infrastructure` puede depender de `application` y `domain` para implementar puertos.
- `ui` depende de `application`; acceso a infraestructura solo mediante puertos/casos de uso.

### 2.3 Prohibiciones duras
- Prohibida lógica de negocio en UI/controladores.
- Prohibido acceso directo desde UI a infraestructura concreta.
- Prohibidos imports circulares.
- Prohibido introducir dependencias de frameworks externos dentro de `app/domain`.
- Prohibido simplificar la arquitectura vigente.

### 2.4 Guardarraíles arquitectónicos
- Mantener en verde:
  - `tests/test_architecture_imports.py`
  - `tests/test_clean_architecture_imports_guard.py`
- Estos checks forman parte de `python -m scripts.gate_rapido` y `python -m scripts.gate_pr`.

---

## 3) Reglas de código

- Máximo 300 LOC por archivo; superar este límite está prohibido.
- Máximo 40 LOC por función (sin contar docstring); superar este límite está prohibido.
- Complejidad ciclomática máxima por función: 10; superar este límite está prohibido.
- Sin duplicación evitable.
- Nombres en español técnico coherente (se admiten términos técnicos estándar).
- Prohibidos hardcodes de texto visible: usar i18n.
- Cambios obligatoriamente pequeños, de bajo riesgo y alta trazabilidad.
- Prohibido `print` en código de aplicación; usar logging estructurado.
- No crear ni modificar binarios/artefactos compilados (`*.mo`, `*.pyc`, `*.sqlite3`, `*.db`, `*.png`, `*.zip`, `*.pdf`, equivalentes).

---

## 4) Testing y validación

### 4.1 Regla de cierre
Ninguna tarea se considera cerrada sin validación ejecutada y reportada.

### 4.2 Cobertura y estándar
- Cobertura mínima del core (`app/domain` + `app/application`): 85%.
- Tests deben ser deterministas, legibles y rápidos.
- Si la tarea no toca código, no se agregan tests nuevos sin motivo real.

### 4.3 Validaciones mínimas por tipo de cambio
- Cambio de código: ejecutar gate rápido durante desarrollo y gate PR antes de cerrar.
- Cambio documental: ejecutar guardarraíles documentales relevantes y, si coste razonable, gate rápido.

### 4.4 Golden UI
- Mantener golden tests de contratos de interacción en `tests/golden/botones`.
- Actualizar snapshots solo con intención explícita: `UPDATE_GOLDEN=1 pytest -q tests/golden/botones`.

---

## 5) Logging y observabilidad

- Logging estructurado obligatorio en runtime y en scripts nuevos o modificados.
- En código de aplicación está prohibido `print` sin excepción.
- En scripts existentes, `print` legado permitido solo donde ya exista; en líneas nuevas o editadas de scripts se exige logging estructurado y no se permite introducir nuevos `print`.
- Cada log operativo debe incluir, como mínimo: acción, módulo, resultado y error cuando aplique.
- Respetar la estrategia vigente de archivos/canales en `logs/` y documentación técnica del repositorio.

---

## 6) Seguridad

- Validar y sanear entradas antes de invocar dominio.
- No confiar en inputs externos ni en estado mutable implícito.
- Manejar errores de forma explícita y controlada.
- Prohibido exponer secretos o PII en logs, mensajes o artefactos.
- Mantener activos los checks de secretos del gate PR.

---

## 7) Flujo de trabajo autónomo del agente

### 7.1 Ejecución de tareas
- Trabajar en tareas atómicas y acotadas.
- Con orden humana explícita, ejecutar exactamente esa tarea y en ese orden.
- Sin orden humana explícita, seleccionar una única tarea según esta prioridad obligatoria:
  1. roturas verificables de imports, wiring o tests;
  2. validaciones/guardrails de bajo riesgo;
  3. bugs pequeños reproducibles;
  4. documentación contractual desalineada;
  5. deuda técnica pequeña, localizada y verificable.
- Prohibido iniciar tareas grandes si existe una tarea pequeña, segura y verificable en una prioridad igual o superior.
- Prohibido mezclar múltiples incidencias en una misma ejecución.
- No tocar código ni archivos fuera del alcance.
- Cambios mínimos, seguros y reversibles son obligatorios.

### 7.2 Gestión de dudas y bloqueos
- Ante ambigüedad o bloqueo, no ejecutar cambios especulativos.
- Si una validación exigida no puede ejecutarse por entorno, marcar estado `bloqueado/no verificable`.
- En estado `bloqueado/no verificable` está prohibido declarar tarea cerrada y está prohibido abrir PR.
- Reportar siempre: comando intentado, error exacto observado, limitación de entorno y siguiente paso mínimo recomendado.
- Prohibido declarar PASS, simular evidencia o inferir resultados no ejecutados.

### 7.3 Política de validación previa a PR
- No abrir PR sin pasar gate local aplicable.
- Ciclo máximo: 3 iteraciones de corrección y revalidación.
- Si no pasa tras 3 iteraciones: detener, reportar fallo y no abrir PR.
- Si una validación aplicable no se puede ejecutar por limitación de entorno, detener, reportar bloqueo y no abrir PR.

---

## 8) Prohibiciones explícitas

- No tocar binarios o artefactos compilados.
- No modificar infraestructura fuera de alcance.
- No hacer refactors globales sin orden explícita.
- No rebajar umbrales de calidad o cobertura.
- No desactivar checks ni gates contractuales.
- No falsificar resultados ni evidencias de validación.
- No introducir texto de relleno, placeholders o documentación hueca.
- No crear ni mantener sistemas paralelos de backlog o bitácora en `docs/` (incluidos `docs/roadmap_codex.md` y `docs/bitacora_codex.md`).

---

## 9) Criterios de cierre de una tarea

Una tarea queda cerrada solo si se cumple simultáneamente:
- Cambio funcional/documental coherente y operativo.
- Validaciones relevantes ejecutadas con evidencia.
- Sin contradicciones con scripts, tests y documentación vigente.
- Sin warnings críticos derivados del cambio.
- Sin huecos operativos para que otro agente continúe.
- No se acepta cierre por criterio subjetivo ("parece correcto").
- Si la validación aplicable no se ejecutó, el estado obligatorio es `bloqueado/no verificable`, nunca `hecho`.

---

## 10) Bitácora obligatoria de ejecución

Cada entrega del agente debe incluir:
- tarea ejecutada;
- alcance aplicado;
- archivos modificados;
- decisiones técnicas tomadas;
- validaciones ejecutadas y resultado;
- errores detectados y corrección aplicada;
- bloqueos actuales;
- siguiente paso recomendado.

Si no hubo cambios, registrar explícitamente: "sin cambios" y motivo.
La bitácora obligatoria se entrega en la salida de ejecución del agente y/o en el PR; no se materializa en archivos paralelos dentro de `docs/`.

---

## 11) Gates y comandos canónicos del repositorio

Fuente de verdad operativa:
- Gate rápido: `python -m scripts.gate_rapido`
- Gate PR: `python -m scripts.gate_pr`

### 11.1 Contrato real de `scripts.gate_rapido`
Ejecuta, en orden:
1. `ruff check .`
2. `ruff format --check` sobre scripts contractuales
3. `pytest -q tests/domain tests/application`
4. tests de arquitectura (`test_architecture_imports` + `test_clean_architecture_imports_guard`)
5. `python -m scripts.i18n.check_hardcode_i18n`

### 11.2 Contrato real de `scripts.gate_pr`
Ejecuta, en orden:
1. `ruff check .`
2. `ruff format --check` sobre scripts contractuales
3. `mypy app` solo si `HS_RUN_MYPY=1`
4. tests core no UI
5. cobertura core con `--cov-fail-under=85`
6. golden UI (`pytest -q tests/golden/botones` en harness no UI)
7. hardcode i18n
8. `python -m scripts.features_sync`
9. tests de secretos (`tests/test_no_secrets_committed.py` y `tests/test_no_secrets_content_scan.py`)
10. verificación de sincronización de `docs/features.md` y `docs/features_pendientes.md` contra `docs/features.json`

Regla contractual:
- CI y cierre de PR deben alinearse con `python -m scripts.gate_pr`.

---

## 12) Reglas de i18n, features y determinismo

### 12.1 i18n
- Todo texto visible debe salir de catálogo i18n.
- Mantener en verde `scripts.i18n.check_hardcode_i18n`.

### 12.2 Inventario de features
- Fuente única: `docs/features.json`.
- Documentos derivados obligatorios: `docs/features.md` y `docs/features_pendientes.md` mediante `python -m scripts.features_sync`.
- Quedan prohibidos `docs/roadmap_codex.md`, `docs/bitacora_codex.md` y cualquier backlog/bitácora paralelo fuera de la salida operativa del agente y del PR.

### 12.3 Determinismo
- Tests sin dependencia de reloj real o aleatoriedad no controlada en core.
- Evitar sleeps arbitrarios y efectos no deterministas.

---

## 13) Presupuesto de cambio por tarea

- Máximo por tarea atómica: 10 archivos modificados; superar este límite está prohibido.
- Máximo de delta por tarea: 300 LOC netas; superar este límite está prohibido.
- Si el trabajo requerido excede cualquier límite, dividir obligatoriamente en etapas antes de continuar.

---

## 14) DoD contractual resumido

Checklist obligatorio antes de declarar fin:
- arquitectura respetada;
- alcance respetado;
- validaciones ejecutadas;
- evidencia reportada;
- sin deuda técnica abierta por el cambio;
- sin alteración de gates ni umbrales de calidad.
