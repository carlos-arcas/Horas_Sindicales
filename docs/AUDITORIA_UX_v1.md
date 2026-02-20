# Auditoría UX Senior — Reserva de Horas Sindicales (v1)

## 1. Resumen Ejecutivo

**Nivel UX global:** 5,2 / 10  
**Nivel de madurez:** Intermedio bajo  
**Riesgo operativo:** Medio–Alto

### Impacto en usuario real
La aplicación permite ejecutar tareas clave, pero exige demasiada interpretación por parte de una delegada no técnica. La interfaz transmite funcionalidad, no claridad operativa: se puede completar el trabajo, pero con fricción, dudas y riesgo de errores evitables en momentos críticos (carga de solicitud, validación y sincronización).

### Conclusión directa
El producto no está en estado UX “profesional serio” para uso intensivo sin apoyo informal. Funciona como herramienta interna utilitaria, pero aún no como sistema robusto y autoexplicativo para operación diaria con bajo margen de error.

---

## 2. Evaluación por Dimensiones (con puntuación)

## A. Jerarquía visual — **5,0/10**
**Justificación técnica**  
La pantalla concentra múltiples bloques funcionales con peso visual similar. Falta una estructura clara de prioridad (qué mirar primero, qué hacer después).

**Problemas detectados**
- Competencia visual entre formulario, acciones y listados.
- Uso de color con función estética más que semántica.
- Densidad alta de elementos visibles de forma simultánea.

**Mejora concreta propuesta**
- Definir jerarquía en tres niveles: acción principal, contexto secundario, soporte.
- Reforzar contraste semántico (primario, secundario, alerta, éxito).
- Reducir ruido visual con agrupación por tarjetas/secciones y más aire vertical.

## B. Claridad funcional — **5,4/10**
**Justificación técnica**  
Se intuyen los objetivos generales, pero no siempre queda explícito el flujo recomendado sin conocimiento previo.

**Problemas detectados**
- Falta de señal clara del “siguiente paso”.
- Acciones relevantes no suficientemente diferenciadas de acciones accesorias.
- Dependencia de conocimiento tácito del proceso sindical.

**Mejora concreta propuesta**
- Incorporar guía contextual breve por bloque (“1. Completa”, “2. Revisa”, “3. Confirma”).
- Etiquetado orientado a tarea y no solo a dato.
- Destacar una acción primaria por pantalla/estado.

## C. Flujo de interacción — **4,9/10**
**Justificación técnica**  
El recorrido operativo presenta fricción por transiciones y validaciones poco anticipadas.

**Problemas detectados**
- Exceso de microdecisiones en una sola vista.
- Puntos de error no prevenidos en origen.
- Estados intermedios ambiguos (si una acción quedó realmente aplicada o no).

**Mejora concreta propuesta**
- Modelo de flujo asistido (wizard ligero o pasos visibles).
- Validación en tiempo real con mensajes accionables.
- Confirmación explícita posterior a acciones de impacto.

## D. Consistencia visual — **5,6/10**
**Justificación técnica**  
Hay base de estilo común, pero se perciben variaciones de tamaños, alineaciones y peso de componentes.

**Problemas detectados**
- Homogeneidad incompleta en botones y controles.
- Espaciado vertical irregular entre secciones.
- Ritmo tipográfico mejorable (jerarquía de títulos/labels/valores).

**Mejora concreta propuesta**
- Definir sistema UI mínimo (tokens de spacing, tamaños, estados).
- Estandarizar componentes reutilizables.
- Crear plantilla visual de formularios y tablas.

## E. Feedback del sistema — **4,8/10**
**Justificación técnica**  
El sistema informa, pero no siempre en el momento ni con la profundidad necesaria para operación segura.

**Problemas detectados**
- Confirmaciones poco contundentes tras acciones críticas.
- Errores con bajo nivel de orientación práctica.
- Estado de procesos (incluida sincronización) insuficientemente narrado.

**Mejora concreta propuesta**
- Patrón uniforme de feedback: inicio/progreso/resultado.
- Mensajes con estructura: qué pasó, por qué, cómo resolver.
- Resumen final de operación (éxitos, omisiones, conflictos).

## F. Gestión de errores — **4,6/10**
**Justificación técnica**  
El enfoque actual parece más reactivo que preventivo.

**Problemas detectados**
- Falta de prevención robusta antes de confirmar.
- Recuperación no siempre evidente para perfiles no técnicos.
- Riesgo de bloqueos operativos por mensajes poco guiados.

**Mejora concreta propuesta**
- Validadores preventivos de negocio antes del envío.
- Acciones de recuperación directas en el mensaje de error.
- Registro visual de incidencias recientes con estado y recomendación.

