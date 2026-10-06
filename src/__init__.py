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

"""Home Cover Print designer for jewel-case and cassette inserts.

The editor uses millimetres as the graphics-scene coordinate system so that
on-screen layout stays aligned with physical PDF and print output.
"""

from src.icon import create_application_icon
from src.window import MainWindow

__all__ = ["MainWindow", "create_application_icon"]

