"""Pure geometry for a prospective native four-sided-frame validation stage.

The physical surface stays W by H. Native 32-pixel side bands and 16-pixel
top/bottom bands reserve terrain (32,16)..(W-33,H-17), inclusive. Controls
overlay that terrain, never the frame. At 640x480 this preserves the native
action anchor (416,400) and exclusive minimap right anchor 608.

This module installs nothing, changes no existing resolution/stage recipe,
and supplies no rendering, input or promotion evidence. A valid geometry plan
is not permission to call the native full loop on a smaller world.
"""
from __future__ import annotations

from dataclasses import dataclass


SIDE_FRAME = 32
HORIZONTAL_FRAME = 16
TILE_SIZE = 64
MAX_WORLD_TILES = 100
MAX_SURFACE_SIZE = 8192  # Bounded like the standalone clipping adapters.


def _integers(*values: int) -> None:
    if any(type(value) is not int for value in values):
        raise ValueError("geometry requires integers, excluding booleans")


@dataclass(frozen=True)
class Rect:
    """Nonempty inclusive pixel rectangle; no implied draw or ownership claim."""

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        _integers(self.left, self.top, self.right, self.bottom)
        if min(self.left, self.top) < 0 or self.right < self.left or self.bottom < self.top:
            raise ValueError("invalid nonempty inclusive rectangle")

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1

    @property
    def area(self) -> int:
        return self.width * self.height

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom

    def contains(self, other: Rect) -> bool:
        return (self.left <= other.left <= other.right <= self.right
                and self.top <= other.top <= other.bottom <= self.bottom)

    def intersection(self, other: Rect) -> Rect | None:
        left, top = max(self.left, other.left), max(self.top, other.top)
        right, bottom = min(self.right, other.right), min(self.bottom, other.bottom)
        return Rect(left, top, right, bottom) if left <= right and top <= bottom else None


