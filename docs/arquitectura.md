# Arquitectura del proyecto `Horas_Sindicales`

## Objetivo

Describir la arquitectura vigente del producto y las restricciones que deben mantenerse al limpiar o ampliar el repositorio. El sistema es una **aplicación desktop en Python + PySide6** con núcleo desacoplado de la UI.

## Capas activas

```text
+---------------------------+
| UI (app/ui)               |
| Ventanas, diálogos, Qt    |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Aplicación (app/application)
| Casos de uso, DTOs, reglas |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Dominio (app/domain)       |
| Entidades y políticas puras|
+-------------+-------------+
              ^
              |
+-------------+-------------+
| Infraestructura            |
| SQLite, FS, Sheets, i18n   |
+---------------------------+
```

Cadena canónica de dependencias:

- `dominio <- aplicacion <- ui`
- `dominio <- aplicacion <- infraestructura`

## Reglas duras

1. **Dominio** no depende de UI, infraestructura ni entrypoints.
2. **Aplicación** orquesta casos de uso y puertos; no mete detalles de framework o persistencia.
3. **Infraestructura** implementa puertos y adaptadores concretos; no define reglas de negocio.
4. **UI** coordina interacción y render; no decide reglas de negocio complejas.
5. **Bootstrap y entrypoints** resuelven wiring, logging y configuración.

## Estado del repositorio

- La fuente real del producto vive en `app/`.
- Los paquetes `dominio/`, `aplicacion/` e `infraestructura/` se mantienen como puentes de compatibilidad controlados para imports en español.
- Los gates del repositorio validan límites de capas, contratos de documentación, i18n y tests core.
- La limpieza del repositorio debe eliminar residuos ajenos al producto desktop, no relajar estas fronteras.

## Verificación automática relacionada

- `tests/test_architecture_imports.py` valida dependencias permitidas entre capas.
- `tests/test_clean_architecture_imports_guard.py` refuerza el guardarraíl estructural.
- `scripts/auditar_clean_architecture.py` genera evidencia documental para auditoría.

## Criterio práctico para cambios

Antes de aceptar un cambio, verificar:

- si el flujo nuevo entra por UI/entrypoint y termina en aplicación/dominio;
- si los textos visibles siguen en i18n;
- si el wiring queda en bootstrap/entrypoints;
- si el adaptador concreto se puede sustituir sin tocar reglas del dominio.

## Integraciones relevantes

- **SQLite** para persistencia local y auditoría.
- **Google Sheets** para sincronización operativa.
- **ReportLab** para generación de PDF.
- **PySide6** como toolkit de escritorio.

## Lo que quedó fuera

El repositorio activo ya no documenta ni conserva verticales web heredadas como parte del producto. Si reaparece código de otro stack, debe justificarse como integración real o eliminarse.
