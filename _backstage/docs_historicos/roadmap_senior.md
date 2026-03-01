# Roadmap Seniorización (Mid -> Senior-) - Horas Sindicales

Estado global: **DOING** (Fase 1: blindaje + señal de calidad).

## KPIs de calidad (objetivos medibles)

- [DOING] **Coverage CORE >= 70%** (sin paquete `app/ui` en el gate bloqueante).
- [TODO] **UI_SMOKE verde >= 95%** de ejecuciones en `main` (ventana de 30 días).
- [TODO] **Tiempo CI bloqueante < 12 min (P95)** para PR estándar.
- [TODO] **0 regresiones críticas en releases** (incidentes Sev1/Sev2 por 2 sprints consecutivos).
- [TODO] **Debt visible**: reporte de LOC + complejidad + coverage por paquete publicado en cada CI.

## Backlog priorizado (ROI primero)

- [DONE] **P0**: separar CI en `CORE` bloqueante, `UI_SMOKE` bloqueante y `UI_EXTENDED` opcional.
  Esfuerzo: **M** · Riesgo: **M**
- [DONE] **P0**: subir umbral de coverage CORE de **63 -> 70** con alcance explícito sin UI.
  Esfuerzo: **S** · Riesgo: **B**
- [DONE] **P0**: generar reporte automático de señales de calidad (LOC, complejidad, coverage por paquete).
  Esfuerzo: **M** · Riesgo: **B**
- [DONE] **P0**: documentar estrategia de calidad en README para señal externa/portfolio.
  Esfuerzo: **S** · Riesgo: **B**
- [TODO] **P1**: estabilizar y etiquetar suite `ui_smoke` con casos canónicos de arranque/navegación mínima.
  Esfuerzo: **M** · Riesgo: **M**
- [TODO] **P1**: baseline de complejidad por módulo y presupuesto de crecimiento por sprint.
  Esfuerzo: **M** · Riesgo: **M**
- [TODO] **P2**: refactor orientado a hotspots (main_window_vista, sync_sheets/use_case) con ADR y tests de contrato.
  Esfuerzo: **L** · Riesgo: **A**

## Plan por sprints

### Sprint 0 (Blindaje inmediato)

- [DONE] Reconfigurar CI en 3 carriles (`CORE`, `UI_SMOKE`, `UI_EXTENDED`).
- [DONE] Eliminar dependencia de `continue-on-error` en smoke UI.
- [DONE] Subir gate de coverage CORE a 70% sin incluir `app/ui`.
- [DONE] Añadir reporte de calidad publicable como artefacto.
- [DONE] Actualizar README con narrativa de calidad y porqué técnico.

### Sprint 1 (Estabilización y observabilidad)

- [TODO] Congelar set de tests `UI_SMOKE` y medir flakiness semanal.
- [TODO] Añadir tablero de métricas CI (duración, retries, fallos por suite).
- [TODO] Definir umbrales de complejidad por paquete y alertas tempranas.
- [TODO] Reforzar guías de contribución para cambios de arquitectura.

### Sprint 2 (Reducción de riesgo técnico)

- [TODO] Diseñar plan de refactor incremental para hotspots (sin big-bang).
- [TODO] Añadir tests de caracterización previos al refactor de UI principal.
- [TODO] Elevar cobertura CORE objetivo a >= 75% si estabilidad de CI se mantiene.
- [TODO] Revisar y cerrar deuda abierta de alto riesgo.

## Definición de Done (DoD)

Un cambio se considera **DONE** si cumple TODO lo siguiente:

1. CI bloqueante (`CORE` + `UI_SMOKE`) en verde.
2. Sin regresiones funcionales en pruebas de contrato existentes.
3. Coverage CORE cumple umbral de gate vigente.
4. Se actualiza documentación operativa afectada (README/docs/scripts).
5. Roadmap de seniorización actualizado con estado real (TODO/DOING/DONE).
6. PR incluye evidencia reproducible (comandos + resultados).

## Registro de progreso de esta PR

- [DONE] Plan técnico ejecutable con KPIs, backlog priorizado, sprints y DoD.
- [DONE] Endurecimiento de CI por carriles y smoke UI bloqueante.
- [DONE] Quality gate progresivo con coverage CORE >= 70.
- [DONE] Reporte automatizado de calidad por paquete.
- [DONE] Actualización de documentación de calidad para portfolio.
- [DOING] Preparar siguiente PR: estabilización de suite `UI_SMOKE` (Sprint 1).

## Registro de progreso de esta PR (refactor sync_sheets lote escritura)

- [DONE] Extracción del servicio `ServicioEscrituraLotes` para centralizar flush de lotes y colas de append/update/backfill.
- [DONE] `app/application/use_cases/sync_sheets/use_case.py` reduce LOC en hotspot de sincronización: **1147 -> 1102** (`logs/quality_before.txt` vs `logs/quality_after.txt`).
- [DONE] Nuevo módulo creado: `app/application/use_cases/sync_sheets/servicio_escritura_lotes.py`.
- [DONE] Cobertura de comportamiento del servicio nuevo con casos unitarios de éxito, error propagado y lote vacío.
- [DONE] Objetivo de complejidad en extracción: métodos del servicio en funciones acotadas (sin ramas profundas, wrappers mínimos en `use_case.py`).

## Registro de progreso de esta PR (refactor builders main window)

- [DONE] Refactor incremental de `app/ui/vistas/builders/main_window_builders.py` a fachada con delegación por secciones.
- [DONE] Extracción en módulos por zona (`builders_barra_superior`, `builders_formulario_solicitud`, `builders_tablas`, `builders_sync_panel`) manteniendo wiring UI.
- [DONE] Reducción de LOC del hotspot: **937 -> 131** en `main_window_builders.py`.
- [DONE] Smoke test UI actualizado para validar widgets clave y conexión de `fecha_input.dateChanged`.


## Registro de progreso de esta PR (refactor state_controller historico/pendientes)

- [DONE] Extracción Iteración 1 en módulos nuevos: `app/ui/vistas/main_window/state_historico.py` y `app/ui/vistas/main_window/state_pendientes.py`.
- [DONE] Wrappers críticos AST conservados en `MainWindow` con delegación thin (1 línea).
- [DONE] LOC de `app/ui/vistas/main_window/state_controller.py`: **694 -> 694** (sin expansión; delegación refactor aplicada en wrappers).
