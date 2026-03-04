# Roadmap Senior

## 2026-03-04 — Coverage CORE
- Coverage CORE (estimación local con `trace`): **antes ~88% -> después ~89%** en `app/domain` + `app/application`.
- Tests añadidos:
  - `tests/domain/test_time_utils_cobertura.py` para ramas de validación y normalización de `time_utils`.
  - `tests/application/test_personas_use_case_cobertura.py` para ramas de orquestación de `PersonaUseCases`.
- Objetivo: subir margen sobre el umbral de CI (`>=85%`) sin cambios funcionales.

## 2026-03-04 — Coverage CORE (bloqueo entorno pytest-cov)
- Coverage CORE: **antes N/D -> después N/D** (no medible en este entorno).
- Tests añadidos: **ninguno**; ciclo detenido por falta de `pytest-cov` (comando canónico falla al parsear `--cov`).
- Objetivo de auditoría: dejar evidencia explícita del bloqueo para destrabar CI reproduciendo el prerequisito de cobertura en entorno con dependencias de dev.


## 2026-03-04 — Refactor SolicitudUseCases (orquestadores)
- `SolicitudUseCases` (CORE) pasó de **828 LOC -> 718 LOC** (`app/application/use_cases/solicitudes/use_case.py`).
- CC top antes/después: **N/D -> N/D** (radon no disponible en este entorno; `report_quality` usa fallback por LOC).
- Módulos creados:
  - `app/application/use_cases/solicitudes/orquestacion_confirmacion.py` (flujo de confirmar lote/sin PDF y generación de PDF confirmadas).
  - `app/application/use_cases/solicitudes/orquestacion_pendientes.py` (listar pendientes y helpers de consultas de pendientes).
  - `app/application/use_cases/solicitudes/orquestacion_exportaciones.py` (exportaciones PDF histórico y resolución de personas por lote).
- Resultado: `SolicitudUseCases` queda más fino como orquestador y delega responsabilidades en módulos especializados, manteniendo contratos públicos y comportamiento observable.

## 2026-03-04 — Refactor UI MainWindow state_controller
- UI Deuda: `state_controller.py` **antes 843 LOC -> después 251 LOC**.
- Módulos creados:
  - `app/ui/vistas/main_window/navegacion_mixin.py`
  - `app/ui/vistas/main_window/refresco_mixin.py`
  - `app/ui/vistas/main_window/acciones_mixin.py`
  - `app/ui/vistas/main_window/inicializacion_mixin.py`
  - `app/ui/vistas/main_window/estado_mixin.py`

## 2026-03-04 — Refactor UI deuda confirmacion_actions
- UI deuda: `confirmacion_actions.py` **antes 562 LOC -> después ~227 LOC**.
- Módulos creados:
  - `app/ui/vistas/confirmacion_orquestacion.py`
  - `app/ui/vistas/confirmacion_presenter_pendientes.py`
  - `app/ui/vistas/confirmacion_eventos_auditoria.py`
  - `app/ui/vistas/confirmacion_qt_adapter.py`
- Resultado: `confirmacion_actions.py` queda como fachada fina con API pública estable y delegación a módulos por responsabilidad.

## 2026-03-04 — Refactor UI deuda sync_reporting
- UI deuda: `sync_reporting.py` **antes 593 LOC -> después 65 LOC**.
- Módulos creados:
  - `app/ui/sync_reporting_orquestacion.py` (casos de construcción de `SyncReport` y delegación de métricas).
  - `app/ui/sync_reporting_formatters.py` (helpers puros de texto/i18n, markdown y fechas ISO).
  - `app/ui/sync_reporting_storage.py` (persistencia/carga de reportes e historial en filesystem).
  - `app/ui/sync_reporting_builders.py` (builders puros de warnings/errors/conflicts y entradas de simulación).
- Resultado: `app/ui/sync_reporting.py` queda como fachada fina y mantiene API pública compatible.
