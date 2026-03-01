# Arquitectura UI modular de `MainWindow`

Este documento describe el patrón de extracción modular aplicado a `MainWindow`, concentrado en `app/ui/vistas/main_window/`.

## Objetivo del patrón

Reducir el tamaño y acoplamiento de `MainWindow` delegando responsabilidades en módulos especializados, manteniendo en la clase principal solo:

- estado compartido de la ventana,
- composición de UI (fases de build/wiring),
- y métodos wrapper muy pequeños que delegan lógica.

La implementación vive en `state_controller.py` y se apoya en módulos de acciones/flujo. 【F:app/ui/vistas/main_window/state_controller.py†L130-L135】

## Responsabilidades por módulo

### `state_controller.py`

- Define `MainWindow` (orquestador de estado + punto de integración). 【F:app/ui/vistas/main_window/state_controller.py†L185-L193】
- Importa y conecta los módulos extraídos de acciones/layout/wiring. 【F:app/ui/vistas/main_window/state_controller.py†L130-L135】
- Conserva wrappers para delegar casos de uso UI sin volver a concentrar lógica de negocio/flujo en una sola clase. 【F:app/ui/vistas/main_window/state_controller.py†L506-L531】

### `layout_builder.py`

- Construcción de widgets y estructura visual por fases (`create_widgets`, `build_shell`, `build_layout_phase`, `apply_initial_state_phase`, etc.).
- Encapsula la composición de layout que antes tendía a crecer en `MainWindow`.

Referencia de delegación desde `MainWindow`: `self._create_widgets()`, `self._build_shell_layout()`, `self._build_layout()`, `self._build_status_bar()`. 【F:app/ui/vistas/main_window/state_controller.py†L423-L443】

### `wiring.py`

- Conexión de señales y secuencia de inicialización UI (`build_ui`, `wire_signals_phase`).

Referencia de delegación desde `MainWindow`: `_build_ui()` y `_wire_signals()`. 【F:app/ui/vistas/main_window/state_controller.py†L420-L427】

### `form_handlers.py`

- Limpieza/reset del formulario y operaciones de soporte de inputs.

Referencia de delegación desde `MainWindow`: `_limpiar_formulario()` y `_clear_form()`. 【F:app/ui/vistas/main_window/state_controller.py†L506-L525】

### `acciones_personas.py`

- Flujo de selección/alta/edición/borrado de persona.
- Manejo de borradores y restauración de contexto de delegada.

Contrato de extracción validado por tests AST (entrypoints esperados + wrappers). 【F:tests/test_main_window_personas_extracted_structure.py†L9-L34】【F:tests/test_main_window_personas_extracted_structure.py†L53-L72】

### `acciones_pendientes.py`

- Lógica de filas pendientes: selección, foco, limpieza, totales y estado UI.

Contrato de extracción validado por tests AST (nombres `on_*` / `helper_*` + wrappers). 【F:tests/test_main_window_pendientes_extracted_structure.py†L9-L33】【F:tests/test_main_window_pendientes_extracted_structure.py†L52-L71】

### `acciones_sincronizacion.py` y `acciones_sincronizacion_resultados.py`

- Flujo de sincronización, callbacks de finalización/error y aplicación de reportes.
- Separación de presentación de resultados para reducir complejidad en el controlador.

Guardrail de wrappers para métodos de sincronización en `MainWindow`. 【F:tests/test_main_window_sync_extracted_structure.py†L20-L31】

### `dialogos_sincronizacion.py`

- Construcción/visualización de diálogos específicos de sincronización.

### `data_refresh.py`

- Refresh de datos y helpers de recarga (incluyendo histórico).

### `validacion_preventiva.py`

- Validación preventiva desacoplada (errores base, reglas de negocio preventivas, warnings, render de feedback).

Contrato de wrappers + entrypoints validado por tests AST. 【F:tests/test_main_window_validacion_preventiva_structure.py†L22-L44】【F:tests/test_main_window_validacion_preventiva_structure.py†L47-L70】

## Regla de wrappers en `MainWindow`

Para métodos extraídos, `MainWindow` debe conservar wrappers delgados:

- wrappers de **1-3 líneas** en áreas como personas, pendientes e histórico,
- wrappers de tamaño acotado también para sincronización y validación preventiva,
- delegación explícita al módulo especializado (sin reintroducir lógica extensa).

Ejemplos de wrappers reales en `state_controller.py`:

- `_load_personas -> acciones_personas.load_personas(...)` 【F:app/ui/vistas/main_window/state_controller.py†L580-L581】
- `_run_preventive_validation -> validacion_preventiva._run_preventive_validation(...)` 【F:app/ui/vistas/main_window/state_controller.py†L694-L695】
- `_on_sync_with_confirmation -> acciones_sincronizacion.on_sync_with_confirmation(...)` 【F:app/ui/vistas/main_window/state_controller.py†L530-L531】

La verificación de esta regla se realiza por AST en tests estructurales (tamaño de método y forma de delegación). 【F:tests/test_main_window_personas_extracted_structure.py†L44-L61】【F:tests/test_main_window_sync_extracted_structure.py†L13-L31】

## Guardrails LOC/AST

El patrón modular está reforzado por guardrails automatizados:

1. **Límite LOC en `state_controller.py`**
   - Máximo de líneas no vacías permitido: `1117`.
   - Si se supera, el mensaje del test exige extraer responsabilidades antes de agregar más LOC. 【F:tests/test_main_window_state_controller_loc_guard.py†L6-L20】

2. **`__init__.py` del paquete `main_window` debe ser delgado**
   - Máximo 50 LOC.
   - No debe contener `class MainWindow` y debe mantenerse como fachada de import/export. 【F:tests/test_main_window_init_is_thin.py†L6-L14】

3. **Guardrails AST de estructura modular**
   - Validan que métodos en `MainWindow` sean wrappers y que existan entrypoints en módulos extraídos (`acciones_personas`, `acciones_pendientes`, `acciones_sincronizacion`, `validacion_preventiva`, etc.). 【F:tests/test_main_window_personas_extracted_structure.py†L53-L72】【F:tests/test_main_window_pendientes_extracted_structure.py†L52-L71】【F:tests/test_main_window_sync_extracted_structure.py†L20-L38】【F:tests/test_main_window_validacion_preventiva_structure.py†L22-L70】

## Convención operativa para nuevas extracciones

Al agregar o modificar comportamiento en `MainWindow`:

1. Preferir implementar la lógica en un módulo de `app/ui/vistas/main_window/`.
2. Mantener en `MainWindow` únicamente un wrapper breve.
3. Si aparece crecimiento sostenido de un área funcional, crear/expandir módulo dedicado.
4. Ajustar o extender los tests AST/LOC para fijar el nuevo contrato estructural.

Así se preserva una UI mantenible, testeable y con responsabilidades explícitas por módulo.
