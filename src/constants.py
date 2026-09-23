"""Physical page sizes, bleed, and jewel-case cover specifications."""

from dataclasses import dataclass


MM_PER_INCH = 25.4
PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0
BLEED_MM = 3.0

# Extra height trimmed from extended-cover flap edges (Slim-case geometry).
EXTENDED_FLAP_INSET_MM = 2.0

# Snap distance in millimetres for edges, centres, and fold guides.
SNAP_THRESHOLD_MM = 2.0

# Keyboard nudge distances in millimetres.
NUDGE_STEP_MM = 1.0
NUDGE_STEP_LARGE_MM = 5.0


@dataclass(frozen=True)
class CoverSpec:
    """Physical dimensions and vertical fold guides for one cover format.

    Attributes:
        key: Stable identifier used by layout and painting logic.
        label: Human-readable name shown in the cover-type combo box.
        width_mm: Cut-line width of the format.
        height_mm: Cut-line height of the format.
        guides: X positions (mm from the left cut line) of fold/score marks.
    """

    key: str
    label: str
    width_mm: float
    height_mm: float
    guides: tuple[float, ...] = ()


COVER_SPECS = (
    CoverSpec("front", "Front Cover (Jewel/Slim) — 120 × 120 mm", 120.0, 120.0),
    CoverSpec("booklet", "Front Booklet (Jewel/Slim) — 240 × 120 mm", 240.0, 120.0, (120.0,)),
    CoverSpec("back", "Back Inlay (Jewel) — 152 × 118 mm", 152.0, 118.0, (6.0, 146.0)),
    CoverSpec("tray", "Tray Inlay (Jewel) — 152 × 118 mm", 152.0, 118.0, (6.0, 146.0)),
    CoverSpec("cass_front", "Front Cover (Cassette) — 97 × 102 mm", 97.0, 102.0, (20.0, 32.0)),
    CoverSpec("cass_booklet", "Front Booklet (Cassette) — 162 × 102 mm", 162.0, 102.0, (20.0, 32.0, 97.0)),
)
