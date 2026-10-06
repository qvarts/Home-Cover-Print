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

"""Unit conversion and mutable active-cover dimensions.

Helper functions keep millimetre-based scene coordinates in one place so that
graphics items and the main window do not duplicate conversion math.
"""

from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from src.constants import MM_PER_INCH, NUDGE_STEP_LARGE_MM, NUDGE_STEP_MM


# Mutable so the rest of the application can query the currently selected
# cover format without threading CoverSpec through every constructor.
ACTIVE_COVER_WIDTH_MM = 120.0
ACTIVE_COVER_HEIGHT_MM = 120.0


def set_active_cover_size(width_mm: float, height_mm: float) -> None:
    """Update the millimetre size used by background and artwork helpers."""
    global ACTIVE_COVER_WIDTH_MM, ACTIVE_COVER_HEIGHT_MM
    ACTIVE_COVER_WIDTH_MM = width_mm
    ACTIVE_COVER_HEIGHT_MM = height_mm


def cover_width() -> float:
    """Return the active cover width in millimetres."""
    return ACTIVE_COVER_WIDTH_MM


def cover_height() -> float:
    """Return the active cover height in millimetres."""
    return ACTIVE_COVER_HEIGHT_MM


def mm_to_points(value: float) -> float:
    """Convert millimetres to PDF points (1/72 inch)."""
    return value * 72.0 / MM_PER_INCH


def nudge_item_with_key(
    item: QtWidgets.QGraphicsItem,
    event: QtGui.QKeyEvent,
) -> bool:
    """Move an editable graphics item with Shift or Ctrl plus an arrow key.

    Ctrl uses a 5 mm step; Shift uses 1 mm. Snapping is suppressed so the
    keyboard increment is applied exactly.

    Returns:
        True when the event was consumed as a nudge.
    """
    modifiers = event.modifiers()
    if not (
        modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier
        or modifiers & QtCore.Qt.KeyboardModifier.ControlModifier
    ):
        return False
    directions = {
        QtCore.Qt.Key.Key_Left: (-1.0, 0.0),
        QtCore.Qt.Key.Key_Right: (1.0, 0.0),
        QtCore.Qt.Key.Key_Up: (0.0, -1.0),
        QtCore.Qt.Key.Key_Down: (0.0, 1.0),
    }
    direction = directions.get(event.key())
    if direction is None or item.scene() is None:
        return False
    step = (
        NUDGE_STEP_LARGE_MM
        if modifiers & QtCore.Qt.KeyboardModifier.ControlModifier
        else NUDGE_STEP_MM
    )
    scene = item.scene()
    scene.suppress_snap = True
    try:
        item.setPos(item.pos() + QtCore.QPointF(direction[0] * step, direction[1] * step))
    finally:
        scene.suppress_snap = False
    item.setSelected(True)
    event.accept()
    return True


def snap_value_to_guides(value: float, guides: tuple[float, ...], threshold: float) -> float:
    """Return the nearest guide within *threshold*, otherwise *value* unchanged."""
    nearest = min(guides, key=lambda guide: abs(guide - value), default=value)
    return nearest if abs(nearest - value) <= threshold else value


def nearest_guide_correction(
    features: tuple[float, ...],
    guides: tuple[float, ...],
    threshold: float,
) -> float:
    """Return the smallest delta that would snap any feature onto a guide."""
    matches = [
        guide - feature
        for feature in features
        for guide in guides
        if abs(guide - feature) <= threshold
    ]
    return min(matches, key=abs) if matches else 0.0


def keep_center_stable(
    item: QtWidgets.QGraphicsItem,
    center_before: QtCore.QPointF,
) -> None:
    """Shift *item* so its visual centre stays at *center_before* after a transform."""
    center_after = item.mapToScene(item.boundingRect().center())
    item.setPos(item.pos() + center_before - center_after)


def supported_image_filter() -> str:
    """Build a file-dialog filter from Qt's supported image formats."""
    formats = " ".join(
        f"*.{fmt.data().decode().lower()}"
        for fmt in QtGui.QImageReader.supportedImageFormats()
    )
    return f"Images ({formats});;All files (*)"


def arrow_nudge_delta(event: QtGui.QKeyEvent) -> Optional[tuple[float, float]]:
    """Return (dx, dy) millimetres for a Shift/Ctrl + arrow nudge, or None."""
    directions = {
        QtCore.Qt.Key.Key_Left: (-1.0, 0.0),
        QtCore.Qt.Key.Key_Right: (1.0, 0.0),
        QtCore.Qt.Key.Key_Up: (0.0, -1.0),
        QtCore.Qt.Key.Key_Down: (0.0, 1.0),
    }
    if event.key() not in directions:
        return None
    modifiers = event.modifiers()
    if not (
        modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier
        or modifiers & QtCore.Qt.KeyboardModifier.ControlModifier
    ):
        return None
    step = (
        NUDGE_STEP_LARGE_MM
        if modifiers & QtCore.Qt.KeyboardModifier.ControlModifier
        else NUDGE_STEP_MM
    )
    dx, dy = directions[event.key()]
    return dx * step, dy * step

