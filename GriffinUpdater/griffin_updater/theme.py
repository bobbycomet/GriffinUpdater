"""
Griffin Dark Theme.

Structurally borrows Steam's dark-UI conventions (flat panels, low-contrast
chrome, a single bright accent color reserved for interactive/positive
elements) but with Griffin's own palette: charcoal/graphite base with a
warm gold-bronze accent (a nod to a griffin's beak/talons) and a cool
steel-blue secondary for informational bits.
"""
from __future__ import annotations

BG_DARKEST = "#12141a"
BG_PANEL = "#191c24"
BG_PANEL_ALT = "#1f2330"
BG_RAISED = "#262b3a"
BORDER = "#30364a"
TEXT_PRIMARY = "#e7e9ef"
TEXT_SECONDARY = "#9aa0b4"
TEXT_DISABLED = "#5c6178"
ACCENT_GOLD = "#d4a13d"
ACCENT_GOLD_HOVER = "#e6b558"
ACCENT_GOLD_PRESSED = "#b98a2e"
ACCENT_BLUE = "#5b8fd4"
DANGER = "#d4573d"
SUCCESS = "#5cb87a"

STYLESHEET = f"""
* {{
    font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

QMainWindow, QDialog {{
    background-color: {BG_DARKEST};
}}

QWidget#Sidebar {{
    background-color: {BG_PANEL};
    border-right: 1px solid {BORDER};
}}

QLabel {{
    background: transparent;
}}

QLabel#HeaderLabel {{
    font-size: 18px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QLabel#SubtleLabel {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QToolBar {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
    spacing: 6px;
    padding: 6px;
}}

QStatusBar {{
    background-color: {BG_PANEL};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER};
}}

QTableWidget, QListWidget, QTreeWidget {{
    background-color: {BG_PANEL};
    alternate-background-color: {BG_PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    gridline-color: {BORDER};
    selection-background-color: {ACCENT_GOLD};
    selection-color: #14161c;
}}

QHeaderView::section {{
    background-color: {BG_PANEL_ALT};
    color: {TEXT_SECONDARY};
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
    font-weight: 600;
}}

QTableWidget::item, QListWidget::item {{
    padding: 6px;
}}

QPushButton {{
    background-color: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 14px;
    color: {TEXT_PRIMARY};
}}
QPushButton:hover {{
    background-color: #2e3446;
    border-color: {ACCENT_GOLD};
}}
QPushButton:pressed {{
    background-color: #1c2030;
}}
QPushButton:disabled {{
    color: {TEXT_DISABLED};
    border-color: {BORDER};
}}

QPushButton#PrimaryButton {{
    background-color: {ACCENT_GOLD};
    border: 1px solid {ACCENT_GOLD};
    color: #14161c;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{
    background-color: {ACCENT_GOLD_HOVER};
}}
QPushButton#PrimaryButton:pressed {{
    background-color: {ACCENT_GOLD_PRESSED};
}}

QPushButton#DangerButton {{
    background-color: transparent;
    border: 1px solid {DANGER};
    color: {DANGER};
}}
QPushButton#DangerButton:hover {{
    background-color: rgba(212, 87, 61, 0.15);
}}

QLineEdit, QComboBox, QSpinBox, QTimeEdit, QPlainTextEdit, QTextEdit {{
    background-color: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 8px;
    selection-background-color: {ACCENT_GOLD};
    selection-color: #14161c;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus {{
    border-color: {ACCENT_GOLD};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}

QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid {BORDER};
    background-color: {BG_RAISED};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT_GOLD};
    border-color: {ACCENT_GOLD};
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background-color: {BG_PANEL};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {BG_PANEL};
    padding: 8px 16px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    color: {TEXT_SECONDARY};
}}
QTabBar::tab:selected {{
    background-color: {BG_RAISED};
    color: {TEXT_PRIMARY};
    border-color: {ACCENT_GOLD};
}}

QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BG_RAISED};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT_GOLD};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QMenu {{
    background-color: {BG_RAISED};
    border: 1px solid {BORDER};
}}
QMenu::item {{
    padding: 6px 20px;
}}
QMenu::item:selected {{
    background-color: {ACCENT_GOLD};
    color: #14161c;
}}

QToolTip {{
    background-color: {BG_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT_GOLD};
    padding: 4px;
}}

QProgressBar {{
    background-color: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: 5px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ACCENT_GOLD};
    border-radius: 5px;
}}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 12px;
    font-weight: 600;
    color: {TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}
"""
