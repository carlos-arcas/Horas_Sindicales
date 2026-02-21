# AUDITORÍA CRÍTICA v1

## 1) Resumen ejecutivo (10-15 líneas)
- Estado global: **APROBADO CON RIESGOS**.
- Nota global: **6.4/10**.
- Explicación: la base de arquitectura por imports está razonablemente protegida por tests automáticos, pero hay deuda crítica de diseño (módulos gigantes y mezcla de responsabilidades) que compromete escalabilidad y capacidad de cambio sin regresiones.
- Fortaleza 1: existen pruebas explícitas de fronteras de capas y dependencias prohibidas, incluyendo variantes `app/*` y paquetes espejo en español.
- Fortaleza 2: observabilidad sólida en runtime principal con JSONL, rotación y `crashes.log`.
- Fortaleza 3: reproducibilidad Windows cuidada con scripts `.bat` que crean `.venv`, instalan dependencias y validan `pytest-cov`.
- Riesgo 1: casos de uso de aplicación con tamaño y responsabilidades excesivas (lógica + persistencia + orquestación), alto riesgo de regressions y bajo aislamiento.
- Riesgo 2: UI principal monolítica y con conocimiento de reglas de dominio, elevando acoplamiento presentación-negocio.
- Riesgo 3: trazabilidad de calidad incompleta en entorno actual: no se pudo medir cobertura real por falta de plugin de cobertura instalado en esta ejecución.
- Acción retorno 1: fragmentar `main_window_vista.py` y `sync_sheets/use_case.py` con límites por feature (criterio: bajar ambos archivos por debajo de 800 líneas).
- Acción retorno 2: mover validaciones/reglas de negocio invocadas desde UI a casos de uso dedicados (criterio: UI deja de importar validadores de dominio directamente).
- Acción retorno 3: endurecer pipeline para asegurar `pytest-cov` efectivo en entorno CI/dev (criterio: comando oficial de cobertura ejecuta y publica porcentaje >=85%).

## 2) Scorecard (0-10) por aspecto, con justificación y evidencias

### A. Arquitectura Clean y dependencias entre capas
- **Nota: 7.5/10**
- **Evidencias**
  - `tests/test_architecture_imports.py::test_architecture_import_rules`
  - `tests/test_architecture_imports.py::test_application_pdf_and_infrastructure_boundary`
  - `app/bootstrap/container.py::build_container`
  - `app/application/use_cases/sync_sheets/use_case.py::SheetsSyncService`
- **Qué está bien**
  - Hay reglas automáticas que bloquean imports prohibidos entre capas.
  - Existe composition root explícito en `build_container`.
  - La aplicación usa puertos en varios puntos del módulo sync.
- **Qué está mal / riesgo**
  - `SheetsSyncService` concentra lógica de aplicación y detalles de persistencia/SQL.
  - La capa application absorbe demasiada orquestación técnica en un solo módulo.
- **Acción recomendada**
  - Separar `SheetsSyncService` en orquestadores + gateways específicos (aceptación: sin SQL inline en caso de uso principal).
  - Añadir test arquitectónico de “máximo tamaño por módulo crítico” para prevenir regresión.

### B. Cohesión, acoplamiento y diseño (SRP, duplicidades, tamaño de módulos)
- **Nota: 3.5/10**
- **Evidencias**
  - `app/ui/vistas/main_window_vista.py::MainWindowVista` (3343 líneas)
  - `app/application/use_cases/sync_sheets/use_case.py::SheetsSyncService` (1819 líneas)
  - `app/application/use_cases/solicitudes/use_case.py::SolicitudUseCases` (887 líneas)
  - `app/infrastructure/repos_sqlite.py::SolicitudRepositorySQLite` (859 líneas)
- **Qué está bien**
  - Hay intención de separación por submódulos en `sync_sheets/*` (`planner`, `executor`, `reporting`).
