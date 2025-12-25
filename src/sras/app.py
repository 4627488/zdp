"""Application entry points for SRAS."""

from __future__ import annotations

import sys
from typing import Sequence

from PySide6.QtWidgets import QApplication

from .gui.main_window import MainWindow


APP_NAME = "SRAS 2025"


def create_qt_app(argv: Sequence[str] | None = None) -> QApplication:
    """Create the QApplication instance with common metadata."""

    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("SRAS")
    app.setOrganizationDomain("sras.local")
    return app


def run(argv: Sequence[str] | None = None) -> int:
    """Launch the PySide6 UI shell."""

    app = create_qt_app(argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
