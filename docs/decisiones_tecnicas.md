# Decisiones técnicas

## Registro de decisiones relevantes

> Formato: `Fecha — Decisión — Estado — Justificación`.

- **2026-02-20 — Lockfiles pinneados (`requirements.txt` y `requirements-dev.txt`) — Vigente**  
  Se mantiene instalación reproducible entre local, CI y scripts de Windows.

- **2026-02-20 — Fuentes editables separadas (`requirements.in` / `requirements-dev.in`) — Vigente**  
  La edición se hace en `.in`; los `.txt` se regeneran con `pip-compile`.

- **2026-02-20 — Logging estructurado JSONL con trazabilidad (`correlation_id`) — Vigente**  
  Facilita auditoría y seguimiento extremo a extremo de operaciones críticas.

- **2026-02-20 — Estrategia de pruebas con `pytest` y cobertura (`--cov`) — Vigente**  
  Se estandariza ejecución local, en Windows y en pipelines con umbral de cobertura.

- **2026-02-20 — Normalización documental: canonical en `/docs` para arquitectura — Vigente**  
  `arquitectura.md` de raíz pasa a stub de redirección para evitar duplicidad confusa.

- **2026-02-20 — Duplicidad de changelog: canonical en raíz (`CHANGELOG.md`) — Vigente**  
  `docs/CHANGELOG.md` queda como stub/enlace de compatibilidad para consulta rápida.

- **2026-02-25 — Colisiones horarias de pendientes acotadas por delegada (`persona_id`) — Vigente**  
  Diagnóstico: la detección de solapes en pendientes agrupaba sólo por `fecha_pedida`, lo que marcaba falsos conflictos entre delegadas distintas. Se corrige para evaluar por `(persona_id, fecha_pedida)` y mantener el bloqueo sólo dentro de la misma delegada.

- **2026-03-01 — Reglas de filtrado de histórico movidas de UI a aplicación — Vigente**  
  Antes: `app/ui/vistas/historico_filter_rules.py` contenía lógica de aceptación/descartes por estado, rango y búsqueda. Después: reglas puras en `app/domain/services.py`, y el módulo UI queda como shim de compatibilidad sin negocio. Se refuerza con guard de imports entre capas.


- **2026-03-02 — Arranque UI aislado del worker Qt para evitar cruces de hilo — Vigente**  
  El `TrabajadorArranque` quedó restringido a tareas de arranque no-UI y ahora emite `ResultadoArranque` (dataclass) en vez de tuplas ad-hoc.  
  La construcción y wiring de `SplashWindow`/`MainWindow` permanece en el hilo principal con conexión encolada (`QueuedConnection`), reduciendo el riesgo del warning `QObject: Cannot create children for a parent that is in a different thread` y cierres silenciosos durante splash.


- **2026-03-05 — Qt thread confinement en arranque: sin QObjects en worker — Vigente**  
  El worker de arranque ahora devuelve solo `ResultadoArranqueCore` (container core) y no ejecuta `crear_mainwindow_deps` ni ninguna factoría Qt.  
  La creación de `DependenciasArranque`, `MainWindow` y `Wizard` se concentra en `on_finished` (hilo UI) y se protege con `asegurar_en_hilo_ui(...)`. Si se detecta violación de hilo, se registra `UI_QT_THREAD_VIOLATION`, se marca la etapa `qt_thread_violation_detected` y el flujo cae a fallback controlado en lugar de continuar con warnings silenciosos.


- **2026-03-06 — Smoke UI de Confirmar+PDF obligatorio en CI (sin skip silencioso) — Vigente**  
  Se endurece `tests/ui/test_confirmar_pdf_mainwindow_smoke.py` para que, en ejecución local, pueda marcar `skip` si PySide6/backend Qt no está disponible, pero en CI (flag explícita `HORAS_UI_SMOKE_CI=1`) cualquier ausencia de backend pase a error duro.  
  El objetivo es eliminar falsos verdes por `skip`: esta prueba es la evidencia operativa crítica de que el flujo real `selección -> guardar PDF -> mover a histórico -> respetar toggle Abrir PDF` funciona de extremo a extremo y con trazas observables en artifact JSON.

