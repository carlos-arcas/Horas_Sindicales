# AUDITORÍA CRÍTICA v1

## 1) Resumen ejecutivo (10-15 líneas)
- Estado global: **APROBADO CON RIESGOS**.
- Nota global: **6.2/10**. La base técnica es seria (capas, tests de arquitectura, composition root explícito), pero hay deuda fuerte en observabilidad operativa, reproducibilidad Windows para testing y tamaño/coupling de módulos críticos.
- Fortaleza 1: existe control automático de imports entre capas con reglas explícitas y bloqueo de dependencias técnicas en `application`.
- Fortaleza 2: hay composition root claro con inyección manual y ensamblado de puertos/adaptadores en bootstrap.
- Fortaleza 3: existe suite de pruebas amplia por capas (domain/application/infrastructure/ui) y smoke tests de bootstrap.
- Riesgo 1: observabilidad incompleta para producción (sin rotación de logs, `print` en entrypoint y CLI de migraciones) rompe trazabilidad homogénea.
- Riesgo 2: mantenibilidad comprometida por módulos gigantes (UI y casos de uso con miles de líneas), alto coste de cambio y regresión.
- Riesgo 3: reproducibilidad Windows parcial: hay `launch.bat`, pero faltan scripts exigibles para ejecución de tests y dependencia de coverage no garantizada en entorno base.
- Acción retorno 1: estandarizar logging estructurado y eliminar `print`; aceptación: `rg "\bprint\(" app main.py` sin resultados y log en JSONL con rotación.
- Acción retorno 2: partir `app/ui/main_window.py` y `app/application/use_cases/__init__.py`; aceptación: ningún archivo de esos dominios supera 700 líneas.
- Acción retorno 3: formalizar tooling Windows de calidad (`lanzar_app.bat`, `ejecutar_tests.bat`) con entorno virtual y cobertura; aceptación: ambos scripts existen y terminan con código 0 en máquina limpia.

## 2) Scorecard (0-10) por aspecto, con justificación y evidencias

### A. Arquitectura Clean y dependencias entre capas
- **Nota: 7.5/10**
- **Evidencias**
  - `tests/test_architecture_imports.py::test_architecture_import_rules`
  - `tests/test_architecture_imports.py::test_application_forbidden_technical_imports`
  - `app/bootstrap/container.py::build_container`
  - `app/entrypoints/ui_main.py::run_ui`
  - `app/application/use_cases/__init__.py::(import app.pdf.pdf_builder)`
- **Qué está bien**
  - Gate automático de imports entre capas.
  - Composition root explícito y auditable.
  - Dominio sin dependencias de frameworks UI/DB.
- **Qué está mal / riesgo**
  - `application` depende de módulo transversal `app.pdf`, frontera difusa.
  - `infrastructure` importa puertos de `application` (`app/application/ports`), acoplamiento pragmático.
  - Capa `pdf` fuera de los cuatro anillos clásicos (clean estricta no cerrada).
- **Acción recomendada**
  - Definir `pdf` como puerto de salida formal y mover implementación a infraestructura (validar con test de arquitectura extendido).
  - Añadir regla de arquitectura para prohibir dependencias no declaradas entre subcapas.

### B. Cohesión, acoplamiento y diseño (SRP, duplicidades, tamaño de módulos)
- **Nota: 4.5/10**
- **Evidencias**
  - `app/ui/main_window.py::MainWindow` (~3363 LOC)
  - `app/application/use_cases/sync_sheets/use_case.py::SyncSheets*` (~1819 LOC)
  - `app/application/use_cases/__init__.py::PersonaUseCases/SolicitudUseCases/GrupoConfigUseCases` (~1072 LOC)
  - `app/infrastructure/repos_sqlite.py::Repositorios SQLite` (~859 LOC)
- **Qué está bien**
  - Existen controladores UI (`app/ui/controllers/*`) que intentan desacoplar eventos.
  - Hay DTOs y puertos para reducir acoplamiento directo entidad-UI.
- **Qué está mal / riesgo**
  - Clases/módulos “god object” con demasiadas responsabilidades.
  - Coste de revisión y pruebas de regresión alto por archivos monolíticos.
  - Mayor probabilidad de side-effects al tocar flujos críticos.
  - Dificulta onboarding técnico y ownership por equipo.
