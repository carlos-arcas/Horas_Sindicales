# Auditoría UX Senior — Reserva de Horas Sindicales (v1)

## 1. Resumen Ejecutivo

**Nivel UX global:** 5,2 / 10  
**Nivel de madurez:** Intermedio  
**Riesgo operativo:** Medio–Alto

**Justificación de la nota (5,2):**
- El producto ya incorpora mejoras reales en flujo principal, histórico y trazabilidad de sincronización, reduciendo fricción crítica frente al estado inicial.
- Aun así, persisten brechas de prevención, consistencia y recuperación guiada que impiden considerarlo robusto para uso intensivo sin apoyo informal.

### Impacto en usuario real
La aplicación es utilizable y hoy más trazable, pero todavía no suficientemente autoexplicativa para delegadas no técnicas en contexto real de trabajo. La carga operativa ya no depende solo de prueba-error, aunque sigue exigiendo interpretación en momentos críticos.

### Conclusión clara y directa
El producto mejoró de forma verificable, pero **aún no** alcanza estándar de herramienta profesional robusta para uso intensivo sin acompañamiento. Prioridad inmediata: cerrar gaps de claridad de flujo, prevención de errores y recuperación asistida.

---

## 1.1 Evidencias en el producto (estado actual)

- Flujo operativo visible en 3 pasos con foco del paso activo (rellenar, añadir, confirmar).
- CTA primario único por estado (`Añadir a pendientes` / `Confirmar seleccionadas`) con guía contextual cuando está deshabilitado.
- Feedback transaccional unificado con toast de alta, opción `Deshacer` y resumen posterior a confirmación.
- Prevención de duplicados antes de añadir (delegada + fecha + tramo), con navegación a pendiente existente.
- Mejoras de teclado y foco en Operativa (Enter en último campo y Escape en resumen/modal).
- Histórico con `HistoricalViewModel`, filtros avanzados (texto, fechas, estado, delegada), orden útil por defecto y acciones contextuales por selección.
- Histórico con diálogo de detalle, atajos de teclado (`Ctrl+F`, `Enter`, `Escape`) y búsqueda con debounce.
- Sync Panel Pro persistente con estados explícitos (`Idle`, `Sincronizando…`, `OK`, `OK con avisos`, `Error`, `Configuración incompleta`).
- Trazabilidad de sincronización con resumen inequívoco del resultado (creadas, actualizadas, omitidas, conflictos, errores).
- Reportes y logs persistidos (`sync_last.json`, `sync_last.md`, historial rotativo), con acciones operativas directas y anti-reentrancia.

## 1.2 Gaps restantes (lo que falta para pasar a 8/10)

### P0
1. Completar validación preventiva end-to-end en todos los puntos de confirmación (no solo en casos principales).
2. Estandarizar mensajes de error con formato obligatorio: problema, causa probable, acción sugerida y CTA de resolución.
3. Incorporar resumen preconfirmación obligatorio en operaciones críticas para minimizar confirmaciones erróneas.
4. Unificar semántica de estados en toda la app (operativa, histórico y sincronización) para evitar interpretaciones mixtas.

### P1
5. Reducir carga cognitiva inicial separando más claramente modo operativo vs modo consulta.
6. Homogeneizar sistema visual (espaciados, jerarquía tipográfica y variantes de botones) en todas las pantallas.
7. Reforzar accesibilidad AA en controles y textos secundarios (contraste, targets y foco visible consistente).
8. Mejorar microcopy orientado a tarea en etiquetas y ayudas contextuales de alto impacto.

### P2
9. Instrumentar métricas UX operativas (tiempo por tarea, tasa de error, retrabajo, soporte solicitado).
10. Añadir asistencia contextual avanzada para interpretación de saldos y conflictos frecuentes.
11. Consolidar shortcuts y navegación por teclado documentada para flujos completos.
12. Elevar percepción de solidez visual con refinamiento de ritmos y densidad informativa en vistas extensas.

---

## 2. Evaluación por Dimensiones (con puntuación)

