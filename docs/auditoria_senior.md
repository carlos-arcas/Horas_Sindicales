# Auditoría senior de producto — Horas Sindicales

## Score global
- **66/100** (ponderado).

## Resumen corto
- Base técnica sólida para un producto real: capas visibles, migraciones, suite de tests útil y documentación operativa.
- Riesgo principal: módulos monolíticos (`MainWindow`, `use_cases`, `repos_sqlite`) y manejo amplio de excepciones que dificulta depuración precisa.
- Con un plan de refactor + hardening de calidad (lint/type/coverage/CI), el repositorio puede subir a 85+ rápidamente.

## Score por áreas
- A Arquitectura y límites de capas (20%): **68**
- B Calidad de código y mantenibilidad (15%): **55**
- C Testing y verificabilidad (20%): **78**
- D Manejo de errores y resiliencia (10%): **58**
- E Logging, trazabilidad y observabilidad (10%): **64**
- F Configuración, entornos y secretos (10%): **70**
- G Packaging, distribución y DX (10%): **60**
- H Documentación y operativa (5%): **74**

## Evidencias destacadas
- Arquitectura por capas documentada y explícita en código.
- Inyección de dependencias en `main.py` con wiring único.
- Puerto de dominio (`Protocol`) y adaptadores en infraestructura.
- Test suite actual: 58 tests pasando.
- Faltan herramientas de calidad automatizadas (lint/type/coverage/CI/pre-commit).

