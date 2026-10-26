"""Shared PyQt6 visual theme for the IOAA sky trainer."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QWidget

NIGHT_BACKGROUND = "#050000"
NIGHT_SURFACE = "#0d0000"
NIGHT_FIELD = "#160000"
NIGHT_BORDER = "#5a0000"
NIGHT_TEXT = "#ff0000"
NIGHT_MUTED = "#a80000"
NIGHT_ACTIVE = "#360000"
NIGHT_SELECTED = "#700000"

LIGHT_BACKGROUND = "#f4f7fb"
LIGHT_SURFACE = "#ffffff"
LIGHT_FIELD = "#f8fafc"
LIGHT_BORDER = "#d7dee8"
LIGHT_TEXT = "#172033"
LIGHT_MUTED = "#647084"
LIGHT_ACCENT = "#2867c7"
LIGHT_ACCENT_HOVER = "#1f58ad"
LIGHT_SELECTED = "#e7effc"


def night_mode_enabled(widget: QWidget | None) -> bool:
    """Return whether the window containing *widget* is using observing mode."""
    if widget is None:
        return False
    current: QWidget | None = widget
    while current is not None:
        value = current.property("ioaaNightMode")
        if value is not None:
            return bool(value)
        current = current.parentWidget()
    app = QApplication.instance()
    return bool(app.property("ioaaNightMode")) if app is not None else False


def _light_stylesheet() -> str:
    return f"""
    QWidget {{
        background: {LIGHT_BACKGROUND};
        color: {LIGHT_TEXT};
        font-size: 13px;
    }}
    QMainWindow, QDialog {{ background: {LIGHT_BACKGROUND}; }}
    QLabel {{ background: transparent; selection-background-color: transparent; }}
    QLabel#Title {{ font-size: 24px; font-weight: 700; letter-spacing: -0.2px; }}
    QLabel#PageTitle {{ font-size: 21px; font-weight: 700; }}
    QLabel#SectionTitle {{ font-size: 15px; font-weight: 700; }}
    QLabel#QuestionText {{ font-weight: 400; }}
    QLabel#HeroTitle {{ font-size: 29px; font-weight: 750; }}
    QLabel#Eyebrow {{ color: {LIGHT_ACCENT}; font-size: 11px; font-weight: 800; letter-spacing: 1.2px; }}
    QLabel#AccentLabel {{ color: {LIGHT_ACCENT}; font-size: 12px; font-weight: 700; }}
    QLabel#Muted {{ color: {LIGHT_MUTED}; }}
    QLabel#Status {{
        color: {LIGHT_MUTED}; background: {LIGHT_SURFACE};
        border: 1px solid {LIGHT_BORDER}; border-radius: 8px; padding: 8px 10px;
    }}
    QFrame#AppHeader {{ background: {LIGHT_SURFACE}; border-bottom: 1px solid {LIGHT_BORDER}; }}
    QFrame#Sidebar {{ background: {LIGHT_SURFACE}; border: 1px solid {LIGHT_BORDER}; border-radius: 12px; }}
    QFrame#ContextNav {{ background: transparent; border: 0; }}
    QFrame#HeroCard {{ background: #eef5ff; border: 1px solid #cbdcf7; border-radius: 14px; }}
    QFrame#HomeCard, QFrame#Card, QGroupBox {{
        background: {LIGHT_SURFACE}; border: 1px solid {LIGHT_BORDER};
        border-radius: 11px;
    }}
    QGroupBox {{ margin-top: 12px; padding: 12px; font-weight: 600; }}
    QGroupBox::title {{
        subcontrol-origin: margin; left: 12px; padding: 0 5px;
        background: {LIGHT_SURFACE}; color: {LIGHT_TEXT};
    }}
    QPushButton {{
        background: {LIGHT_SURFACE}; border: 1px solid {LIGHT_BORDER};
        border-radius: 7px; padding: 8px 12px; min-height: 18px;
    }}
    QPushButton[compact="true"] {{ padding: 6px 10px; min-height: 16px; }}
    QPushButton:hover {{ border-color: #9cabc0; background: #f8fbff; }}
    QPushButton:pressed {{ background: #edf2f8; }}
    QPushButton:disabled {{ color: #a3acba; background: #f1f3f6; }}
    QPushButton[primary="true"] {{
        color: white; background: {LIGHT_ACCENT}; border-color: {LIGHT_ACCENT}; font-weight: 600;
    }}
    QPushButton[primary="true"]:hover {{ background: {LIGHT_ACCENT_HOVER}; }}
    QPushButton[homeAction="true"] {{ min-width: 120px; padding: 9px 14px; }}
    QPushButton[flatNav="true"] {{
        text-align: left; background: transparent; border: 0; padding: 10px 12px;
        color: {LIGHT_MUTED};
    }}
    QPushButton[flatNav="true"]:hover {{ background: #edf2f9; color: {LIGHT_TEXT}; }}
    QPushButton[flatNav="true"]:checked {{
        background: {LIGHT_SELECTED}; color: {LIGHT_ACCENT}; font-weight: 700;
    }}
    QFrame#SegmentedControl {{
        background: #edf2f8; border: 1px solid {LIGHT_BORDER}; border-radius: 9px;
    }}
    QPushButton[segment="true"] {{
        background: transparent; border: 0; border-radius: 7px; padding: 7px 10px;
        color: {LIGHT_MUTED}; font-weight: 600;
    }}
    QPushButton[segment="true"]:hover {{ background: #f8fbff; color: {LIGHT_TEXT}; }}
    QPushButton[segment="true"]:checked {{
        background: {LIGHT_SURFACE}; color: {LIGHT_ACCENT};
        border: 1px solid {LIGHT_BORDER}; font-weight: 700;
    }}
    QLineEdit, QComboBox, QDateEdit, QTimeEdit, QDoubleSpinBox, QSpinBox, QTextEdit, QPlainTextEdit {{
        background: {LIGHT_FIELD}; border: 1px solid {LIGHT_BORDER};
        border-radius: 7px; padding: 7px 9px; selection-background-color: {LIGHT_ACCENT};
    }}
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {LIGHT_ACCENT}; }}
    QLineEdit:disabled, QComboBox:disabled {{ background: #eef1f5; color: #9ba5b3; }}
    QComboBox::drop-down {{ border: 0; width: 24px; }}
    QTabWidget::pane {{ border: 1px solid {LIGHT_BORDER}; border-radius: 9px; background: {LIGHT_SURFACE}; }}
    QTabBar::tab {{
        background: transparent; color: {LIGHT_MUTED}; padding: 9px 14px;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{ color: {LIGHT_ACCENT}; border-bottom-color: {LIGHT_ACCENT}; font-weight: 700; }}
    QScrollArea {{ border: 0; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{
        background: transparent; width: 8px; margin: 3px 1px;
    }}
    QScrollBar::handle:vertical {{
        background: #c2cad6; min-height: 38px; border-radius: 3px; margin: 1px;
    }}
    QScrollBar::handle:vertical:hover {{ background: #929fb0; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: transparent; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QScrollBar:horizontal {{
        background: transparent; height: 8px; margin: 1px 3px;
    }}
    QScrollBar::handle:horizontal {{
        background: #c2cad6; min-width: 38px; border-radius: 3px; margin: 1px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: #929fb0; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: transparent; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
    QSlider::groove:horizontal {{ height: 5px; background: #dce3ec; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {LIGHT_ACCENT}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ width: 16px; margin: -6px 0; background: white; border: 2px solid {LIGHT_ACCENT}; border-radius: 8px; }}
    QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid #9aa7b7; background: white; }}
    QCheckBox::indicator:checked {{ background: {LIGHT_ACCENT}; border-color: {LIGHT_ACCENT}; }}
    QToolBar {{ background: transparent; border: 0; spacing: 1px; padding: 0; }}
    QToolBar#MapToolbar {{ background: transparent; border: 0; spacing: 1px; padding: 0; }}
    QToolButton {{ background: transparent; color: {LIGHT_TEXT}; border: 1px solid transparent; border-radius: 6px; padding: 3px; }}
    QToolButton:hover {{ background: #edf2f9; border-color: {LIGHT_BORDER}; }}
    QToolBar#MapToolbar QToolButton {{ min-width: 22px; min-height: 22px; max-width: 24px; max-height: 24px; padding: 1px; }}
    QToolTip {{ background: #172033; color: white; border: 0; padding: 5px; }}
    QStatusBar {{ background: {LIGHT_SURFACE}; border-top: 1px solid {LIGHT_BORDER}; }}
    """


def _night_stylesheet() -> str:
    return f"""
    QWidget {{ background: {NIGHT_BACKGROUND}; color: {NIGHT_TEXT}; font-size: 13px; }}
    QMainWindow, QDialog {{ background: {NIGHT_BACKGROUND}; }}
    QLabel {{ background: transparent; selection-background-color: transparent; }}
    QLabel#Title {{ font-size: 24px; font-weight: 700; }}
    QLabel#PageTitle {{ font-size: 21px; font-weight: 700; }}
    QLabel#SectionTitle {{ font-size: 15px; font-weight: 700; }}
    QLabel#QuestionText {{ font-weight: 400; }}
    QLabel#HeroTitle {{ font-size: 29px; font-weight: 750; }}
    QLabel#Eyebrow {{ color: {NIGHT_TEXT}; font-size: 11px; font-weight: 800; letter-spacing: 1.2px; }}
    QLabel#AccentLabel {{ color: {NIGHT_TEXT}; font-size: 12px; font-weight: 700; }}
    QLabel#Muted {{ color: {NIGHT_MUTED}; }}
    QLabel#Status {{
        color: {NIGHT_TEXT}; background: {NIGHT_SURFACE};
        border: 1px solid {NIGHT_BORDER}; border-radius: 8px; padding: 8px 10px;
    }}
    QFrame#AppHeader {{ background: {NIGHT_SURFACE}; border-bottom: 1px solid {NIGHT_BORDER}; }}
    QFrame#Sidebar {{ background: {NIGHT_SURFACE}; border: 1px solid {NIGHT_BORDER}; border-radius: 12px; }}
    QFrame#ContextNav {{ background: transparent; border: 0; }}
    QFrame#HeroCard {{ background: {NIGHT_SURFACE}; border: 1px solid {NIGHT_BORDER}; border-radius: 14px; }}
    QFrame#HomeCard, QFrame#Card, QGroupBox {{ background: {NIGHT_SURFACE}; border: 1px solid {NIGHT_BORDER}; border-radius: 11px; }}
    QGroupBox {{ margin-top: 12px; padding: 12px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 5px; background: {NIGHT_SURFACE}; color: {NIGHT_TEXT}; }}
    QPushButton {{
        background: {NIGHT_SURFACE}; color: {NIGHT_TEXT}; border: 1px solid {NIGHT_BORDER};
        border-radius: 7px; padding: 8px 12px; min-height: 18px;
    }}
    QPushButton[compact="true"] {{ padding: 6px 10px; min-height: 16px; }}
    QPushButton:hover {{ background: {NIGHT_ACTIVE}; }}
    QPushButton:pressed {{ background: {NIGHT_SELECTED}; }}
    QPushButton:disabled {{ color: {NIGHT_MUTED}; background: {NIGHT_BACKGROUND}; }}
    QPushButton[primary="true"] {{ background: {NIGHT_SELECTED}; border-color: {NIGHT_TEXT}; color: {NIGHT_TEXT}; font-weight: 700; }}
    QPushButton[homeAction="true"] {{ min-width: 120px; padding: 9px 14px; }}
    QPushButton[flatNav="true"] {{ text-align: left; background: transparent; border: 0; padding: 10px 12px; color: {NIGHT_MUTED}; }}
    QPushButton[flatNav="true"]:hover {{ background: {NIGHT_ACTIVE}; color: {NIGHT_TEXT}; }}
    QPushButton[flatNav="true"]:checked {{ background: {NIGHT_SELECTED}; color: {NIGHT_TEXT}; font-weight: 700; }}
    QFrame#SegmentedControl {{ background: {NIGHT_FIELD}; border: 1px solid {NIGHT_BORDER}; border-radius: 9px; }}
    QPushButton[segment="true"] {{
        background: transparent; border: 0; border-radius: 7px; padding: 7px 10px;
        color: {NIGHT_MUTED}; font-weight: 600;
    }}
    QPushButton[segment="true"]:hover {{ background: {NIGHT_ACTIVE}; color: {NIGHT_TEXT}; }}
    QPushButton[segment="true"]:checked {{
        background: {NIGHT_SELECTED}; color: {NIGHT_TEXT}; border: 1px solid {NIGHT_BORDER}; font-weight: 700;
    }}
    QLineEdit, QComboBox, QDateEdit, QTimeEdit, QDoubleSpinBox, QSpinBox, QTextEdit, QPlainTextEdit {{
        background: {NIGHT_FIELD}; color: {NIGHT_TEXT}; border: 1px solid {NIGHT_BORDER};
        border-radius: 7px; padding: 7px 9px; selection-background-color: {NIGHT_SELECTED};
    }}
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {NIGHT_TEXT}; }}
    QLineEdit:disabled, QComboBox:disabled {{ background: {NIGHT_BACKGROUND}; color: {NIGHT_MUTED}; }}
    QComboBox QAbstractItemView {{ background: {NIGHT_FIELD}; color: {NIGHT_TEXT}; selection-background-color: {NIGHT_SELECTED}; }}
    QTabWidget::pane {{ border: 1px solid {NIGHT_BORDER}; border-radius: 9px; background: {NIGHT_SURFACE}; }}
    QTabBar::tab {{ background: transparent; color: {NIGHT_MUTED}; padding: 9px 14px; border-bottom: 2px solid transparent; }}
    QTabBar::tab:selected {{ color: {NIGHT_TEXT}; border-bottom-color: {NIGHT_TEXT}; font-weight: 700; }}
    QScrollArea {{ border: 0; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 3px 1px; }}
    QScrollBar::handle:vertical {{ background: {NIGHT_BORDER}; min-height: 38px; border-radius: 3px; margin: 1px; }}
    QScrollBar::handle:vertical:hover {{ background: {NIGHT_TEXT}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: transparent; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 1px 3px; }}
    QScrollBar::handle:horizontal {{ background: {NIGHT_BORDER}; min-width: 38px; border-radius: 3px; margin: 1px; }}
    QScrollBar::handle:horizontal:hover {{ background: {NIGHT_TEXT}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: transparent; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
    QSlider::groove:horizontal {{ height: 5px; background: {NIGHT_BORDER}; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {NIGHT_TEXT}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ width: 16px; margin: -6px 0; background: {NIGHT_BACKGROUND}; border: 2px solid {NIGHT_TEXT}; border-radius: 8px; }}
    QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid {NIGHT_BORDER}; background: {NIGHT_BACKGROUND}; }}
    QCheckBox::indicator:checked {{ background: {NIGHT_TEXT}; border-color: {NIGHT_TEXT}; }}
    QToolBar {{ background: transparent; border: 0; spacing: 1px; padding: 0; }}
    QToolBar#MapToolbar {{ background: transparent; border: 0; spacing: 1px; padding: 0; }}
    QToolButton {{ background: transparent; color: {NIGHT_TEXT}; border: 1px solid transparent; border-radius: 6px; padding: 3px; }}
    QToolBar#MapToolbar QToolButton {{ min-width: 22px; min-height: 22px; max-width: 48px; max-height: 24px; padding: 1px 4px; }}
    QToolButton:hover {{ background: {NIGHT_ACTIVE}; border-color: {NIGHT_BORDER}; }}
    QToolTip {{ background: {NIGHT_FIELD}; color: {NIGHT_TEXT}; border: 1px solid {NIGHT_BORDER}; padding: 5px; }}
    QStatusBar {{ background: {NIGHT_SURFACE}; border-top: 1px solid {NIGHT_BORDER}; }}
    """


def apply_night_theme(window: QWidget, enabled: bool) -> None:
    """Apply the modern light or red-only observing theme to the Qt process."""
    enabled = bool(enabled)
    window.setProperty("ioaaNightMode", enabled)
    app = QApplication.instance()
    if app is not None:
        app.setProperty("ioaaNightMode", enabled)
        app.setStyleSheet(_night_stylesheet() if enabled else _light_stylesheet())
    refresh_widget_theme(window)


def refresh_widget_theme(widget: QWidget) -> None:
    """Ask custom widgets to refresh colours after a theme change."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
    for child in widget.findChildren(QWidget):
        refresh = getattr(child, "refresh_theme", None)
        if callable(refresh):
            refresh()
        child.style().unpolish(child)
        child.style().polish(child)
        child.update()
