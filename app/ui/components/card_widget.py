from __future__ import annotations

"""Card widget basado en PySide6 con carga diferida y fallback seguro.

Este módulo intenta importar ``PySide6`` al cargarlo. Si ``PySide6`` (o una
dependencia nativa como ``libEGL``) no está disponible, la importación del
módulo **no** falla: se exponen sustitutos mínimos compatibles para
``QLabel``, ``QVBoxLayout`` y ``QWidget`` que lanzan ``RuntimeError`` al
instanciarse, indicando que la versión GUI requiere PySide6.
"""

try:
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
except ImportError:
    _PYSIDE6_MISSING_ERROR = RuntimeError(
        "PySide6 es obligatorio para la versión GUI de CardWidget. "
        "Instala PySide6 y sus dependencias del sistema (p. ej., libEGL)."
    )

    class QWidget:  # type: ignore[no-redef]
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise _PYSIDE6_MISSING_ERROR

    class QLabel:  # type: ignore[no-redef]
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise _PYSIDE6_MISSING_ERROR

    class QVBoxLayout:  # type: ignore[no-redef]
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise _PYSIDE6_MISSING_ERROR


class CardWidget(QWidget):
    def __init__(self, titulo: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.title_label = QLabel(titulo)
        self.title_label.setProperty("role", "cardTitle")
        self.title_label.setVisible(bool(titulo))
        layout.addWidget(self.title_label)

    def set_titulo(self, titulo: str) -> None:
        self.title_label.setText(titulo)
        self.title_label.setVisible(bool(titulo))
