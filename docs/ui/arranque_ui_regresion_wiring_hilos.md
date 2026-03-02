# Arranque UI: regresión por wiring/mixins/hilos (mar-2026)

## Causa raíz
- El `MainWindow` modular dependía de `registrar_state_bindings(MainWindow)` para inyectar métodos de contrato (ej. `_configure_historico_focus_order`).
- Un fallo de import en el bloque `try` compartido de `state_controller.py` anulaba **todas** las importaciones de mixins/bindings y dejaba handlers sin registrar durante `_build_ui`.
- En paralelo, ciertas rutas de finalización de arranque ejecutaban callbacks sin forzar cola al hilo UI, provocando warnings tipo *Cannot create children for a parent that is in a different thread*.

## Correcciones aplicadas
- Importes de estado separados por bloque (`state_helpers`, `state_actions`, `state_validations`, `state_bindings`) con logging operacional por módulo fallido.
- Handler explícito `_configure_historico_focus_order` en `MainWindow` para no depender exclusivamente del binding dinámico.
- `on_finished`/fail-safe de arranque encapsulados con encolado explícito al hilo UI (`_enqueue_on_ui_thread`).
- Hardening del fallo de arranque para evitar excepciones secundarias al cerrar splash/thread si el `QObject` ya fue destruido.
- `write_crash_log` ahora tiene fallback robusto a `stderr` si no puede persistir archivo.

## Guardrails para evitar regresión
- Mantener test de contrato `tests/test_main_window_wiring_contract.py`.
- Mantener smoke `scripts/ui_main_window_smoke.py` con lista de handlers mínimos de wiring.
- Evitar bloques `try` monolíticos para importes opcionales de mixins/bindings en fachada UI.