- **2026-03-06 — Smoke real MainWindow confirmar+PDF ahora valida transiciones funcionales diagnósticas — Vigente**  
  El smoke real deja de validar únicamente estado final (ej. existencia de PDF) y pasa a comprobar hitos contractuales por escenario (`START`, `SELECTED_ROWS`, `SAVE_PATH_CHOSEN`, `EXECUTE_OK/ERROR`, `OPEN_OK`, `RETURN_EARLY`) junto con conteos antes/después de pendientes e histórico y evidencia JSON separada por escenario + resumen maestro.  
  Esto reduce falsos verdes porque un pass exige trazabilidad funcional completa del flujo visible y, en caso de fallo, permite ubicar el punto exacto de rotura sin inferencias manuales.


- **2026-03-07 — Fuente única runtime para dataset de pendientes en UI — Vigente**  
  Se detectó incoherencia porque la tabla, el contador de ocultas y los mensajes de “otras delegadas” no leían siempre el mismo cálculo: en algunos ciclos se combinaba `listar_pendientes_all()` con ramas por delegada y derivaciones separadas de ocultas.  
  Se centraliza el contrato en `calcular_estado_dataset_pendientes(...)`, que entrega simultáneamente: totales, visibles, ocultas, “otras delegadas” y motivos de exclusión por fila. `reload_pending_views` consume ese único estado para render, copy de warning/CTA y sincronización de selección, garantizando que con “ver todas delegadas” no queden ocultas por delegada.


- **2026-03-07 — Post-confirmación de Solicitudes desacoplada a módulo puro de estado — Vigente**  
  `SolicitudesController.aplicar_confirmacion` deja de mezclar derivación de listas y pasa a orquestar: construye entrada, delega en `resolver_estado_post_confirmacion(...)` y aplica el resultado en `window`.  
  El contrato de post-confirmación queda explícito para `_pending_solicitudes`, `_pending_all_solicitudes`, `_pending_otras_delegadas`, `_hidden_pendientes` y `_orphan_pendientes`, reduciendo fragilidad de stubs UI y permitiendo tests puros sin Qt.


- **2026-03-07 — MainWindow: estado de acciones centralizado en resolver puro de presentación — Vigente**  
  Se detectó fragilidad porque `_update_action_state` (proxy) y `state_helpers.update_action_state` derivaban flags en paralelo (persona, pendientes, selección, conflictos y sync), con riesgo de contradicciones por refresh o por cambios parciales.  
  Se define una única fuente de verdad en `estado_acciones.py` con contrato explícito de entrada/salida (dataclasses) y función pura `resolver_estado_acciones_main_window(...)`. La UI queda como orquestador: lee estado, llama al resolver y aplica widgets/textos sin duplicar reglas.

## Procedimiento de actualización

1. Añadir una nueva entrada con fecha ISO (`YYYY-MM-DD`).
2. Indicar estado (`Vigente`, `Revisar`, `Deprecada`).
3. Resumir impacto técnico (build, runtime, calidad o trazabilidad).
4. Referenciar docs complementarias cuando aplique (`guia_pruebas`, `guia_logging`, arquitectura).

## Pendiente de completar

- Pendiente de completar un ADR formal por cada integración externa crítica si auditoría lo exige.

- **2026-03-01 — Wiring perezoso de preferencias con fallback INI headless — Vigente**  
  `build_container()` deja de importar `QSettings` en import-time y resuelve el adaptador en runtime para evitar fallos en colección de tests UI en CI sin backend Qt completo.  
  Si `infraestructura.repositorio_preferencias_qsettings` no está disponible, se registra `RepositorioPreferenciasIni` (sin PySide6) y se emite WARNING estructurado para trazabilidad operativa.  
  La aplicación sigue dependiendo del puerto `IRepositorioPreferencias`; las implementaciones concretas permanecen en infraestructura, preservando inversión de dependencias y compatibilidad Windows.