## G. Carga cognitiva — **4,7/10**
**Justificación técnica**  
La interfaz obliga a sostener demasiada información en memoria de trabajo.

**Problemas detectados**
- Sobrecarga de datos visibles sin progresión.
- Mezcla de captura, revisión e histórico en un mismo foco atencional.
- Terminología con posible ambigüedad para usuario no experto.

**Mejora concreta propuesta**
- Progresive disclosure real: mostrar solo lo necesario en cada fase.
- Separar “hacer” vs “consultar” en zonas claramente distintas.
- Microcopys orientados a decisión y resultado.

## H. Accesibilidad — **4,5/10**
**Justificación técnica**  
Hay riesgo de exclusión funcional por contraste, tamaño útil y navegación.

**Problemas detectados**
- Contraste y legibilidad con margen de mejora.
- Objetivos clicables potencialmente pequeños para uso intensivo.
- Navegación por teclado no percibida como prioritaria.

**Mejora concreta propuesta**
- Ajustar contraste mínimo WCAG AA en texto y controles clave.
- Aumentar áreas de interacción y espaciado táctico.
- Definir orden de foco y atajos de teclado visibles.

## I. Experiencia emocional — **5,1/10**
**Justificación técnica**  
La aplicación se percibe útil, pero con sensación de herramienta “en evolución” más que de producto consolidado.

**Problemas detectados**
- Baja sensación de control en operaciones sensibles.
- Poca “tranquilidad operativa” al confirmar acciones.
- Señales de robustez insuficientes (estado, trazabilidad, cierre de flujo).

**Mejora concreta propuesta**
- Reforzar rituales de cierre: confirmaciones + resumen + próximo paso.
- Mejorar lenguaje de confianza (“guardado”, “sincronizado”, “pendiente de revisión”).
- Estabilizar patrones de interacción para previsibilidad.

---

## 3. Análisis de Flujo Principal

## Crear solicitud
**Riesgos de confusión**
- No siempre queda claro qué campos son obligatorios y en qué orden conviene completarlos.
- Si hay reglas de negocio implícitas, la usuaria las descubre tarde.

**Errores probables**
- Carga incompleta o inconsistente de datos.
- Elecciones válidas técnicamente pero incorrectas operativamente.

**Partes frágiles**
- Dependencia de validación tardía.
- Falta de ayudas contextuales durante la captura.

## Confirmar solicitud
**Riesgos de confusión**
- Ambigüedad sobre el alcance de la confirmación (qué queda cerrado y qué no).

**Errores probables**
- Confirmación prematura sin revisión suficiente.
- Duplicación por duda de estado final.

**Partes frágiles**
- Feedback final insuficiente para dar sensación de transacción completada.

## Ver histórico
**Riesgos de confusión**
- Dificultad para distinguir rápidamente estados, fechas o criterios relevantes.

**Errores probables**
- Lectura errónea del estado de una solicitud.
- Pérdida de tiempo por búsqueda manual sin filtros claros.

**Partes frágiles**
- Escalabilidad visual limitada cuando crece el volumen de registros.

## Revisar saldos
**Riesgos de confusión**
- Interpretación ambigua de saldos disponibles, consumidos o pendientes.

**Errores probables**
- Toma de decisiones con lectura incompleta del saldo real.

**Partes frágiles**
- Ausencia de explicaciones de cálculo en contexto.

## Sincronizar con Google Sheets
**Riesgos de confusión**
- Incertidumbre sobre cuándo sincronizar y qué impacto tiene.

**Errores probables**
- Reintentos innecesarios por no comprender el resultado.
- Dudas ante conflictos o diferencias de datos.

**Partes frágiles**
- Falta de trazabilidad visible de la operación (qué se subió, qué falló, qué requiere acción).

---

## 4. Problemas Críticos (Top 10)

1. **Falta de jerarquía de acción principal**  
   **Severidad:** Alta  
   **Impacto real:** Incrementa errores de secuencia y tiempos de operación.  
   **Solución concreta:** Diseñar layout por prioridad operativa con CTA primaria única por estado.

2. **Validación tardía de reglas de negocio**  
   **Severidad:** Alta  
   **Impacto real:** La usuaria corrige tarde, con frustración y riesgo de datos erróneos.  
   **Solución concreta:** Validación en campo y prechequeo antes de confirmar.

3. **Feedback débil tras acciones críticas**  
   **Severidad:** Alta  
   **Impacto real:** Dudas sobre si una solicitud quedó registrada/sincronizada.  
   **Solución concreta:** Mensaje de resultado estructurado con identificador y siguiente paso.

