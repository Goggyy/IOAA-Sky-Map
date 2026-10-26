"""Help and About content for Sky Map Trainer."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from .theme import night_mode_enabled

HELP_FILE = Path(__file__).with_name("HELP.md")


class HelpPage(QWidget):
    """Embeddable help page used by the main application shell."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("ioaaNightMode", night_mode_enabled(parent))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)
        title = QLabel("Help & About")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        try:
            browser.setMarkdown(HELP_FILE.read_text(encoding="utf-8"))
        except OSError as error:
            browser.setPlainText(f"Could not load {HELP_FILE.name}: {error}")
        layout.addWidget(browser, 1)


class HelpWindow(QDialog):
    """Standalone help dialog retained for direct/legacy callers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Help & About — Sky Map Trainer")
        self.resize(720, 650)
        self.setMinimumSize(520, 420)
        self.setProperty("ioaaNightMode", night_mode_enabled(parent))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(HelpPage(self), 1)
        row = QHBoxLayout()
        row.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        layout.addLayout(row)
