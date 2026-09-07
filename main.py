"""CD jewel case cover designer.

The application uses millimetres as the coordinate system of its graphics
scene.  This keeps on-screen editing and physical PDF/print output aligned.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtPrintSupport, QtWidgets


MM_PER_INCH = 25.4
PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0
BLEED_MM = 3.0


@dataclass(frozen=True)
class CoverSpec:
    """Physical dimensions and guide lines for one cover format."""

    key: str
    label: str
    width_mm: float
    height_mm: float
    guides: tuple[float, ...] = ()


COVER_SPECS = (
    CoverSpec("front", "Jewel Case (Front) — 120 × 120 mm", 120.0, 120.0),
    CoverSpec("booklet", "Jewel Case (Booklet) — 240 × 120 mm", 240.0, 120.0, (120.0,)),
    CoverSpec("back", "Jewel Case (Back) — 150 × 118 mm", 150.0, 118.0, (6.0, 144.0)),
    CoverSpec("slim", "Slim Case (Front) — 122 × 122 mm", 122.0, 122.0),
    CoverSpec(
        "slim_booklet_plain",
        "Slim Case (Booklet) — 244 × 122 mm",
        244.0,
        122.0,
        (122.0,),
    ),
    CoverSpec(
        "slim_booklet",
        "Slim Case (Folded) — 262 × 122 mm",
        262.0,
        122.0,
        (4.0, 140.0),
    ),
)

ACTIVE_COVER_WIDTH_MM = 120.0
ACTIVE_COVER_HEIGHT_MM = 120.0


def create_application_icon() -> QtGui.QIcon:
    """Create a simple vector-style CD icon without external image assets."""
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


def cover_width() -> float:
    """Return the active cover width in millimetres."""
    return ACTIVE_COVER_WIDTH_MM


def cover_height() -> float:
    """Return the active cover height in millimetres."""
    return ACTIVE_COVER_HEIGHT_MM


def mm_to_points(value: float) -> float:
    """Convert millimetres to PDF points."""
    return value * 72.0 / MM_PER_INCH


class GridItem(QtWidgets.QGraphicsItem):
    """Non-selectable 5 mm editing grid."""

    def __init__(self, rect: QtCore.QRectF, step: float = 5.0) -> None:
        super().__init__()
        self._rect = rect
        self._step = step
        self.setZValue(-1000)
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)

    def boundingRect(self) -> QtCore.QRectF:
        return self._rect

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        del option, widget
        painter.save()
        painter.setPen(QtGui.QPen(QtGui.QColor(225, 230, 235), 0))
        x = self._rect.left()
        while x <= self._rect.right():
            painter.drawLine(QtCore.QPointF(x, self._rect.top()), QtCore.QPointF(x, self._rect.bottom()))
            x += self._step
        y = self._rect.top()
        while y <= self._rect.bottom():
            painter.drawLine(QtCore.QPointF(self._rect.left(), y), QtCore.QPointF(self._rect.right(), y))
            y += self._step
        painter.restore()


class CoverFrameItem(QtWidgets.QGraphicsItem):
    """Draws the 120 mm cover, bleed boundary, and crop marks."""

    def __init__(self) -> None:
        super().__init__()
        self._width = cover_width()
        self._height = cover_height()
        self._guides: tuple[float, ...] = ()
        self.show_guides = True
        self.fold_guide_opacity = 210
        # Keep the cut line visible over artwork while leaving resize handles
        # above it during image editing.
        self.setZValue(100000)
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(
            -BLEED_MM,
            -BLEED_MM,
            self._width + 2 * BLEED_MM,
            self._height + 2 * BLEED_MM,
        )

    def set_spec(self, spec: CoverSpec) -> None:
        """Update the visible cut and fold guides for a cover format."""
        self.prepareGeometryChange()
        self._width = spec.width_mm
        self._height = spec.height_mm
        self._guides = spec.guides
        self.update()

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        del option, widget
        painter.save()
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        cut_line_color = QtGui.QColor(127, 139, 152, 150)
        painter.setPen(QtGui.QPen(cut_line_color, 0.25, QtCore.Qt.PenStyle.DashLine))
        painter.drawRect(QtCore.QRectF(0, 0, self._width, self._height))
        if self.show_guides:
            painter.setPen(
                QtGui.QPen(
                    QtGui.QColor(127, 139, 152, self.fold_guide_opacity),
                    0.25,
                    QtCore.Qt.PenStyle.DotLine,
                )
            )
            for guide_x in self._guides:
                painter.drawLine(QtCore.QPointF(guide_x, 0), QtCore.QPointF(guide_x, self._height))
        mark = BLEED_MM
        painter.setPen(QtGui.QPen(cut_line_color, 0.25, QtCore.Qt.PenStyle.DashLine))
        for x, y, dx, dy in (
            (0, 0, -mark, 0), (0, 0, 0, -mark),
            (self._width, 0, mark, 0), (self._width, 0, 0, -mark),
            (0, self._height, -mark, 0), (0, self._height, 0, mark),
            (self._width, self._height, mark, 0),
            (self._width, self._height, 0, mark),
        ):
            painter.drawLine(QtCore.QPointF(x, y), QtCore.QPointF(x + dx, y + dy))
        painter.restore()


class CoverTextItem(QtWidgets.QGraphicsTextItem):
    """Movable, selectable, in-place editable text element."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextEditorInteraction)
        self.setDefaultTextColor(QtGui.QColor("#111820"))
        self.setZValue(10)
        font = QtGui.QFont("Arial", 10)
        self.setFont(font)
        self.setTextWidth(120.0)
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.SelectionType.Document)
        char_format = QtGui.QTextCharFormat()
        char_format.setFont(font)
        block_format = QtGui.QTextBlockFormat()
        block_format.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        block_format.setLineHeight(
            100.0,
            QtGui.QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
        )
        cursor.setBlockFormat(block_format)
        cursor.setCharFormat(char_format)
        self.setTextCursor(cursor)
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.setTransformOriginPoint(self.boundingRect().center())

    def set_text_color(self, color: QtGui.QColor) -> None:
        """Apply a color to all existing and subsequently edited text."""
        self.setDefaultTextColor(color)
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QtGui.QTextCursor.SelectionType.Document)
        format_ = QtGui.QTextCharFormat()
        format_.setForeground(color)
        cursor.setCharFormat(format_)
        self.setTextCursor(cursor)
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def itemChange(
        self,
        change: QtWidgets.QGraphicsItem.GraphicsItemChange,
        value: object,
    ) -> object:
        """Snap normal text movement to the five millimetre grid."""
        if (
            change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and self.scene() is not None
            and getattr(self.scene(), "snap_to_guides", False)
        ):
            position = value
            if isinstance(position, QtCore.QPointF):
                snap = getattr(self.scene(), "snap_position", None)
                if callable(snap):
                    return snap(self, position)
        return super().itemChange(change, value)

    def set_text_font(self, font: QtGui.QFont) -> None:
        """Apply a font to selected text or to the complete text block."""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QtGui.QTextCursor.SelectionType.Document)
        format_ = QtGui.QTextCharFormat()
        format_.setFont(font)
        cursor.mergeCharFormat(format_)
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.setTransformOriginPoint(self.boundingRect().center())