4. **Ambigüedad en estados de sincronización**  
   **Severidad:** Alta  
   **Impacto real:** Repetición de acciones, posibles duplicados o desconfianza en datos.  
   **Solución concreta:** Panel de estado con progreso, resumen y conflictos accionables.

5. **Sobrecarga cognitiva en la vista principal**  
   **Severidad:** Media  
   **Impacto real:** Lentitud operativa y mayor tasa de error en tareas repetitivas.  
   **Solución concreta:** Separar captura, revisión e histórico por pestañas o bloques progresivos.

6. **Consistencia visual parcial en componentes**  
   **Severidad:** Media  
   **Impacto real:** Reduce previsibilidad y aumenta curva de aprendizaje.  
   **Solución concreta:** Sistema de componentes con variantes y reglas de espaciado.

7. **Mensajes de error poco prescriptivos**  
   **Severidad:** Media  
   **Impacto real:** Dependencia de soporte informal para resolver incidencias.  
   **Solución concreta:** Errores con causa probable + acción recomendada + botón directo.

8. **Histórico con lectura operativa mejorable**  
   **Severidad:** Media  
   **Impacto real:** Dificulta auditoría rápida y seguimiento de casos.  
   **Solución concreta:** Filtros por estado/fecha y códigos visuales consistentes.

9. **Accesibilidad funcional insuficiente**  
   **Severidad:** Media  
   **Impacto real:** Fatiga visual y menor eficiencia en uso prolongado.  
   **Solución concreta:** Mejorar contraste, tamaños mínimos y orden de foco por teclado.

10. **Lenguaje de interfaz poco orientado a tarea**  
    **Severidad:** Baja  
    **Impacto real:** Necesidad de aprendizaje implícito para entender decisiones.  
    **Solución concreta:** Reescritura de etiquetas y ayudas en lenguaje de acción.

---

## 5. Recomendaciones Prioritarias

## Alta prioridad (debe hacerse)
- Reestructurar flujo principal en pasos visibles: capturar, validar, confirmar, registrar resultado.
- Implementar feedback transaccional completo en guardar y sincronizar.
- Introducir prevención de errores de negocio antes de confirmación.
- Clarificar estados operativos con códigos visuales y texto inequívoco.

## Media prioridad
- Unificar diseño de componentes y espaciados.
- Mejorar histórico con filtros y lectura rápida.
- Reducir densidad inicial de información mediante revelado progresivo.

## Mejora estética
- Refinar tipografía y contraste para elevar percepción de calidad.
- Alinear ritmo visual (márgenes, títulos, bloques) para reducir sensación de improvisación.

---

## 6. Roadmap UX Profesional

## Para pasar a nivel “profesional serio”
1. Definir arquitectura de interacción por tareas críticas (no por acumulación de widgets).  
2. Establecer sistema de feedback estándar para todas las operaciones sensibles.  
3. Implementar accesibilidad base (contraste, foco, targets, teclado).  
4. Normalizar componentes y lenguaje de interfaz en toda la app.

## Para llegar a “producto de referencia”
1. Incorporar asistencia contextual inteligente (explicaciones de saldo, conflictos y próximos pasos).  
2. Añadir trazabilidad operativa completa y legible para auditoría diaria.  
3. Diseñar experiencia resiliente a errores con recuperación guiada end-to-end.  
4. Medir UX en producción (tiempos por tarea, tasa de error, retrabajo, soporte requerido).

---

## 7. Nota Final

**Nota UX actual:** 5,2 / 10  
**Nota UX potencial tras mejoras prioritarias:** 8,1 / 10

**Veredicto final**  
La herramienta es funcional, pero todavía no alcanza el estándar de producto profesional robusto para operación real sin fricción. Su evolución debe centrarse en claridad de flujo, prevención de errores y confianza operativa, no en sumar funciones.

---

## Cambios aplicados (P0)

- Operativa ahora muestra un flujo visible de 3 pasos con resaltado del paso activo (rellenar, añadir, confirmar).
- Se estableció un CTA primario único y dinámico por estado: `Añadir a pendientes` o `Confirmar seleccionadas`.
- Se añadió guía contextual cuando el CTA primario está deshabilitado (`Selecciona al menos una pendiente` / motivo de validación).
- Se implementó notificación transaccional unificada con helper de presentación (`NotificationService`), incluyendo toast de alta con acción `Deshacer` (9s).
- Tras confirmar, se muestra un resumen transaccional con cantidad, total confirmado y próximos pasos.
- Se agregó prevención de duplicados antes de añadir (misma delegada + fecha + tramo), con opción de navegar a la pendiente existente.
- Se añadió soporte mínimo de teclado: Enter en el último campo para CTA primario y Escape en resumen/modal.
- Se reforzó el orden de foco del formulario en Operativa.