- **2026-03-02 — Normalización de datetimes ISO en reportes de sincronización — Vigente**  
  Se extrae `app/ui/tiempo/parseo_iso_datetime.py` para centralizar `parsear_iso_datetime`, `normalizar_zona_horaria` y `duracion_ms_desde_iso`, evitando restas entre `datetime` naive/aware en `build_simulation_report` y demás constructores de reportes.  
  Política aplicada: si el valor ISO llega naive se asume zona horaria local y luego se normaliza explícitamente a la zona objetivo del cálculo.

- **2026-03-02 — `duracion_ms_desde_iso` tolera ISO inválido sin excepción — Vigente**  
  Se protege el cálculo con manejo de `TypeError`/`ValueError` y se retorna `0` ante entradas inválidas para evitar caídas en reportes cuando llega un `generated_at` corrupto o incompleto.  
  Verificación recomendada: `pytest -q tests/application/test_parseo_iso_datetime.py tests/application/test_sync_reporting_datetime.py` y `python -m scripts.quality_gate`.


- **2026-03-08 — Contexto de delegada: resolución pura para cambio + estado de configuración — Vigente**  
  Se detectó fragilidad por lógica repartida entre handlers UI: lectura de `currentData`, decisión de confirmación por formulario sucio y habilitación de botones de configuración.  
  Se introduce `resolver_estado_contexto_delegada(...)` en `app/ui/vistas/main_window/contexto_delegada.py` con entrada/salida tipadas para centralizar la decisión. `acciones_personas` queda como orquestador mínimo (leer widgets → resolver → confirmar si aplica → aplicar cambio), reduciendo acoplamiento y mejorando testabilidad sin Qt real.

## 2026-03-04 — Reportes de contenido y moderación (MVP)

- Se implementa idempotencia con índice único parcial SQLite sobre `(denunciante_id, recurso_tipo, recurso_id)` cuando `estado='pendiente'`.
- **Trade-off**: se evita FK genérica a múltiples tablas de recursos para mantener bajo acoplamiento y coste de migración; se valida existencia desde repositorio de moderación por tipo de recurso.
- Si `ocultar_recurso` falla por inexistencia, el reporte se resuelve como `descartar` para evitar colas eternas.

- **2026-03-05 — Watchdog de arranque UI con timeout configurable y guardrail late-finish — Vigente**  
  Se añade un watchdog explícito de arranque para evitar bloqueos indefinidos en splash: si no se llega a estado terminal dentro de `STARTUP_TIMEOUT_MS` (resuelto por configuración + entorno), se marca `startup_timeout`, se cierra splash y se activa fallback con detalle de última etapa alcanzada.  
  Se registran eventos estructurados `UI_STARTUP_TIMEOUT` (ERROR con `ultima_etapa`, `timeout_ms`, `elapsed_ms`) y `UI_STARTUP_FINISHED_AFTER_TIMEOUT` (WARNING con decisión `ignore`) para descartar resultados tardíos del worker y evitar transiciones UI inconsistentes.

- **2026-03-05 — Mostrar ayuda contextual condicionado a valor operativo — Vigente**  
  El bloque de estado de Solicitudes se reemplaza por un resumen operativo contextual (delegada, selección, pendientes y saldo reservado) más una próxima acción concreta.  
  El control **Mostrar ayuda** solo se mantiene visible/habilitado cuando existe ayuda contextual accionable; en estados “lista para confirmar y generar PDF” se oculta temporalmente para evitar texto redundante sin valor.

- **2026-03-06 — Extracción mínima de helpers runtime desde `ui_main.py` — Vigente**  
  Para cumplir el budget de tamaño del quality gate sin alterar comportamiento, se movieron helpers cohesivos de splash/watchdog/fallback y dump de widgets a `app/entrypoints/ayudantes_arranque_interfaz.py`.  
  `ui_main.py` mantiene el rol de orquestador del pipeline de arranque; se preservan contratos y wiring existentes mediante enlace explícito de métodos al coordinador.

