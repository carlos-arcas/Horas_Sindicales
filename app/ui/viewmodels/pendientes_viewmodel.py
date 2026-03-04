from dataclasses import dataclass


@dataclass(slots=True)
class PendienteSolicitudViewModel:
    """
    ViewModel para solicitudes pendientes en UI.
    """

    id: int
    fecha: str
    horas: str
    descripcion: str
