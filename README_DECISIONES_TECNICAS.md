# Decisiones técnicas UX (resumen)

## 1) Patrón: UI fina + reglas testeables (headless)

Se mantiene el patrón del proyecto:
- La UI Qt orquesta eventos.
- Las decisiones de UX/estado se extraen a módulos puros.
- Los tests nuevos son headless (sin depender de PySide6).

Aplicado en:
- `app/ui/vistas/solicitudes_ux_rules.py` para foco del primer error y estado visible de Solicitudes.
- `app/application/sync_diagnostics.py` para diagnóstico de credenciales por `reason_code`.

## 2) Catálogo central de copy

Se crea `app/ui/copy_catalog.py` para centralizar textos de:
- `solicitudes.*`
- `sync_credenciales.*`

Beneficios:
- Menos hardcodes.
- Menos duplicación de mensajes.
- Cambios de microcopy más seguros y rápidos.

## 3) Asistente de credenciales + diagnósticos por reason_code

La configuración de Sync se rehace como flujo guiado en 4 pasos (sin cambiar backend):
1. Qué necesitas.
2. Cargar credenciales.
3. Probar conexión.
4. Guardar y siguiente acción.

Los errores se traducen a mensajes accionables mediante `reason_code` estable.
No se muestra stacktrace al usuario, pero sí se deja logging técnico.

## 4) Impacto esperado (ROI)

- Menos tickets de soporte por errores de formulario y credenciales.
- Menos retrabajo por mensajes ambiguos.
- Mayor autonomía de usuarias no técnicas (40–55) en tareas diarias.
- Menor riesgo de regresión gracias a tests puros y parametrizados.