- **2026-03-07 — Toasts con doble capa (humana + técnica) y cierre manual consistente — Vigente**  
  Se separa el contenido visible del toast (estado simple + frase humana) de los detalles técnicos (`details`) que quedan detrás de la acción **Ver detalles**. Esto evita exponer `correlation_id`, trazas o códigos internos en la primera capa y mantiene trazabilidad para soporte.  
  Además, el cierre manual prioriza emitir señal de dominio UI (`cerrado`) para que el gestor limpie modelo/cache/timer en un único punto y evite “zombies” visuales o incoherencias.  
  En paralelo, se unifica un estilo sobrio reutilizable para diálogos de feedback/confirmación (cabecera clara, espaciado estable, bordes por severidad), evitando aspecto de diálogo Qt desnudo y estilos inline dispersos.

- **2026-03-07 — Pendientes: diálogos de duplicado/conflicto consumen copy catalog (sin hardcode UI) — Vigente**  
  El flujo de `acciones_pendientes` deja de declarar textos visibles inline para el diálogo de pendiente duplicada (título, cuerpo, ayuda, botones y tooltip de bloqueo) y para los prompts de sustitución parcial/completo.  
  Se consolidan claves en `app/ui/copy_catalog/catalogo.json` y la vista solo resuelve copy mediante `copy_text(...)`, manteniendo UX y haciendo que el guard de hardcodes valide el contrato i18n sin tocar baseline.

- **2026-03-07 — Externalización de estilos QSS de toasts y diálogos para cumplir i18n_hardcode sin tocar baseline — Vigente**  
  **Problema:** el quality gate `i18n_hardcode` marcaba nuevos offenders en `app/ui/notification_service.py` y `app/ui/widgets/widget_toast.py` por bloques QSS inline, aunque no eran copys visibles al usuario.  
  **Causa raíz:** las hojas de estilo de `OperationFeedbackDialog`, `dialogoConfirmacionResumen` y `TarjetaToast` estaban embebidas como literales en Python, por lo que el escáner AST de strings UI las detectaba como hardcodes nuevos.  
  **Por qué no se tocó baseline:** la baseline no era el problema; el problema era estructural (estilo inline en código UI). Ajustar baseline ocultaría regresión arquitectónica y rompería el contrato del gate.  
  **Solución aplicada:** se movió la fuente de verdad de estilos a `app/ui/estilos/*.qss` y se creó `app/ui/estilos/cargador_estilos_notificaciones.py` para leer/parametrizar plantillas (toast + diálogos) sin incrustar bloques QSS en esos `.py`.  
  **Ventaja arquitectónica:** UI más limpia, estilos reutilizables/testeables, menor acoplamiento de presentación, y prevención explícita de regresión mediante test dedicado que bloquea reintroducir QSS inline en los dos archivos críticos.

- **2026-03-07 — Notificaciones/toasts: presentación pura para confirmar cierre y recepción de toasts — Vigente**  
  Se desacopla la construcción de copy/resumen de `NotificationService.show_confirmation_closure` hacia `app/ui/presentacion_confirmacion_notificaciones.py` y la decisión de ids a cerrar de `GestorToasts.recibir_notificacion` hacia `app/ui/toasts/presentador_recepcion_toast.py`.  
  Resultado: menor complejidad ciclomática en hotspots UI, contratos más testeables (presentación confirmación y limpieza/dedupe de recepción) y mismo comportamiento visible/callbacks del sistema de toasts.

- **2026-03-08 — Consolidación de contratos de toast en helper de tests compartido — Vigente**  
  Se detectó duplicación en tests de compatibilidad del `ToastManager` (captura de payload `show(...)` y validación de acción asociada) que elevaba ruido y coste de mantenimiento sin aportar cobertura nueva.  
  Se extrae `tests/ui/toast_test_helpers.py` con utilidades puras para registrar llamadas y validar contrato de acción (`level`, `action_label`, `action_callback` callable), manteniendo asserts funcionales y reduciendo fragilidad por repetición.

