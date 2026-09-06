"""Native-size army portraits contained by the physical four-sided frame.

This is geometry only. MARKS.S32 sprite 35 is 387x66, including its opaque
outer pixels. Its native (29,400) anchor therefore moves by (3,H-482),
leaving every pixel inside the 32px side and 16px bottom frame bands.
"""
from __future__ import annotations

from dataclasses import dataclass

from .framed_viewport import FramedViewport, Rect, _integers


@dataclass(frozen=True)
class FramedArmyViewport:
    width: int
    height: int

    def __post_init__(self) -> None:
        framed = FramedViewport(self.width, self.height)
        # At native640 the shifted backing intersects the action dock. This
        # adapter is exclusively an HD lane, not a change to native640 geometry.
        if self.width < 800 or self.height < 600:
            raise ValueError("army HD geometry requires at least 800x600")
        if not framed.terrain.contains(self.backing) or self.backing.intersection(framed.action_bar):
            raise ValueError("army backing intersects the frame or action dock")

    @property
    def framed(self) -> FramedViewport:
        return FramedViewport(self.width, self.height)

    @property
    def dx(self) -> int:
        return 3

    @property
    def dy(self) -> int:
        return self.height - 482

    @property
    def backing(self) -> Rect:
        return Rect(32, self.height - 82, 418, self.height - 17)

    @property
    def hit(self) -> Rect:
        # Preserve the native 64px click height and ten38px cells. The
        # decorative backing's last two rows are excluded from map clicks too.
        return Rect(38, self.height - 82, 417, self.height - 19)

    def portrait(self, slot: int) -> Rect:
        _integers(slot)
        if not 0 <= slot < 10:
            raise ValueError("portrait slot must be0..9")
        return Rect(38 + slot * 38, self.height - 81,
                    69 + slot * 38, self.height - 18)

    def pixel_to_slot(self, x: int, y: int, count: int = 10) -> int | None:
        _integers(x, y, count)
        if not 0 <= count <= 10:
            raise ValueError("squad count must be0..10")
        if not (self.hit.left <= x <= self.hit.right and self.hit.top <= y <= self.hit.bottom):
            return None
        slot = (x - self.hit.left) // 38
        return slot if slot < count else None

    def excludes_map_pixel(self, x: int, y: int) -> bool:
        _integers(x, y)
        return self.backing.left <= x <= self.backing.right and self.backing.top <= y <= self.backing.bottom