- **Qué está mal / riesgo**
  - Módulos de miles de líneas: SRP incumplido de facto.
  - Aumenta coste de revisión, onboarding y depuración.
  - Acoplamiento temporal alto en UI principal.
- **Acción recomendada**
  - Definir budget de complejidad por archivo (aceptación: CI falla si >800 líneas en módulos productivos críticos).
  - Extraer presenters/controllers de UI por flujo funcional con pruebas unitarias dedicadas.

### C. Testing (unitarios/integración/E2E, cobertura y calidad)
- **Nota: 6.0/10**
- **Evidencias**
  - `pytest --collect-only -q` (258 tests recogidos antes de error de entorno)
  - `tests/e2e/test_auditoria_e2e_generates_auditoria_files.py::test_auditoria_e2e_generates_auditoria_files`
  - `tests/ui/test_controllers_unit.py::test_sync_controller_blocks_reentrancy`
  - `tests/integration/test_exception_logging_contains_id.py::test_exception_logging_contains_id`
  - `tests/test_quality_gate_metrics.py` falla en colección por `ModuleNotFoundError: radon`
- **Qué está bien**
  - Suite amplia con unit/integration/e2e.
  - Pruebas específicas para arquitectura, logs, scripts Windows y políticas de repo.
- **Qué está mal / riesgo**
  - Cobertura real **NO EVALUABLE sin ejecución completa con pytest-cov activo**.
  - Entorno actual no tiene `radon`, rompiendo colección total.
- **Acción recomendada**
  - Ejecutar `ejecutar_tests.bat` en entorno limpio y publicar cobertura efectiva (aceptación: salida con `%` y umbral >=85%).
  - Blindar preflight de dependencias dev antes de test suite.

### D. Observabilidad (logging, rotación, crash logs, trazabilidad, sin print)
- **Nota: 8.0/10**
- **Evidencias**
  - `app/bootstrap/logging.py::configure_logging`
  - `app/bootstrap/logging.py::JsonLinesFormatter`
  - `app/bootstrap/exception_handler.py::manejar_excepcion_global`
  - `scripts/quality_gate.py::main` (uso de `print`)
  - `scripts/release/release.py::main` (uso de `print`)
- **Qué está bien**
  - JSONL estructurado con `correlation_id` y `result_id`.
  - Rotación activa y separación `seguimiento.log` / `crashes.log`.
  - Manejador global de excepciones con ID de incidente.
- **Qué está mal / riesgo**
  - Persisten `print` en scripts operativos (fuera de runtime app, pero contradicen estándar estricto).
- **Acción recomendada**
  - Sustituir `print` por logging estructurado también en scripts (aceptación: búsqueda `rg "\bprint\(" app scripts` devuelve 0 coincidencias en código productivo).

### E. Reproducibilidad/Packaging Windows (scripts .bat, .venv, requirements pin, rutas)
- **Nota: 9.0/10**
- **Evidencias**
  - `lanzar_app.bat::(bootstrap .venv e instalación deps)`
  - `ejecutar_tests.bat::(pytest --cov ... --cov-fail-under=85)`
  - `tests/test_windows_scripts_contract.py::test_windows_scripts_contract_tokens`
  - `requirements.txt` y `requirements-dev.txt` con versiones fijadas
- **Qué está bien**
  - Scripts robustos con `%~dp0`, logs y creación de `.venv`.
  - Verificación explícita de `pytest-cov` antes de ejecutar cobertura.
  - Dependencias pinneadas.
- **Qué está mal / riesgo**
  - Duplicidad de launchers (`launch.bat`, `launcher.bat`, `lanzar_app.bat`) puede confundir operación.
- **Acción recomendada**
  - Declarar script canónico y deprecar aliases (aceptación: README referencia un único launcher oficial).

