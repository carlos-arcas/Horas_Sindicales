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

## 2026-02 ROI: Solicitudes confirmar sin PDF (Planner/Runner)
- Hotspot abordado: `SolicitudUseCases.confirmar_sin_pdf` por mezcla de reglas + orquestación.
- Decisión: extraer planificación pura a `confirmar_sin_pdf_planner.py`.
- `plan_confirmar_sin_pdf` clasifica cada solicitud en `RESOLVE_EXISTING` o `CREATE_NEW`.
- La use case mantiene el runner fino (`_run_confirmar_sin_pdf_action`) sin cambiar contratos públicos.
- Beneficio ROI: misma conducta observable, menor señal de “lógica mezclada”.
- Beneficio técnico: se habilitan tests headless de reglas de planificación sin DB/UI.
- Riesgo controlado: se conservaron mensajes de error y excepciones de persistencia.
- Criterio de éxito: `pytest -q -m "not ui"` en verde y flujo de confirmación intacto.

- Contrato planner (estable): cada acción expone `action_type`, `reason_code` y `payload` mínimo para runner.
- `reason_code` vigente:
  - `HAS_ID_RESOLVE_EXISTING` cuando `id is not None` (precedencia máxima, incluso para `id=0`).
  - `MISSING_ID_CREATE_NEW` cuando `id is None`.
- Orden del plan estable: misma secuencia de entrada en lote.

## 2026-03 Hardening UI: callbacks de toast seguros
- Decisión: centralizar la ejecución de `action_callback` en `app/ui/toasts/ejecutar_callback_seguro.py`.
- Motivo: evitar que excepciones de callbacks lleguen al event loop de Qt y degraden estabilidad de UI.
- Logging: se emite evento estructurado `toast_action_callback_failed` con `contexto` y `correlation_id`.
- Seguridad: el mensaje de error anonimiza rutas absolutas (solo conserva nombre de archivo) para reducir exposición de paths sensibles.
- Verificación: tests unitarios del helper + smoke test UI de callback fallido sin crash.
