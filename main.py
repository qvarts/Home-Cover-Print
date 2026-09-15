"""Entry point for the CD jewel-case cover designer."""

from __future__ import annotations

import sys

from PySide6 import QtWidgets

from src.icon import create_application_icon
from src.window import MainWindow


def main() -> int:
    """Run the desktop application."""
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CD Cover Print")
    app.setApplicationDisplayName("CD Cover Print")
    app.setOrganizationName("Qvart")
    app.setWindowIcon(create_application_icon())
    window = MainWindow()
    window.setWindowIcon(app.windowIcon())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