@dataclass(frozen=True)
class FramedViewport:
    """Immutable proposed layout, including native size for a geometry oracle.

    Even dimensions retain integral native-screen centering. The geometry
    accepts 640x480 for comparison; it does not register that size, or any size,
    as supported by the current patcher/launcher. The 8192 cap matches existing
    standalone clipping bounds, not a claim of usable game resolution.
    """

    width: int
    height: int

    def __post_init__(self) -> None:
        _integers(self.width, self.height)
        if not (640 <= self.width <= MAX_SURFACE_SIZE and 480 <= self.height <= MAX_SURFACE_SIZE):
            raise ValueError("framed geometry requires 640..8192 by 480..8192")
        if self.width % 2 or self.height % 2:
            raise ValueError("even dimensions are required for native-screen centering")

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    @property
    def surface(self) -> Rect:
        return Rect(0, 0, self.width - 1, self.height - 1)

    @property
    def terrain(self) -> Rect:
        return Rect(SIDE_FRAME, HORIZONTAL_FRAME,
                    self.width - SIDE_FRAME - 1, self.height - HORIZONTAL_FRAME - 1)

    @property
    def frame_bands(self) -> tuple[Rect, Rect, Rect, Rect]:
        """Disjoint top, bottom, left, right bands; horizontal bands own corners."""
        return (Rect(0, 0, self.width - 1, HORIZONTAL_FRAME - 1),
                Rect(0, self.height - HORIZONTAL_FRAME, self.width - 1, self.height - 1),
                Rect(0, HORIZONTAL_FRAME, SIDE_FRAME - 1, self.height - HORIZONTAL_FRAME - 1),
                Rect(self.width - SIDE_FRAME, HORIZONTAL_FRAME,
                     self.width - 1, self.height - HORIZONTAL_FRAME - 1))

    @property
    def full_tiles(self) -> tuple[int, int]:
        return self.terrain.width // TILE_SIZE, self.terrain.height // TILE_SIZE

    @property
    def ceil_tiles(self) -> tuple[int, int]:
        return ((self.terrain.width + TILE_SIZE - 1) // TILE_SIZE,
                (self.terrain.height + TILE_SIZE - 1) // TILE_SIZE)

    @property
    def partial_pixels(self) -> tuple[int, int]:
        return self.terrain.width % TILE_SIZE, self.terrain.height % TILE_SIZE

    @property
    def action_bar(self) -> Rect:
        return Rect(self.width - 224, self.height - 80,
                    self.terrain.right, self.terrain.bottom)

    @property
    def action_cells(self) -> tuple[Rect, ...]:
        """Six native 64x32 footprints in descriptor order: upper row, lower row."""
        left, top = self.action_bar.left, self.action_bar.top
        return tuple(Rect(left + 64 * col, top + 32 * row,
                          left + 64 * col + 63, top + 32 * row + 31)
                     for row in range(2) for col in range(3))

    @property
    def minimap_right_anchor(self) -> int:
        """Exclusive right edge used by native left = anchor - actual width."""
        return self.width - SIDE_FRAME

    def minimap_box(self, width: int, height: int) -> Rect:
        """Use the caller's actual backing dimensions, not FRAME sprite size.

        Native sub_40D330 stores y=16 and left=608-backing_width. Its backing
        dimensions vary with world size/scale (214x214 for a 100x100 world);
        FRAME sprite 4 itself is 214x213 and is not the backing-size contract.
        This only establishes containment. An unusual caller-supplied box may
        overlap other terrain overlays; ownership/composition requires its own
        source contract and is not inferred from this rectangle.
        """
        _integers(width, height)
        if not (1 <= width <= self.terrain.width and 1 <= height <= self.terrain.height):
            raise ValueError("minimap backing dimensions must fit inside the framed terrain")
        return Rect(self.minimap_right_anchor - width, HORIZONTAL_FRAME,
                    self.minimap_right_anchor - 1, HORIZONTAL_FRAME + height - 1)

    def cell_rect(self, column: int, row: int) -> Rect:
        """Clip a visible screen tile to the terrain, excluding every frame pixel."""
        _integers(column, row)
        columns, rows = self.ceil_tiles
        if not (0 <= column < columns and 0 <= row < rows):
            raise ValueError("screen cell lies outside the ceiling viewport")
        left, top = SIDE_FRAME + TILE_SIZE * column, HORIZONTAL_FRAME + TILE_SIZE * row
        return Rect(left, top, min(left + TILE_SIZE - 1, self.terrain.right),
                    min(top + TILE_SIZE - 1, self.terrain.bottom))

    def world_view(self, map_width: int, map_height: int,
                   scroll_x: int = 0, scroll_y: int = 0) -> WorldView:
        return WorldView(self, map_width, map_height, scroll_x, scroll_y)


@dataclass(frozen=True)
class CellPlan:
    column: int
    row: int
    world_x: int
    world_y: int
    rect: Rect
    in_world: bool

    @property
    def partial(self) -> bool:
        return self.rect.width != TILE_SIZE or self.rect.height != TILE_SIZE


@dataclass(frozen=True)
class WorldView:
    """Bounded world/scroll geometry, with outside-world cells kept explicit.

    Smaller worlds may safely be described for a future guarded renderer which
    clears ALL outside-world cells. They cannot enter the unguarded native full
    loop merely because this plan is valid; check ``native_full_loop_safe``.
    No tile pointers, draw results, or visibility evidence are manufactured.
    """

    layout: FramedViewport
    map_width: int
    map_height: int
    scroll_x: int = 0
    scroll_y: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.layout, FramedViewport):
            raise ValueError("world view requires a validated framed layout")
        _integers(self.map_width, self.map_height, self.scroll_x, self.scroll_y)
        if not (1 <= self.map_width <= MAX_WORLD_TILES and 1 <= self.map_height <= MAX_WORLD_TILES):
            raise ValueError("world dimensions must fit the native 1..100 backing grid")
        max_x, max_y = self.max_scroll
        if not (0 <= self.scroll_x <= max_x and 0 <= self.scroll_y <= max_y):
            raise ValueError("scroll lies outside the full-tile clamp")

    @property
    def max_scroll(self) -> tuple[int, int]:
        cols, rows = self.layout.full_tiles
        return max(0, self.map_width - cols), max(0, self.map_height - rows)

    @property
    def native_full_loop_safe(self) -> bool:
        cols, rows = self.layout.full_tiles
        return self.scroll_x + cols <= self.map_width and self.scroll_y + rows <= self.map_height

    def require_native_full_loop(self) -> None:
        if not self.native_full_loop_safe:
            raise ValueError("native full loop would form outside-world tile pointers")

    def cell(self, column: int, row: int) -> CellPlan:
        rect = self.layout.cell_rect(column, row)
        x, y = self.scroll_x + column, self.scroll_y + row
        return CellPlan(column, row, x, y, rect, x < self.map_width and y < self.map_height)

    def cells(self, *, partial_only: bool = False) -> tuple[CellPlan, ...]:
        if type(partial_only) is not bool:
            raise ValueError("partial_only must be a boolean")
        cols, rows = self.layout.ceil_tiles
        full_cols, full_rows = self.layout.full_tiles
        return tuple(self.cell(col, row) for row in range(rows) for col in range(cols)
                     if not partial_only or col >= full_cols or row >= full_rows)
