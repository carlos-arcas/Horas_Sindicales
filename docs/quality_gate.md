# Quality Gate

`quality_gate.bat` ejecuta validaciones previas y pruebas para bloquear regresiones antes de liberar.

## Paso PRECHECK_UI

`PRECHECK_UI` ejecuta `scripts/ui_main_window_smoke.py` con un smoke de wiring de `MainWindow`.

- Inicializa `QApplication` en modo `offscreen` para no abrir ventanas visibles en CI/local headless.
- Intenta importar `app.ui.vistas.main_window_vista` y valida handlers críticos de `MainWindow`.
- Si detecta errores de wiring (`NameError`, `AttributeError`, `ImportError`, `TypeError`), registra `error_operativo` y termina con `exit code 1`.
- En fallo, emite un resumen corto en stdout:
  - `SMOKE_UI_FAIL: <tipo> <mensaje> <archivo>:<linea>`
- Warnings benignos de Qt no bloquean el gate por sí solos mientras no se conviertan en excepción.

Si `PRECHECK_UI` falla, `quality_gate.bat` corta el proceso con `FAIL_STEP=PRECHECK_UI`.