### F. UX preventiva y robustez UI (si aplica): hilos, bloqueo UI, progreso, errores, validaciones
- **Nota: 6.5/10**
- **Evidencias**
  - `app/ui/controllers/sync_controller.py::_run_background_operation` (QThread)
  - `app/ui/workers/sincronizacion_workers.py::SyncWorker.run`
  - `app/ui/vistas/main_window_vista.py` (gestión masiva de UI + validación/flujo)
  - `tests/ui/test_error_message_includes_incident_id.py::test_error_message_includes_incident_id`
- **Qué está bien**
  - Operaciones de sync se ejecutan en background thread.
  - Hay manejo de errores y mensaje orientado al usuario.
- **Qué está mal / riesgo**
  - Vista principal hipermonolítica: difícil asegurar no bloqueos colaterales.
  - Mezcla de lógica de flujo/validación en capa de presentación.
- **Acción recomendada**
  - Particionar vista por subcomponentes y mover validaciones a casos de uso/policies (aceptación: UI sin imports directos de validadores de dominio).

### G. Seguridad básica (credenciales, paths, sanitización, permisos)
- **Nota: 7.0/10**
- **Evidencias**
  - `tests/test_no_secrets_committed.py::test_no_secrets_in_repo`
  - `app/bootstrap/settings.py::resolve_log_dir`
  - `app/infrastructure/local_config_store.py::LocalConfigStore`
- **Qué está bien**
  - Test automático de secretos comprometidos.
  - Resolución de directorio de logs con validación de escritura.
- **Qué está mal / riesgo**
  - No se evidencian controles centralizados de sanitización de rutas de credenciales en esta revisión.
  - Modelo de permisos de archivos sensibles **NO EVALUABLE** desde código inspeccionado.
- **Acción recomendada**
  - Añadir validación explícita de rutas permitidas y permisos de archivo para credenciales (aceptación: tests unitarios cubren rutas inválidas y permisos inseguros).

### H. Documentación y trazabilidad (README, arquitectura, decisiones, changelog, VERSION)
- **Nota: 9.0/10**
- **Evidencias**
  - `tests/test_docs_minimas.py::test_docs_minimas_existen`
  - `docs/arquitectura.md`
  - `docs/decisiones_tecnicas.md`
  - `CHANGELOG.md`
  - `VERSION`
- **Qué está bien**
  - Set mínimo documental cubierto y testeado.
  - VERSION y CHANGELOG presentes.
- **Qué está mal / riesgo**
  - Existe duplicidad de changelog (`docs/CHANGELOG.md` y raíz), potencial divergencia.
- **Acción recomendada**
  - Definir fuente de verdad de changelog y enlazar la otra como derivada (aceptación: política documental explícita en README).

### I. Mantenibilidad y escalabilidad (añadir features sin romper capas)
- **Nota: 4.5/10**
- **Evidencias**
  - `app/ui/vistas/main_window_vista.py`
  - `app/application/use_cases/sync_sheets/use_case.py`
  - `app/infrastructure/repos_sqlite.py`
  - `tests/test_architecture_imports.py`
- **Qué está bien**
  - Guardrails de arquitectura reducen riesgo de violaciones groseras.
- **Qué está mal / riesgo**
  - Tamaño y acoplamiento de módulos críticos frena evolución segura.
  - Refactors en piezas gigantes implican alto blast radius.
- **Acción recomendada**
  - Plan de descomposición incremental con contratos de interfaz estables (aceptación: PRs de refactor sin cambios funcionales y tests de snapshot verdes).

### J. Calidad global (consistencia, naming en español, orden del repo)
- **Nota: 7.0/10**
- **Evidencias**
  - `tests/test_naming_conventions_guardrail.py`
  - `tests/test_spanish_layer_packages_are_thin.py`
  - coexistencia de `app/*` + `dominio/aplicacion/infraestructura/presentacion`
- **Qué está bien**
  - Existen guardrails de naming y paquetes puente.
  - Estructura ordenada y amplia cobertura de políticas.
