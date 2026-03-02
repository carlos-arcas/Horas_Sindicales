# Slots seguros en Qt

Desde `app/ui/vistas/main_window/wiring_helpers.py`, cada conexión de `signal.connect(...)` pasa por `envolver_slot_seguro`.

## ¿Qué resuelve?

- Si un handler lanza excepción, la excepción no se propaga al loop de Qt.
- Se registra log estructurado con `reason_code=QT_SLOT_EXCEPTION`, `contexto` y nombre de handler.
- Si la ventana expone `toast`, se informa un error accionable a la usuaria.

## Alcance

Este guardrail evita caída por excepciones en handlers de UI.
No cubre problemas de threading (`QObject in different thread`) ni ciclo de vida de `QThread`.
