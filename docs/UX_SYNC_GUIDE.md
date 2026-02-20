# UX Sync Guide

## Cuándo sincronizar

- Al iniciar jornada: para traer cambios remotos antes de operar.
- Después de confirmar un lote relevante de solicitudes.
- Antes de cerrar jornada si hubo conflictos o errores pendientes.

## Simulación de sincronización (dry-run)

La opción **Simular sincronización** genera un plan previo de cambios sin escribir en Google Sheets.

- Evalúa normalización y comparación completa antes de ejecutar.
- Muestra resumen previsible:
  - Se crearán: X
  - Se actualizarán: Y
  - Sin cambios: Z
  - Conflictos detectados: N
- En detalle de diff se muestran campos cambiados con formato:
  - `campo | valor actual | nuevo valor`
- Los nuevos elementos se etiquetan como **Nuevo registro**.
- Los conflictos muestran su causa para revisión operativa.

### Garantía de no escritura

Durante la simulación **no se ejecuta ninguna escritura en Google Sheets**. Solo se calcula un plan inmutable (SyncPlanner) para validación humana.

## Confirmación explícita

Tras simular:

- Si hay cambios, se habilita **Confirmar y ejecutar sincronización**.
- Si no hay cambios, se muestra **No hay cambios que aplicar** y el botón confirmar queda deshabilitado.

Esto refuerza idempotencia y evita dobles sincronizaciones innecesarias.

## Estados del panel

- **Idle**: sin operación en curso.
- **Sincronizando…**: operación en ejecución (progreso indeterminado).
- **OK**: sincronización finalizada sin conflictos ni errores.
- **OK con avisos**: finalizó, pero hubo omitidas/conflictos menores que requieren revisión.
- **Error**: la sincronización falló y requiere acción.
- **Configuración incompleta**: falta `Spreadsheet ID` o credenciales JSON.

## Qué hacer ante conflictos o errores

1. Abrir **Ver detalles** y revisar entradas `WARN`/`ERROR`.
2. Usar acciones:
   - **Abrir registro afectado** para inspección operativa.
   - **Marcar para revisión** cuando no se pueda resolver de inmediato.
   - **Reintentar solo fallidos** tras corregir causa.
3. Si no se puede resolver desde UI:
   - **Copiar informe** y compartir con soporte.
   - **Abrir carpeta de logs** para adjuntar `sync_last.json` / `sync_last.md`.

## Trazabilidad

Cada sync guarda:

- `logs/sync_last.json`
- `logs/sync_last.md`
- Historial rotativo en `logs/sync_history/`

Esto permite auditoría y evita dudas sobre qué se sincronizó y qué quedó pendiente.