- **Qué está mal / riesgo**
  - Nombres duplicados en capas espejo pueden confundir ownership.
- **Acción recomendada**
  - Publicar mapa de ownership por carpeta y responsabilidades (aceptación: documento con responsables + límites por capa).

## 3) Hallazgos clasificados (tabla en texto)
| Severidad | Hallazgo | Impacto | Evidencia | Recomendación |
|---|---|---|---|---|
| ALTO | Módulo UI monolítico extremo | Aumenta regresiones y hace inviable revisión fina de cambios UI+flujo | `app/ui/vistas/main_window_vista.py::MainWindowVista` | Dividir por features/paneles con controladores aislados |
| ALTO | Caso de uso sync sobredimensionado | Mezcla reglas y detalles técnicos, dificulta test unitario puro | `app/application/use_cases/sync_sheets/use_case.py::SheetsSyncService` | Extraer servicios de dominio/aplicación y adaptadores dedicados |
| MEDIO | Cobertura real no medible en entorno actual | Imposible afirmar cumplimiento >=85% en esta corrida | comando `pytest -q --cov=. ...` falla por argumentos no reconocidos | Asegurar instalación de `pytest-cov` en entorno de ejecución |
| MEDIO | Dependencia dev faltante en colección total | Se rompe validación integral de suite | `tests/test_quality_gate_metrics.py` + error `ModuleNotFoundError: radon` | Instalar `requirements-dev.txt` antes de colección completa |
| MEDIO | Presencia de `print` en scripts operativos | Trazabilidad inconsistente fuera de runtime principal | `scripts/quality_gate.py::main`, `scripts/release/release.py::main` | Migrar scripts a logging estructurado |
| BAJO | Duplicidad de launchers y changelogs | Riesgo de confusión operativa/documental | `launch.bat`, `launcher.bat`, `lanzar_app.bat`; `CHANGELOG.md` y `docs/CHANGELOG.md` | Definir artefacto canónico y aliases documentados |

## 4) Plan de mejora priorizado (backlog)
- **P0-01**
  - Prioridad: P0
  - Esfuerzo: L
  - Riesgo: alto
  - Dependencias: ninguna
  - Cambio propuesto: dividir `main_window_vista.py` en vistas por contexto (solicitudes, sync, configuración, histórico).
  - Criterio de aceptación: ningún archivo UI supera 800 líneas; tests UI existentes pasan.
- **P0-02**
  - Prioridad: P0
  - Esfuerzo: L
  - Riesgo: alto
  - Dependencias: P0-01
  - Cambio propuesto: separar `SheetsSyncService` en orquestador + servicios especializados (`planner`, `executor`, `repository_gateway`).
  - Criterio de aceptación: `use_case.py` <800 líneas y sin SQL inline en métodos públicos.
- **P0-03**
  - Prioridad: P0
  - Esfuerzo: S
  - Riesgo: medio
  - Dependencias: ninguna
  - Cambio propuesto: reforzar entorno test instalando deps dev antes de ejecutar colección/cobertura.
  - Criterio de aceptación: `pytest --collect-only -q` termina sin errores de import.
- **P0-04**
  - Prioridad: P0
  - Esfuerzo: S
  - Riesgo: medio
  - Dependencias: P0-03
  - Cambio propuesto: hacer obligatorio `pytest-cov` en pipeline de calidad.
  - Criterio de aceptación: `pytest --cov=. --cov-report=term-missing --cov-fail-under=85` ejecuta y reporta porcentaje.
- **P1-01**
  - Prioridad: P1
  - Esfuerzo: M
  - Riesgo: medio
  - Dependencias: P0-02
  - Cambio propuesto: mover validaciones de negocio usadas en UI a use cases/policies.
  - Criterio de aceptación: UI no importa `app.domain.request_time` ni servicios de dominio directos para validar formularios.