### A. Jerarquía visual — 4,8/10

**Justificación técnica**  
La pantalla principal muestra múltiples bloques con peso visual parecido y sin secuencia perceptiva dominante. El usuario no identifica de forma inmediata qué acción es principal.

**Problemas detectados**
- Competencia visual entre captura, listados y acciones.
- Uso de color con baja semántica funcional.
- Escasez de separación jerárquica entre información crítica y secundaria.

**Mejora concreta propuesta**
- Definir estructura visual por prioridad: acción principal, validación, contexto.
- Reducir densidad inicial con bloques plegables o pestañas por tarea.
- Reservar color acento exclusivamente para CTA principal y estados críticos.

### B. Claridad funcional — 5,0/10

**Justificación técnica**  
Se entiende el propósito general de la herramienta, pero no el camino óptimo para completar tareas sin entrenamiento informal.

**Problemas detectados**
- Campos y acciones no siempre comunican secuencia.
- Ambigüedad entre acciones de edición, confirmación y sincronización.
- Lenguaje de interfaz parcialmente técnico o poco orientado a tarea.

**Mejora concreta propuesta**
- Incorporar guía de pasos en la propia interfaz.
- Reescribir etiquetas y ayudas en lenguaje operativo.
- Hacer explícito qué acción cierra una operación y cuál solo prepara datos.

### C. Flujo de interacción — 4,6/10

**Justificación técnica**  
El flujo principal presenta fricción por validaciones tardías y cambios de estado poco visibles.

**Problemas detectados**
- Exceso de decisiones en una sola vista.
- Puntos de fallo descubiertos al final, no durante la entrada.
- Escasa trazabilidad del estado de cada solicitud durante el recorrido.

**Mejora concreta propuesta**
- Implementar flujo asistido por pasos con progreso visible.
- Validar en tiempo real campos y reglas de negocio críticas.
- Mostrar resumen final antes de confirmar y comprobante claro después.

### D. Consistencia visual — 5,3/10

**Justificación técnica**  
Existe una base común, pero con diferencias de espaciado, jerarquía tipográfica y tratamiento de controles.

**Problemas detectados**
- Variación perceptible en tamaño/peso de botones similares.
- Alineaciones y márgenes no completamente uniformes.
- Jerarquía texto-label-valor mejorable.

**Mejora concreta propuesta**
- Definir sistema mínimo de diseño (tokens de spacing, tipografía, estados).
- Normalizar botones por importancia y contexto.
- Estandarizar retículas y alineación por sección.

### E. Feedback del sistema — 4,5/10

**Justificación técnica**  
Los resultados de acciones críticas no siempre se comunican con claridad suficiente para trabajo confiable.

**Problemas detectados**
- Confirmaciones poco contundentes tras guardar/confirmar/sincronizar.
- Falta de detalle accionable cuando algo falla.
- Estados de proceso no siempre distinguibles (en curso, completado, con incidencias).

**Mejora concreta propuesta**
- Aplicar patrón de feedback único: inicio, progreso, resultado, siguiente acción.
- Incorporar resúmenes operativos post-acción con métricas básicas.
- Diferenciar visual y textual estados exitosos, parciales y fallidos.

### F. Gestión de errores — 4,4/10

**Justificación técnica**  
La estrategia parece centrada en notificar error, no en evitarlo y guiar recuperación.

**Problemas detectados**
- Prevención limitada de entradas inválidas o inconsistentes.
- Mensajes con baja capacidad de resolución autónoma.
- Recuperación no guiada en conflictos de sincronización.

**Mejora concreta propuesta**
- Añadir validadores preventivos y restricciones antes de confirmar.
- Redactar errores con estructura: problema, causa probable, acción recomendada.
- Incluir acciones directas de recuperación en el mismo mensaje.

### G. Carga cognitiva — 4,7/10

**Justificación técnica**  
La usuaria debe mantener demasiada información en memoria de trabajo para completar tareas simples.

