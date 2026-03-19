# Validación Windows real

## Objetivo

Este documento define el **paquete operativo mínimo** para ejecutar la validación final en una máquina Windows real sin abrir una ronda nueva de refactor.

Estado editorial vigente del repositorio:

- **La validación Windows real sigue pendiente** hasta que una ejecución real deje evidencia auditable.
- Mientras esa evidencia no exista, el estado honesto del producto es **PRODUCTO CANDIDATO A CIERRE**.
- Si la ejecución Windows real detecta fallos reales, el estado pasa a **PRODUCTO NO CERRADO**.
- Solo con todos los pasos en PASS y evidencia completa puede declararse **PRODUCTO CERRADO**.

## Alcance

Esta validación cubre exclusivamente el cierre operativo final en Windows real:

1. preparación del entorno,
2. arranque real de la aplicación,
3. ejecución de tests/gate,
4. auditoría E2E,
5. recopilación de evidencias,
6. dictamen final PASS/FAIL/WARNING.

No redefine arquitectura, no cambia readonly y no introduce nuevas features.

## Precondiciones obligatorias

Ejecutar en una máquina Windows real con:

- acceso al repositorio clonado,
- permisos para crear `.venv` y escribir en `logs/`,
- Python compatible disponible,
- conexión de red si los instaladores de dependencias la necesitan,
- árbol limpio o snapshot identificable del commit validado.

Registrar antes de empezar:

- fecha y hora,
- equipo/host Windows,
- usuario que ejecuta,
- commit exacto validado (`git rev-parse HEAD`),
- versión de Python (`py -3 --version` o `python --version`).

## Preparación de carpeta de evidencias

### Opción recomendada

Ejecutar primero:

```bat
scripts\validar_windows_real.bat
```

Ese script crea una carpeta de corrida bajo `logs\windows_real\<run_id>` y deja una plantilla de evidencia para rellenar durante la ejecución manual.

### Estructura esperada de evidencia

