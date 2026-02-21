# Quality Gate y resumen de cobertura

El proceso de calidad genera ahora un artefacto adicional para priorizar deuda de tests:

- `logs\coverage_summary.txt`
- `logs\runs\<run_id>\coverage_summary.txt` (cuando se ejecuta desde `menu_validacion.bat` con `RUN_DIR`)

También puede generar `coverage.json` en la misma carpeta del run.

## Qué contiene `coverage_summary.txt`

El archivo está dividido en secciones:

1. **Cobertura global**
   - Muestra el porcentaje total reportado por `coverage.py`.
2. **Top ficheros con peor cobertura**
   - Lista ordenada de peor a mejor, con líneas cubiertas y faltantes.
3. **Ficheros bajo umbral**
   - Enumeración directa de módulos bajo el umbral configurado (por defecto 85%).

## Cómo interpretarlo rápido

- Si la cobertura global está por debajo de 85%, empezar por la sección **Top ficheros con peor cobertura**.
- Si el quality gate falla por umbral, revisar primero la sección **Ficheros bajo umbral** para elegir qué módulos cubrir.
- En ejecuciones por run (`logs\runs\<run_id>`), el resumen queda asociado al mismo lote de logs del pipeline local.

## Comando manual

```bat
python scripts/coverage_summary.py --package app --threshold 85 --out-txt "logs\coverage_summary.txt" --out-json "logs\coverage.json"
```

Este comando reutiliza `.coverage` si existe y exporta un resumen de texto legible para acción inmediata.

## Paso `PRECHECK_UI` (smoke de MainWindow)

`quality_gate.bat` ejecuta `python scripts/ui_main_window_smoke.py` antes de auditoría y pytest.

- Inicializa Qt en modo `offscreen` para CI local (sin ventanas visibles).
- Intenta construir `MainWindow` con un contenedor en memoria para validar wiring real de UI.
- Si aparece un error operativo de wiring (`NameError`, `AttributeError`, `ImportError` o `TypeError` típico de signal/slot), el gate falla con salida corta:
  - `SMOKE_UI_FAIL: <tipo> <mensaje> archivo:linea`
- Además del resumen corto en consola, el detalle se registra en `error_operativo.log`.
- Warnings benignos de Qt (por ejemplo, mensajes comunes de plataforma) se consideran `SMOKE_UI_WARN` y no bloquean el gate.