**Problemas detectados**
- Exceso de datos simultáneos visibles.
- Mezcla de tareas transaccionales y consultas históricas en el mismo foco.
- Falta de agrupación progresiva por objetivo.

**Mejora concreta propuesta**
- Separar claramente modo operativo y modo consulta.
- Mostrar solo información indispensable por fase.
- Priorizar microcopys de decisión y consecuencias.

### H. Accesibilidad — 4,3/10

**Justificación técnica**  
Hay riesgo de fatiga y errores por contraste, tamaño utilizable y navegación de teclado no priorizada.

**Problemas detectados**
- Contraste potencialmente insuficiente en elementos secundarios.
- Objetivos de clic mejorables para uso prolongado.
- Orden de foco y shortcuts no suficientemente explícitos.

**Mejora concreta propuesta**
- Asegurar contraste mínimo AA en controles y textos clave.
- Incrementar tamaño mínimo de hit targets y separación entre controles.
- Definir y documentar flujo completo por teclado.

### I. Experiencia emocional — 4,9/10

**Justificación técnica**  
La aplicación transmite utilidad, pero no plena sensación de solidez ni control en operaciones sensibles.

**Problemas detectados**
- Dudas sobre estado final de acciones críticas.
- Percepción de herramienta funcional pero no consolidada.
- Confianza afectada cuando hay incidencias sin guía clara.

**Mejora concreta propuesta**
- Reforzar ritual de cierre de operación con comprobante breve.
- Unificar tono de mensajes hacia claridad y control.
- Hacer visible historial de acciones recientes con estado final.

---

## 3. Análisis de Flujo Principal

### Crear solicitud

**Dónde puede confundirse una delegada real**
- En la secuencia correcta de cumplimentación de campos.
- En la diferencia entre guardar borrador, añadir pendiente y confirmar.

**Dónde puede cometer errores**
- Introduciendo datos incompletos que solo fallan al final.
- Repitiendo solicitud por no tener confirmación inequívoca.

**Qué partes son frágiles**
- Dependencia de validación tardía.
- Falta de ayudas contextuales en el momento de captura.

### Confirmar solicitud

**Dónde puede confundirse una delegada real**
- En el alcance de la confirmación (qué cambia de estado y qué no).

**Dónde puede cometer errores**
- Confirmando sin revisar elementos pendientes.
- Asumiendo éxito cuando hubo incidencias parciales.

**Qué partes son frágiles**
- Ausencia de resumen preconfirmación y postconfirmación suficientemente explícitos.

### Ver histórico

**Dónde puede confundirse una delegada real**
- En la interpretación rápida de estados y cronología.

**Dónde puede cometer errores**
- Tomando decisiones con lectura incompleta por falta de filtros visibles.

**Qué partes son frágiles**
- Escalado deficiente cuando crece volumen de registros.

### Revisar saldos

**Dónde puede confundirse una delegada real**
- En la lectura de disponible, consumido y pendiente si no hay desglose claro.

**Dónde puede cometer errores**
- Confirmando solicitudes con interpretación errónea del saldo real.

**Qué partes son frágiles**
- Falta de contexto explicativo de cálculo en la propia vista.

### Sincronizar con Google Sheets

**Dónde puede confundirse una delegada real**
- En cuándo ejecutar sincronización y qué consecuencias tiene.

**Dónde puede cometer errores**
- Reintentando sin necesidad por feedback ambiguo.
- Ignorando conflictos por mensajes no accionables.

**Qué partes son frágiles**
- Baja trazabilidad visible del resultado (qué subió, qué falló, qué requiere acción).

---

## 4. Problemas Críticos (Top 10)

1. **Ausencia de CTA principal inequívoco por estado**  
   **Severidad:** Alta  
   **Impacto real:** Errores de secuencia y mayor tiempo por tarea.  
   **Solución concreta:** Definir una acción primaria única por fase y despriorizar el resto.

2. **Validación de reglas de negocio tardía**  
   **Severidad:** Alta  
   **Impacto real:** Correcciones tardías y frustración operativa.  
   **Solución concreta:** Validación incremental en cada campo crítico y prechequeo antes de confirmar.

