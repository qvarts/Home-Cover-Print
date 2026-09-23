"""Main application window and controller for the cover editor."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtPrintSupport, QtWidgets

from src.constants import (
    BLEED_MM,
    COVER_SPECS,
    CoverSpec,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    SNAP_THRESHOLD_MM,
)
from src.geometry import (
    cover_height,
    cover_width,
    keep_center_stable,
    nearest_guide_correction,
    set_active_cover_size,
    supported_image_filter,
)
from src.items import (
    BackgroundImageItem,
    CoverFrameItem,
    CoverImageItem,
    CoverTextItem,
    GridItem,
    ImageHandleItem,
)
from src.render import CoverRenderer
from src.view import CoverGraphicsView

EDITABLE_ITEM_TYPES = (CoverTextItem, CoverImageItem, BackgroundImageItem)


def expanded_cover_layout(spec: CoverSpec) -> tuple[float, float, list[float]]:
    """Grow each main panel by 1 mm on every side and shift fold guides.

    Returns:
        Tuple of (width_mm, height_mm, guide_x_positions).
    """
    width = spec.width_mm
    height = spec.height_mm
    guides = list(spec.guides)
    main_sections = _main_section_indices(spec)
    width += len(main_sections) * 2.0
    height += 2.0
    shifted = []
    for index, guide in enumerate(guides):
        # Each preceding main section (including the current one) adds 2 mm.
        count_main = sum(1 for section in range(index + 1) if section in main_sections)
        shifted.append(guide + count_main * 2.0)
    return width, height, shifted


def _main_section_indices(spec: CoverSpec) -> list[int]:
    """Return panel indices that should grow when 'Expand cover size' is on."""
    guides_count = len(spec.guides)
    if spec.key in ("front", "booklet"):
        return list(range(guides_count + 1))
    if spec.key in ("back", "tray"):
        return [1]
    if spec.key in ("ext_front", "ext_booklet"):
        return list(range(2, guides_count + 1))
    return []


class MainWindow(QtWidgets.QMainWindow):
    """Main application window and controller for the cover editor."""

    MAX_IMAGE_PIXELS = 2400
    FILE_DIRECTORY_KEY = "last-file-directory"
    VIEW_MARGIN_MM = 12.0

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Home Cover Print")
        self.resize(1350, 860)
        self.cover_spec = COVER_SPECS[0]
        set_active_cover_size(self.cover_spec.width_mm, self.cover_spec.height_mm)
        self._closing = False
        self._scene_alive = True
        self._initial_fit_done = False
        self.background_item: Optional[BackgroundImageItem] = None
        self._active_item: Optional[QtWidgets.QGraphicsItem] = None
        self._init_scene()
        self._init_view()
        self._build_ui()
        QtCore.QTimer.singleShot(0, self._fit_scene_once)

    def _init_scene(self) -> None:
        """Create the millimetre scene, grid, and cut-line overlay."""
        self.scene = QtWidgets.QGraphicsScene(
            -BLEED_MM,
            -BLEED_MM,
            cover_width() + 2 * BLEED_MM,
            cover_height() + 2 * BLEED_MM,
        )
        self.scene.destroyed.connect(self._mark_scene_deleted)
        self.scene.snap_to_guides = True
        self.scene.suppress_snap = False
        self.scene.snap_position = self._snap_item_position
        self.scene.snap_guides = self._build_snap_guides()
        self.grid_item = GridItem(self.scene.sceneRect())
        self.frame_item = CoverFrameItem()
        self.frame_item.set_spec(self.cover_spec)
        self.scene.addItem(self.grid_item)
        self.scene.addItem(self.frame_item)

    def _init_view(self) -> None:
        """Wire the canvas signals that drive editor actions."""
        self.view = CoverGraphicsView(self.scene)
        self.view.setToolTip("Ctrl + mouse wheel to zoom")
        self.view.imageDropped.connect(self.add_image_from_path)
        self.view.imagePasted.connect(self.add_image_from_pixmap)
        self.view.deleteRequested.connect(self.delete_selected)
        self.view.nudgeRequested.connect(self.nudge_selected)
        self.scene.selectionChanged.connect(self.update_controls)
        self.scene.focusItemChanged.connect(
            lambda _new_item, _old_item, _reason: self.update_controls()
        )
        self.scene.changed.connect(
            lambda _regions: QtCore.QTimer.singleShot(0, self.update_controls)
        )

    @QtCore.Slot()
    def _mark_scene_deleted(self) -> None:
        """Prevent deferred UI refreshes from touching a deleted scene."""
        self._scene_alive = False

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Stop deferred scene updates before Qt tears down the window."""
        self._closing = True
        self._scene_alive = False
        super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """Apply the initial canvas zoom after the window has its final size."""
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._fit_scene_once)

    def _build_ui(self) -> None:
        """Construct the sidebar and central canvas."""
        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.addWidget(self.view, 1)
        sidebar = QtWidgets.QWidget()
        sidebar.setFixedWidth(300)
        side = QtWidgets.QVBoxLayout(sidebar)
        self._build_cover_type_controls(side)
        self._build_action_buttons(side)
        self._build_print_option_checks(side)
        self._build_selection_form(side)
        self._build_background_controls(side)
        self._build_style_and_layer_controls(side)
        self._build_option_checks(side)
        side.addStretch()
        side.addWidget(self._copyright_label())
        layout.addWidget(sidebar)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Select an image and use its handles to resize or rotate")

    def _build_cover_type_controls(self, side: QtWidgets.QVBoxLayout) -> None:
        side.addWidget(QtWidgets.QLabel("Cover type"))
        self.cover_type_combo = QtWidgets.QComboBox()
        for spec in COVER_SPECS:
            self.cover_type_combo.addItem(spec.label, spec.key)
        self.cover_type_combo.currentIndexChanged.connect(self.set_cover_type)
        side.addWidget(self.cover_type_combo)

    def _build_action_buttons(self, side: QtWidgets.QVBoxLayout) -> None:
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

    def _build_print_option_checks(self, side: QtWidgets.QVBoxLayout) -> None:
        self.export_fold_guides_check = QtWidgets.QCheckBox("Print fold lines")
        self.export_fold_guides_check.setToolTip(
            "When enabled, fold lines are included in PDF export, printing, and print preview."
        )
        self.export_fold_guides_check.setChecked(True)
        side.addWidget(self.export_fold_guides_check)
        self.add_bleed_margin_check = QtWidgets.QCheckBox("Expand cover size")
        self.add_bleed_margin_check.setToolTip("Adds 1mm to each side of the main cover area.")
        self.add_bleed_margin_check.setChecked(False)
        self.add_bleed_margin_check.toggled.connect(self.update_cover_dimensions)
        side.addWidget(self.add_bleed_margin_check)

    def _build_selection_form(self, side: QtWidgets.QVBoxLayout) -> None:
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

    def _build_background_controls(self, side: QtWidgets.QVBoxLayout) -> None:
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

    def _build_style_and_layer_controls(self, side: QtWidgets.QVBoxLayout) -> None:
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

    def _build_option_checks(self, side: QtWidgets.QVBoxLayout) -> None:
        side.addSpacing(10)
        self.snap_check = QtWidgets.QCheckBox("Snap to guides")
        self.snap_check.setChecked(True)
        self.snap_check.toggled.connect(self.set_snap)
        side.addWidget(self.snap_check)
        self.aspect_check = QtWidgets.QCheckBox("Lock image proportions")
        self.aspect_check.toggled.connect(self.set_aspect_lock)
        side.addWidget(self.aspect_check)

    @staticmethod
    def _copyright_label() -> QtWidgets.QLabel:
        copyright_label = QtWidgets.QLabel("Made by Qvart\nFree for personal use")
        copyright_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet("color: #6f7b86; padding-top: 8px;")
        return copyright_label

    def set_cover_type(self, index: int) -> None:
        """Switch the active physical cover format without deleting artwork."""
        if not 0 <= index < len(COVER_SPECS):
            return
        spec = COVER_SPECS[index]
        self.cover_spec = spec
        self.frame_item.set_spec(spec)
        self.update_cover_dimensions()
        set_active_cover_size(self.frame_item.width_mm, self.frame_item.height_mm)
        self._update_status_dimensions()

    def update_cover_dimensions(self) -> None:
        """Recalculate cover size and guides based on spec and optional margins."""
        spec = self.cover_spec
        if self.add_bleed_margin_check.isChecked():
            width, height, guides = expanded_cover_layout(spec)
        else:
            width, height, guides = spec.width_mm, spec.height_mm, list(spec.guides)
        self.scene.setSceneRect(
            -BLEED_MM,
            -BLEED_MM,
            width + 2 * BLEED_MM,
            height + 2 * BLEED_MM,
        )
        self.grid_item.set_rect(self.scene.sceneRect())
        self.frame_item.set_layout(width, height, tuple(guides))
        self.scene.snap_guides = self._build_snap_guides(width, height, tuple(guides))
        set_active_cover_size(width, height)
        if self.background_item is not None:
            self.background_item.apply_size_mode()
        self.view.viewport().update()
        self._update_status_dimensions()

    def _update_status_dimensions(self) -> None:
        """Update the status bar with current cover dimensions."""
        self.statusBar().showMessage(
            f"Print area: {self.frame_item.width_mm:.1f} × {self.frame_item.height_mm:.1f} mm"
        )

    def _fit_scene_once(self) -> None:
        """Fit the canvas only on first display so minimize/restore keeps the zoom."""
        if self._initial_fit_done:
            return
        self._initial_fit_done = True
        self._fit_scene_with_margin()

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
        # Freeze the startup zoom: it becomes the zoom-out limit and the scale
        # at which the grid keeps its on-screen size while zooming.
        fit_scale = self.view.transform().m11()
        self.view.set_min_zoom(fit_scale)
        self.grid_item.set_reference_scale(fit_scale)

    def _build_snap_guides(
        self,
        width: Optional[float] = None,
        height: Optional[float] = None,
        guides: Optional[tuple[float, ...]] = None,
    ) -> tuple[tuple[float, ...], tuple[float, ...]]:
        """Return vertical and horizontal snap guides in scene millimetres."""
        w = width if width is not None else cover_width()
        h = height if height is not None else cover_height()
        g = guides if guides is not None else self.cover_spec.guides
        vertical = [-BLEED_MM, 0.0, w / 2.0, w, w + BLEED_MM, *g]
        horizontal = [-BLEED_MM, 0.0, h / 2.0, h, h + BLEED_MM]
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
        return QtCore.QPointF(
            position.x() + nearest_guide_correction(x_features, self.scene.snap_guides[0], SNAP_THRESHOLD_MM),
            position.y() + nearest_guide_correction(y_features, self.scene.snap_guides[1], SNAP_THRESHOLD_MM),
        )

    def selected_item(self) -> Optional[QtWidgets.QGraphicsItem]:
        """Return the first editable selected item."""
        if self._closing or not self._scene_alive:
            return None
        focused = self.scene.focusItem()
        if isinstance(focused, EDITABLE_ITEM_TYPES):
            return focused
        for item in self.scene.selectedItems():
            if isinstance(item, EDITABLE_ITEM_TYPES):
                return item
        active_item = getattr(self, "_active_item", None)
        if active_item is not None and active_item.scene() is self.scene:
            return active_item
        return None

    def _file_dialog_directory(self) -> str:
        """Return the last directory used by any file dialog."""
        settings = QtCore.QSettings("HomeCoverPrint", "HomeCoverPrint")
        return str(settings.value(self.FILE_DIRECTORY_KEY, str(Path.home())))

    def _remember_file_path(self, path: str) -> None:
        """Remember the directory containing a successfully chosen file."""
        QtCore.QSettings("HomeCoverPrint", "HomeCoverPrint").setValue(
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
        item.setPos((cover_width() - item.boundingRect().width()) / 2.0, 15.0)
        self._select_and_focus(item)

    def choose_image(self) -> None:
        """Open the image file picker."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose artwork",
            self._file_dialog_directory(),
            supported_image_filter(),
        )
        if path:
            self._remember_file_path(path)
            self.add_image_from_path(path)

    def choose_background(self) -> None:
        """Choose and install the single background image."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose background",
            self._file_dialog_directory(),
            supported_image_filter(),
        )
        if not path:
            return
        self._remember_file_path(path)
        pixmap = self._read_image_pixmap(path, "Background error")
        if pixmap is not None:
            self.set_background_pixmap(pixmap)

    def _read_image_pixmap(self, path: str, error_title: str) -> Optional[QtGui.QPixmap]:
        """Load an image file, reporting Qt reader errors to the user."""
        reader = QtGui.QImageReader(path)
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            QtWidgets.QMessageBox.warning(
                self, error_title, reader.errorString() or "Could not load image."
            )
            return None
        return QtGui.QPixmap.fromImage(image)

    def set_background_pixmap(self, pixmap: QtGui.QPixmap) -> None:
        """Replace the current background and keep it behind all artwork."""
        if self.background_item is not None:
            self.background_item.remove_handles_from_scene(self.scene)
            self.scene.removeItem(self.background_item)
        self.background_item = BackgroundImageItem(pixmap)
        self.scene.addItem(self.background_item)
        self.background_item.detach_handles()
        self.background_item.setPos(0, 0)
        self.scene.clearSelection()
        self._select_and_focus(self.background_item)
        self.background_size_combo.setCurrentIndex(0)
        self.background_rotation_combo.setCurrentIndex(0)
        self.statusBar().showMessage("Background image inserted")

    def remove_background(self) -> None:
        """Remove the installed background image, if one exists."""
        item = self.background_item
        if item is None:
            return
        old_rect = item.sceneBoundingRect()
        item.remove_handles_from_scene(self.scene)
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
        self.background_item.set_rotation_preset(int(data))

    def add_image_from_path(self, path: str) -> None:
        """Load and add an image file, reporting invalid files to the user."""
        self.statusBar().showMessage(f"Loading image: {Path(path).name}")
        reader = QtGui.QImageReader(path)
        reader.setAutoTransform(True)
        self._maybe_downscale_reader(reader)
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

    def _maybe_downscale_reader(self, reader: QtGui.QImageReader) -> None:
        """Cap decoded pixel size so very large files stay interactive."""
        source_size = reader.size()
        if not source_size.isValid():
            return
        largest = max(source_size.width(), source_size.height())
        if largest <= self.MAX_IMAGE_PIXELS:
            return
        factor = self.MAX_IMAGE_PIXELS / largest
        reader.setScaledSize(
            QtCore.QSize(
                max(1, round(source_size.width() * factor)),
                max(1, round(source_size.height() * factor)),
            )
        )

    def add_image_from_pixmap(self, pixmap: QtGui.QPixmap) -> None:
        """Add a valid pixmap to the cover and select it."""
        if pixmap.isNull():
            QtWidgets.QMessageBox.warning(
                self, "Image error", "The clipboard does not contain a usable image."
            )
            return
        item = CoverImageItem(pixmap)
        self.scene.addItem(item)
        item.detach_handles()
        image_rect = QtCore.QRectF(item.pixmap().rect())
        item.setPos(
            QtCore.QPointF(
                (cover_width() - image_rect.width() * item.scale_x) / 2,
                (cover_height() - image_rect.height() * item.scale_y) / 2,
            )
        )
        artwork_z_values = (
            candidate.zValue()
            for candidate in self.scene.items()
            if candidate not in (self.grid_item, self.frame_item)
        )
        item.setZValue(max(5.0, max(artwork_z_values, default=5.0) + 1.0))
        self._select_and_focus(item)
        self.view.viewport().update()
        self.statusBar().showMessage(f"Image inserted: {pixmap.width()} x {pixmap.height()} px")

    def _select_and_focus(self, item: QtWidgets.QGraphicsItem) -> None:
        item.setSelected(True)
        self.scene.setFocusItem(item)
        self.view.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)
        self.view.ensureVisible(item)

    def delete_selected(self) -> None:
        """Remove the selected editable element from the scene."""
        item = self.selected_item()
        if item is None or item in (self.grid_item, self.frame_item):
            return
        if item is self.background_item:
            self.remove_background()
            return
        if isinstance(item, CoverImageItem):
            item.remove_handles_from_scene(self.scene)
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
        self.scene.suppress_snap = True
        try:
            item.setPos(self.x_spin.value(), self.y_spin.value())
        finally:
            self.scene.suppress_snap = False

    def nudge_selected(self, dx: int, dy: int) -> None:
        """Move the selected artwork by one millimetre, or five with Ctrl."""
        item = self.selected_item()
        if item is None or item in (self.grid_item, self.frame_item):
            return
        self.scene.suppress_snap = True
        try:
            item.setPos(item.pos() + QtCore.QPointF(float(dx), float(dy)))
        finally:
            self.scene.suppress_snap = False
        item.setSelected(True)
        self.scene.setFocusItem(item)

    def scale_selected(self, value: int) -> None:
        """Apply a relative scale to an image or text item."""
        item = self.selected_item()
        if item is None:
            return
        center_before = item.mapToScene(item.boundingRect().center())
        if isinstance(item, BackgroundImageItem):
            if not self._scale_background(item, value):
                return
        elif isinstance(item, CoverImageItem):
            item.set_user_scale(value / 100.0)
        elif isinstance(item, CoverTextItem):
            item.setScale(value / 100.0)
        else:
            return
        keep_center_stable(item, center_before)

    @staticmethod
    def _scale_background(item: BackgroundImageItem, value: int) -> bool:
        reference_scale = (item.reference_scale_x + item.reference_scale_y) / 2.0
        if reference_scale <= 0:
            return False
        ratio = value / 100.0
        item.scale_x = item.reference_scale_x * ratio
        item.scale_y = item.reference_scale_y * ratio
        item._apply_transform()
        item._update_handle_positions()
        return True

    def rotate_selected(self, value: float) -> None:
        """Apply a rotation while preserving the item's visual centre."""
        item = self.selected_item()
        if isinstance(item, CoverImageItem):
            item.set_rotation(value)
        elif item is not None:
            center_before = item.mapToScene(item.boundingRect().center())
            item.setTransformOriginPoint(item.boundingRect().center())
            item.setRotation(value)
            keep_center_stable(item, center_before)

    def choose_font(self) -> None:
        """Choose and apply a font to selected text."""
        item = self.selected_item()
        if not isinstance(item, CoverTextItem):
            return
        original_html = item.toHtml()
        dialog = QtWidgets.QFontDialog(item.font(), self)
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
            self._select_and_focus(item)
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
            self._select_and_focus(item)
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
        if self._closing or not self._scene_alive:
            return
        item = self.selected_item()
        if item is not None:
            self._active_item = item
        enabled = item is not None and item not in (self.grid_item, self.frame_item)
        self._set_control_enabled_state(item, enabled)
        if not enabled:
            return
        self._sync_position_spins(item)
        self._sync_scale_and_aspect(item)
        self._sync_rotation_spin(item)
        self._sync_background_combos(item)

    def _set_control_enabled_state(
        self,
        item: Optional[QtWidgets.QGraphicsItem],
        enabled: bool,
    ) -> None:
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

    def _sync_position_spins(self, item: QtWidgets.QGraphicsItem) -> None:
        blocker_x = QtCore.QSignalBlocker(self.x_spin)
        blocker_y = QtCore.QSignalBlocker(self.y_spin)
        self.x_spin.setValue(item.pos().x())
        self.y_spin.setValue(item.pos().y())
        del blocker_x, blocker_y

    def _sync_scale_and_aspect(self, item: QtWidgets.QGraphicsItem) -> None:
        blocker_scale = QtCore.QSignalBlocker(self.scale_slider)
        if isinstance(item, BackgroundImageItem):
            reference_scale = (item.reference_scale_x + item.reference_scale_y) / 2.0
            scale_percent = round(((item.scale_x + item.scale_y) / (2.0 * reference_scale)) * 100)
            self.scale_slider.setValue(
                max(self.scale_slider.minimum(), min(self.scale_slider.maximum(), scale_percent))
            )
        elif isinstance(item, CoverImageItem):
            blocker_aspect = QtCore.QSignalBlocker(self.aspect_check)
            self.aspect_check.setChecked(item.lock_aspect_ratio)
            del blocker_aspect
            item._update_handle_positions()
            self.scale_slider.setValue(
                round(((item.scale_x / item.base_scale) + (item.scale_y / item.base_scale)) * 50)
            )
        elif isinstance(item, CoverTextItem):
            self.scale_slider.setValue(round(item.scale() * 100))
        del blocker_scale

    def _sync_rotation_spin(self, item: QtWidgets.QGraphicsItem) -> None:
        blocker_rotation = QtCore.QSignalBlocker(self.rotation_spin)
        if isinstance(item, CoverImageItem):
            self.rotation_spin.setValue(item.rotation_angle())
        else:
            self.rotation_spin.setValue(item.rotation())
        del blocker_rotation

    def _sync_background_combos(self, item: QtWidgets.QGraphicsItem) -> None:
        if not isinstance(item, BackgroundImageItem):
            return
        size_index = self.background_size_combo.findData(item.size_mode)
        if size_index >= 0:
            self.background_size_combo.setCurrentIndex(size_index)
        blocker = QtCore.QSignalBlocker(self.background_rotation_combo)
        rotation_index = self.background_rotation_combo.findData(item.rotation_preset)
        self.background_rotation_combo.setCurrentIndex(rotation_index if rotation_index >= 0 else -1)
        del blocker

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
            str(Path(self._file_dialog_directory()) / "cover.pdf"),
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
            page_rect = self._pdf_page_rect(writer)
            CoverRenderer.render(
                self.scene,
                painter,
                page_rect,
                self.export_fold_guides_check.isChecked(),
            )
        finally:
            painter.end()

    @staticmethod
    def _pdf_page_rect(writer: QtGui.QPdfWriter) -> QtCore.QRectF:
        page_rect_points = writer.pageLayout().paintRect(QtGui.QPageLayout.Unit.Point)
        points_to_device = writer.resolution() / 72.0
        return QtCore.QRectF(
            page_rect_points.x() * points_to_device,
            page_rect_points.y() * points_to_device,
            page_rect_points.width() * points_to_device,
            page_rect_points.height() * points_to_device,
        )

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