- **2026-03-09 — Consolidación de carga stub de `ToastManager` en tests UI — Vigente**  
  Se detectó duplicación real en la preparación de stubs de módulos Qt para `app.ui.widgets.toast` en suites de compatibilidad (`test_toast_manager_api_compat` y `test_toast_manager_action_kwargs_puros`).  
  Se centralizó la carga en `tests/ui/toast_module_loader.py`, eliminando repetición de wiring de `sys.modules` y reduciendo fragilidad por divergencia entre tests que validan el mismo contrato (kwargs de acción, firma pública y validación de kwargs desconocidos).  
  El cambio mantiene los asserts funcionales intactos y mejora auditabilidad al dejar una única fuente de verdad del entorno stub para este eje de toasts.

- **2026-03-09 — Consolidación de instrumentación de `ToastManager` en tests de compatibilidad — Vigente**  
  Se detectó duplicación en la preparación de `manager.show` para capturar payloads de `success/error` en varios tests del eje toast (compatibilidad de kwargs de acción y firma pública).  
  Se extrajo `instrumentar_manager_con_registro(...)` en `tests/ui/toast_test_helpers.py` para reutilizar un único contrato de captura tipada (`message`, `level`, `title`, `action_label`, `action_callback`) sin ocultar asserts funcionales.  
  El alcance se mantuvo exclusivamente en tests; no se tocó runtime, no se redujo cobertura y se bajó boilerplate repetido en tres módulos del eje.

- **2026-03-09 — Harness pytest core/UI: desactivar `pytest-qt` en runs `not ui` desde fuente única — Vigente**  
  Se detectó que, con `pytest-qt` instalado, el plugin intentaba autodetectar Qt en `pytest_configure` y disparaba `ImportError` al coexistir con el bloqueo contractual de `PySide6` para core (`-m "not ui"`), provocando `INTERNALERROR` en vez de fallo controlado.  
  Se centralizó la política en `app/testing/qt_harness.py` (constante `PLUGIN_PYTEST_QT`) y se aplicó en `scripts/gate_pr.py`, `scripts/diagnosticar_pytest.py` y `scripts/quality_gate.py` para forzar `-p no:pytestqt -p no:pytestqt.plugin` solo en runs core/no-ui.  
  Resultado: los runs core preservan el contrato “sin Qt/PySide6”, mientras que los runs UI mantienen soporte de `pytest-qt`/`qtbot`, y `HORAS_UI_SMOKE_CI=1` conserva modo estricto sin degradar a skip.

- **2026-03-09 — `update_action_state` dividido en helpers de presentación para cumplir budget de complejidad — Vigente**  
  El `quality_gate` reportó `cc_targets: FAIL` en `app/ui/vistas/main_window/state_helpers.py:update_action_state` (CC=9 con límite=8). La función concentraba tres responsabilidades de UI: (1) cálculo de estado, (2) habilitación de controles y (3) actualización de copy en botones de histórico.  
  Se refactorizó en el mismo módulo de presentación sin mover negocio de capa: `update_action_state` quedó como orquestador y se extrajeron `_aplicar_habilitacion_controles`, `_actualizar_textos_historico` y `_actualizar_texto_boton_historico`.  
  Decisión: **refactor** y no ajuste de budget, porque el hotspot sí tenía responsabilidad acumulada real y el límite actual (8) sigue siendo coherente para este punto crítico de mantenibilidad UI.


