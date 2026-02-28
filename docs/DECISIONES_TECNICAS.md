# Decisiones técnicas

## Arquitectura base

Se mantiene arquitectura en capas:

```text
UI -> Application -> Domain -> Infrastructure
```

Objetivos:

- separar reglas de negocio de detalles de UI/infra,
- facilitar testabilidad,
- permitir evolución de adaptadores sin romper dominio.

## Decisiones vigentes

- Dependencias pinneadas para reproducibilidad (`requirements*.txt`).
- Observabilidad estructurada con trazabilidad por identificadores de correlación.
- Estrategia de tests con `pytest` y verificación en CI.
- Canonical de decisiones en documentación técnica (`docs/`).

## Referencias

- Arquitectura: [`arquitectura.md`](arquitectura.md)
- Decisiones históricas/extendidas: [`decisiones_tecnicas.md`](decisiones_tecnicas.md), [`decisiones.md`](decisiones.md)
- Política de calidad: [`quality_gate.md`](quality_gate.md)