3. **Feedback insuficiente tras acciones críticas**  
   **Severidad:** Alta  
   **Impacto real:** Duda sobre si la operación se ejecutó correctamente.  
   **Solución concreta:** Confirmación transaccional con resultado, identificador y siguiente paso.

4. **Estados de sincronización ambiguos**  
   **Severidad:** Alta  
   **Impacto real:** Reintentos erróneos, posibles duplicados y pérdida de confianza.  
   **Solución concreta:** Panel de estado con progreso, resultado y conflictos accionables.

5. **Sobrecarga de información en vista principal**  
   **Severidad:** Media  
   **Impacto real:** Mayor fatiga y tasa de error en uso continuado.  
   **Solución concreta:** Separar operativa, revisión y consulta en espacios diferenciados.

6. **Inconsistencia de controles y espaciados**  
   **Severidad:** Media  
   **Impacto real:** Menor previsibilidad y curva de aprendizaje más lenta.  
   **Solución concreta:** Sistema de componentes con reglas de layout uniformes.

7. **Errores no orientados a resolución**  
   **Severidad:** Media  
   **Impacto real:** Dependencia de soporte informal.  
   **Solución concreta:** Mensajes con causa probable y acción concreta ejecutable.

8. **Histórico con lectura operativa limitada**  
   **Severidad:** Media  
   **Impacto real:** Dificultad para seguimiento y auditoría diaria.  
   **Solución concreta:** Filtros persistentes, estados normalizados y ordenación por defecto útil.

9. **Accesibilidad funcional insuficiente**  
   **Severidad:** Media  
   **Impacto real:** Menor productividad y más errores por interacción.  
   **Solución concreta:** Mejorar contraste, targets, foco visible y navegación teclado.

10. **Lenguaje UI poco orientado a tarea**  
    **Severidad:** Baja  
    **Impacto real:** Incremento de dudas en usuarias no técnicas.  
    **Solución concreta:** Revisión integral de microcopy con enfoque en acción y resultado.

---

## 5. Recomendaciones Prioritarias

### Alta prioridad
- Rediseñar flujo principal en pasos explícitos: capturar, validar, confirmar, registrar resultado.
- Implementar feedback transaccional robusto en guardar, confirmar y sincronizar.
- Introducir prevención activa de errores antes de permitir confirmaciones.
- Clarificar estados operativos con semántica visual y textual consistente.

### Media prioridad
- Normalizar componentes, jerarquía tipográfica y espaciados.
- Mejorar histórico con filtros visibles y lectura rápida por estado.
- Reducir carga cognitiva inicial mediante revelado progresivo.

### Mejora estética
- Refinar paleta y contraste para reforzar percepción de solidez.
- Unificar ritmo visual entre bloques para eliminar sensación de herramienta improvisada.

---

## 6. Roadmap UX Profesional

### Cambios para pasar a nivel “profesional serio”
1. Arquitectura de interacción orientada a tareas críticas, no a acumulación de controles.
2. Modelo único de feedback para todas las operaciones sensibles.
3. Base de accesibilidad aplicada de forma transversal.
4. Biblioteca de patrones UI y microcopy consistente en toda la aplicación.

### Cambios para llegar a nivel “producto de referencia”
1. Asistencia contextual avanzada para saldos, conflictos y decisiones.
2. Trazabilidad completa de operaciones con historial legible y auditable.
3. Recuperación guiada de errores end-to-end sin dependencia de soporte.
4. Métricas UX en producción (tiempo por tarea, errores, retrabajo, tasa de soporte).

---

## 7. Nota Final

**Nota UX actual:** 5,2 / 10  
**Nota UX potencial tras mejoras:** 8,3 / 10

**Veredicto final sin suavizar**  
La aplicación mejoró y hoy ofrece señales de madurez, pero **aún no** está al nivel de producto profesional robusto para operación intensiva sin fricción. Siguen abiertas tres causas críticas: (1) validación preventiva incompleta en todo el recorrido, (2) errores todavía no totalmente guiados a resolución autónoma, y (3) consistencia de estados/semántica aún irregular entre módulos clave.

