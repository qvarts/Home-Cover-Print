# Copyright (C) 2026 Vitaliy Kolobanov <vitaliy.kolobanov@yahoo.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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

