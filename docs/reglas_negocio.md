# Reglas de negocio

> Esta guía describe reglas funcionales. Para detalles de implementación de sincronización, ver [docs/sincronizacion_google_sheets.md](./sincronizacion_google_sheets.md). Para contexto arquitectónico, ver [arquitectura.md](../arquitectura.md).

## 1) Solicitud de horas
Una **solicitud** registra horas sindicales para una persona delegada en una fecha de disfrute.

Campos funcionales relevantes:
- `fecha`: día de disfrute.
- `completo`: jornada completa (`true`) o tramo parcial (`false`).
- `minutos_total`: minutos finales solicitados.
- rango horario (`desde`/`hasta`) cuando aplica.
- `estado`: pendiente o histórica.

Al crearse, una solicitud nace en estado **pendiente**.

## 2) Solicitud completa vs parcial
- **Completa**: representa toda la jornada sindical del día.
  - Toma como base el cuadrante diario (mañana + tarde).
  - Si el cuadrante es `0`, solo es válida si se informa un valor manual `> 0`.
- **Parcial**: requiere rango `desde < hasta`.

Ejemplos:
- Completa con cuadrante 6h (`360 min`) ⇒ `minutos_total = 360`.
- Parcial de 09:00 a 11:30 ⇒ `150 min`.

## 3) Cálculo de minutos
Regla de prioridad:
1. Si se informa un valor manual `> 0`, prevalece.
2. Si no, se calcula automáticamente.

Cálculo automático:
- Parcial: `hasta - desde`.
- Completa: total de cuadrante del día.

Resultado final: siempre `minutos_total > 0`.

## 4) Cuándo computan en saldos
- Las solicitudes **pendientes** no consumen bolsa mensual ni anual.
- Solo consumen cuando pasan a estado **histórica**.

Consecuencia:
- Crear/eliminar pendientes no altera saldos.
- Una histórica sí altera saldos del periodo.

## 5) Duplicados

### 5.1 En operación local
Hay duplicado si existe otra solicitud activa con la misma combinación:
- persona,
- fecha,
- tipo (`completo`/`parcial`),
- `desde` y `hasta` (o ausencia en completas).

No se consideran duplicados sobre registros eliminados.

### 5.2 En sincronización con Google Sheets
Se usa una clave funcional:
- identidad delegada (`delegada_uuid`, o `persona_id` como fallback),
- fecha,
- tipo,
- `minutos_total`,
- `desde`/`hasta` normalizados (solo en parciales).

Ejemplos:
- `09:00` y `9:0` se consideran iguales tras normalización.
- En completas, diferencias de `desde/hasta` no cambian la igualdad.

## 6) Cuadrantes base
Los cuadrantes base son la plantilla por defecto en días laborables:
- lunes a viernes,
- mañana 09:00–15:00 (`360 min`),
- tarde `0 min`.

Al crear una persona, el sistema asegura cuadrantes faltantes sin duplicar existentes.

## 7) Eliminación de solicitudes
La eliminación es lógica (`deleted = true`).

Efectos:
- deja de aparecer en listados operativos,
- no participa en control de duplicados locales,
- deja de computar en saldos.

## 8) Total en PDF
- Cada fila muestra horas en `HH:MM`.
- El PDF incluye una fila final `TOTAL`.
- `TOTAL` = suma de `minutos_total` de las filas incluidas, convertido a `HH:MM`.
- En filas completas se imprime `COMPLETO`; en parciales, `desde - hasta`.

## 9) Reglas de sincronización (resumen)
- Modos: `pull`, `push`, `sync` (`pull` + `push`).
- Conflicto: el registro cambió local y remoto después del último sync.
- Sin conflicto: prevalece la versión más reciente.
- Se sincroniza borrado lógico, trazabilidad temporal y dispositivo de origen.

Para flujo técnico, errores y resolución de conflictos, ver [docs/sincronizacion_google_sheets.md](./sincronizacion_google_sheets.md).