- **Acción recomendada**
  - Refactor por bounded responsibilities (estado UI, acciones, rendering, wiring).
  - Establecer regla de tamaño máximo por archivo/clase y chequeo en CI.

### C. Testing (unitarios/integración/E2E, cobertura y calidad)
- **Nota: 7.0/10**
- **Evidencias**
  - `tests/` con suites por capas (`domain`, `application`, `infrastructure`, `ui`, `bootstrap`).
  - `pytest tests/test_architecture_imports.py tests/bootstrap/test_logging_smoke.py tests/test___main___smoke.py -q` (5 passed).
  - `pytest -q` falla en recolección UI por dependencia de `libGL.so.1` ausente.
  - `pytest --cov=app ...` no ejecutable por ausencia de plugin `pytest-cov` en entorno actual.
- **Qué está bien**
  - Cobertura temática amplia y tests de arquitectura explícitos.
  - Smoke tests de bootstrap y entrypoint presentes.
- **Qué está mal / riesgo**
  - Cobertura real **NO EVALUABLE** aquí sin entorno completo.
  - Pipeline local no garantiza `pytest-cov` instalado automáticamente.
  - Tests UI dependen de librerías de sistema no documentadas en la guía mínima.
- **Acción recomendada**
  - Añadir verificación preflight de entorno de test (plugin cov + dependencias Qt headless).
  - Publicar comando único reproducible Windows para tests con cobertura.

### D. Observabilidad (logging, rotación, crash logs, trazabilidad, sin print)
- **Nota: 4.0/10**
- **Evidencias**
  - `app/bootstrap/logging.py::configure_logging` usa `FileHandler` sin rotación.
  - `app/bootstrap/logging.py::write_crash_log` crea `crash.log`.
  - `main.py::__main__` hace `print(...)` ante fallo fatal.
  - `app/infrastructure/migrations.py::main` usa `print(...)` en estado CLI.
  - `app/core/observability.py::log_event` registra dict pero sin formatter estructurado obligatorio.
- **Qué está bien**
  - Hay hook global de excepciones y crash log dedicado.
  - Existe correlation id en utilidades de observabilidad.
- **Qué está mal / riesgo**
  - Violación explícita de política “sin print”.
  - Sin rotación: riesgo de crecimiento indefinido de `app.log`.
  - Logging no está forzado a formato estructurado JSON en handlers.
- **Acción recomendada**
  - Implementar `RotatingFileHandler`/`TimedRotatingFileHandler` + formatter JSONL.
  - Reemplazar `print` por `logger` en entrypoints/CLI con IDs de error.

### E. Reproducibilidad/Packaging Windows (scripts .bat, .venv, requirements pin, rutas)
- **Nota: 5.5/10**
- **Evidencias**
  - `launch.bat` crea `.venv`, instala deps y ejecuta app.
  - Existen scripts release en `scripts/release/*.bat`.
  - No existen `lanzar_app.bat` ni `ejecutar_tests.bat` con esos nombres obligatorios.
  - `requirements.txt` y `requirements-dev.txt` usan rangos (`>=,<`) sin pin exacto.
- **Qué está bien**
  - Flujo de arranque Windows utilizable para usuario final.
  - Hay base de automatización para release.
- **Qué está mal / riesgo**
  - Reproducibilidad fuerte no garantizada por falta de lock/pin exacto.
  - Falta script estándar de tests para soporte interno.
  - Divergencia de nombres esperados vs scripts reales.
- **Acción recomendada**
  - Definir scripts canónicos solicitados y documentarlos en README.
  - Generar lockfile reproducible (pip-tools/uv) para build estable.

### F. UX preventiva y robustez UI (si aplica): hilos, bloqueo UI, progreso, errores, validaciones
- **Nota: 6.5/10**
- **Evidencias**
  - `app/ui/main_window.py::SyncWorker` y `PushWorker` en `QThread`.
  - `app/ui/main_window.py::MainWindow` mantiene estados `_sync_in_progress` y progreso en status bar.
  - `app/ui/error_mapping.py::map_error_to_ui_message` clasifica errores negocio/infra.
  - `app/ui/notification_service.py::NotificationService` genera `result_id` de operación.
- **Qué está bien**
  - Operaciones de sincronización salen del hilo principal.
  - Hay feedback al usuario (toasts, diálogos, estados).
  - Existe taxonomía básica de errores para UI.
