"""Graphics-scene items for the grid, cut frame, text, and images."""

from __future__ import annotations

import math
from typing import Optional, Union

from PySide6 import QtCore, QtGui, QtWidgets

from src.constants import (
    BLEED_MM,
    CoverSpec,
    EXTENDED_FLAP_INSET_MM,
    SNAP_THRESHOLD_MM,
)
from src.geometry import cover_height, cover_width, nudge_item_with_key, snap_value_to_guides

# Handle kinds: eight resize handles around the image, plus one rotate handle.
HandleKind = Union[str, tuple[str, int]]

CORNER_HANDLE_INDICES = (0, 2, 4, 6)
TOP_BOTTOM_HANDLE_INDICES = (1, 5)
LEFT_RIGHT_HANDLE_INDICES = (3, 7)
LEFT_SIDE_INDICES = (0, 6, 7)
RIGHT_SIDE_INDICES = (2, 3, 4)
TOP_SIDE_INDICES = (0, 1, 2)
BOTTOM_SIDE_INDICES = (4, 5, 6)

ROTATION_PRESETS = (0.0, 90.0, 180.0, 270.0, 360.0)
ROTATION_SNAP_DEGREES = 5.0
MIN_SCALE_FACTOR = 0.05
MAX_SCALE_FACTOR = 20.0


class GridItem(QtWidgets.QGraphicsItem):
    """Non-selectable 5 mm editing grid drawn behind all artwork."""

    def __init__(self, rect: QtCore.QRectF, step: float = 5.0) -> None:
        super().__init__()
        self._rect = rect
        self._step = step
        self.setZValue(-1000)
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)

    def set_rect(self, rect: QtCore.QRectF) -> None:
        """Replace the grid bounds after the cover format changes."""
        self.prepareGeometryChange()
        self._rect = rect
        self.update()

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
            painter.drawLine(
                QtCore.QPointF(x, self._rect.top()),
                QtCore.QPointF(x, self._rect.bottom()),
            )
            x += self._step
        y = self._rect.top()
        while y <= self._rect.bottom():
            painter.drawLine(
                QtCore.QPointF(self._rect.left(), y),
                QtCore.QPointF(self._rect.right(), y),
            )
            y += self._step
        painter.restore()


