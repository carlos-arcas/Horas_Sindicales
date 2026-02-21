from __future__ import annotations

from PySide6.QtWidgets import QApplication

COLOR_PRIMARY = "#D1001F"
COLOR_PRIMARY_DARK = "#A00018"
COLOR_ACCENT = "#111111"
COLOR_BACKGROUND = "#F7F7F8"
COLOR_CARD = "#FFFFFF"
COLOR_BORDER = "#E2E2E2"
COLOR_SUCCESS = "#1F7A3A"
COLOR_WARNING = "#C27A00"
COLOR_ERROR = "#B00020"


def build_stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {COLOR_BACKGROUND};
    color: {COLOR_ACCENT};
    font-size: 13px;
}}
QMainWindow, QScrollArea, QTabWidget::pane {{
    background-color: {COLOR_BACKGROUND};
    border: none;
}}
QFrame[card="true"], QFrame[role="card"], QWidget[role="card"] {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}
QLineEdit, QPlainTextEdit, QTextEdit, QDateEdit, QTimeEdit, QComboBox, QSpinBox {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 8px;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QDateEdit:focus, QTimeEdit:focus, QComboBox:focus {{
    border-color: {COLOR_PRIMARY};
}}
QPushButton {{
    background-color: {COLOR_CARD};
    color: {COLOR_ACCENT};
    border: 1px solid #B8B8B8;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: #F1F1F2;
}}
QPushButton[variant="primary"], QPushButton[role="primary"] {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: 1px solid {COLOR_PRIMARY};
}}
QPushButton[variant="primary"]:hover, QPushButton[role="primary"]:hover {{
    background-color: {COLOR_PRIMARY_DARK};
    border-color: {COLOR_PRIMARY_DARK};
}}
QPushButton[variant="secondary"], QPushButton[role="secondary"] {{
    background-color: {COLOR_CARD};
    color: {COLOR_ACCENT};
    border: 1px solid {COLOR_ACCENT};
}}
QPushButton[variant="secondary"]:hover, QPushButton[role="secondary"]:hover {{
    background-color: #F3F3F3;
}}
QPushButton[variant="ghost"] {{
    background-color: transparent;
    border: 1px solid transparent;
}}
QPushButton[variant="ghost"]:hover {{
    background-color: #EFEFEF;
}}
QFrame#sidebar QPushButton[active="true"] {{
    background-color: #F9E5E8;
    color: {COLOR_PRIMARY};
    border-color: #F0C4CB;
    font-weight: 600;
}}
QLabel[role="secondary"] {{
    color: #5F6368;
}}
QLabel[role="title"] {{
    font-size: 18px;
    font-weight: 700;
}}
QLabel[role="subtitle"] {{
    color: #4F555C;
    font-size: 12px;
}}
QLabel[role="cardTitle"] {{
    font-size: 14px;
    font-weight: 700;
}}
QFrame#header_shell {{
    background: {COLOR_CARD};
    border-bottom: 1px solid {COLOR_BORDER};
}}
QLabel#header_state_badge {{
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#header_state_badge[tone="neutral"] {{
    background: #F0F0F0;
    color: #404040;
}}
QLabel#header_state_badge[tone="warning"] {{
    background: #FFEED2;
    color: #7A4D00;
}}
QLabel#header_state_badge[tone="success"] {{
    background: #DDF4E3;
    color: {COLOR_SUCCESS};
}}
QLabel#header_state_badge[tone="error"] {{
    background: #FADCE2;
    color: {COLOR_ERROR};
}}
QHeaderView::section {{
    background-color: #F2F2F3;
    border: none;
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 8px;
    font-weight: 600;
}}
QTableView {{
    background: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    gridline-color: #EEEEEE;
    selection-background-color: #F9E5E8;
    selection-color: {COLOR_ACCENT};
}}
"""


def aplicar_tema(app: QApplication) -> None:
    app.setStyleSheet(build_stylesheet())
