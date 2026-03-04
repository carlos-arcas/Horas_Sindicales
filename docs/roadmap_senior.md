# Roadmap Senior

## 2026-03-04 — Fix arranque: evitar salida prematura tras splash_closed
- Causa raíz: hueco sin ventanas visibles tras `splash_closed` + `quitOnLastWindowClosed=True`, lo que permite que el event loop se cierre antes de `show()` del wizard/main.
- Fix: durante transición de arranque se fuerza temporalmente `quitOnLastWindowClosed=False`, se restaura tras `main_window_shown` y se añaden BOOT_STAGE de diagnóstico (`about_to_quit`, `last_window_closed`, `run_ui_exec_enter`, `run_ui_exec_exit`, `wizard_*`, `main_window_*`).
- Tests añadidos: cobertura de restauración de `quitOnLastWindowClosed` en el flujo de `on_finished`.

## 2026-03-04 — Fix boot splash + guard anti-crash
- Fix boot: splash closed before wizard/main + guard anti-crash 0xc0000374.

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

## 2026-03-04 — Refactor UI deuda builders_formulario_solicitud
- UI deuda: `builders_formulario_solicitud.py` **antes 344 LOC -> después 12 LOC**.
- Módulos creados:
  - `app/ui/vistas/builders/formulario_solicitud/contratos.py`
  - `app/ui/vistas/builders/formulario_solicitud/builders_solicitud.py`
  - `app/ui/vistas/builders/formulario_solicitud/builders_pendientes.py`
  - `app/ui/vistas/builders/formulario_solicitud/bindings_senales.py`
  - `app/ui/vistas/builders/formulario_solicitud/helpers_puros.py`
  - `app/ui/vistas/builders/formulario_solicitud/helpers_qt.py`
- Resultado: fachada fina con API pública estable (`create_formulario_solicitud`) y separación por responsabilidades de secciones, wiring y helpers.

## 2026-03-04 — Refactor UI deuda builders_sync_panel
- UI deuda: `builders_sync_panel.py` **antes 379 LOC -> después 11 LOC**.
- Módulos creados:
  - `app/ui/vistas/builders/sync_panel/orquestacion_sync_panel.py`
  - `app/ui/vistas/builders/sync_panel/builders_secciones.py`
  - `app/ui/vistas/builders/sync_panel/builders_diagnostico.py`
  - `app/ui/vistas/builders/sync_panel/bindings_senales.py`
  - `app/ui/vistas/builders/sync_panel/helpers_puros.py`
  - `app/ui/vistas/builders/sync_panel/helpers_qt.py`
  - `app/ui/vistas/builders/sync_panel/contratos.py`
  - `app/ui/vistas/builders/sync_panel/__init__.py`
- Resultado: `builders_sync_panel.py` queda como fachada fina y mantiene el contrato público (`create_sync_panel`) delegando construcción, bindings y utilidades por responsabilidad.

## 2026-03-04 — Refactor UI deuda conflicts_dialog
- UI deuda: `app/ui/conflicts_dialog.py` **antes 339 LOC -> después 3 LOC** (fachada vía `app/ui/conflicts_dialog/__init__.py`).
- Módulos creados:
  - `app/ui/conflicts_dialog/dialogo_qt.py`
  - `app/ui/conflicts_dialog/presenter_conflictos.py`
  - `app/ui/conflicts_dialog/contratos.py`
  - `app/ui/conflicts_dialog/adaptador_i18n.py`
- Resultado: separación Qt/presenter puro con API pública estable (`from app.ui.conflicts_dialog import ConflictsDialog`).

## 2026-03-04 — Refactor UI deuda copy_catalog
- UI deuda: `app/ui/copy_catalog.py` **antes 469 LOC -> después 41 LOC** (fachada en `app/ui/copy_catalog/__init__.py`).
- Módulos creados:
  - `app/ui/copy_catalog/orquestacion_catalogo.py`
  - `app/ui/copy_catalog/parseo_catalogo.py`
  - `app/ui/copy_catalog/diff_catalogo.py`
  - `app/ui/copy_catalog/storage_catalogo.py`
  - `app/ui/copy_catalog/modelos.py`
  - `app/ui/copy_catalog/catalogo.json`
- Tests añadidos:
  - `tests/application/test_copy_catalog_puros.py`
- Resultado: catálogo i18n de UI mantenido con API pública (`copy_text`, `copy_keys`) y separación de parseo/diffs/storage en módulos puros testeables sin Qt.

## 2026-03-04 — Fix CI wrappers+naming+métricas
- Fix CI: wrappers MainWindow + naming debt + métrica `pdfs_generados`.
- Renombres de archivos/símbolos para deuda de naming: `presenter_conflictos.py` → `presentador_conflictos.py`, `confirmacion_presenter_pendientes.py` → `confirmacion_presentador_pendientes.py`, `confirmacion_qt_adapter.py` → `confirmacion_adaptador_qt.py`, `helpers_*.py` → `ayudantes_*.py`, `ViewModel*` → `ModeloVista*`, `ConflictsTableModel` → `ModeloTablaConflictos`, `resolver_dto_y_persona_para_creacion` → `resolver_peticion_y_persona_para_creacion`.
- Se restauró el incremento del contador `pdfs_generados` en exportación de histórico usando el registro de métricas activo (monkeypatch-friendly).

## 2026-03-04 — Refuerzo tests contratos MainWindow: menos frágiles ante refactors
- Se reforzaron los tests de contrato de `MainWindow` para evitar dependencia rígida de `state_controller.py`.
- Cambios clave: búsqueda AST multiarchivo (`state_controller.py`, `main_window_vista.py`, `app/ui/main_window.py`) + resolución de métodos en mixins de `app/ui/vistas/main_window/`.
- Se mantiene enforcement: firma de handlers de señales (incluyendo `QDate`) y validación de wrappers mínimos por delegación (`super().metodo(...)`) cuando el wrapper existe en archivos fachada.

## 2026-03-04 — Fix CI i18n_hardcode + ui_smoke import
- Fix CI: i18n_hardcode nuevos=5 -> 0 + ui_smoke import NameError (SolicitudDTO) resuelto.
