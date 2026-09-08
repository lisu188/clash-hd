"""Geometry for a wider tactical view with native-size artwork.

This installs no patch and supplies no runtime/input acceptance. The combat
arena keeps its native seven rows and actual column count. Only the visible
column count changes. Whole columns avoid exposing a partially clickable cell;
space outside the arena is explicitly inert, including the gap before the HUD.

The native field origin stays (32,16), retaining animation Y coordinates.
The 160-pixel HUD uses its own native backing, never the expanded field's
pixels at x480. Drawing/copy ownership must be implemented separately.
"""
from __future__ import annotations

from dataclasses import dataclass

from .framed_viewport import FramedViewport, Rect

TILE = 64
ARENA_ROWS = 7
MAX_ARENA_COLUMNS = 20
HUD_WIDTH = 160
NATIVE_HUD_LEFT = 480
# Native command descriptor514B78 starts at y370. Its lower panel is copied
# with the surrounding native frame; actual sprite/draw coverage remains a
# separate source and runtime contract.
NATIVE_BOTTOM_PANEL_TOP = 368


def _ints(*values):
    if any(type(v) is not int for v in values):
        raise ValueError("tactical geometry requires integers, excluding booleans")


@dataclass(frozen=True)
class HudSlice:
    source: Rect
    destination: Rect

    def __post_init__(self):
        if (self.source.width, self.source.height) != (self.destination.width, self.destination.height):
            raise ValueError("native-size HUD copies must not scale")


@dataclass(frozen=True)
class TacticalViewport:
    width: int
    height: int
    world_columns: int

    def __post_init__(self):
        _ints(self.width, self.height, self.world_columns)
        FramedViewport(self.width, self.height)
        if not 1 <= self.world_columns <= MAX_ARENA_COLUMNS:
            raise ValueError("arena columns must fit the native twenty-column storage")

    @property
    def visible_columns(self):
        return min(self.world_columns, (self.width - 32 - HUD_WIDTH) // TILE)

    @property
    def max_scroll_x(self):
        return self.world_columns - self.visible_columns

    @property
    def arena(self):
        return Rect(32, 16, 32 + self.visible_columns * TILE - 1, 16 + ARENA_ROWS * TILE - 1)

    @property
    def surface(self):
        return Rect(0, 0, self.width - 1, self.height - 1)

    @property
    def frame_bands(self):
        """Battle chrome geometry only; source-pixel composition is separate.

        The right band is16 pixels. The native tactical HUD reaches x623/624;
        copying the map's32-pixel right band would cover those controls.
        """
        return (Rect(0, 0, self.width - 1, 15),
                Rect(0, self.height - 16, self.width - 1, self.height - 1),
                Rect(0, 16, 31, self.height - 17),
                Rect(self.width - 16, 16, self.width - 1, self.height - 17))

    @property
    def hud(self):
        return Rect(self.width - HUD_WIDTH, 0, self.width - 1, self.height - 1)

    @property
    def hud_slices(self):
        left = self.width - HUD_WIDTH
        return (
            HudSlice(Rect(NATIVE_HUD_LEFT, 0, 639, NATIVE_BOTTOM_PANEL_TOP - 1),
                     Rect(left, 0, self.width - 1, NATIVE_BOTTOM_PANEL_TOP - 1)),
            HudSlice(Rect(NATIVE_HUD_LEFT, NATIVE_BOTTOM_PANEL_TOP, 639, 479),
                     Rect(left, self.height - (480 - NATIVE_BOTTOM_PANEL_TOP), self.width - 1, self.height - 1)),
        )

    def clamp_scroll(self, requested_x):
        _ints(requested_x)
        return max(0, min(requested_x, self.max_scroll_x))

    def _scroll(self, scroll_x):
        _ints(scroll_x)
        if not 0 <= scroll_x <= self.max_scroll_x:
            raise ValueError("scroll origin is outside the expanded view")

    def screen_to_cell(self, x, y, *, scroll_x):
        """Reject all out-of-arena coordinates before any native array index."""
        _ints(x, y)
        self._scroll(scroll_x)
        box = self.arena
        if not (box.left <= x <= box.right and box.top <= y <= box.bottom):
            return None
        return scroll_x + (x - box.left) // TILE, (y - box.top) // TILE

    def world_cell_rect(self, column, row, *, scroll_x):
        _ints(column, row)
        self._scroll(scroll_x)
        if not (0 <= column < self.world_columns and 0 <= row < ARENA_ROWS):
            raise ValueError("cell is outside the native combat arena")
        if not scroll_x <= column < scroll_x + self.visible_columns:
            return None
        x = 32 + (column - scroll_x) * TILE
        y = 16 + row * TILE
        return Rect(x, y, x + TILE - 1, y + TILE - 1)

    def hud_to_native(self, x, y):
        """Coordinates in decorative HUD padding never reach descriptors."""
        _ints(x, y)
        for part in self.hud_slices:
            dest = part.destination
            if dest.left <= x <= dest.right and dest.top <= y <= dest.bottom:
                return part.source.left + x - dest.left, part.source.top + y - dest.top
        return None

    def native_hud_to_screen(self, x, y):
        _ints(x, y)
        for part in self.hud_slices:
            source = part.source
            if source.left <= x <= source.right and source.top <= y <= source.bottom:
                return part.destination.left + x - source.left, part.destination.top + y - source.top
        return None