- **Qué está mal / riesgo**
  - MainWindow excesivo dificulta garantizar no-bloqueo en todas las rutas.
  - El `result_id` UI no está correlacionado explícitamente con `correlation_id` de logs.
  - Falta contrato unificado de error con ID + stacktrace enlazable para soporte.
- **Acción recomendada**
  - Propagar correlation_id desde casos de uso a capa UI.
  - Añadir prueba de no-bloqueo/performance para operaciones largas de sincronización.

### G. Seguridad básica (credenciales, paths, sanitización, permisos)
- **Nota: 5.0/10**
- **Evidencias**
  - `app/infrastructure/local_config.py::SheetsConfigStore` guarda metadata en AppData.
  - `.gitignore` solo excluye `*.log`, `.venv`, `build/dist/output`.
  - `launch.bat` escribe logs de ejecución en directorio local.
  - No hay política visible de permisos/ACL para `config.json` y credenciales.
- **Qué está bien**
  - Separación de ruta de credenciales respecto al repo.
  - No se detectan secretos hardcodeados en código revisado.
- **Qué está mal / riesgo**
  - `.gitignore` no cubre artefactos sensibles potenciales (`*.db`, `credentials*.json`, `.env`).
  - No hay endurecimiento de permisos de archivos de configuración.
  - No hay validación explícita de rutas permitidas para credenciales.
- **Acción recomendada**
  - Endurecer `.gitignore` y política de secretos.
  - Validar y restringir ubicaciones de credenciales a directorio controlado.

### H. Documentación y trazabilidad (README, arquitectura, decisiones, changelog, VERSION)
- **Nota: 7.0/10**
- **Evidencias**
  - `README.md` amplio, con instalación, ejecución, arquitectura y quality gate.
  - `arquitectura.md` con diagrama textual y límites por capas.
  - `docs/decisiones.md`, `docs/definition_of_done.md`, `docs/release_process.md`.
  - `CHANGELOG.md` existe.
  - Archivo `VERSION` no existe.
- **Qué está bien**
  - Documentación base por encima de la media.
  - Hay trazabilidad de release y auditoría previa.
- **Qué está mal / riesgo**
  - Falta `VERSION` explícito para tooling y packaging.
  - Solapamiento entre `docs/CHANGELOG.md` y `CHANGELOG.md` puede inducir inconsistencia.
- **Acción recomendada**
  - Introducir `VERSION` único y automatizar su validación en release.
  - Consolidar fuente única de changelog.

### I. Mantenibilidad y escalabilidad (añadir features sin romper capas)
- **Nota: 5.0/10**
- **Evidencias**
  - `app/ui/main_window.py::MainWindow` centraliza demasiadas rutas funcionales.
  - `app/application/use_cases/__init__.py` concentra múltiples casos de uso.
  - `tests/test_architecture_imports.py` protege imports pero no complejidad/tamaño.
  - `app/bootstrap/container.py::build_container` muestra wiring manual creciente.
- **Qué está bien**
  - La separación por capas reduce parte del riesgo de expansión.
  - Existen tests que frenan regresiones de arquitectura por imports.
- **Qué está mal / riesgo**
  - Escalar features en módulos gigantes aumenta deuda exponencial.
  - Wiring manual sin fábricas por módulo puede crecer desordenadamente.
- **Acción recomendada**
  - Introducir módulos de feature y fábricas dedicadas por bounded context.
  - Añadir métricas de complejidad (radon/ruff mccabe) al gate.

### J. Calidad global (consistencia, naming en español, orden del repo)
- **Nota: 6.0/10**
- **Evidencias**
  - Mezcla de naming español/inglés (`MainWindow`, `sync`, `delegada`, `NotificationService`).
  - Estructura de carpetas principal está ordenada (`app`, `tests`, `docs`, `scripts`).
  - Existen documentos y scripts de release/quality gate.
- **Qué está bien**
  - Repositorio ordenado por dominios funcionales.
  - Convenciones generales de tipado y dataclasses bien usadas.
- **Qué está mal / riesgo**
  - Inconsistencia de idioma en identificadores y documentación parcial.
  - Nombres de scripts esperados por operación no están normalizados.
- **Acción recomendada**
  - Definir convención oficial de naming y aplicarla gradualmente con lint semántico.

