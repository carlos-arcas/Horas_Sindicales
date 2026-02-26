# Reglas de negocio del sistema

## 1) Qué es una petición
- Una **petición** es una solicitud de horas sindicales asociada a una persona delegada para una fecha concreta de disfrute.
- Cada petición registra:
  - la fecha en que se solicita,
  - la fecha para la que se pide,
  - si es de jornada **completa** o **parcial**,
  - el número final de minutos/hours solicitados,
  - información de apoyo (notas/observaciones),
  - y su estado operativo (pendiente o histórica).
- Una petición se considera inicialmente **pendiente** al crearse.

## 2) Qué significa “completo”
- “**Completo**” significa que la petición cubre la jornada sindical completa de ese día.
- En una petición completa, el sistema toma como referencia el cuadrante diario de la persona para calcular los minutos.
- Si ese valor de cuadrante no existe o es 0, la petición completa solo es válida si se informa manualmente una cantidad de horas/minutos mayor que cero.
- Una petición parcial requiere rango horario (desde/hasta) válido; una completa no depende de ese rango para el cálculo funcional.

## 3) Cómo se calculan las horas
- Regla general:
  - Si se informan horas manuales mayores que 0, ese valor prevalece como minutos solicitados.
  - Si no se informan horas manuales, se calculan automáticamente.
- Petición parcial:
  - minutos = hora_hasta - hora_desde,
  - con la condición de que “hasta” sea mayor que “desde”.
- Petición completa:
  - minutos = total de cuadrante del día (mañana + tarde),
  - salvo que se haya introducido manualmente un valor mayor que 0.
- En todos los casos, el resultado debe ser estrictamente mayor que 0.

## 4) Cuándo se contabilizan horas (histórico vs pendientes)
- Las peticiones pendientes **no consumen** bolsa mensual ni anual.
- Las horas se contabilizan en saldos únicamente cuando la petición pasa a histórico (estado generado/documentado).
- Por tanto:
  - crear una petición pendiente no incrementa consumos,
  - eliminar una petición pendiente no altera consumos,
  - una petición generada sí incrementa consumos del período y del año.

## 5) Cómo se detectan duplicados

### 5.1 Duplicados en operación local de peticiones
- La deduplicación local se evalúa por **persona_id + fecha pedida** y solape horario.
- Regla de solapamiento: se usan intervalos **semiabiertos** `[inicio, fin)`.
  - Ejemplo: `17:00-18:00` y `18:00-19:00` **no** solapan.
- Una solicitud con `completo = true` siempre se normaliza como `[00:00, 24:00)` y, por tanto, colisiona con cualquier tramo parcial del mismo día.
- `00:00-00:00` no se interpreta como completo si `completo = false`; se considera rango inválido (duración 0).
- La comprobación ignora registros eliminados.

### 5.2 Duplicados en sincronización con Google Sheets
- Se usa una clave funcional de deduplicación por solicitud.
- Componentes base de la clave:
  - identidad de delegada (uuid; si no, id),
  - fecha pedida,
  - tipo completo/parcial,
  - minutos totales.
- Si es parcial, además incluye desde/hasta normalizados a minutos.
- Si es completa, **no** usa desde/hasta para deduplicar.
- Implicaciones:
  - dos registros con mismas franjas pero distinto total de minutos no son duplicados,
  - formatos horarios distintos (por ejemplo “09:00” y “9 + 0”) se consideran equivalentes tras normalización,
  - en completo, distintas horas de inicio/fin no rompen la igualdad si el resto coincide.

## 6) Qué son cuadrantes base
- Los **cuadrantes base** son la plantilla de jornada de referencia que el sistema asigna por defecto para los días laborables.
- Valor base por defecto:
  - lunes a viernes,
  - turno de mañana de 09:00 a 15:00 (6 horas = 360 minutos),
  - tarde en 0 minutos.
- Se aseguran automáticamente al crear una persona:
  - si un día laborable está a cero, se rellena con la base,
  - se crean los registros de cuadrante que falten,
  - no se duplican cuadrantes ya existentes.

## 7) Qué ocurre al eliminar una petición
- La eliminación es lógica (se marca como eliminada), no una destrucción física inmediata.
- Una petición eliminada deja de computar para listados operativos, control de duplicados locales y consumos.
- Si era pendiente, su eliminación no modifica saldos consumidos (porque aún no contabilizaba).

## 8) Cómo se calcula el total en PDF
- En el PDF se muestran las peticiones con su columna de horas en formato HH:MM.
- El total del PDF se calcula sumando los minutos de todas las filas impresas y convirtiendo el resultado final a HH:MM.
- El documento siempre añade una fila final “TOTAL”.
- Para filas completas, el horario mostrado es “COMPLETO”; para parciales se muestra “desde - hasta”.

## 9) Reglas de sincronización con Google Sheets

### 9.1 Modelo de sincronización
- La sincronización contempla dos sentidos:
  - **pull** (de Sheets a local),
  - **push** (de local a Sheets),
  - y un modo combinado (pull + push).
- Solo se consideran para envío los cambios locales posteriores al último instante de sincronización.

### 9.2 Detección de conflictos
- Hay conflicto si un mismo registro fue modificado local y remotamente después del último sync.
- En conflicto:
  - no se sobreescribe automáticamente,
  - se registra como conflicto para resolución posterior.

### 9.3 Regla “más reciente gana” cuando no hay conflicto
- Si no hay conflicto y la versión remota es más reciente, en pull se actualiza local.
- Si no hay conflicto y hay cambios locales nuevos, en push se actualiza remoto.

### 9.4 Deduplicación durante sync de solicitudes
- En pull: si llega una solicitud nueva remota pero funcionalmente duplicada de una local existente, se omite.
- En push: si hay solicitud local nueva pero ya existe un duplicado funcional en remoto, se omite.
- Estas omisiones cuentan como “duplicados omitidos” en el resumen de sincronización.

### 9.5 Borrados y trazabilidad
- El estado de borrado se sincroniza como dato para mantener consistencia entre entornos.
- Se conserva trazabilidad temporal y de origen mediante marca de actualización y dispositivo origen.

### 9.6 Cuadrantes y configuración
- Antes de sincronizar, el sistema alinea cuadrantes locales a partir de la configuración de personas para evitar divergencias.
- Además de personas/solicitudes/cuadrantes, también se sincronizan:
  - log de PDFs,
  - y parámetros de configuración compartidos.