class CoverFrameItem(QtWidgets.QGraphicsItem):
    """Draws the cover cut line, bleed area, and optional fold guides.

    The frame sits above artwork so the cut outline remains visible, but it
    does not accept mouse buttons so handles still receive clicks.
    """

    def __init__(self) -> None:
        super().__init__()
        self._width = cover_width()
        self._height = cover_height()
        self._guides: tuple[float, ...] = ()
        self._spec: Optional[CoverSpec] = None
        self.show_guides = True
        self.fold_guide_opacity = 210
        self.setZValue(100000)
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)

    @property
    def width_mm(self) -> float:
        """Current cut-line width including optional expand-cover adjustment."""
        return self._width

    @property
    def height_mm(self) -> float:
        """Current cut-line height including optional expand-cover adjustment."""
        return self._height

    @property
    def guides(self) -> tuple[float, ...]:
        """Vertical fold-guide X positions in millimetres."""
        return self._guides

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
        self._spec = spec
        self._width = spec.width_mm
        self._height = spec.height_mm
        self._guides = spec.guides
        self.update()

    def set_layout(self, width: float, height: float, guides: tuple[float, ...]) -> None:
        """Apply computed dimensions after expand-cover or format changes."""
        self.prepareGeometryChange()
        self._width = width
        self._height = height
        self._guides = guides
        self.update()

    def _is_extended(self) -> bool:
        return bool(self._spec and self._spec.key.startswith("ext_"))

    def _flap_end(self) -> float:
        """X position where the reduced-height flap meets the full-height panel."""
        if len(self._guides) > 1:
            return self._guides[1]
        return self._guides[0] if self._guides else 0.0

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
        if self._is_extended():
            self._paint_extended_cut_line(painter)
        else:
            painter.drawRect(QtCore.QRectF(0, 0, self._width, self._height))
        if self.show_guides:
            self._paint_fold_guides(painter)
        painter.restore()

    def _paint_extended_cut_line(self, painter: QtGui.QPainter) -> None:
        """Draw the notched Slim-case outline (2 mm inset on the flap edge)."""
        flap_end = self._flap_end()
        top_reduced_y = EXTENDED_FLAP_INSET_MM
        bot_reduced_y = self._height - EXTENDED_FLAP_INSET_MM
        painter.drawLine(QtCore.QPointF(0, top_reduced_y), QtCore.QPointF(flap_end, top_reduced_y))
        painter.drawLine(QtCore.QPointF(flap_end, 0), QtCore.QPointF(self._width, 0))
        painter.drawLine(QtCore.QPointF(0, bot_reduced_y), QtCore.QPointF(flap_end, bot_reduced_y))
        painter.drawLine(QtCore.QPointF(flap_end, self._height), QtCore.QPointF(self._width, self._height))
        painter.drawLine(QtCore.QPointF(0, top_reduced_y), QtCore.QPointF(0, bot_reduced_y))
        painter.drawLine(QtCore.QPointF(self._width, 0), QtCore.QPointF(self._width, self._height))
        painter.drawLine(QtCore.QPointF(flap_end, 0), QtCore.QPointF(flap_end, top_reduced_y))
        painter.drawLine(QtCore.QPointF(flap_end, bot_reduced_y), QtCore.QPointF(flap_end, self._height))

    def _paint_fold_guides(self, painter: QtGui.QPainter) -> None:
        """Draw vertical dotted fold marks, truncated on the reduced-height flap."""
        painter.setPen(
            QtGui.QPen(
                QtGui.QColor(127, 139, 152, self.fold_guide_opacity),
                0.25,
                QtCore.Qt.PenStyle.DotLine,
            )
        )
        flap_end = self._flap_end()
        for guide_x in self._guides:
            if self._is_extended() and guide_x < flap_end:
                painter.drawLine(
                    QtCore.QPointF(guide_x, EXTENDED_FLAP_INSET_MM),
                    QtCore.QPointF(guide_x, self._height - EXTENDED_FLAP_INSET_MM),
                )
            else:
                painter.drawLine(QtCore.QPointF(guide_x, 0), QtCore.QPointF(guide_x, self._height))


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
        self._apply_initial_format(font)
        self.setTransformOriginPoint(self.boundingRect().center())

    def _apply_initial_format(self, font: QtGui.QFont) -> None:
        """Centre the starter block and apply a proportional line height."""
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

    def set_text_color(self, color: QtGui.QColor) -> None:
        """Apply a color to all existing and subsequently edited text."""
        self.setDefaultTextColor(color)
        cursor = self._selection_or_document_cursor()
        format_ = QtGui.QTextCharFormat()
        format_.setForeground(color)
        cursor.setCharFormat(format_)
        self._clear_cursor_selection(cursor)

    def set_text_font(self, font: QtGui.QFont) -> None:
        """Apply a font to selected text or to the complete text block."""
        cursor = self._selection_or_document_cursor()
        format_ = QtGui.QTextCharFormat()
        format_.setFont(font)
        cursor.mergeCharFormat(format_)
        self._clear_cursor_selection(cursor)
        self.setTransformOriginPoint(self.boundingRect().center())

    def _selection_or_document_cursor(self) -> QtGui.QTextCursor:
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QtGui.QTextCursor.SelectionType.Document)
        return cursor

    def _clear_cursor_selection(self, cursor: QtGui.QTextCursor) -> None:
        self.setTextCursor(cursor)
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Move the text block with arrow keys instead of editing its cursor."""
        if nudge_item_with_key(self, event):
            return
        super().keyPressEvent(event)

    def itemChange(
        self,
        change: QtWidgets.QGraphicsItem.GraphicsItemChange,
        value: object,
    ) -> object:
        """Snap normal text movement to the cover guides."""
        if (
            change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and self.scene() is not None
            and getattr(self.scene(), "snap_to_guides", False)
            and not getattr(self.scene(), "suppress_snap", False)
        ):
            position = value
            if isinstance(position, QtCore.QPointF):
                snap = getattr(self.scene(), "snap_position", None)
                if callable(snap):
                    return snap(self, position)
        return super().itemChange(change, value)


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
        self.base_scale = max(cover_width(), cover_height()) / max(
            1, normalized.width(), normalized.height()
        )
        self.scale_x = self.base_scale
        self.scale_y = self.base_scale
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setTransformationMode(QtCore.Qt.TransformationMode.SmoothTransformation)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)
        self.setZValue(5)
        # The transform already translates around the image centre. Keep Qt's
        # implicit origin at (0, 0) to avoid applying that translation twice.
        self.setTransformOriginPoint(QtCore.QPointF(0, 0))
        self._rotation_angle = 0.0
        self._apply_transform()
        self.user_scale = 1.0
        self._mouse_mode: Optional[HandleKind] = None
        self._mouse_start_scene = QtCore.QPointF()
        self._mouse_start_scale = 1.0
        self._mouse_start_scale_x = self.scale_x
        self._mouse_start_scale_y = self.scale_y
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
        self._handles = self._create_handles()
        self._update_handle_positions()

    def _create_handles(self) -> list[ImageHandleItem]:
        handles = [ImageHandleItem(self, str(index)) for index in range(8)]
        handles.append(ImageHandleItem(self, "rotate"))
        return handles

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Move the image with arrow keys."""
        if nudge_item_with_key(self, event):
            return
        super().keyPressEvent(event)

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
            painter.setPen(QtGui.QPen(QtGui.QColor("#8e44ad"), 0.0))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRect(QtCore.QRectF(self.pixmap().rect()))
            painter.restore()

    def itemChange(
        self,
        change: QtWidgets.QGraphicsItem.GraphicsItemChange,
        value: object,
    ) -> object:
        """Keep child handles synchronized with the owner's selection state."""
        if self._should_snap_position(change):
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

    def _should_snap_position(self, change: QtWidgets.QGraphicsItem.GraphicsItemChange) -> bool:
        return (
            change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and self.scene() is not None
            and getattr(self.scene(), "snap_to_guides", False)
            and not getattr(self.scene(), "suppress_snap", False)
            and self._mouse_mode is None
        )

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
        return QtCore.QRectF(self.pixmap().rect())

    def shape(self) -> QtGui.QPainterPath:
        """Use the image rectangle for selection; handles are separate items."""
        path = QtGui.QPainterPath()
        path.addRect(QtCore.QRectF(self.pixmap().rect()))
        return path

    def _update_handle_positions(self) -> None:
        """Place child handles in local or scene coordinates around the image."""
        rect = QtCore.QRectF(self.pixmap().rect())
        for index, center in enumerate(self._handle_centers(rect)):
            self._place_handle(self._handles[index], center)
        rotate_point = QtCore.QPointF(
            rect.center().x(),
            rect.top() - 12.0 / max(self.scale_y, 0.01),
        )
        self._place_handle(self._handles[8], rotate_point)

    def _place_handle(self, handle: ImageHandleItem, local_point: QtCore.QPointF) -> None:
        handle.setZValue(self.zValue() + 1000.0)
        if handle.parentItem() is None:
            handle.setPos(self.mapToScene(local_point))
            handle.setTransform(QtGui.QTransform())
            handle.setRotation(self._rotation_angle)
        else:
            handle.setPos(local_point)
            handle.setTransform(
                QtGui.QTransform.fromScale(
                    1.0 / max(self.scale_x, 0.01),
                    1.0 / max(self.scale_y, 0.01),
                )
            )
            handle.setRotation(-self._rotation_angle)
        handle.setVisible(self.isSelected())

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
        # Keep the transformed item anchored at its local top-left. The caller
        # positions that top-left in scene coordinates when inserting the image.
        target_center_x = center.x() * self.scale_x
        target_center_y = center.y() * self.scale_y
        dx = target_center_x - m11 * center.x() - m21 * center.y()
        dy = target_center_y - m12 * center.x() - m22 * center.y()
        self.setTransform(QtGui.QTransform(m11, m12, m21, m22, dx, dy), combine=False)

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

    def remove_handles_from_scene(self, scene: QtWidgets.QGraphicsScene) -> None:
        """Hide and detach handles before the owner is deleted."""
        for handle in self._handles:
            handle.setVisible(False)
            scene.removeItem(handle)

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
        self._capture_drag_start(scene_pos)
        if kind != "rotate":
            self._prepare_resize_anchors(int(kind))
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
        if self._try_begin_inline_handle_drag(event):
            event.accept()
            return
        super().mousePressEvent(event)

    def _try_begin_inline_handle_drag(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> bool:
        """Return True if the press landed on a handle drawn on the pixmap itself."""
        if not self.isSelected():
            return False
        rect = QtCore.QRectF(self.pixmap().rect())
        hit_radius = 4.0 / max(min(self.scale_x, self.scale_y), 0.01)
        distances = [QtCore.QLineF(event.pos(), point).length() for point in self._handle_centers(rect)]
        rotate_point = QtCore.QPointF(
            rect.center().x(),
            rect.top() - 12.0 / max(self.scale_y, 0.01),
        )
        if QtCore.QLineF(event.pos(), rotate_point).length() <= hit_radius:
            self._mouse_mode = "rotate"
        elif distances and min(distances) <= hit_radius:
            index = distances.index(min(distances))
            self._mouse_mode = ("resize", index)
            self._resize_index = index
            self._prepare_resize_anchors(index)
        else:
            return False
        self._capture_drag_start(event.scenePos())
        self.setSelected(True)
        return True

    def _capture_drag_start(self, scene_pos: QtCore.QPointF) -> None:
        self._mouse_start_scene = scene_pos
        self._mouse_start_scale = self.scale()
        self._mouse_start_scale_x = self.scale_x
        self._mouse_start_scale_y = self.scale_y
        self._mouse_start_rotation = self._rotation_angle
        center = self.mapToScene(QtCore.QRectF(self.pixmap().rect()).center())
        self._mouse_start_angle = math.atan2(scene_pos.y() - center.y(), scene_pos.x() - center.x())

    def _prepare_resize_anchors(self, index: int) -> None:
        rect = QtCore.QRectF(self.pixmap().rect())
        handles = self._handle_centers(rect)
        self._resize_start_handle = handles[index]
        self._resize_anchor = handles[(index + 4) % 8]
        self._resize_anchor_scene = self.mapToScene(self._resize_anchor)
        self._resize_center_scene = self.mapToScene(QtCore.QPointF(rect.center()))
        self._resize_start_inverse = self.sceneTransform().inverted()[0]

    def _apply_handle_motion(self, scene_pos: QtCore.QPointF, aspect_locked: bool = False) -> None:
        """Apply a handle movement using the transform captured at mouse-down."""
        if isinstance(self._mouse_mode, tuple) and self._mouse_mode[0] == "resize":
            self._apply_resize_motion(scene_pos, aspect_locked)
            return
        if self._mouse_mode == "rotate":
            self._apply_rotate_motion(scene_pos)

    def _apply_resize_motion(self, scene_pos: QtCore.QPointF, aspect_locked: bool) -> None:
        index = self._mouse_mode[1]
        scene_pos = self._snap_resize_position(scene_pos)
        # Convert the cursor with the transform captured at mouse-down.
        # Reusing the changing transform here causes visible resize jitter.
        current = self._resize_start_inverse.map(scene_pos)
        scale_x, scale_y = self._compute_resize_scales(index, current)
        if aspect_locked:
            scale_x, scale_y = self._lock_aspect_scales(index, scale_x, scale_y)
        self.prepareGeometryChange()
        self.scale_x = scale_x
        self.scale_y = scale_y
        self._apply_transform(self._rotation_angle)
        self._update_handle_positions()
        self._reposition_after_resize()
        self._invalidate_scene()

    def _compute_resize_scales(
        self,
        index: int,
        current: QtCore.QPointF,
    ) -> tuple[float, float]:
        start = self._resize_start_handle
        anchor = self._resize_anchor
        width_denominator = max(1.0, abs(start.x() - anchor.x()))
        height_denominator = max(1.0, abs(start.y() - anchor.y()))
        scale_x = self._mouse_start_scale_x
        scale_y = self._mouse_start_scale_y
        if self._symmetric_resize:
            return self._symmetric_resize_scales(index, current, start, scale_x, scale_y)
        if index in LEFT_SIDE_INDICES or index in RIGHT_SIDE_INDICES:
            scale_x *= self._clamped_factor(abs(current.x() - anchor.x()) / width_denominator)
        if index in TOP_SIDE_INDICES or index in BOTTOM_SIDE_INDICES:
            scale_y *= self._clamped_factor(abs(current.y() - anchor.y()) / height_denominator)
        return scale_x, scale_y

    def _symmetric_resize_scales(
        self,
        index: int,
        current: QtCore.QPointF,
        start: QtCore.QPointF,
        scale_x: float,
        scale_y: float,
    ) -> tuple[float, float]:
        center = QtCore.QRectF(self.pixmap().rect()).center()
        start_center_distance_x = max(1.0, abs(start.x() - center.x()))
        start_center_distance_y = max(1.0, abs(start.y() - center.y()))
        if index in CORNER_HANDLE_INDICES:
            scale_x *= self._clamped_factor(abs(current.x() - center.x()) / start_center_distance_x)
            scale_y *= self._clamped_factor(abs(current.y() - center.y()) / start_center_distance_y)
        elif index in TOP_BOTTOM_HANDLE_INDICES:
            scale_y *= self._clamped_factor(abs(current.y() - center.y()) / start_center_distance_y)
        elif index in LEFT_RIGHT_HANDLE_INDICES:
            scale_x *= self._clamped_factor(abs(current.x() - center.x()) / start_center_distance_x)
        return scale_x, scale_y

    @staticmethod
    def _clamped_factor(factor: float) -> float:
        return max(MIN_SCALE_FACTOR, min(MAX_SCALE_FACTOR, factor))

    def _lock_aspect_scales(
        self,
        index: int,
        scale_x: float,
        scale_y: float,
    ) -> tuple[float, float]:
        factor_x = scale_x / self._mouse_start_scale_x
        factor_y = scale_y / self._mouse_start_scale_y
        if index in CORNER_HANDLE_INDICES:
            factor = max(factor_x, factor_y)
        elif index in LEFT_RIGHT_HANDLE_INDICES:
            factor = factor_x
        else:
            factor = factor_y
        return self._mouse_start_scale_x * factor, self._mouse_start_scale_y * factor

    def _reposition_after_resize(self) -> None:
        """Keep the opposite handle (or centre) fixed in scene space after a scale."""
        reference_scene = self._resize_center_scene if self._symmetric_resize else self._resize_anchor_scene
        reference_local = (
            QtCore.QRectF(self.pixmap().rect()).center()
            if self._symmetric_resize
            else self._resize_anchor
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

    def _apply_rotate_motion(self, scene_pos: QtCore.QPointF) -> None:
        center = self.mapToScene(QtCore.QRectF(self.pixmap().rect()).center())
        angle = math.atan2(scene_pos.y() - center.y(), scene_pos.x() - center.x())
        rotation = self._mouse_start_rotation + math.degrees(angle - self._mouse_start_angle)
        snapped_rotation = self._snap_rotation(rotation)
        self._apply_transform(snapped_rotation)
        self._sync_rotation_preset(snapped_rotation)
        self._update_handle_positions()
        self._invalidate_scene()
        self.update()

    def _sync_rotation_preset(self, snapped_rotation: float) -> None:
        if not isinstance(self, BackgroundImageItem):
            return
        normalized = snapped_rotation % 360.0
        self.rotation_preset = (
            int(normalized)
            if normalized in (0.0, 90.0, 180.0, 270.0)
            else -1
        )

    def _invalidate_scene(self) -> None:
        scene = self.scene()
        if scene is not None:
            scene.invalidate(self.sceneBoundingRect(), QtWidgets.QGraphicsScene.SceneLayer.AllLayers)

    def _snap_resize_position(self, position: QtCore.QPointF) -> QtCore.QPointF:
        """Snap the resize cursor to the nearest main vertical and horizontal guide."""
        scene = self.scene()
        if scene is None or not getattr(scene, "snap_to_guides", False):
            return position
        guides_x, guides_y = getattr(scene, "snap_guides", ((), ()))
        return QtCore.QPointF(
            snap_value_to_guides(position.x(), guides_x, SNAP_THRESHOLD_MM),
            snap_value_to_guides(position.y(), guides_y, SNAP_THRESHOLD_MM),
        )

    def _snap_rotation(self, angle: float) -> float:
        """Snap rotation to the background rotation presets when close to one."""
        scene = self.scene()
        if scene is None or not getattr(scene, "snap_to_guides", False):
            return angle
        normalized = angle % 360.0
        nearest = min(ROTATION_PRESETS, key=lambda preset: abs(preset - normalized))
        distance = abs(nearest - normalized)
        if distance > ROTATION_SNAP_DEGREES:
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
            self._invalidate_scene()
            if self.scene() is not None:
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
