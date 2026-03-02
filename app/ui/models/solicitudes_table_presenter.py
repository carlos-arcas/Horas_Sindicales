from __future__ import annotations

from dataclasses import dataclass

from app.domain.time_utils import minutes_to_hhmm


STATUS_BADGES: dict[str, str] = {
    "CONFIRMED": "✅ Confirmada",
    "PENDING": "🕒 Pendiente",
    "DELETED": "🗑 Eliminada",
}


@dataclass(frozen=True)
class SolicitudDisplayEntrada:
    """Entrada pura para calcular el texto de una celda de solicitudes.

    Reglas de contrato:
    - `column` representa el índice visual actual del modelo (incluyendo columnas dinámicas).
    - `show_estado` y `show_delegada` controlan el desplazamiento de columnas dinámicas.
    - `is_deleted` tiene precedencia para columna Estado: si es `True`, se muestra
      estado eliminado aunque `generated` también sea `True`.
    - Valores vacíos en `desde`/`hasta` usan placeholder `-`.
    - Valores vacíos en `notas` se renderizan como `—`.
    """

    column: int
    fecha_pedida: str
    desde: str | None
    hasta: str | None
    completo: bool
    horas: float
    notas: str | None
    generated: bool
    show_estado: bool
    show_delegada: bool
    persona_nombre: str | None = None
    is_deleted: bool = False


@dataclass(frozen=True)
class SolicitudDisplaySalida:
    """Salida tipada del presenter para facilitar mapeo desde el modelo Qt."""

    texto_display: str | None


def _format_minutes(minutes: int) -> str:
    if minutes < 0:
        return f"-{minutes_to_hhmm(abs(minutes))}"
    return minutes_to_hhmm(minutes)


def _status_text(*, generated: bool, is_deleted: bool) -> str:
    """Devuelve badge textual de estado con precedencia:

    1) Eliminada (`is_deleted=True`)
    2) Confirmada (`generated=True`)
    3) Pendiente
    """

    if is_deleted:
        return STATUS_BADGES["DELETED"]
    return STATUS_BADGES["CONFIRMED"] if generated else STATUS_BADGES["PENDING"]




def resumen_nota(notas: str | None) -> str:
    texto = (notas or '').strip()
    if not texto:
        return '—'
    return f'🔒 {len(texto)}'

def _base_column_text(entrada: SolicitudDisplayEntrada) -> str | None:
    if entrada.column == 0:
        return entrada.fecha_pedida
    if entrada.column == 1:
        return entrada.desde or "-"
    if entrada.column == 2:
        return entrada.hasta or "-"
    if entrada.column == 3:
        return "Sí" if entrada.completo else "No"
    if entrada.column == 4:
        return _format_minutes(int(round(entrada.horas * 60)))
    if entrada.column == 5:
        return resumen_nota(entrada.notas)
    return None


def _dynamic_column_text(entrada: SolicitudDisplayEntrada) -> str | None:
    dynamic_column = 6
    if entrada.show_estado and entrada.column == dynamic_column:
        return _status_text(generated=entrada.generated, is_deleted=entrada.is_deleted)
    if entrada.show_estado:
        dynamic_column += 1

    if entrada.show_delegada and entrada.column == dynamic_column:
        return entrada.persona_nombre or "—"
    return None


def build_display(entrada: SolicitudDisplayEntrada) -> SolicitudDisplaySalida:
    """Construye el texto final de la celda.

    Se evalúan primero columnas base fijas (0..5). Si no coincide, se evalúan
    columnas dinámicas (`Estado`, `Delegada`) respetando visibilidad y orden.
    """

    texto_base = _base_column_text(entrada)
    if texto_base is not None:
        return SolicitudDisplaySalida(texto_display=texto_base)
    return SolicitudDisplaySalida(texto_display=_dynamic_column_text(entrada))
