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

"""Graphics view for drag-and-drop, clipboard paste, and keyboard nudging."""

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from src.geometry import arrow_nudge_delta
from src.items import BackgroundImageItem, CoverImageItem, CoverTextItem

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}


class CoverGraphicsView(QtWidgets.QGraphicsView):
    """Graphics view with clipboard paste, drag-and-drop, snapping, and zoom."""

    WHEEL_ZOOM_STEP = 1.2
    DEFAULT_MIN_ZOOM = 0.05
    MAX_ZOOM = 50.0

    imageDropped = QtCore.Signal(str)
    imagePasted = QtCore.Signal(QtGui.QPixmap)
    deleteRequested = QtCore.Signal()
    nudgeRequested = QtCore.Signal(int, int)

    def __init__(self, scene: QtWidgets.QGraphicsScene) -> None:
        super().__init__(scene)
        self.setAcceptDrops(True)
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
        self.snap_to_grid = True
        # The lower bound is raised to the initial fit zoom once the window
        # is shown, so the user can never zoom out past the startup view.
        self.min_zoom = self.DEFAULT_MIN_ZOOM
        self.max_zoom = self.MAX_ZOOM

    def set_min_zoom(self, value: float) -> None:
        """Raise the minimum zoom to a value such as the startup fit scale."""
        if value <= 0:
            return
        self.min_zoom = value
        if self.transform().m11() < value:
            self.zoom_at(value / self.transform().m11())

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in IMAGE_SUFFIXES:
                self.imageDropped.emit(url.toLocalFile())
                event.acceptProposedAction()
                return
        event.ignore()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle clipboard actions and keyboard movement of selected artwork."""
        if event.key() == QtCore.Qt.Key.Key_Delete:
            self.deleteRequested.emit()
            event.accept()
            return
        if self._try_nudge_selected(event):
            return
        if event.matches(QtGui.QKeySequence.StandardKey.Paste):
            clipboard = QtWidgets.QApplication.clipboard()
            if clipboard is not None and clipboard.mimeData().hasImage():
                self.imagePasted.emit(QtGui.QPixmap.fromImage(clipboard.image()))
                event.accept()
                return
        super().keyPressEvent(event)

    def _try_nudge_selected(self, event: QtGui.QKeyEvent) -> bool:
        """Nudge the first editable selection, or emit a request if none is found."""
        delta = arrow_nudge_delta(event)
        if delta is None:
            return False
        dx, dy = delta
        selected = next(
            (
                item
                for item in self.scene().selectedItems()
                if isinstance(item, (CoverTextItem, CoverImageItem, BackgroundImageItem))
            ),
            None,
        )
        if selected is not None:
            scene = self.scene()
            scene.suppress_snap = True
            try:
                selected.setPos(selected.pos() + QtCore.QPointF(dx, dy))
            finally:
                scene.suppress_snap = False
            selected.setSelected(True)
            event.accept()
            return True
        self.nudgeRequested.emit(int(dx), int(dy))
        event.accept()
        return True

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Keep keyboard focus on the canvas after selecting an item."""
        self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """Zoom around the cursor while Ctrl is held, otherwise scroll normally."""
        if not event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        self.zoom_at(self.WHEEL_ZOOM_STEP ** (delta / 120.0))
        event.accept()

    def zoom_at(self, factor: float) -> None:
        """Scale the view by a factor, anchored under the mouse and clamped."""
        current = self.transform().m11()
        if current <= 0:
            return
        target = max(self.min_zoom, min(self.max_zoom, current * factor))
        if target == current:
            return
        previous_anchor = self.transformationAnchor()
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.scale(target / current, target / current)
        self.setTransformationAnchor(previous_anchor)

