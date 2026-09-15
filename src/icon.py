"""Application icon drawn as vector primitives so no image asset is required."""

from PySide6 import QtCore, QtGui


def create_application_icon() -> QtGui.QIcon:
    """Create a simple CD-disc icon used as the window and taskbar icon."""
    pixmap = QtGui.QPixmap(64, 64)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setBrush(QtGui.QColor("#263746"))
    painter.setPen(QtGui.QPen(QtGui.QColor("#17232d"), 2))
    painter.drawEllipse(QtCore.QRectF(5, 5, 54, 54))
    painter.setBrush(QtGui.QColor("#79c2d0"))
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.drawEllipse(QtCore.QRectF(25, 25, 14, 14))
    painter.setBrush(QtGui.QColor("#f4f7f8"))
    painter.drawEllipse(QtCore.QRectF(29, 29, 6, 6))
    painter.setPen(QtGui.QPen(QtGui.QColor("#79c2d0"), 2))
    painter.drawArc(QtCore.QRectF(13, 13, 38, 38), 25 * 16, 75 * 16)
    painter.end()
    return QtGui.QIcon(pixmap)
