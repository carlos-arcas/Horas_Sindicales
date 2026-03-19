# Decisiones técnicas

## Propósito

Este documento registra decisiones vigentes que afectan a arquitectura, ejecución, pruebas y trazabilidad del producto. No es un cajón de sastre ni un backlog: sólo quedan decisiones que siguen ayudando a mantener o auditar la aplicación desktop.

## Decisiones activas

- **2026-02-20 — Producto declarado como desktop Python + PySide6 — Vigente**  
  La documentación y los entrypoints se alinean con una aplicación de escritorio. Se eliminan descripciones ambiguas de “app web”, “frontend” o similares como definición del producto.

- **2026-02-20 — Clean Architecture como contrato duro — Vigente**  
  `app/domain` no depende de UI ni infraestructura; `app/application` orquesta casos de uso y puertos; `app/infrastructure` implementa adaptadores; `app/ui` presenta y delega. Los guardarraíles de imports y los tests de arquitectura son bloqueantes.

- **2026-02-20 — Gate contractual único: `python -m scripts.gate_pr` — Vigente**  
  Se evita dispersión entre CI, scripts Windows y ejecución local. `quality_gate.bat` sigue existiendo para operación en Windows, pero el contrato del repositorio se cierra con `scripts.gate_pr`.

- **2026-02-20 — Logging estructurado JSONL con `correlation_id` — Vigente**  
  Las operaciones relevantes dejan rastro auditable en `logs/seguimiento.log`, `logs/error_operativo.log` y `logs/crash.log`, manteniendo compatibilidad con `logs/crashes.log`.

- **2026-02-20 — Documentación mínima contractual concentrada en `docs/` — Vigente**  
  Se conserva sólo la documentación necesaria para ejecutar, probar, diagnosticar y auditar. Los documentos duplicados, históricos o de marketing se eliminan o se degradan a compatibilidad explícita cuando un contrato aún los necesita.

- **2026-02-25 — Preferencias y onboarding desacoplados por puertos — Vigente**  
  La UI no persiste estado directamente: depende de casos de uso (`ObtenerEstadoOnboarding`, `GuardarIdiomaUI`, `GuardarPreferenciaInicioMaximizado`, etc.) y de repositorios definidos en aplicación.

- **2026-03-01 — Reglas puras fuera de `MainWindow` — Vigente**  
  La lógica reusable de filtrado, validación y derivación de estado se mueve a dominio/aplicación o a módulos puros de presentación. `MainWindow` queda como orquestador de estado y wiring.

- **2026-03-01 — Fallback headless para preferencias sin romper arquitectura — Vigente**  
  Cuando `QSettings` no está disponible en ciertos entornos de prueba, la infraestructura resuelve un adaptador alternativo sin contaminar dominio ni aplicación con detalles de PySide.

- **2026-03-02 — Arranque UI seguro respecto a hilos Qt — Vigente**  
  La creación y el cierre de `SplashWindow`/`MainWindow` se fuerzan al hilo principal; el worker de arranque queda limitado a trabajo no UI. Esto reduce cierres silenciosos y warnings por cruces de hilo.

- **2026-03-02 — Datetimes ISO normalizados en reporting — Vigente**  
  El parsing de timestamps se centraliza para evitar operaciones entre valores naive y aware en reportes y sincronización.

- **2026-03-07 — Dataset de pendientes con fuente única de verdad — Vigente**  
  La UI consume un estado derivado único para contadores, filas visibles, ocultas y mensajes de contexto. Se evita duplicar derivaciones en distintos handlers.

- **2026-03-07 — Estado de acciones de `MainWindow` resuelto por función pura — Vigente**  
  Los botones y acciones relevantes leen un resolver de presentación puro con entrada/salida explícita. Esto baja complejidad, evita contradicciones entre helpers y hace más fácil testear regresiones.

- **2026-03-07 — Post-confirmación de solicitudes desacoplada de la vista — Vigente**  
  El cálculo del estado posterior a confirmar una solicitud deja de vivir repartido en la ventana y se expresa en contratos puros que la UI aplica.

- **2026-03-08 — Contratos de toast estabilizados con helpers de test — Vigente**  
  La API visible de notificaciones se protege con tests puros y helpers compartidos para evitar regresiones de firma o wiring sin inflar boilerplate.

- **2026-03-09 — Harness de pytest separado para runs core y UI — Vigente**  
  Los runs `not ui` desactivan plugins Qt y preservan el contrato “sin PySide en core”; las suites UI mantienen `pytest-qt` cuando corresponde. Esto evita falsos fallos de infraestructura durante el gate.

## Criterio para añadir nuevas decisiones

Añade una entrada sólo si cumple las cuatro condiciones:

1. afecta al runtime, a la arquitectura, al gate o a la trazabilidad;
2. sigue vigente después del cambio;
3. puede respaldarse con código, tests o documentación concreta;
4. ahorra discusiones futuras sobre por qué el sistema está montado así.

Si una nota no cumple ese umbral, no debe vivir aquí.
