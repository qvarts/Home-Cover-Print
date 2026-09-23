"""Home Cover Print designer for jewel-case and cassette inserts.

The editor uses millimetres as the graphics-scene coordinate system so that
on-screen layout stays aligned with physical PDF and print output.
"""

from src.icon import create_application_icon
from src.window import MainWindow

__all__ = ["MainWindow", "create_application_icon"]
