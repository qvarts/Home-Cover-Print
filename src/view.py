"""Graphics view for drag-and-drop, clipboard paste, and keyboard nudging."""

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from src.geometry import arrow_nudge_delta
from src.items import BackgroundImageItem, CoverImageItem, CoverTextItem

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}


class CoverGraphicsView(QtWidgets.QGraphicsView):
    """Graphics view with clipboard paste, drag-and-drop, and snapping."""

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
