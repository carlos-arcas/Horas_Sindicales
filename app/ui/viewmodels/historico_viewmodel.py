from dataclasses import dataclass


@dataclass(slots=True)
class HistoricoSolicitudViewModel:
    """
    ViewModel de solicitud para tabla de histórico.
    """

    id: int
    fecha: str
    horas: str
    estado: str
