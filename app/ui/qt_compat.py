from __future__ import annotations

try:
    from PySide6.QtCore import QDate, QEvent, QItemSelectionModel, QObject, QSettings, QThread, QTime, QTimer, Qt
    # `QKeyEvent` vive en QtGui en PySide6 (no en QtCore); importarlo aquí evita NameError en eventFilter.
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDateEdit,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFrame,
        QHeaderView,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QTableView,
        QTextEdit,
        QTimeEdit,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except (ImportError, ModuleNotFoundError):  # pragma: no cover - habilita import en entornos CI sin Qt
    class _QtFallbackBase:
        pass

    QDate = QEvent = QItemSelectionModel = QObject = QSettings = QThread = QTime = QTimer = Qt = object
    QKeyEvent = object
    QCheckBox = QComboBox = QDateEdit = QDialog = QFileDialog = QHBoxLayout = QLabel = object
    QMainWindow = type("QMainWindow", (_QtFallbackBase,), {})
    QMessageBox = QPushButton = QApplication = QAbstractItemView = QPlainTextEdit = object
    QFrame = QHeaderView = QProgressBar = QSizePolicy = QSplitter = QTableView = QTimeEdit = object
    QVBoxLayout = QWidget = QDialogButtonBox = QTextEdit = QTreeWidget = QTreeWidgetItem = object
