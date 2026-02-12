# Registro de decisiones arquitectónicas (ADR)

> Complementa [arquitectura.md](../arquitectura.md) con decisiones y trade-offs.

## ADR-001: Modelos de dominio inmutables (`dataclass(frozen=True)`)
**Decisión**
Usar modelos inmutables para entidades de dominio con valor histórico (por ejemplo, solicitudes).

**Motivo**
Reduce mutaciones accidentales y mejora trazabilidad.

**Consecuencias**
- Menos efectos colaterales.
- Más claridad en pruebas.
- Necesidad de crear nuevas instancias para cambios.

**Alternativas**
- Clases mutables.
- Diccionarios sin tipado.
- Librerías de modelos externas (p. ej. Pydantic).

## ADR-002: SQLite como almacenamiento local
**Decisión**
SQLite es la base de datos local principal.

**Motivo**
No requiere servidor y encaja en un entorno desktop.

**Consecuencias**
- Despliegue simple.
- Buen ajuste para uso local.
- Limitaciones de concurrencia y escalado horizontal.

**Alternativas**
- JSON/CSV.
- PostgreSQL/MySQL con servidor.
- Otras bases embebidas.

## ADR-003: Sincronización con Google Sheets (sin backend propio)
**Decisión**
Usar Google Sheets como capa compartida de sincronización externa.

**Motivo**
Menor coste operativo y adopción rápida por perfiles no técnicos.

**Consecuencias**
- Menos infraestructura propia.
- Dependencia de APIs/credenciales de Google.
- Cuotas y latencia de red.

**Alternativas**
- API REST propia.
- Intercambio por CSV/Excel.
- Otra plataforma SaaS.

## ADR-004: Arquitectura por capas con puertos/adaptadores
**Decisión**
Organizar en capas (`domain`, `application`, `infrastructure`, `ui`) con dependencias hacia el núcleo.

**Motivo**
Mejora mantenibilidad, testeo y sustitución de integraciones.

**Consecuencias**
- Fronteras más claras.
- Mejor extensibilidad.
- Mayor estructura inicial.

**Alternativas**
- Monolito sin capas claras.
- MVC acoplado a UI.
- Diseño procedural.

## ADR-005: Cálculo de saldos desde histórico persistido
**Decisión**
Calcular horas acumuladas solo desde solicitudes históricas persistidas.

**Motivo**
Mantiene reproducibilidad y evita inconsistencias por estado transitorio.

**Consecuencias**
- Reportes consistentes.
- Requiere persistir antes de consolidar saldos.
- Menor inmediatez en borradores.

**Alternativas**
- Cálculo mixto (histórico + memoria).
- Cálculo en UI.
- Preagregados incrementales.
