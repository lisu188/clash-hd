"""Geometry contract for the isolated 1280x720 tactical battle lane.

Rectangles are half-open. Battle map dimensions remain owned by the game;
this profile changes only the number of cells visible on screen.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BattleLayout:
    width: int = 1280
    height: int = 720
    tile_size: int = 64
    columns: int = 17
    rows: int = 7
    left: int = 32
    top: int = 136
    sidebar_left: int = 1120
    band_top: int = 120
    band_height: int = 480

    @property
    def battlefield(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.sidebar_left, self.top + self.rows * self.tile_size

    @property
    def sidebar(self) -> tuple[int, int, int, int]:
        return self.sidebar_left, self.band_top, self.width, self.band_top + self.band_height

    @property
    def sidebar_offset(self) -> tuple[int, int]:
        return self.sidebar_left - 480, self.band_top

    def clamp_camera(self, column: int, arena_columns: int) -> int:
        return min(max(0, column), max(0, arena_columns - self.columns))

    def visible_columns(self, arena_columns: int, camera: int = 0) -> int:
        return max(0, min(self.columns, arena_columns - self.clamp_camera(camera, arena_columns)))

    def cell_at(self, x: int, y: int, arena_columns: int, camera: int = 0) -> tuple[int, int] | None:
        left, top, right, bottom = self.battlefield
        if not (left <= x < right and top <= y < bottom):
            return None
        column = (x - left) // self.tile_size + self.clamp_camera(camera, arena_columns)
        if column >= arena_columns:
            return None
        return column, (y - top) // self.tile_size

    def recenter(self, selected_column: int, arena_columns: int, camera: int) -> int:
        camera = self.clamp_camera(camera, arena_columns)
        if camera <= selected_column < camera + self.columns:
            return camera
        return self.clamp_camera(selected_column - self.columns // 2, arena_columns)


BATTLE_LAYOUT = BattleLayout()