---

## 8. Evidencias de implementación

### Cambios aplicados (P0)

- Operativa ahora muestra un flujo visible de 3 pasos con resaltado del paso activo (rellenar, añadir, confirmar).
- Se estableció un CTA primario único y dinámico por estado: `Añadir a pendientes` o `Confirmar seleccionadas`.
- Se añadió guía contextual cuando el CTA primario está deshabilitado (`Selecciona al menos una pendiente` / motivo de validación).
- Se implementó notificación transaccional unificada con helper de presentación (`NotificationService`), incluyendo toast de alta con acción `Deshacer` (9s).
- Tras confirmar, se muestra un resumen transaccional con cantidad, total confirmado y próximos pasos.
- Se agregó prevención de duplicados antes de añadir (misma delegada + fecha + tramo), con opción de navegar a la pendiente existente.
- Se añadió soporte mínimo de teclado: Enter en el último campo para CTA primario y Escape en resumen/modal.
- Se reforzó el orden de foco del formulario en Operativa.

### Mejoras aplicadas P1: Histórico

- Se incorporó un modelo dedicado (`HistoricalViewModel`) para desacoplar **fuente de datos -> proxy de filtros/orden -> tabla**, mejorando legibilidad y rendimiento con volúmenes altos.
- Filtros disponibles en la barra superior:
  - Búsqueda por texto libre (concepto/notas/columnas visibles/delegada/estado).
  - Rango de fechas `Desde` / `Hasta`.
  - Atajo rápido **Últimos 30 días**.
  - Estado (Todos / Pendiente / Confirmada).
  - Delegada (Todas / delegada específica).
  - Limpieza integral con **Limpiar filtros**.
- El estado ahora se presenta de forma legible en columna dedicada con badge textual (ej. `✅ Confirmada`, `🕒 Pendiente`).
- Ordenación activa por cabecera; orden por defecto: fecha descendente con desempate por hora descendente.
- Acciones del histórico ahora son contextuales por selección:
  - `Eliminar (n)`
  - `Generar PDF (n)`
  - `Ver detalle (n)`
  - `Re-sincronizar (n)`
- Se añadió diálogo de detalle para inspeccionar una fila completa sin depender de columnas extensas.
- Accesibilidad y teclado:
  - **Ctrl+F** enfoca la búsqueda del histórico.
  - **Enter** abre detalle de la fila seleccionada.
  - **Escape** limpia foco de búsqueda o selección activa.
- Rendimiento:
  - Filtrado implementado con `QSortFilterProxyModel` (sin barridos manuales por keypress).
  - Búsqueda con debounce de 250ms para minimizar lag al escribir.

### Mejoras aplicadas: Sync Panel Pro

- Se añadió un panel de sincronización persistente en Configuración con estado explícito (`Idle`, `Sincronizando…`, `OK`, `OK con avisos`, `Error`, `Configuración incompleta`).
- El panel muestra trazabilidad operativa: última sincronización con fecha/hora y delegada, fuente configurada (credencial + spreadsheet parcial), alcance y criterio de idempotencia.
- Se incorporó resumen inequívoco del último resultado: filas creadas, actualizadas, omitidas, conflictos y errores.
- Nuevas acciones operativas: `Sincronizar ahora`, `Ver detalles`, `Copiar informe`, `Abrir carpeta de logs`, más CTA `Ir a configuración` cuando faltan credenciales/ID.
- Se implementó vista de detalle con entradas estructuradas por severidad/entidad/sección/mensaje/acción sugerida.
- Se persiste cada ejecución en `logs/sync_last.json` y `logs/sync_last.md`, además de historial rotativo en `logs/sync_history/` (últimas 20 sync).
- Se reforzó anti-reentrancia: no se pueden disparar dos sincronizaciones simultáneas ni por doble click.
