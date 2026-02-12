# Registro de Decisiones Arquitectónicas (ADR)

## ADR-001: Uso de dataclasses frozen

### Decisión
Se utilizarán `dataclasses` con `frozen=True` para los modelos de dominio que representen hechos históricos (por ejemplo, solicitudes y registros de horas).

### Motivo
La inmutabilidad evita cambios accidentales sobre datos ya consolidados y facilita razonar sobre el estado del sistema. También mejora la trazabilidad de reglas de negocio al forzar la creación de nuevas instancias cuando hay una modificación lógica.

### Consecuencias
- Menor probabilidad de efectos colaterales por mutación.
- Mayor claridad en pruebas y depuración.
- Puede requerir más transformaciones (copias) cuando cambian valores.

### Alternativas consideradas
- Clases mutables tradicionales.
- Diccionarios sin tipado estricto.
- Pydantic u otras librerías de modelos para imponer inmutabilidad.

---

## ADR-002: Uso de SQLite como almacenamiento local

### Decisión
Se adopta SQLite como base de datos local principal para persistencia.

### Motivo
SQLite no requiere servidor, simplifica despliegue en entornos de escritorio y proporciona transacciones suficientes para el volumen esperado del sistema.

### Consecuencias
- Instalación y mantenimiento simples para usuarios finales.
- Adecuado para operación local y un único proceso principal.
- Limitaciones para concurrencia intensa y escalabilidad horizontal.

### Alternativas consideradas
- Archivos JSON/CSV.
- PostgreSQL o MySQL en servidor dedicado.
- Almacenamiento embebido alternativo (por ejemplo, DuckDB).

---

## ADR-003: Sincronización con Google Sheets en vez de servidor propio

### Decisión
Se implementará sincronización con Google Sheets como mecanismo de intercambio y consolidación externa, en lugar de mantener un backend propio.

### Motivo
Google Sheets reduce el coste operativo (hosting, seguridad, backups, mantenimiento) y permite colaboración rápida con actores no técnicos.

### Consecuencias
- Menor esfuerzo de infraestructura y operación.
- Dependencia de disponibilidad de APIs de Google y credenciales.
- Restricciones de cuota y latencia de red en sincronizaciones.

### Alternativas consideradas
- API REST con servidor propio.
- Sincronización por archivos compartidos (CSV/Excel).
- Integración con otras plataformas SaaS de base de datos.

---

## ADR-004: Arquitectura por capas inspirada en Clean Architecture

### Decisión
La solución se organizará por capas (dominio, aplicación, infraestructura y UI), con dependencias orientadas hacia el núcleo de dominio.

### Motivo
Separar responsabilidades facilita pruebas, mantenimiento y reemplazo de detalles técnicos (por ejemplo, motor de persistencia o proveedor de sincronización) sin impactar reglas de negocio.

### Consecuencias
- Mejor desacoplamiento y extensibilidad.
- Mayor claridad en fronteras entre casos de uso y adaptadores.
- Incremento inicial de estructura y abstracciones.

### Alternativas consideradas
- Arquitectura monolítica sin separación clara por capas.
- Patrón MVC clásico acoplado a la UI.
- Arquitectura orientada a scripts/procedimientos.

---

## ADR-005: Cálculo de horas solo en histórico

### Decisión
El cálculo acumulado de horas sindicales se realizará exclusivamente a partir del histórico persistido, no desde estados temporales en memoria o borradores.

### Motivo
Tomar el histórico como fuente de verdad asegura reproducibilidad de resultados y evita inconsistencias por datos transitorios no confirmados.

### Consecuencias
- Consistencia funcional en reportes y liquidaciones.
- Necesidad de guardar eventos/solicitudes antes de reflejar cómputos finales.
- Posible percepción de menor inmediatez en cálculos preliminares.

### Alternativas consideradas
- Cálculo mixto (histórico + estado en memoria).
- Cálculo únicamente en vistas de UI.
- Preagregados incrementales sin recomputación desde histórico.