- **2026-03-10 — Política única de arranque pytest core/no-ui: autoload OFF + reinyección explícita de plugins — Vigente**  
  Se confirmó un rojo de harness donde `pytest-qt` podía autoload-earse antes de aplicar `-p no:pytestqt`, detonando `INTERNALERROR` al coexistir con el bloqueo contractual de `PySide6` en `tests/conftest.py`.  
  Se fija política auditable para runs core/no-ui: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` + `PYTEST_CORE_SIN_QT=1`, y se reinyectan explícitamente los plugins requeridos por comando (`-p pytest_cov` cuando aplica cobertura, `-p no:pytestqt -p no:pytestqt.plugin` para blindar ausencia de Qt). Esta política se aplica de forma homogénea en `scripts/gate_pr.py`, `scripts/diagnosticar_pytest.py`, `scripts/quality_gate.py` y en pasos shell directos de `.github/workflows/ci.yml`.  
  Resultado esperado: los jobs core/no-ui no descubren Qt/PySide6 ni cargan `pytest-qt` por autoload, se mantiene cobertura con `pytest-cov`, y los jobs UI/smoke conservan `qtbot` bajo `HORAS_UI_SMOKE_CI=1` estricto.

- **2026-03-10 — Blindaje de sub-runs core/no-ui posteriores en `gate_pr` con fuente única de harness — Vigente**  
  Se identificó una ruta remanente en `scripts/gate_pr.py` donde varios sub-runs de `pytest` (suite `tests/domain + tests/application`, cobertura core y scans de secretos) se invocaban sin reutilizar la política central del harness (`app/testing/qt_harness.py`). En entornos CI con autoload de plugins, esa divergencia permitía cargar `pytest-qt` y provocar `ImportError` de `libEGL`/`Qt` fuera de los jobs UI.  
  Se corrigió con una fábrica única de comandos core/no-ui en `gate_pr` que aplica siempre args de plugin (`-p no:pytestqt -p no:pytestqt.plugin` y `-p pytest_cov` cuando corresponde) y entorno contractual (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTEST_CORE_SIN_QT=1`). Se mantienen intactos los runs UI (golden/smoke) y `HORAS_UI_SMOKE_CI=1` estricto.

- **2026-03-10 — Cierre de escape residual en sub-run `tests/golden/botones` dentro de `gate_pr` — Vigente**  
  Se verificó que aún existía una invocación directa `python -m pytest -q tests/golden/botones` en `scripts/gate_pr.py` fuera de `_comando_pytest_core_no_ui(...)`; por esa vía el runner quedaba sin `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` y podía autoload-ear `pytest-qt`, reproduciendo el `INTERNALERROR` por `libEGL.so.1` en CI.  
  Se migró ese sub-run a la misma fábrica reusable de comandos core/no-ui para unificar política de plugins/entorno en todo `gate_pr` y se reforzó el contrato con tests en `tests/tools/test_gate_pr.py` que exigen blindaje explícito también para `tests/golden/botones`.

- **2026-03-13 — Contrato explícito de capacidades opcionales para botones de MainWindow — Vigente**  
  Se detectó deuda técnica en el contrato runtime de botones: la disponibilidad de `open_saldos_modal_button` dependía de `hasattr/getattr` sobre un atributo privado mágico (`_saldos_dialog_class`) sin declarar capacidad de forma explícita.  
  Se introduce `app/ui/vistas/main_window/capacidades_opcionales.py` como registro explícito (`capacidades_opcionales`) y APIs pequeñas (`registrar_capacidades_opcionales`, `obtener_capacidad_opcional`, `capacidad_disponible`). `state_controller` registra `modal_saldos_detalle` en el arranque, `acciones_personas` consume la capacidad declarada para abrir el modal y `contrato_botones` declara dependencias opcionales por botón mediante `nombre_capacidad_opcional`.  
  Resultado: se mantiene UX vigente (habilitar/deshabilitar + tooltip de indisponibilidad), se elimina la dependencia del atributo privado mágico para saldos y el contrato queda más testeable y mantenible sin reescritura de MainWindow.

- **2026-03-13 — Desacople de imports Qt en contrato/capacidades/saldos para pytest directo — Vigente**  
  Se diagnosticó que los tests focales de contrato/capacidades/saldos fallaban en `pytest` directo por carga transitiva de Qt desde el paquete `app.ui.vistas.main_window`: importar `app.ui.vistas.main_window.capacidades_opcionales` ejecutaba `main_window/__init__.py`, que importaba `layout_builder` y detonaba `ImportError: libGL.so.1`. Además, `acciones_personas` importaba `PersonaDialog` en módulo raíz, forzando `PySide6` incluso al usar sólo `on_open_saldos_modal`.  
  Se aplicó carga diferida en `main_window/__init__.py` con `__getattr__` + `import_module` para evitar imports pesados al consumir submódulos puros, y se movió el import de `PersonaDialog` a helper local (`_crear_dialogo_persona`) usado únicamente en acciones que realmente abren ese diálogo.  
  Resultado: `test_capacidades_opcionales`, `test_contrato_botones` y `test_boton_saldos` corren con `pytest` directo sin wrapper del gate en entorno sin stack gráfico completo, manteniendo intacto el comportamiento funcional del botón de saldos en la UI real.

