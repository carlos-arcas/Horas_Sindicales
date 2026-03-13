# Diagnóstico de arranque (cierre silencioso)

Usa `scripts/run_ui_debug.bat` para ejecutar la UI con observabilidad de arranque y detectar cierres mudos sin depender del crash log de Python.

## Qué hace el script

1. Activa `PYTHONFAULTHANDLER=1`.
2. Activa `QT_LOGGING_RULES=qt.*=true`.
3. Ejecuta:
   - `python -X faulthandler -m app.entrypoints.ui_main`
4. Redirige salidas a:
   - `logs/stdout.log`
   - `logs/stderr.log`
5. Guarda el código de salida del proceso en:
   - `logs/exit_code.txt`
6. Verifica guardrails post-run:
   - Si falta `logs/boot_trace.log`, finaliza con `exit 1`.
   - Si `stderr.log` contiene `Cannot create children`, finaliza con `exit 2`.
   - En cualquier otro caso, devuelve el exit code original de la app.

## Uso

Desde la raíz del repositorio en Windows:

```bat
scripts\run_ui_debug.bat
```

## Evidencias esperadas tras el cierre

Después de cada ejecución deben existir:

- `logs/stdout.log`
- `logs/stderr.log`
- `logs/exit_code.txt`
- `logs/boot_trace.log`

Si no aparece `boot_trace.log`, el script devuelve `1` para marcar falla de instrumentación de arranque.
Si se detecta `Cannot create children`, el script devuelve `2` para identificar el patrón de thread safety de Qt.

## Contrato de arranque maximizado (headless-safe)

El contrato de primera visualización se valida con tests deterministas en `tests/entrypoints/test_ui_main_visibilidad_arranque.py`.

Política vigente:

- Si `iniciar_maximizada=True`, la activación usa `showMaximized()` y evita `show()` en el primer pintado útil.
- Si `iniciar_maximizada=False`, se usa `show()` salvo que la ventana ya reporte estado maximizado restaurado.
- El flujo de wizard (`onboarding` pendiente) siempre retorna `iniciar_maximizada=False` para no contaminar el contrato de la ventana principal.
- `raise_()` y `activateWindow()` solo elevan foco; no degradan el modo elegido de visibilidad inicial.
