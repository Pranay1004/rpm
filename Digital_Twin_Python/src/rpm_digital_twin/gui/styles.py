"""
Professional PyQt6 stylesheet for RPM Digital Twin.
Provides dark theme with accent colors suitable for scientific applications.
"""

STYLESHEET = """
QMainWindow {
    background-color: #1a1a1a;
    color: #ffffff;
}

QWidget {
    background-color: #1a1a1a;
    color: #ffffff;
}

QGroupBox {
    color: #ffffff;
    border: 2px solid #0d7377;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

QPushButton {
    background-color: #0d7377;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 11px;
}

QPushButton:hover {
    background-color: #14919b;
}

QPushButton:pressed {
    background-color: #0a5460;
}

QPushButton:disabled {
    background-color: #555555;
    color: #999999;
}

QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #0d7377;
    border-radius: 3px;
    padding: 5px;
}

QLineEdit:focus {
    border: 2px solid #14919b;
}

QSpinBox, QDoubleSpinBox {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #0d7377;
    border-radius: 3px;
    padding: 5px;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #0d7377;
}

QComboBox {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #0d7377;
    border-radius: 3px;
    padding: 5px;
}

QComboBox:drop-down {
    border-left: 1px solid #0d7377;
}

QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    color: #ffffff;
    selection-background-color: #0d7377;
}

QSlider::groove:horizontal {
    background-color: #333333;
    height: 8px;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background-color: #0d7377;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #14919b;
}

QTableWidget, QTableView {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #0d7377;
    gridline-color: #3a3a3a;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: #0d7377;
}

QHeaderView::section {
    background-color: #1f4f56;
    color: #ffffff;
    padding: 5px;
    border: 1px solid #0d7377;
}

QScrollBar:vertical {
    background-color: #2a2a2a;
    width: 12px;
}

QScrollBar::handle:vertical {
    background-color: #0d7377;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background-color: #14919b;
}

QScrollBar:horizontal {
    background-color: #2a2a2a;
    height: 12px;
}

QScrollBar::handle:horizontal {
    background-color: #0d7377;
    border-radius: 6px;
}

QLabel {
    color: #ffffff;
}

QMenu {
    background-color: #2a2a2a;
    color: #ffffff;
    border: 1px solid #0d7377;
}

QMenu::item:selected {
    background-color: #0d7377;
}

QStatusBar {
    background-color: #1f4f56;
    color: #ffffff;
    border-top: 1px solid #0d7377;
}

QTabBar::tab {
    background-color: #1f4f56;
    color: #ffffff;
    padding: 6px 20px;
    border: 1px solid #0d7377;
}

QTabBar::tab:selected {
    background-color: #0d7377;
    border-bottom: 2px solid #14919b;
}

QTabBar::tab:hover {
    background-color: #14919b;
}

QToolTip {
    background-color: #0d7377;
    color: #ffffff;
    border: 1px solid #14919b;
    border-radius: 3px;
    padding: 3px;
}

QCheckBox {
    color: #ffffff;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QCheckBox::indicator:unchecked {
    background-color: #2a2a2a;
    border: 1px solid #0d7377;
}

QCheckBox::indicator:checked {
    background-color: #0d7377;
    border: 1px solid #0d7377;
}

QRadioButton {
    color: #ffffff;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
}

QRadioButton::indicator:unchecked {
    background-color: #2a2a2a;
    border: 1px solid #0d7377;
    border-radius: 9px;
}

QRadioButton::indicator:checked {
    background-color: #0d7377;
    border: 1px solid #0d7377;
    border-radius: 9px;
}

/* Accent colors for status indicators */
.statusOK {
    color: #2ecc71;
}

.statusWarning {
    color: #f39c12;
}

.statusError {
    color: #e74c3c;
}

.statusInfo {
    color: #3498db;
}
"""