- **2026-03-18 — UI read-only sin fallbacks implícitos y con inventario mutante auditado — Vigente**  
  Se detectó una ambigüedad en `MainWindow`: la UI aceptaba `proveedor_ui_solo_lectura` pero, si faltaba, derivaba el estado desde dependencias internas (`_politica_modo_solo_lectura`) o caía a `lambda: False`, lo que ocultaba wiring roto y reintroducía lógica de backend dentro de presentación. Además, el inventario centralizado de acciones mutantes no cubría todos los triggers visibles relevantes (por ejemplo, sincronizaciones explícitas, borrado de huérfanas y la acción de menú para cargar demo).  
  Se fija contrato explícito: `proveedor_ui_solo_lectura` pasa a ser obligatorio y callable en `state_controller.MainWindow`, `state_helpers` falla si el proveedor no está inyectado y `ui_main` expone/inyecta también la acción de menú demo para que el bloqueo read-only siga una única fuente de verdad UI. Se amplía `ACCIONES_MUTANTES_AUDITADAS_UI` con triggers mutantes reales de sincronización/menú y se añaden guardarraíles estructurales que prohíben reintroducir fallback silencioso o acceso UI a `_politica_modo_solo_lectura`.  
  Resultado: la UI ya no es “read-only explícita pero opcional”; el wiring roto falla temprano, la auditoría mutante es trazable desde una sola constante y el patrón queda protegido por tests AST/contrato.

- **2026-03-18 — Política UI de solo lectura extraída a módulo dedicado con descriptores inmutables — Vigente**  
  Persistía deuda de cohesión en `state_helpers`: además de orquestar el estado general de botones, también era owner del inventario mutante auditado, del tooltip preventivo y del disable read-only. Ese acoplamiento hacía crecer un helper mochila y mantenía la auditoría muy dependiente de strings dispersos.  
  Se extrae la política de presentación a `app/ui/vistas/main_window/politica_solo_lectura.py`, con un inventario inmutable basado en `DescriptorAccionMutante` y APIs acotadas (`aplicar_politica_solo_lectura`, `exportar_inventario_acciones_mutantes`). `state_helpers` queda sólo como orquestador de estado y delega la política read-only al nuevo módulo.  
  Resultado: una sola fuente de verdad UI para controles mutantes/tooltip/disable, menor acoplamiento estructural en `state_helpers` y guardarraíles que impiden reintroducir checks manuales o redefinir el inventario fuera del módulo dedicado.


- **2026-03-18 — EstadoModoSoloLectura compartido como única fuente read-only entre aplicación y UI — Vigente**  
  Persistía una duplicidad conceptual: backend modelaba el read-only con `PoliticaModoSoloLectura`, mientras la UI recibía `Callable[[], bool]` cruda mediante `proveedor_ui_solo_lectura`. Aunque funcional, el contrato público divergía entre capas y dejaba abierta la puerta a wiring débil y a deriva futura.  
  Se introduce `EstadoModoSoloLectura` en `app/application/modo_solo_lectura.py` como abstracción mínima compartida. El bootstrap compone una sola instancia desde `settings`, la política de aplicación consulta `estado.esta_activo()` y `MainWindow`/`politica_solo_lectura` consumen el mismo objeto explícito. Se elimina el `Callable[[], bool]` como API pública principal de read-only y se añaden guardarraíles para impedir su reintroducción en backend/UI.  
  Resultado: una sola fuente de verdad tipada, sin globals nuevos, sin acoplamiento a Qt y manteniendo intacta la semántica preventiva ya validada.
