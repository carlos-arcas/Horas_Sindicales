# Arquitectura del proyecto `Horas_Sindicales`

## Objetivo

Este documento describe la arquitectura vigente a nivel de capas, sus límites de responsabilidad y las reglas de dependencia que se validan en el repositorio.

## Diagrama de capas (ASCII)

```text
+---------------------------+
| UI (app/ui)               |
| Pantallas, diálogos, Qt   |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Aplicación (app/application)
| Casos de uso, orquestación |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Dominio (app/domain)       |
| Entidades y reglas negocio |
+-------------+-------------+
              ^
              |
+-------------+-------------+
| Infraestructura (app/infrastructure)
| SQLite, Sheets, adapters   |
+---------------------------+
```

Cadena canónica de dependencias:

- `dominio <- aplicacion <- ui`
- `dominio <- aplicacion <- infraestructura` (la infraestructura implementa puertos consumidos por aplicación).

## Reglas de dependencia

1. **Dominio** no depende de UI ni de detalles de infraestructura.
2. **Aplicación** depende del dominio y de puertos/DTOs de aplicación.
3. **Infraestructura** puede depender de dominio/aplicación para implementar contratos, pero no debe imponer reglas de negocio.
4. **UI** consume casos de uso y servicios de aplicación; no debe contener reglas de negocio complejas.
5. **Entrypoints/Bootstrap** realizan wiring e inyección de dependencias concretas.

## Estado actual y límites

- El proyecto sigue una arquitectura por capas pragmática, no una Clean Architecture estricta.
- Existen integraciones con SQLite y Google Sheets aisladas mayormente en infraestructura.
- La trazabilidad operativa se centraliza mediante eventos estructurados con `correlation_id`.
- `app/` continúa siendo la implementación actual (sin renombres masivos en esta etapa).
- `dominio/`, `aplicacion/`, `infraestructura/` y `presentacion/` funcionan como paquetes puente de compatibilidad que reexportan desde `app/`.

### Estrategia de transición (sin big-bang)

1. Mantener `app/` estable como fuente real mientras se evita romper entrypoints y scripts existentes.
2. Exponer nuevas rutas de import en español mediante wrappers (`dominio`, `aplicacion`, `infraestructura`, `presentacion`).
3. Redirigir gradualmente módulos nuevos hacia los paquetes en español, sin mover cientos de archivos de una sola vez.
4. Una vez estabilizado el repositorio, planificar el movimiento físico definitivo hacia carpetas en español.

## Verificación automática relacionada

- `tests/test_architecture_imports.py` valida restricciones de imports por capas.
- `tests/test_docs_minimas.py` valida presencia y contenido mínimo de esta documentación obligatoria.

## Pendientes de completar

- Pendiente de completar un diagrama C4 (contexto/contenedores) si se requiere para auditoría externa.
- Pendiente de completar inventario de dependencias externas por flujo crítico.
