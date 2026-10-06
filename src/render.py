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

"""A4 PDF and printer rendering of the millimetre-based cover scene."""

from PySide6 import QtCore, QtGui, QtWidgets

from src.constants import BLEED_MM, MM_PER_INCH
from src.geometry import cover_height, cover_width
from src.items import CoverFrameItem, GridItem


class CoverRenderer:
    """Renders the cover scene to a precisely sized A4 PDF or printer page."""

    @staticmethod
    def render(
        scene: QtWidgets.QGraphicsScene,
        painter: QtGui.QPainter,
        page_rect: QtCore.QRectF,
        show_fold_guides: bool = False,
    ) -> None:
        """Render the cover compactly in the printable A4 area.

        The artwork keeps its exact physical size. It is anchored to the
        printable area's top-left corner instead of being centred, which
        avoids unnecessary whitespace around the exported or printed layout.
        """
        dpi_x, dpi_y = CoverRenderer._device_dpi(painter)
        artwork_width = cover_width() + 2 * BLEED_MM
        artwork_height = cover_height() + 2 * BLEED_MM
        target = QtCore.QRectF(
            page_rect.x(),
            page_rect.y(),
            artwork_width * dpi_x / MM_PER_INCH,
            artwork_height * dpi_y / MM_PER_INCH,
        )
        source = QtCore.QRectF(-BLEED_MM, -BLEED_MM, artwork_width, artwork_height)
        grid_items = [item for item in scene.items() if isinstance(item, GridItem)]
        frame_items = [item for item in scene.items() if isinstance(item, CoverFrameItem)]
        previous_guide_states = CoverRenderer._hide_editor_overlays(
            grid_items, frame_items, show_fold_guides
        )
        try:
            scene.render(painter, target, source, QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)
        finally:
            CoverRenderer._restore_editor_overlays(grid_items, frame_items, previous_guide_states)

    @staticmethod
    def _device_dpi(painter: QtGui.QPainter) -> tuple[int, int]:
        device = painter.device()
        if device is None:
            raise RuntimeError("The painter has no active paint device")
        dpi_x = device.logicalDpiX()
        dpi_y = device.logicalDpiY()
        if dpi_x <= 0 or dpi_y <= 0:
            raise RuntimeError("The paint device has invalid logical DPI")
        return dpi_x, dpi_y

    @staticmethod
    def _hide_editor_overlays(
        grid_items: list[GridItem],
        frame_items: list[CoverFrameItem],
        show_fold_guides: bool,
    ) -> list[tuple[bool, int]]:
        """Hide the editing grid and optionally dim fold guides for print output."""
        for item in grid_items:
            item.setVisible(False)
        previous_guide_states = [(item.show_guides, item.fold_guide_opacity) for item in frame_items]
        for item in frame_items:
            item.show_guides = show_fold_guides
            item.fold_guide_opacity = 110
        return previous_guide_states

    @staticmethod
    def _restore_editor_overlays(
        grid_items: list[GridItem],
        frame_items: list[CoverFrameItem],
        previous_guide_states: list[tuple[bool, int]],
    ) -> None:
        for item in grid_items:
            item.setVisible(True)
        for item, (previous_state, previous_opacity) in zip(frame_items, previous_guide_states):
            item.show_guides = previous_state
            item.fold_guide_opacity = previous_opacity

