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

"""Entry point for the Home Cover Print designer."""

from __future__ import annotations

import sys

from PySide6 import QtWidgets

from src.version import __version__
from src.icon import create_application_icon
from src.window import MainWindow


def main() -> int:
    """Run the desktop application."""
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Home Cover Print")
    app.setOrganizationName("Qvart")
    app.setWindowIcon(create_application_icon())
    
    window = MainWindow()
    window.setWindowTitle(f"Home Cover Print v{__version__}")
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

