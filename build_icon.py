"""Generate the Windows icon used by PyInstaller."""

from pathlib import Path

from PySide6 import QtWidgets

from src.icon import create_application_icon


app = QtWidgets.QApplication([])
icon = create_application_icon()
output = Path(__file__).with_name("home_cover_print.ico")
if not icon.pixmap(64, 64).save(str(output), "ICO"):
    raise RuntimeError(f"Could not write application icon: {output}")