## 3) Hallazgos clasificados (tabla en texto)
| Severidad | Hallazgo | Impacto | Evidencia | Recomendación |
|---|---|---|---|---|
| ALTO | Módulo UI monolítico | Alto riesgo de regresión y bloqueo de evolución | `app/ui/main_window.py::MainWindow` | Dividir por componentes/controladores con contratos y tests unitarios por sección |
| ALTO | Casos de uso concentrados en archivo gigante | Cambios de negocio con side-effects no controlados | `app/application/use_cases/__init__.py` | Separar casos de uso por agregado y puertos explícitos |
| ALTO | Dependencias de capa no canónicas por módulo transversal PDF | Frontera Clean incompleta y difícil de escalar | `app/application/use_cases/__init__.py::import app.pdf` | Convertir PDF en puerto de salida + adapter infra |
| MEDIO | Logging sin rotación | Riesgo operativo por crecimiento de logs y mantenimiento manual | `app/bootstrap/logging.py::configure_logging` | Activar rotación y política de retención |
| MEDIO | Uso de `print` en rutas de ejecución | Telemetría inconsistente, rompe estándar observabilidad | `main.py::__main__`, `app/infrastructure/migrations.py::main` | Reemplazar por logging estructurado con contexto |
| MEDIO | Reproducibilidad de dependencias no determinista | Diferencias entre entornos y builds no repetibles | `requirements*.txt` | Pin exacto + lockfile firmado |
| MEDIO | Scripts Windows obligatorios faltantes | Fricción de operación y soporte para equipos Windows | raíz del repo (ausencia de `lanzar_app.bat`, `ejecutar_tests.bat`) | Crear scripts estándar con contrato de salida |
| BAJO | Falta archivo VERSION | Trazabilidad de release incompleta | raíz del repo (ausencia de `VERSION`) | Añadir `VERSION` único y validarlo en release-check |

## 4) Plan de mejora priorizado (backlog)
- **P0-01**
  - Prioridad: P0
  - Esfuerzo: L
  - Riesgo: alto
  - Dependencias: Ninguna
  - Cambio propuesto: Partir `MainWindow` en módulos (estado, handlers, render tabs, sync flow).
  - Criterio de aceptación: `app/ui/main_window.py` < 700 LOC; tests `tests/ui/test_main_window_smoke.py` y `tests/ui/test_controllers_unit.py` pasan.
- **P0-02**
  - Prioridad: P0
  - Esfuerzo: L
  - Riesgo: alto
  - Dependencias: P0-01
  - Cambio propuesto: Separar `app/application/use_cases/__init__.py` en módulos por caso de uso.
  - Criterio de aceptación: módulo original eliminado o reducido a re-export; `pytest tests/application -q` pasa.
- **P0-03**
  - Prioridad: P0
  - Esfuerzo: M
  - Riesgo: alto
  - Dependencias: P0-02
  - Cambio propuesto: Definir puerto `PdfGeneratorPort` y mover implementación concreta a infraestructura.
  - Criterio de aceptación: sin import `app.pdf` desde `app/application`; test de arquitectura ampliado pasa.
- **P0-04**
  - Prioridad: P0
  - Esfuerzo: S
  - Riesgo: medio
  - Dependencias: Ninguna
  - Cambio propuesto: Eliminar `print` en `main.py` y CLI de migraciones.
  - Criterio de aceptación: `rg "\bprint\(" app main.py` devuelve 0 coincidencias funcionales.
- **P0-05**
  - Prioridad: P0
  - Esfuerzo: M
  - Riesgo: medio
  - Dependencias: P0-04
  - Cambio propuesto: Logging con rotación + formato JSONL + policy de retención.
  - Criterio de aceptación: logs rotan automáticamente y contienen campos `event`, `level`, `correlation_id`, `timestamp`.
- **P1-01**
  - Prioridad: P1
  - Esfuerzo: S
  - Riesgo: medio
  - Dependencias: Ninguna
  - Cambio propuesto: Crear `lanzar_app.bat` estándar (wrapper de `launch.bat` o reemplazo controlado).
  - Criterio de aceptación: script existe, crea `.venv`, instala deps y abre app en Windows limpio.
- **P1-02**
  - Prioridad: P1
  - Esfuerzo: S
  - Riesgo: medio
  - Dependencias: Ninguna
  - Cambio propuesto: Crear `ejecutar_tests.bat` con pytest y cobertura.
  - Criterio de aceptación: script devuelve exit code !=0 al fallar tests y muestra reporte de cobertura.
