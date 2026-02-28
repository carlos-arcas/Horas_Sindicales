# Transición de naming: español canónico sin ruptura

## Objetivo
Establecer una ruta de migración evolutiva para eliminar la mezcla español/inglés sin renombrado masivo y sin romper imports existentes.

## Regla de transición vigente
1. **No se renombra legacy en bloque** durante esta fase.
2. **`app/` sigue siendo la fuente real temporal**.
3. Todo módulo nuevo debe vivir bajo los paquetes canónicos en español:
   - `dominio/`
   - `aplicacion/`
   - `infraestructura/`
   - `presentacion/`
4. Los paquetes canónicos actúan como puente de compatibilidad:
   - reexportan (`from app... import *`) o envuelven comportamiento legacy cuando sea necesario.
5. En imports nuevos (código nuevo o refactor localizado), preferir rutas canónicas en español.

## Auditoría automática de deuda
Script oficial: `scripts/auditar_naming.py`.

Genera:
- `logs/naming_report.json`
- `logs/naming_report.md`

Cobertura del análisis:
- archivos Python de `app/` con tokens en inglés en la ruta,
- símbolos públicos (`class`, `def`, `async def`) con tokens en inglés,
- ranking Top 20 por archivo según densidad de tokens en inglés.

Uso recomendado:

```bash
python scripts/auditar_naming.py --umbral-offenders 0
```

> El estado PASS/FAIL depende del umbral (`--umbral-offenders`).

## Guardarraíl de regresión en tests
Test oficial: `tests/test_naming_debt_guard.py`.

Comportamiento:
- ejecuta el análisis en memoria (sin escribir archivos),
- compara offenders actuales contra baseline en `.config/naming_baseline.json`,
- falla solo cuando aparecen offenders nuevos.

## Cómo actualizar baseline conscientemente
Solo cuando la deuda nueva sea intencional y esté justificada:

1. Ejecutar auditoría para revisar impactos.
2. Actualizar `.config/naming_baseline.json` incorporando únicamente los offenders nuevos necesarios.
3. Documentar en el PR:
   - motivo técnico,
   - plan de remediación,
   - alcance y riesgo.
4. Evitar crecimiento silencioso de baseline: mantenerla mínima.

## Criterio en PRs
- Si un PR agrega código nuevo, debe usar imports y paquetes canónicos en español.
- Si toca legacy, evitar renombrados masivos colaterales.
- Si aumenta naming debt, el PR debe incluir justificación y actualización explícita de baseline.