- `logs\windows_real\<run_id>\resumen_validacion_windows_real.txt`
- `logs\windows_real\<run_id>\entorno.txt`
- `logs\windows_real\<run_id>\pasos_ejecutados.txt`
- logs generados por los scripts estándar del repo dentro de `logs\`
- evidencias E2E generadas por `auditar_e2e.bat --dry-run` y `auditar_e2e.bat --write`
- notas manuales y, si aplica, capturas manuales fuera del repo o referenciadas desde el resumen

## Orden exacto de ejecución

Ejecutar **en este orden** y registrar resultado por paso.

### Paso 0 — Identificación de ejecución

Comandos:

```bat
git rev-parse HEAD
py -3 --version
```

Si `py` no está disponible:

```bat
python --version
```

**PASS:** se registran commit y versión de Python.

**FAIL:** no se puede identificar con precisión qué build se está validando.

### Paso 1 — Preparar carpeta de evidencia

Comando:

```bat
scripts\validar_windows_real.bat
```

**PASS:** existe una nueva carpeta `logs\windows_real\<run_id>` con plantilla de resumen.

**FAIL:** no se crea la carpeta o falla la inicialización de evidencia.

### Paso 2 — Preparación del entorno

Comando:

```bat
setup.bat
```

**Revisar:**

- creación/actualización de `.venv`,
- instalación de dependencias,
- ausencia de errores de activación,
- generación de logs en `logs\`.

**Evidencia mínima:** stdout/stderr del script y logs creados.

**PASS:** `setup.bat` termina con exit code 0.

**FAIL:** errores de `venv`, `pip`, activación o dependencias.

### Paso 3 — Arranque real de la app

Comando:

```bat
lanzar_app.bat
```

**Revisión visual obligatoria:**

- la app abre en Windows real,
- no se congela al arrancar,
- no aparece traceback crudo al usuario,
- se generan logs operativos,
- el cierre de la ventana no deja incidente no controlado.

**Evidencia mínima:**

- nota manual del resultado,
- referencia a `logs\lanzar_app_stdout.log`, `logs\lanzar_app_stderr.log`, `logs\lanzar_app_debug.log`,
- captura manual si hubo comportamiento dudoso.

**PASS:** la UI arranca y puede cerrarse sin error real.

**FAIL:** no arranca, se congela, muestra error real o no deja trazabilidad suficiente.

### Paso 4 — Suite contractual con cobertura

Comando:

```bat
ejecutar_tests.bat
```

**Revisar:**

- exit code final,
- cobertura >= 85%,
- generación de `logs\pytest_output.txt`, `logs\coverage_report.txt`, `logs\coverage_summary.txt`.

**PASS:** exit code 0 y cobertura contractual cumplida.

**FAIL:** tests rojos, cobertura insuficiente o logs ausentes.

### Paso 5 — Gate operativo

Comando:

```bat
quality_gate.bat
```

**Revisar:**

- ejecución completa del gate,
- logs emitidos por el gate,
- ausencia de errores ocultos.

**PASS:** exit code 0.

**FAIL:** cualquier error del gate o pasos omitidos.

### Paso 6 — Auditoría E2E sin escritura

Comando:

```bat
auditar_e2e.bat --dry-run
```

**Revisar:**

- salida reproducible,
- generación de evidencia de auditoría,
- estado global coherente.

**PASS:** exit code 0 y reporte dry-run disponible.

**FAIL:** no genera evidencia o informa fallo real.

### Paso 7 — Auditoría E2E con escritura

Comando:

```bat
auditar_e2e.bat --write
```

**Revisar:**

- salida reproducible,
- artefactos de auditoría generados,
- logs coherentes con el modo write.

**PASS:** exit code 0 y artefactos write presentes.

**FAIL:** no genera artefactos, deja errores reales o rompe trazabilidad.

### Paso 8 — Launcher manual integral

Comando:

```bat
launcher.bat
```

**Revisión visual obligatoria:**

- el menú abre correctamente,
- permite invocar las opciones publicadas,
- muestra PASS/FAIL por operación,
- refleja ruta de logs,
- no depende de rutas absolutas rotas.

**PASS:** abre y permite operar de forma consistente.

**FAIL:** no abre, las opciones no funcionan o la trazabilidad es engañosa.

## Qué revisar visualmente

Checklist visual mínimo:

- la UI abre en Windows real,
- no hay congelación visible,
- no aparecen mensajes contradictorios de “todo completado” cuando Windows real sigue pendiente,
- launcher y scripts muestran rutas de logs claras,
- los exit codes reportados coinciden con el resultado observado,
- los logs se escriben en la carpeta esperada,
- si aparece error, existe stacktrace/log técnico y nota funcional asociada.

## Evidencia auditable mínima

Se considera evidencia suficiente si quedan preservados **todos** estos elementos:

1. `stdout/stderr` de los scripts ejecutados o su referencia directa en `logs\`.
2. `logs\seguimiento.log` y, si existiera incidente, `logs\crashes.log` o `logs\crash.log`.
3. logs específicos de:
   - `lanzar_app.bat`,
   - `ejecutar_tests.bat`,
   - `quality_gate.bat`.
4. reportes de auditoría E2E de `--dry-run` y `--write`.
5. `logs\windows_real\<run_id>\resumen_validacion_windows_real.txt` con resultado paso a paso.
6. nota manual de revisión visual de arranque real y launcher.
7. captura manual solo si ayuda a explicar un PASS dudoso o un FAIL; no sustituye logs.

## Plantilla de resultado por paso

Registrar cada paso como:

- `PASS` = ejecutado en Windows real y sin fallo.
- `FAIL` = ejecutado en Windows real y con fallo real.
- `WARNING` = no ejecutado completo o evidencia incompleta.

Formato recomendado:

```text
PASO 3 | lanzar_app.bat | PASS | Abre UI, cierra sin error, logs generados.
PASO 4 | ejecutar_tests.bat | PASS | Cobertura 85%+ y exit code 0.
PASO 8 | launcher.bat | WARNING | Se abrió, pero no se recorrieron todas las opciones.
```

## Criterio final de dictamen

### PRODUCTO CERRADO

Solo si:

- todos los pasos obligatorios quedan en `PASS`,
- la evidencia está completa y es rastreable,
- no aparecen fallos reales en UI, tests, gate ni auditoría E2E,
- la documentación final puede actualizarse honestamente a “Windows real validado”.

### PRODUCTO CANDIDATO A CIERRE

Se mantiene si:

- la validación Windows real sigue pendiente,
- o algún paso quedó en `WARNING`,
- o la evidencia existe pero todavía no es suficiente para auditoría completa.

### PRODUCTO NO CERRADO

Corresponde si:

- cualquier paso obligatorio termina en `FAIL`,
- Windows real revela un bug real,
- hay contradicción entre resultado observado y documentación,
- o la trazabilidad/evidencia impide sostener el cierre.

## Regla documental de consistencia

Hasta que esta guía se ejecute en Windows real con evidencia suficiente:

- `docs/definicion_producto_final.md` debe seguir declarando **PRODUCTO CANDIDATO A CIERRE**,
- los checklists no deben presentar Windows real como completado,
- cualquier resumen final debe indicar explícitamente que la validación Windows real está **pendiente**.