- **P1-03**
  - Prioridad: P1
  - Esfuerzo: M
  - Riesgo: medio
  - Dependencias: P1-02
  - Cambio propuesto: Incorporar lockfile de dependencias reproducible.
  - Criterio de aceptación: instalación determinista y hashable en CI.
- **P1-04**
  - Prioridad: P1
  - Esfuerzo: M
  - Riesgo: bajo
  - Dependencias: P0-05
  - Cambio propuesto: Correlacionar `result_id` UI con `correlation_id` técnico.
  - Criterio de aceptación: error mostrado al usuario incluye ID rastreable en logs.
- **P1-05**
  - Prioridad: P1
  - Esfuerzo: S
  - Riesgo: bajo
  - Dependencias: Ninguna
  - Cambio propuesto: Añadir `VERSION` y validación en release-check.
  - Criterio de aceptación: `make release-check` falla si `VERSION` y changelog no están alineados.
- **P1-06**
  - Prioridad: P1
  - Esfuerzo: S
  - Riesgo: medio
  - Dependencias: Ninguna
  - Cambio propuesto: Endurecer `.gitignore` para secretos/DB temporales.
  - Criterio de aceptación: `.gitignore` cubre `*.db`, `credentials*.json`, `.env*`.
- **P2-01**
  - Prioridad: P2
  - Esfuerzo: S
  - Riesgo: bajo
  - Dependencias: Ninguna
  - Cambio propuesto: Unificar convención de idioma para naming técnico.
  - Criterio de aceptación: guía de estilo publicada + lint de naming aplicado a nuevas contribuciones.
- **P2-02**
  - Prioridad: P2
  - Esfuerzo: M
  - Riesgo: bajo
  - Dependencias: P0-01, P0-02
  - Cambio propuesto: Agregar métrica de complejidad y tamaño al quality gate.
  - Criterio de aceptación: gate falla si LOC/CC exceden umbrales definidos.

## 5) Quick wins (máx 5)
- Sustituir `print` por logger en entrypoint y migraciones. Criterio: búsqueda de `print(` en app/main sin coincidencias funcionales.
- Añadir `VERSION` en raíz y referenciarlo desde release. Criterio: release-check valida versión.
- Crear `ejecutar_tests.bat` para estandarizar calidad en Windows. Criterio: comando único genera pass/fail + cobertura.
- Endurecer `.gitignore` para evitar fugas de secretos/DB. Criterio: patrón para credenciales y DB incluido.
- Activar rotación de logs en bootstrap. Criterio: al superar tamaño umbral se crea archivo rotado.

## 6) Checklist de cumplimiento (con PASS/FAIL)
- [x] No hay imports prohibidos entre capas (**PASS**)
- [x] Dominio sin dependencias externas (**PASS**)
- [x] No hay lógica de negocio en UI (**PASS** parcial, sin hallazgo crítico verificable)
- [ ] Logging estructurado sin prints (**FAIL**)
- [ ] Logs con rotación + crashes.log (**FAIL**: crash existe, rotación no)
- [ ] requirements.txt con versiones fijadas (**FAIL**)
- [ ] Scripts .bat: lanzar_app.bat y ejecutar_tests.bat (**FAIL**)
- [ ] pytest --cov... pasa con >=85% (**NO EVALUABLE** sin plugin/entorno)
- [x] docs mínimos existen (**PASS**)
- [ ] VERSION y CHANGELOG.md existen (**FAIL** por ausencia de VERSION)

## 7) Comandos recomendados (Windows)
- Lanzar app:
  - `launch.bat` (actual)
  - Recomendado estandarizar alias: `lanzar_app.bat` -> invoca flujo de `launch.bat`.
- Ejecutar tests + cobertura:
  - Recomendado: `ejecutar_tests.bat` con contrato conceptual:
    1) crear/activar `.venv`
    2) instalar `requirements-dev.txt`
    3) ejecutar `pytest --cov=app --cov-report=term-missing --cov-fail-under=85`
    4) devolver código de salida de pytest
- Si faltan scripts:
  - Nombre exacto propuesto: `lanzar_app.bat`, `ejecutar_tests.bat`
  - Especificación conceptual únicamente (sin implementación completa en esta auditoría).
