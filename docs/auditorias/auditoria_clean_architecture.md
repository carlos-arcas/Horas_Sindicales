# Auditoría Clean Architecture

**Estado global:** PASS

## Resumen
- Infracciones totales: 1
- Corregidas: 1
- Pendientes: 0

## Infracciones detectadas
- **CA-UI-001** | `A2_logica_negocio_en_ui` | Severidad: **alta** | Estado: **corregida**  
  - Archivo: `app/ui/vistas/historico_filter_rules.py` (línea aprox 1)
  - Impacto: Las reglas de filtrado del histórico vivían en UI, mezclando presentación con reglas de aplicación y dificultando pruebas por capa.
  - Propuesta: Mover reglas puras a app/domain/services.py y dejar UI como compatibilidad.

## Resumen de dependencias por capa (imports internos app/*)
- `domain` -> domain:8
- `application` -> application:111, domain:61
- `infrastructure` -> application:10, domain:18, infrastructure:21
- `ui` -> application:41, domain:28, ui:107

## Evidencia de control
- Se ejecutó escaneo AST de imports entre capas para detectar A1 y A4.
- Se revisó A2 manualmente para ubicar reglas de filtrado en UI y se movieron a dominio puro.
