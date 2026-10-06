
"""Load the application icon from the bundled image asset."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6 import QtGui


def _icon_path() -> Path:
    """Return the ICO next to the project root, including a frozen EXE."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "home_cover_print.ico"
    return Path(__file__).resolve().parent.parent / "home_cover_print.ico"


def create_application_icon() -> QtGui.QIcon:
    """Load the window and taskbar icon from the bundled ICO."""
    icon = QtGui.QIcon(str(_icon_path()))
    if icon.isNull():
        raise RuntimeError(f"Could not load application icon: {_icon_path()}")
    return icon