class ImageHandleItem(QtWidgets.QGraphicsObject):
    """Independent Qt graphics handle with an exact visible hit area."""

    def __init__(self, owner: "CoverImageItem", kind: str) -> None:
        super().__init__()
        self.owner = owner
        self.kind = kind
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        self.setZValue(100)
        self._rect = QtCore.QRectF(-5.0, -5.0, 10.0, 10.0)

    def boundingRect(self) -> QtCore.QRectF:
        return self._rect

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        del option, widget
        if not self.owner.isSelected():
            return
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor("#cbd0d4"), 0.0))
        painter.setBrush(QtGui.QColor("#f7f8f9"))
        if self.kind == "rotate":
            painter.drawEllipse(self._rect)
        else:
            painter.drawRect(self._rect)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        handle_center = self.mapToScene(QtCore.QPointF(0, 0))
        self.owner.begin_handle_drag(self.kind, event.scenePos(), handle_center, event.modifiers())
        event.accept()

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.owner.update_handle_drag(event.scenePos(), event.modifiers())
        event.accept()

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.owner.end_handle_drag()
        event.accept()


class CoverImageItem(QtWidgets.QGraphicsPixmapItem):
    """Image element with a stable base scale and aspect-ratio preservation."""

    def __init__(self, pixmap: QtGui.QPixmap) -> None:
        # Keep the scene lightweight: 1200 px corresponds to 10 px/mm at 300 DPI.
        normalized = pixmap.scaled(
            1200,
            1200,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        super().__init__(normalized)
        # Start with the largest dimension aligned to the 120 mm cover.
        self.base_scale = max(cover_width(), cover_height()) / max(1, normalized.width(), normalized.height())
        self.scale_x = self.base_scale
        self.scale_y = self.base_scale
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setTransformationMode(QtCore.Qt.TransformationMode.SmoothTransformation)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)
        self.setZValue(5)
        # The transform below already translates around the image center.
        # Keep Qt's implicit transform origin at (0, 0) to avoid applying
        # the center translation twice.
        self.setTransformOriginPoint(QtCore.QPointF(0, 0))
        self._rotation_angle = 0.0
        self._apply_transform()
        self.user_scale = 1.0
        self._mouse_mode: Optional[str] = None
        self._mouse_start_scene = QtCore.QPointF()
        self._mouse_start_scale = 1.0
        self._mouse_start_rotation = 0.0
        self._mouse_start_angle = 0.0
        self._resize_index = -1
        self._resize_anchor = QtCore.QPointF()
        self._resize_start_handle = QtCore.QPointF()
        self._resize_anchor_scene = QtCore.QPointF()
        self._resize_center_scene = QtCore.QPointF()
        self._resize_start_inverse = QtGui.QTransform()
        self._handle_press_offset = QtCore.QPointF()
        self._symmetric_resize = False
        self.lock_aspect_ratio = False
        self.skip_snap_once = False
        self._handles: list[ImageHandleItem] = []
        for index in range(8):
            self._handles.append(ImageHandleItem(self, str(index)))
        self._handles.append(ImageHandleItem(self, "rotate"))
        self._update_handle_positions()

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        """Paint the image and a thin native-style selection outline."""
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.save()
            rect = QtCore.QRectF(self.pixmap().rect())
            painter.setPen(QtGui.QPen(QtGui.QColor("#8e44ad"), 0.0))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            painter.restore()
    def itemChange(
        self,
        change: QtWidgets.QGraphicsItem.GraphicsItemChange,
        value: object,
    ) -> object:
        """Keep child handles synchronized with the owner's selection state."""
        if (
            change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and self.scene() is not None
            and getattr(self.scene(), "snap_to_guides", False)
            and self._mouse_mode is None
        ):
            position = value
            if isinstance(position, QtCore.QPointF):
                snap = getattr(self.scene(), "snap_position", None)
                if callable(snap):
                    value = snap(self, position)
        result = super().itemChange(change, value)
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            selected = bool(value)
            for handle_item in self._handles:
                handle_item.setVisible(selected)
        elif hasattr(self, "_handles") and change in (
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged,
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemTransformHasChanged,
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemRotationHasChanged,
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemZValueHasChanged,
        ):
            self._update_handle_positions()
        return result

    @staticmethod
    def _handle_centers(rect: QtCore.QRectF) -> tuple[QtCore.QPointF, ...]:
        """Return handles for corners and the four individual resize sides."""
        cx, cy = rect.center().x(), rect.center().y()
        return (
            QtCore.QPointF(rect.left(), rect.top()),
            QtCore.QPointF(cx, rect.top()),
            QtCore.QPointF(rect.right(), rect.top()),
            QtCore.QPointF(rect.right(), cy),
            QtCore.QPointF(rect.right(), rect.bottom()),
            QtCore.QPointF(cx, rect.bottom()),
            QtCore.QPointF(rect.left(), rect.bottom()),
            QtCore.QPointF(rect.left(), cy),
        )

    def boundingRect(self) -> QtCore.QRectF:
        """Return only the image bounds; handles have independent geometry."""
        rect = QtCore.QRectF(self.pixmap().rect())
        return rect

    def shape(self) -> QtGui.QPainterPath:
        """Use the image rectangle for selection; handles are separate items."""
        rect = QtCore.QRectF(self.pixmap().rect())
        path = QtGui.QPainterPath()
        path.addRect(rect)
        return path

    def _update_handle_positions(self) -> None:
        """Place child handles in local coordinates around the current image."""
        rect = QtCore.QRectF(self.pixmap().rect())
        centers = self._handle_centers(rect)
        for index, center in enumerate(centers):
            handle = self._handles[index]
            handle.setZValue(self.zValue() + 1000.0)
            if handle.parentItem() is None:
                handle.setPos(self.mapToScene(center))
                handle.setTransform(QtGui.QTransform())
                handle.setRotation(self._rotation_angle)
            else:
                handle.setPos(center)
                handle.setTransform(
                    QtGui.QTransform.fromScale(
                        1.0 / max(self.scale_x, 0.01),
                        1.0 / max(self.scale_y, 0.01),
                    )
                )
                handle.setRotation(-self._rotation_angle)
            handle.setVisible(self.isSelected())
        rotate_point = QtCore.QPointF(rect.center().x(), rect.top() - 12.0 / max(self.scale_y, 0.01))
        self._handles[8].setZValue(self.zValue() + 1000.0)
        if self._handles[8].parentItem() is None:
            self._handles[8].setPos(self.mapToScene(rotate_point))
            self._handles[8].setTransform(QtGui.QTransform())
            self._handles[8].setRotation(self._rotation_angle)
        else:
            self._handles[8].setPos(rotate_point)
            self._handles[8].setTransform(
                QtGui.QTransform.fromScale(
                    1.0 / max(self.scale_x, 0.01),
                    1.0 / max(self.scale_y, 0.01),
                )
            )
            self._handles[8].setRotation(-self._rotation_angle)

    def _apply_transform(self, angle: Optional[float] = None) -> None:
        """Apply the image scale and rotation as one affine transform."""
        if angle is not None:
            self._rotation_angle = angle
        center = QtCore.QRectF(self.pixmap().rect()).center()
        radians = math.radians(self._rotation_angle)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        m11 = self.scale_x * cosine
        m12 = self.scale_x * sine
        m21 = -self.scale_y * sine
        m22 = self.scale_y * cosine
        # Keep the transformed item anchored at its local top-left.  The
        # caller positions that top-left in scene coordinates when inserting
        # the image, so the transformed center must be scaled, not preserved
        # at the original pixel coordinates.
        target_center_x = center.x() * self.scale_x
        target_center_y = center.y() * self.scale_y
        dx = target_center_x - m11 * center.x() - m21 * center.y()
        dy = target_center_y - m12 * center.x() - m22 * center.y()
        transform = QtGui.QTransform(m11, m12, m21, m22, dx, dy)
        self.setTransform(transform, combine=False)

    def rotation_angle(self) -> float:
        """Return the image rotation in degrees."""
        return self._rotation_angle

    def set_rotation(self, angle: float) -> None:
        """Set the image rotation without composing a second Qt transform."""
        self._apply_transform(angle)
        self._update_handle_positions()

    def detach_handles(self) -> None:
        """Promote handles to scene-level items for transform-independent geometry."""
        if self.scene() is None:
            return
        for handle in self._handles:
            handle.setParentItem(None)
            self.scene().addItem(handle)
        self._update_handle_positions()

    def begin_handle_drag(
        self,
        kind: str,
        scene_pos: QtCore.QPointF,
        handle_center: QtCore.QPointF,
        modifiers: QtCore.Qt.KeyboardModifiers,
    ) -> None:
        """Start a drag on a dedicated child handle without changing cursor position."""
        self._mouse_mode = kind if kind == "rotate" else ("resize", int(kind))
        self._handle_press_offset = scene_pos - handle_center
        self._symmetric_resize = bool(modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier)
        self._mouse_start_scene = scene_pos
        self._mouse_start_scale_x = self.scale_x
        self._mouse_start_scale_y = self.scale_y
        self._mouse_start_rotation = self._rotation_angle
        center = self.mapToScene(QtCore.QRectF(self.pixmap().rect()).center())
        self._mouse_start_angle = math.atan2(scene_pos.y() - center.y(), scene_pos.x() - center.x())
        if kind != "rotate":
            rect = QtCore.QRectF(self.pixmap().rect())
            handles = self._handle_centers(rect)
            index = int(kind)
            self._resize_start_handle = handles[index]
            self._resize_anchor = handles[(index + 4) % 8]
            self._resize_anchor_scene = self.mapToScene(self._resize_anchor)
            self._resize_center_scene = self.mapToScene(QtCore.QPointF(rect.center()))
            self._resize_start_inverse = self.sceneTransform().inverted()[0]
        self.setSelected(True)

    def update_handle_drag(
        self,
        scene_pos: QtCore.QPointF,
        modifiers: QtCore.Qt.KeyboardModifiers,
    ) -> None:
        """Forward a dedicated handle drag to the stable transform calculation."""
        if isinstance(self._mouse_mode, tuple):
            self._symmetric_resize = bool(modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier)
            aspect_locked = self.lock_aspect_ratio or bool(
                modifiers & QtCore.Qt.KeyboardModifier.ControlModifier
            )
        else:
            aspect_locked = False
        self._apply_handle_motion(scene_pos - self._handle_press_offset, aspect_locked)

    def end_handle_drag(self) -> None:
        """Finish a dedicated handle drag."""
        self._mouse_mode = None
        self._update_handle_positions()

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Start moving, resizing, or rotating from a generously sized handle zone."""
        rect = QtCore.QRectF(self.pixmap().rect())
        hit_radius = 4.0 / max(min(self.scale_x, self.scale_y), 0.01)
        distances = [QtCore.QLineF(event.pos(), point).length() for point in self._handle_centers(rect)]
        rotate_point = QtCore.QPointF(
            rect.center().x(),
            rect.top() - 12.0 / max(self.scale_y, 0.01),
        )
        if self.isSelected() and QtCore.QLineF(event.pos(), rotate_point).length() <= hit_radius:
            self._mouse_mode = "rotate"
        elif self.isSelected() and distances and min(distances) <= hit_radius:
            index = distances.index(min(distances))
            self._mouse_mode = ("resize", index)
            self._resize_index = index
            handles = self._handle_centers(rect)
            self._resize_start_handle = handles[index]
            anchor_index = (index + 4) % 8
            self._resize_anchor = handles[anchor_index]
            self._resize_anchor_scene = self.mapToScene(self._resize_anchor)
            self._resize_start_inverse = self.sceneTransform().inverted()[0]
        if self._mouse_mode:
            self._mouse_start_scene = event.scenePos()
            self._mouse_start_scale = self.scale()
            self._mouse_start_scale_x = self.scale_x
            self._mouse_start_scale_y = self.scale_y
            self._mouse_start_rotation = self._rotation_angle
            center = self.mapToScene(QtCore.QRectF(self.pixmap().rect()).center())
            self._mouse_start_angle = math.atan2(
                self._mouse_start_scene.y() - center.y(),
                self._mouse_start_scene.x() - center.x(),
            )
            self.setSelected(True)
            event.accept()
            return
        super().mousePressEvent(event)

    def _apply_handle_motion(self, scene_pos: QtCore.QPointF, aspect_locked: bool = False) -> None:
        """Apply a handle movement using the transform captured at mouse-down."""
        if isinstance(self._mouse_mode, tuple) and self._mouse_mode[0] == "resize":
            index = self._mouse_mode[1]
            scene_pos = self._snap_resize_position(scene_pos)
            # Convert the cursor with the transform captured at mouse-down.
            # Reusing the changing transform here causes visible resize jitter.
            current = self._resize_start_inverse.map(scene_pos)
            start = self._resize_start_handle
            anchor = self._resize_anchor
            width_denominator = max(1.0, abs(start.x() - anchor.x()))
            height_denominator = max(1.0, abs(start.y() - anchor.y()))
            scale_x = self._mouse_start_scale_x
            scale_y = self._mouse_start_scale_y
            if self._symmetric_resize:
                center = QtCore.QRectF(self.pixmap().rect()).center()
                start_center_distance_x = max(1.0, abs(start.x() - center.x()))
                start_center_distance_y = max(1.0, abs(start.y() - center.y()))
                if index in (0, 2, 4, 6):
                    scale_x *= max(0.05, min(20.0, abs(current.x() - center.x()) / start_center_distance_x))
                    scale_y *= max(0.05, min(20.0, abs(current.y() - center.y()) / start_center_distance_y))
                elif index in (1, 5):
                    scale_y *= max(0.05, min(20.0, abs(current.y() - center.y()) / start_center_distance_y))
                elif index in (3, 7):
                    scale_x *= max(0.05, min(20.0, abs(current.x() - center.x()) / start_center_distance_x))
            else:
                if index in (0, 6, 7):
                    scale_x *= max(0.05, min(20.0, abs(current.x() - anchor.x()) / width_denominator))
                elif index in (2, 3, 4):
                    scale_x *= max(0.05, min(20.0, abs(current.x() - anchor.x()) / width_denominator))
                if index in (0, 1, 2):
                    scale_y *= max(0.05, min(20.0, abs(current.y() - anchor.y()) / height_denominator))
                elif index in (4, 5, 6):
                    scale_y *= max(0.05, min(20.0, abs(current.y() - anchor.y()) / height_denominator))
            if aspect_locked:
                factor_x = scale_x / self._mouse_start_scale_x
                factor_y = scale_y / self._mouse_start_scale_y
                factor = max(factor_x, factor_y) if index in (0, 2, 4, 6) else (
                    factor_x if index in (3, 7) else factor_y
                )
                scale_x = self._mouse_start_scale_x * factor
                scale_y = self._mouse_start_scale_y * factor
            self.prepareGeometryChange()
            self.scale_x = scale_x
            self.scale_y = scale_y
            current_rotation = self._rotation_angle
            self._apply_transform(current_rotation)
            self._update_handle_positions()
            reference_scene = self._resize_center_scene if self._symmetric_resize else self._resize_anchor_scene
            reference_local = (
                QtCore.QRectF(self.pixmap().rect()).center()
                if self._symmetric_resize
                else anchor
            )
            # Recalculate the position from a zero parent position. Adding a
            # scene-space delta to pos() is incorrect when the item is rotated.
            self.setPos(0, 0)
            new_reference_scene = self.mapToScene(reference_local)
            parent = self.parentItem()
            if parent is None:
                target_parent = reference_scene
                current_parent = new_reference_scene
            else:
                target_parent = parent.mapFromScene(reference_scene)
                current_parent = parent.mapFromScene(new_reference_scene)
            self.setPos(target_parent - current_parent)
            self.scene().invalidate(self.sceneBoundingRect(), QtWidgets.QGraphicsScene.SceneLayer.AllLayers)
            return
        if self._mouse_mode == "rotate":
            center = self.mapToScene(QtCore.QRectF(self.pixmap().rect()).center())
            angle = math.atan2(scene_pos.y() - center.y(), scene_pos.x() - center.x())
            rotation = self._mouse_start_rotation + math.degrees(angle - self._mouse_start_angle)
            snapped_rotation = self._snap_rotation(rotation)
            self._apply_transform(snapped_rotation)
            if isinstance(self, BackgroundImageItem):
                normalized = snapped_rotation % 360.0
                self.rotation_preset = (
                    int(normalized)
                    if normalized in (0.0, 90.0, 180.0, 270.0)
                    else -1
                )
            self._update_handle_positions()
            self.scene().invalidate(self.sceneBoundingRect(), QtWidgets.QGraphicsScene.SceneLayer.AllLayers)
            self.update()
            return

    def _snap_resize_position(self, position: QtCore.QPointF) -> QtCore.QPointF:
        """Snap the resize cursor to the nearest main vertical and horizontal guide."""
        scene = self.scene()
        if scene is None or not getattr(scene, "snap_to_guides", False):
            return position
        guides_x, guides_y = getattr(scene, "snap_guides", ((), ()))

        def snap(value: float, guides: tuple[float, ...]) -> float:
            nearest = min(guides, key=lambda guide: abs(guide - value), default=value)
            return nearest if abs(nearest - value) <= 2.0 else value

        return QtCore.QPointF(snap(position.x(), guides_x), snap(position.y(), guides_y))

    def _snap_rotation(self, angle: float) -> float:
        """Snap rotation to the background rotation presets when close to one."""
        scene = self.scene()
        if scene is None or not getattr(scene, "snap_to_guides", False):
            return angle
        presets = (0.0, 90.0, 180.0, 270.0, 360.0)
        normalized = angle % 360.0
        nearest = min(presets, key=lambda preset: abs(preset - normalized))
        distance = abs(nearest - normalized)
        if distance > 5.0:
            return angle
        return angle + (nearest - normalized)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Move the image normally when no dedicated handle is active."""
        if self._mouse_mode:
            self._apply_handle_motion(event.scenePos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Finish a mouse manipulation."""
        if self._mouse_mode:
            event.accept()
            self._mouse_mode = None
            self.skip_snap_once = True
            self._resize_index = -1
            self.scene().invalidate(self.sceneBoundingRect(), QtWidgets.QGraphicsScene.SceneLayer.AllLayers)
            self.scene().update()
            self.update()
            return
        self._mouse_mode = None
        super().mouseReleaseEvent(event)

    def set_user_scale(self, value: float) -> None:
        """Set a relative scale while retaining the image aspect ratio."""
        self.prepareGeometryChange()
        self.user_scale = value
        self.scale_x = self.base_scale * value
        self.scale_y = self.base_scale * value
        self._apply_transform()
        self._update_handle_positions()


class BackgroundImageItem(CoverImageItem):
    """Background image with the same mouse resize and rotation handles as artwork."""

    def __init__(self, pixmap: QtGui.QPixmap) -> None:
        self.size_mode = "cover"
        self.rotation_preset = 0
        self.reference_scale_x = 1.0
        self.reference_scale_y = 1.0
        super().__init__(pixmap)
        self.setZValue(-500)
        self.setOpacity(1.0)
        self.apply_size_mode()

    def apply_size_mode(self, mode: Optional[str] = None) -> None:
        """Apply a CSS-like baseline size while preserving mouse-adjusted transforms."""
        if mode is not None:
            self.size_mode = mode
        width = max(1.0, float(self.pixmap().width()))
        height = max(1.0, float(self.pixmap().height()))
        if self.size_mode == "cover":
            scale_x = scale_y = max(cover_width() / width, cover_height() / height)
        elif self.size_mode == "contain":
            scale_x = scale_y = min(cover_width() / width, cover_height() / height)
        elif self.size_mode == "stretch":
            scale_x = cover_width() / width
            scale_y = cover_height() / height
        else:
            raise ValueError(f"Unsupported background size mode: {self.size_mode}")
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.reference_scale_x = scale_x
        self.reference_scale_y = scale_y
        self._apply_transform()
        self._update_handle_positions()

    def _apply_transform(self, angle: Optional[float] = None) -> None:
        """Apply the transform while keeping the background centred on the cover."""
        if angle is not None:
            self._rotation_angle = angle
        center = QtCore.QRectF(self.pixmap().rect()).center()
        radians = math.radians(self._rotation_angle)
        cosine, sine = math.cos(radians), math.sin(radians)
        m11 = self.scale_x * cosine
        m12 = self.scale_x * sine
        m21 = -self.scale_y * sine
        m22 = self.scale_y * cosine
        dx = cover_width() / 2 - m11 * center.x() - m21 * center.y()
        dy = cover_height() / 2 - m12 * center.x() - m22 * center.y()
        self.setTransform(QtGui.QTransform(m11, m12, m21, m22, dx, dy), combine=False)

    def set_rotation_preset(self, angle: int) -> None:
        """Set one of the supported background rotation presets."""
        self.rotation_preset = angle % 360
        self._rotation_angle = float(angle)
        self._apply_transform()
        self._update_handle_positions()


class CoverGraphicsView(QtWidgets.QGraphicsView):
    """Graphics view with standard clipboard paste, drag-and-drop, and snapping."""

    imageDropped = QtCore.Signal(str)
    imagePasted = QtCore.Signal(QtGui.QPixmap)
    deleteRequested = QtCore.Signal()

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
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
                self.imageDropped.emit(url.toLocalFile())
                event.acceptProposedAction()
                return
        event.ignore()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Paste an image from the system clipboard with Ctrl+V."""
        if event.key() == QtCore.Qt.Key.Key_Delete:
            self.deleteRequested.emit()
            event.accept()
            return
        if event.matches(QtGui.QKeySequence.StandardKey.Paste):
            clipboard = QtWidgets.QApplication.clipboard()
            if clipboard is not None and clipboard.mimeData().hasImage():
                self.imagePasted.emit(QtGui.QPixmap.fromImage(clipboard.image()))
                event.accept()
                return
        super().keyPressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Finish a drag without changing the position selected by the user."""
        super().mouseReleaseEvent(event)

    def drawForeground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        super().drawForeground(painter, rect)


class CoverRenderer:
    """Renders the cover scene to a precisely sized A4 PDF or printer page."""

    @staticmethod
    def render(
        scene: QtWidgets.QGraphicsScene,
        painter: QtGui.QPainter,
        page_rect: QtCore.QRectF,
        show_fold_guides: bool = False,
    ) -> None:
        """Render the active cover, optionally including subtle fold guides."""
        device = painter.device()
        if device is None:
            raise RuntimeError("The painter has no active paint device")
        dpi_x = device.logicalDpiX()
        dpi_y = device.logicalDpiY()
        if dpi_x <= 0 or dpi_y <= 0:
            raise RuntimeError("The paint device has invalid logical DPI")
        artwork_width = cover_width() + 2 * BLEED_MM
        artwork_height = cover_height() + 2 * BLEED_MM
        target_width = artwork_width * dpi_x / MM_PER_INCH
        target_height = artwork_height * dpi_y / MM_PER_INCH
        x = page_rect.x() + (page_rect.width() - target_width) / 2
        y = page_rect.y() + (page_rect.height() - target_height) / 2
        target = QtCore.QRectF(
            x, y, target_width, target_height
        )
        source = QtCore.QRectF(-BLEED_MM, -BLEED_MM, artwork_width, artwork_height)
        grid_items = [item for item in scene.items() if isinstance(item, GridItem)]
        frame_items = [item for item in scene.items() if isinstance(item, CoverFrameItem)]
        for item in grid_items:
            item.setVisible(False)
        previous_guide_states = [(item.show_guides, item.fold_guide_opacity) for item in frame_items]
        for item in frame_items:
            item.show_guides = show_fold_guides
            item.fold_guide_opacity = 110
        try:
            scene.render(painter, target, source, QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)
        finally:
            for item in grid_items:
                item.setVisible(True)
            for item, (previous_state, previous_opacity) in zip(frame_items, previous_guide_states):
                item.show_guides = previous_state
                item.fold_guide_opacity = previous_opacity


class MainWindow(QtWidgets.QMainWindow):
    """Main application window and controller for the cover editor."""

    MAX_IMAGE_PIXELS = 2400
    FILE_DIRECTORY_KEY = "last-file-directory"
    VIEW_MARGIN_MM = 12.0

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CD Cover Print")
        self.resize(1350, 860)
        self.cover_spec = COVER_SPECS[0]
        global ACTIVE_COVER_WIDTH_MM, ACTIVE_COVER_HEIGHT_MM
        ACTIVE_COVER_WIDTH_MM = self.cover_spec.width_mm
        ACTIVE_COVER_HEIGHT_MM = self.cover_spec.height_mm
        self.scene = QtWidgets.QGraphicsScene(
            -BLEED_MM,
            -BLEED_MM,
            cover_width() + 2 * BLEED_MM,
            cover_height() + 2 * BLEED_MM,
        )
        self.scene.snap_to_guides = True
        self.scene.snap_position = self._snap_item_position
        self.scene.snap_guides = self._build_snap_guides()
        self.grid_item = GridItem(self.scene.sceneRect())
        self.frame_item = CoverFrameItem()
        self.frame_item.set_spec(self.cover_spec)
        self.background_item: Optional[BackgroundImageItem] = None
        self.scene.addItem(self.grid_item)
        self.scene.addItem(self.frame_item)
        self.view = CoverGraphicsView(self.scene)
        self.view.imageDropped.connect(self.add_image_from_path)
        self.view.imagePasted.connect(self.add_image_from_pixmap)
        self.view.deleteRequested.connect(self.delete_selected)
        self.scene.selectionChanged.connect(self.update_controls)
        self.scene.focusItemChanged.connect(
            lambda _new_item, _old_item, _reason: self.update_controls()
        )
        self.scene.changed.connect(
            lambda _regions: QtCore.QTimer.singleShot(0, self.update_controls)
        )
        self._build_ui()
        QtCore.QTimer.singleShot(0, self._fit_scene_with_margin)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """Apply the fixed canvas zoom after the window has its final size."""
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._fit_scene_with_margin)

    def _build_ui(self) -> None:
        """Construct the sidebar and central canvas."""
        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.addWidget(self.view, 1)
        sidebar = QtWidgets.QWidget()
        sidebar.setFixedWidth(250)
        side = QtWidgets.QVBoxLayout(sidebar)

        side.addWidget(QtWidgets.QLabel("Cover type"))
        self.cover_type_combo = QtWidgets.QComboBox()
        for spec in COVER_SPECS:
            self.cover_type_combo.addItem(spec.label, spec.key)
        self.cover_type_combo.currentIndexChanged.connect(self.set_cover_type)
        side.addWidget(self.cover_type_combo)
        add_text = QtWidgets.QPushButton("Add Text")
        add_text.clicked.connect(self.add_text)
        add_image = QtWidgets.QPushButton("Add Image")
        add_image.clicked.connect(self.choose_image)
        add_background = QtWidgets.QPushButton("Add Background")
        add_background.clicked.connect(self.choose_background)
        preview_button = QtWidgets.QPushButton("Print Preview")
        preview_button.clicked.connect(self.preview_print)
        export_pdf = QtWidgets.QPushButton("Export PDF")
        export_pdf.clicked.connect(self.export_pdf)
        print_button = QtWidgets.QPushButton("Print")
        print_button.clicked.connect(self.print_cover)
        for button in (add_image, add_background, add_text, export_pdf, print_button, preview_button):
            side.addWidget(button)
        self.export_fold_guides_check = QtWidgets.QCheckBox(
            "Print fold lines"
        )
        self.export_fold_guides_check.setToolTip(
            "When enabled, fold lines are included in PDF export, printing, and print preview."
        )
        self.export_fold_guides_check.setChecked(True)
        side.addWidget(self.export_fold_guides_check)
        side.addSpacing(16)
        side.addWidget(QtWidgets.QLabel("Selected element"))
        form = QtWidgets.QFormLayout()
        self.x_spin = QtWidgets.QDoubleSpinBox()
        self.y_spin = QtWidgets.QDoubleSpinBox()
        for spin in (self.x_spin, self.y_spin):
            spin.setRange(-10000.0, 10000.0)
            spin.setDecimals(2)
            spin.setSuffix(" mm")
        self.x_spin.valueChanged.connect(self.move_selected)
        self.y_spin.valueChanged.connect(self.move_selected)
        form.addRow("X:", self.x_spin)
        form.addRow("Y:", self.y_spin)
        self.scale_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.scale_slider.setRange(10, 300)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.scale_selected)
        form.addRow("Scale:", self.scale_slider)
        self.rotation_spin = QtWidgets.QDoubleSpinBox()
        self.rotation_spin.setRange(-360.0, 360.0)
        self.rotation_spin.setDecimals(1)
        self.rotation_spin.setSuffix("°")
        self.rotation_spin.valueChanged.connect(self.rotate_selected)
        form.addRow("Rotation:", self.rotation_spin)
        side.addLayout(form)
        side.addSpacing(10)
        side.addWidget(QtWidgets.QLabel("Background size"))
        self.background_size_combo = QtWidgets.QComboBox()
        self.background_size_combo.addItem("Cover", "cover")
        self.background_size_combo.addItem("Contain", "contain")
        self.background_size_combo.addItem("100% x 100%", "stretch")
        self.background_size_combo.activated.connect(self.set_background_size_mode)
        side.addWidget(self.background_size_combo)
        side.addWidget(QtWidgets.QLabel("Background rotation"))
        self.background_rotation_combo = QtWidgets.QComboBox()
        for angle in (0, 90, 180, 270):
            self.background_rotation_combo.addItem(f"{angle}°", angle)
        self.background_rotation_combo.currentIndexChanged.connect(self.set_background_rotation)
        self.background_size_combo.setEnabled(False)
        self.background_rotation_combo.setEnabled(False)
        side.addWidget(self.background_rotation_combo)
        side.addSpacing(10)
        self.font_button = QtWidgets.QPushButton("Choose Font")
        self.font_button.clicked.connect(self.choose_font)
        side.addWidget(self.font_button)
        self.text_color_button = QtWidgets.QPushButton("Choose Text Color")
        self.text_color_button.clicked.connect(self.choose_text_color)
        side.addWidget(self.text_color_button)
        front = QtWidgets.QPushButton("Bring to Front")
        front.clicked.connect(lambda: self.change_layer(1))
        back = QtWidgets.QPushButton("Send to Back")
        back.clicked.connect(lambda: self.change_layer(-1))
        side.addWidget(front)
        side.addWidget(back)
        side.addSpacing(10)
        self.snap_check = QtWidgets.QCheckBox("Snap to guides")
        self.snap_check.setChecked(True)
        self.snap_check.toggled.connect(self.set_snap)
        side.addWidget(self.snap_check)
        self.aspect_check = QtWidgets.QCheckBox("Lock image proportions")
        self.aspect_check.toggled.connect(self.set_aspect_lock)
        side.addWidget(self.aspect_check)
        side.addStretch()
        copyright_label = QtWidgets.QLabel("Made by Qvart\nFree for personal use")
        copyright_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet("color: #6f7b86; padding-top: 8px;")
        side.addWidget(copyright_label)
        layout.addWidget(sidebar)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Select an image and use its handles to resize or rotate")

    def set_cover_type(self, index: int) -> None:
        """Switch the active physical cover format without deleting artwork."""
        global ACTIVE_COVER_WIDTH_MM, ACTIVE_COVER_HEIGHT_MM
        if not 0 <= index < len(COVER_SPECS):
            return
        spec = COVER_SPECS[index]
        self.cover_spec = spec
        ACTIVE_COVER_WIDTH_MM = spec.width_mm
        ACTIVE_COVER_HEIGHT_MM = spec.height_mm
        self.scene.setSceneRect(
            -BLEED_MM,
            -BLEED_MM,
            spec.width_mm + 2 * BLEED_MM,
            spec.height_mm + 2 * BLEED_MM,
        )
        self.grid_item.prepareGeometryChange()
        self.grid_item._rect = self.scene.sceneRect()
        self.grid_item.update()
        self.frame_item.set_spec(spec)
        self.scene.snap_guides = self._build_snap_guides()
        if self.background_item is not None:
            self.background_item.apply_size_mode()
        self._fit_scene_with_margin()
        self.view.viewport().update()
        self.statusBar().showMessage(f"Cover type: {spec.label}")

    def _fit_scene_with_margin(self) -> None:
        """Use one zoom for every cover while reserving the safe-area margin."""
        reference_width = max(spec.width_mm for spec in COVER_SPECS) + 2 * BLEED_MM
        reference_height = max(spec.height_mm for spec in COVER_SPECS) + 2 * BLEED_MM
        reference_rect = QtCore.QRectF(
            0.0,
            0.0,
            reference_width + 2 * self.VIEW_MARGIN_MM,
            reference_height + 2 * self.VIEW_MARGIN_MM,
        )
        self.view.fitInView(reference_rect, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.view.centerOn(self.scene.sceneRect().center())

    def _build_snap_guides(self) -> tuple[tuple[float, ...], tuple[float, ...]]:
        """Return vertical and horizontal snap guides in scene millimetres."""
        vertical = [-BLEED_MM, 0.0, cover_width() / 2.0, cover_width(), cover_width() + BLEED_MM]
        vertical += list(self.cover_spec.guides)
        horizontal = [-BLEED_MM, 0.0, cover_height() / 2.0, cover_height(), cover_height() + BLEED_MM]
        return tuple(sorted(set(vertical))), tuple(sorted(set(horizontal)))

    def _snap_item_position(
        self,
        item: QtWidgets.QGraphicsItem,
        position: QtCore.QPointF,
    ) -> QtCore.QPointF:
        """Snap item edges or centre to the nearest main guide."""
        if item.parentItem() is not None:
            return position
        current = item.pos()
        rect = item.sceneBoundingRect().translated(position - current)
        x_features = (rect.left(), rect.center().x(), rect.right())
        y_features = (rect.top(), rect.center().y(), rect.bottom())
        threshold = 2.0

        def correction(features: tuple[float, ...], guides: tuple[float, ...]) -> float:
            matches = [
                guide - feature
                for feature in features
                for guide in guides
                if abs(guide - feature) <= threshold
            ]
            return min(matches, key=abs) if matches else 0.0

        return QtCore.QPointF(
            position.x() + correction(x_features, self.scene.snap_guides[0]),
            position.y() + correction(y_features, self.scene.snap_guides[1]),
        )

    def selected_item(self) -> Optional[QtWidgets.QGraphicsItem]:
        """Return the first editable selected item."""
        focused = self.scene.focusItem()
        if isinstance(focused, (CoverTextItem, CoverImageItem, BackgroundImageItem)):
            return focused
        selected = self.scene.selectedItems()
        for item in selected:
            if isinstance(item, (CoverTextItem, CoverImageItem, BackgroundImageItem)):
                return item
        active_item = getattr(self, "_active_item", None)
        if active_item is not None and active_item.scene() is self.scene:
            return active_item
        return None

    def _file_dialog_directory(self) -> str:
        """Return the last directory used by any file dialog."""
        settings = QtCore.QSettings("CDCoverPrint", "CDCoverPrint")
        return str(settings.value(self.FILE_DIRECTORY_KEY, str(Path.home())))

    def _remember_file_path(self, path: str) -> None:
        """Remember the directory containing a successfully chosen file."""
        QtCore.QSettings("CDCoverPrint", "CDCoverPrint").setValue(
            self.FILE_DIRECTORY_KEY, str(Path(path).parent)
        )

    def _page_orientation(self) -> QtGui.QPageLayout.Orientation:
        """Choose A4 orientation so the active cover fits its printable width."""
        artwork_width = cover_width() + 2 * BLEED_MM
        artwork_height = cover_height() + 2 * BLEED_MM
        if artwork_width > PAGE_WIDTH_MM or (
            artwork_width > PAGE_HEIGHT_MM and artwork_width > artwork_height
        ):
            return QtGui.QPageLayout.Orientation.Landscape
        return QtGui.QPageLayout.Orientation.Portrait

    def add_text(self) -> None:
        """Insert a starter text item into the cover."""
        item = CoverTextItem("Album Title")
        self.scene.addItem(item)
        item.setPos(
            (cover_width() - item.boundingRect().width()) / 2.0,
            15.0,
        )
        item.setSelected(True)
        self.view.ensureVisible(item)

    def choose_image(self) -> None:
        """Open the image file picker."""
        formats = " ".join(f"*.{fmt.data().decode().lower()}" for fmt in QtGui.QImageReader.supportedImageFormats())
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose artwork",
            self._file_dialog_directory(),
            f"Images ({formats});;All files (*)",
        )
        if path:
            self._remember_file_path(path)
            self.add_image_from_path(path)

    def choose_background(self) -> None:
        """Choose and install the single background image."""
        formats = " ".join(
            f"*.{fmt.data().decode().lower()}"
            for fmt in QtGui.QImageReader.supportedImageFormats()
        )
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose background",
            self._file_dialog_directory(),
            f"Images ({formats});;All files (*)",
        )
        if not path:
            return
        self._remember_file_path(path)
        reader = QtGui.QImageReader(path)
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            QtWidgets.QMessageBox.warning(
                self, "Background error", reader.errorString() or "Could not load background image."
            )
            return
        self.set_background_pixmap(QtGui.QPixmap.fromImage(image))

    def set_background_pixmap(self, pixmap: QtGui.QPixmap) -> None:
        """Replace the current background and keep it behind all artwork."""
        if self.background_item is not None:
            for handle in self.background_item._handles:
                handle.setVisible(False)
                self.scene.removeItem(handle)
            self.scene.removeItem(self.background_item)
        self.background_item = BackgroundImageItem(pixmap)
        self.scene.addItem(self.background_item)
        self.background_item.detach_handles()
        self.background_item.setPos(0, 0)
        self.scene.clearSelection()
        self.background_item.setSelected(True)
        self.background_size_combo.setCurrentIndex(0)
        self.background_rotation_combo.setCurrentIndex(0)
        self.view.ensureVisible(self.background_item)
        self.statusBar().showMessage("Background image inserted")

    def remove_background(self) -> None:
        """Remove the installed background image, if one exists."""
        item = self.background_item
        if item is None:
            return
        old_rect = item.sceneBoundingRect()
        for handle in item._handles:
            handle.setVisible(False)
            self.scene.removeItem(handle)
        item.setVisible(False)
        self.scene.removeItem(item)
        self.background_item = None
        self.scene.clearSelection()
        self._refresh_scene_region(old_rect)
        self.statusBar().showMessage("Background image removed")

    def _refresh_scene_region(self, region: QtCore.QRectF) -> None:
        """Immediately repaint an area after removing a transformed item."""
        self.scene.invalidate(region, QtWidgets.QGraphicsScene.SceneLayer.AllLayers)
        self.scene.update(region)
        self.view.viewport().update()

    def set_background_size_mode(self, _index: int = -1) -> None:
        """Apply the selected CSS-like background size mode."""
        if self.background_item is None:
            return
        mode = self.background_size_combo.currentData()
        self.background_item.setPos(0, 0)
        self.background_item.apply_size_mode(str(mode))

    def set_background_rotation(self) -> None:
        """Apply the selected background rotation preset."""
        if self.background_item is None:
            return
        data = self.background_rotation_combo.currentData()
        if data is None:
            return
        angle = int(data)
        self.background_item.set_rotation_preset(angle)

    def add_image_from_path(self, path: str) -> None:
        """Load and add an image file, reporting invalid files to the user."""
        self.statusBar().showMessage(f"Loading image: {Path(path).name}")
        reader = QtGui.QImageReader(path)
        reader.setAutoTransform(True)
        source_size = reader.size()
        if source_size.isValid() and max(source_size.width(), source_size.height()) > self.MAX_IMAGE_PIXELS:
            factor = self.MAX_IMAGE_PIXELS / max(source_size.width(), source_size.height())
            reader.setScaledSize(QtCore.QSize(
                max(1, round(source_size.width() * factor)),
                max(1, round(source_size.height() * factor)),
            ))
        image = reader.read()
        if image.isNull():
            error = reader.errorString() or "unknown image format"
            QtWidgets.QMessageBox.warning(
                self,
                "Image error",
                f"Could not load image:\n{path}\n\nReason: {error}",
            )
            self.statusBar().showMessage("Image could not be loaded")
            return
        self.add_image_from_pixmap(QtGui.QPixmap.fromImage(image))

    def add_image_from_pixmap(self, pixmap: QtGui.QPixmap) -> None:
        """Add a valid pixmap to the cover and select it."""
        if pixmap.isNull():
            QtWidgets.QMessageBox.warning(self, "Image error", "The clipboard does not contain a usable image.")
            return
        item = CoverImageItem(pixmap)
        self.scene.addItem(item)
        item.detach_handles()
        image_rect = QtCore.QRectF(item.pixmap().rect())
        top_left = QtCore.QPointF(
            (cover_width() - image_rect.width() * item.scale_x) / 2,
            (cover_height() - image_rect.height() * item.scale_y) / 2,
        )
        item.setPos(top_left)
        artwork_z_values = (
            candidate.zValue()
            for candidate in self.scene.items()
            if candidate not in (self.grid_item, self.frame_item)
        )
        item.setZValue(max(5.0, max(artwork_z_values, default=5.0) + 1.0))
        item.setSelected(True)
        self.scene.setFocusItem(item)
        self.view.ensureVisible(item)
        self.view.viewport().update()
        self.statusBar().showMessage(f"Image inserted: {pixmap.width()} x {pixmap.height()} px")

    def delete_selected(self) -> None:
        """Remove the selected editable element from the scene."""
        item = self.selected_item()
        if item is None or item in (self.grid_item, self.frame_item):
            return
        if item is self.background_item:
            self.remove_background()
            return
        if isinstance(item, CoverImageItem):
            for handle in item._handles:
                handle.setVisible(False)
                self.scene.removeItem(handle)
        old_rect = item.sceneBoundingRect()
        item.setVisible(False)
        self.scene.removeItem(item)
        del item
        self._refresh_scene_region(old_rect)
        self.update_controls()

    def move_selected(self) -> None:
        """Apply sidebar coordinates to the selected item."""
        item = self.selected_item()
        if item is None or not self.x_spin.isEnabled():
            return
        x, y = self.x_spin.value(), self.y_spin.value()
        item.setPos(x, y)

    def scale_selected(self, value: int) -> None:
        """Apply a relative scale to an image or text item."""
        item = self.selected_item()
        if item is None:
            return
        center_before = item.mapToScene(item.boundingRect().center())
        if isinstance(item, BackgroundImageItem):
            reference_scale = (item.reference_scale_x + item.reference_scale_y) / 2.0
            if reference_scale <= 0:
                return
            ratio = value / 100.0
            item.scale_x = item.reference_scale_x * ratio
            item.scale_y = item.reference_scale_y * ratio
            item._apply_transform()
            item._update_handle_positions()
        elif isinstance(item, CoverImageItem):
            item.set_user_scale(value / 100.0)
        elif isinstance(item, CoverTextItem):
            item.setScale(value / 100.0)
        else:
            return
        center_after = item.mapToScene(item.boundingRect().center())
        item.setPos(item.pos() + center_before - center_after)

    def rotate_selected(self, value: float) -> None:
        """Apply a rotation while preserving the item's aspect ratio."""
        item = self.selected_item()
        if isinstance(item, BackgroundImageItem):
            item.set_rotation(value)
        elif item is not None:
            if isinstance(item, CoverImageItem):
                item.set_rotation(value)
            else:
                center_before = item.mapToScene(item.boundingRect().center())
                item.setTransformOriginPoint(item.boundingRect().center())
                item.setRotation(value)
                center_after = item.mapToScene(item.boundingRect().center())
                item.setPos(item.pos() + center_before - center_after)

    def choose_font(self) -> None:
        """Choose and apply a font to selected text."""
        item = self.selected_item()
        if not isinstance(item, CoverTextItem):
            return
        original_font = item.font()
        original_html = item.toHtml()
        dialog = QtWidgets.QFontDialog(original_font, self)
        dialog.setWindowTitle("Choose text font")
        dialog.currentFontChanged.connect(item.set_text_font)
        accepted = dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
        if accepted:
            item.set_text_font(dialog.currentFont())
        else:
            item.setHtml(original_html)
        cursor = item.textCursor()
        cursor.clearSelection()
        item.setTextCursor(cursor)
        if accepted:
            item.setSelected(True)
            self.scene.setFocusItem(item)
            self.update_controls()

    def choose_text_color(self) -> None:
        """Choose and apply a color to the selected text item."""
        item = self.selected_item()
        if not isinstance(item, CoverTextItem):
            return
        color = QtWidgets.QColorDialog.getColor(
            item.defaultTextColor(),
            self,
            "Choose text color",
        )
        if color.isValid():
            item.set_text_color(color)
            item.setSelected(True)
            self.scene.setFocusItem(item)
            self.update_controls()

    def change_layer(self, direction: int) -> None:
        """Move the selected element above or below its neighbouring elements."""
        item = self.selected_item()
        if item is None or item in (self.grid_item, self.frame_item):
            return
        artwork_items = [
            candidate
            for candidate in self.scene.items()
            if candidate not in (self.grid_item, self.frame_item)
            and not isinstance(candidate, ImageHandleItem)
        ]
        if not artwork_items:
            return
        if direction > 0:
            item.setZValue(max(candidate.zValue() for candidate in artwork_items) + 1.0)
        else:
            item.setZValue(min(candidate.zValue() for candidate in artwork_items) - 1.0)
        item.setSelected(True)
        self.scene.setFocusItem(item)
        self.scene.update()

    def set_snap(self, enabled: bool) -> None:
        """Enable or disable snapping to the main cover guides."""
        self.view.snap_to_grid = enabled
        self.scene.snap_to_guides = enabled

    def set_aspect_lock(self, enabled: bool) -> None:
        """Enable or disable proportional image resizing."""
        item = self.selected_item()
        if isinstance(item, CoverImageItem):
            item.lock_aspect_ratio = enabled

    def update_controls(self) -> None:
        """Refresh sidebar values from the selected item."""
        item = self.selected_item()
        if item is not None:
            self._active_item = item
        enabled = item is not None and item not in (self.grid_item, self.frame_item)
        self.x_spin.setEnabled(enabled)
        self.y_spin.setEnabled(enabled)
        self.scale_slider.setEnabled(enabled)
        self.rotation_spin.setEnabled(enabled)
        self.aspect_check.setEnabled(isinstance(item, CoverImageItem))
        self.font_button.setEnabled(isinstance(item, CoverTextItem))
        has_background = isinstance(item, BackgroundImageItem)
        self.background_size_combo.setEnabled(has_background)
        self.background_rotation_combo.setEnabled(has_background)
        self.text_color_button.setEnabled(isinstance(item, CoverTextItem))
        if not enabled:
            return
        blocker_x = QtCore.QSignalBlocker(self.x_spin)
        blocker_y = QtCore.QSignalBlocker(self.y_spin)
        self.x_spin.setValue(item.pos().x())
        self.y_spin.setValue(item.pos().y())
        del blocker_x, blocker_y
        if isinstance(item, BackgroundImageItem):
            blocker_scale = QtCore.QSignalBlocker(self.scale_slider)
            reference_scale = (item.reference_scale_x + item.reference_scale_y) / 2.0
            scale_percent = round(((item.scale_x + item.scale_y) / (2.0 * reference_scale)) * 100)
            self.scale_slider.setValue(max(self.scale_slider.minimum(), min(self.scale_slider.maximum(), scale_percent)))
            del blocker_scale
        elif isinstance(item, CoverImageItem):
            blocker_aspect = QtCore.QSignalBlocker(self.aspect_check)
            self.aspect_check.setChecked(item.lock_aspect_ratio)
            del blocker_aspect
            item._update_handle_positions()
            blocker_scale = QtCore.QSignalBlocker(self.scale_slider)
            self.scale_slider.setValue(round(((item.scale_x / item.base_scale) + (item.scale_y / item.base_scale)) * 50))
            del blocker_scale
        elif isinstance(item, CoverTextItem):
            blocker_scale = QtCore.QSignalBlocker(self.scale_slider)
            self.scale_slider.setValue(round(item.scale() * 100))
            del blocker_scale
        blocker_rotation = QtCore.QSignalBlocker(self.rotation_spin)
        self.rotation_spin.setValue(
            item.rotation_angle()
            if isinstance(item, CoverImageItem)
            else item.rotation_angle()
            if isinstance(item, BackgroundImageItem)
            else item.rotation()
        )
        del blocker_rotation
        background_selected = has_background
        if background_selected:
            size_index = self.background_size_combo.findData(item.size_mode)
            if size_index >= 0:
                self.background_size_combo.setCurrentIndex(size_index)
            blocker_background_rotation = QtCore.QSignalBlocker(self.background_rotation_combo)
            rotation_index = self.background_rotation_combo.findData(item.rotation_preset)
            self.background_rotation_combo.setCurrentIndex(rotation_index if rotation_index >= 0 else -1)
            del blocker_background_rotation

    def _configure_printer(self, printer: QtPrintSupport.QPrinter, output_path: Optional[str] = None) -> None:
        """Configure a printer for A4, 300 DPI output."""
        printer.setResolution(300)
        printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))
        printer.setPageOrientation(self._page_orientation())
        if output_path:
            printer.setOutputFormat(QtPrintSupport.QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(output_path)

    def export_pdf(self) -> None:
        """Export the artwork and crop marks as a vector PDF."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export PDF",
            str(Path(self._file_dialog_directory()) / "cd-cover.pdf"),
            "PDF files (*.pdf)",
        )
        if not path:
            return
        self._remember_file_path(path)
        writer = QtGui.QPdfWriter(path)
        writer.setResolution(300)
        writer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))
        writer.setPageOrientation(self._page_orientation())
        painter = QtGui.QPainter(writer)
        try:
            page_rect_points = writer.pageLayout().paintRect(QtGui.QPageLayout.Unit.Point)
            points_to_device = writer.resolution() / 72.0
            page_rect = QtCore.QRectF(
                page_rect_points.x() * points_to_device,
                page_rect_points.y() * points_to_device,
                page_rect_points.width() * points_to_device,
                page_rect_points.height() * points_to_device,
            )
            CoverRenderer.render(
                self.scene,
                painter,
                page_rect,
                self.export_fold_guides_check.isChecked(),
            )
        finally:
            painter.end()

    def _render_printer_page(self, printer: QtPrintSupport.QPrinter) -> None:
        """Render the current cover into a printer or preview paint device."""
        painter = QtGui.QPainter(printer)
        try:
            page_rect = printer.pageRect(QtPrintSupport.QPrinter.Unit.DevicePixel)
            CoverRenderer.render(
                self.scene,
                painter,
                page_rect,
                self.export_fold_guides_check.isChecked(),
            )
        finally:
            painter.end()

    def preview_print(self) -> None:
        """Show the native print preview for the current cover."""
        printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.PrinterMode.HighResolution)
        self._configure_printer(printer)
        preview = QtPrintSupport.QPrintPreviewDialog(printer, self)
        preview.resize(self.size())
        preview.paintRequested.connect(self._render_printer_page)
        preview.exec()

    def print_cover(self) -> None:
        """Open the native system print dialog and print the cover."""
        printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.PrinterMode.HighResolution)
        self._configure_printer(printer)
        dialog = QtPrintSupport.QPrintDialog(printer, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._render_printer_page(printer)


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
