from dataclasses import dataclass


@dataclass(slots=True)
class SolicitudViewModel:
    """
    Representación de una solicitud preparada para la UI.
    No depende de DTO ni de Qt.
    """

    id: int
    fecha: str
    horas: str
    estado: str
    descripcion: str