- **P1-02**
  - Prioridad: P1
  - Esfuerzo: S
  - Riesgo: bajo
  - Dependencias: ninguna
  - Cambio propuesto: reemplazar `print` en scripts por logging JSONL.
  - Criterio de aceptación: `rg "\bprint\(" app scripts -n` no reporta scripts operativos.
- **P1-03**
  - Prioridad: P1
  - Esfuerzo: S
  - Riesgo: bajo
  - Dependencias: ninguna
  - Cambio propuesto: unificar launcher oficial y documentar aliases deprecados.
  - Criterio de aceptación: README define único launcher recomendado.
- **P1-04**
  - Prioridad: P1
  - Esfuerzo: M
  - Riesgo: medio
  - Dependencias: P0-02
  - Cambio propuesto: añadir métricas de complejidad por módulo en quality gate.
  - Criterio de aceptación: CI falla cuando un módulo crítico supera umbral acordado.
- **P2-01**
  - Prioridad: P2
  - Esfuerzo: S
  - Riesgo: bajo
  - Dependencias: ninguna
  - Cambio propuesto: definir política única de changelog canónico.
  - Criterio de aceptación: docs y raíz apuntan a la misma fuente oficial.
- **P2-02**
  - Prioridad: P2
  - Esfuerzo: M
  - Riesgo: medio
  - Dependencias: P1-01
  - Cambio propuesto: documentar mapa de ownership técnico por carpeta/capa.
  - Criterio de aceptación: documento versionado con responsables y límites de dependencia.

## 5) Quick wins (máx 5)
- QW-01: instalar `requirements-dev.txt` en entorno local/CI antes de correr pytest completo.
  - Criterio de aceptación: `pytest --collect-only -q` sin `ModuleNotFoundError`.
- QW-02: eliminar `print` de `scripts/quality_gate.py` y `scripts/release/release.py`.
  - Criterio de aceptación: `rg "\bprint\(" scripts -n` retorna 0 para scripts operativos.
- QW-03: declarar launcher canónico en README.
  - Criterio de aceptación: sección “Arranque Windows” con un único comando principal.
- QW-04: añadir regla CI de tamaño máximo en módulos críticos.
  - Criterio de aceptación: fallo automático al superar umbral configurado.
- QW-05: registrar explícitamente cobertura real en artefacto de auditoría.
  - Criterio de aceptación: `auditoria.json` incluye `cobertura_porcentaje` no nulo en ejecución completa.

## 6) Checklist de cumplimiento (con PASS/FAIL)
- [x] No hay imports prohibidos entre capas (**PASS**)
- [x] Dominio sin dependencias externas (**PASS**)
- [ ] No hay lógica de negocio en UI (**FAIL**)
- [ ] Logging estructurado sin prints (**FAIL**)
- [x] Logs con rotación + crashes.log (**PASS**)
- [x] requirements.txt con versiones fijadas (**PASS**)
- [x] Scripts .bat: lanzar_app.bat y ejecutar_tests.bat (**PASS**)
- [ ] pytest --cov... pasa con >=85% (**FAIL / NO EVALUABLE sin entorno con pytest-cov activo**)
- [x] docs mínimos existen (**PASS**)
- [x] VERSION y CHANGELOG.md existen (**PASS**)

## 7) Comandos recomendados (Windows)
- Lanzar app:
  - `lanzar_app.bat`
- Ejecutar tests + cobertura:
  - `ejecutar_tests.bat`
  - alternativo directo: `python -m pytest --cov=. --cov-report=term-missing --cov-fail-under=85`
- Si faltan scripts en otro repo/proyecto, especificación mínima esperada:
  - `lanzar_app.bat`: crear/activar `.venv`, instalar `requirements.txt`, crear `logs`, ejecutar entrypoint.
  - `ejecutar_tests.bat`: crear/activar `.venv`, instalar `requirements.txt` + `requirements-dev.txt`, ejecutar pytest con cobertura y umbral.
