from __future__ import annotations

COLORS = {
    "primary": "#2D6CDF",
    "danger": "#D64545",
    "success": "#2E9E5B",
    "warning": "#E6A23C",
    "background": "#F5F7FA",
    "surface": "#FFFFFF",
    "text_primary": "#1F2937",
    "text_secondary": "#6B7280",
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
}

RADIUS = {
    "sm": 4,
    "md": 8,
    "lg": 12,
}


def build_stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text_primary']};
    font-size: 13px;
}}

QLabel {{
    color: {COLORS['text_primary']};
}}

QFrame {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['background']};
    border-radius: {RADIUS['md']}px;
    padding: {SPACING['sm']}px;
}}

QPushButton {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['text_secondary']};
    border-radius: {RADIUS['sm']}px;
    padding: {SPACING['sm']}px {SPACING['lg']}px;
}}

QPushButton:hover {{
    border-color: {COLORS['primary']};
}}

QPushButton:pressed {{
    background-color: {COLORS['background']};
}}

QPushButton[variant="primary"] {{
    background-color: {COLORS['primary']};
    color: {COLORS['surface']};
    border: 1px solid {COLORS['primary']};
}}

QPushButton[variant="primary"]:hover {{
    background-color: {COLORS['success']};
    border-color: {COLORS['success']};
}}

QLineEdit,
QComboBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['text_secondary']};
    border-radius: {RADIUS['sm']}px;
    padding: {SPACING['sm']}px;
}}

QLineEdit:focus,
QComboBox:focus {{
    border: 1px solid {COLORS['primary']};
}}

QTableView {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    gridline-color: {COLORS['background']};
    border: 1px solid {COLORS['text_secondary']};
    border-radius: {RADIUS['sm']}px;
    selection-background-color: {COLORS['primary']};
    selection-color: {COLORS['surface']};
}}
"""

