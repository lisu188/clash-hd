from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib
import json
import re
from typing import Any, Mapping


PLAN_SCHEMA = 1
RECIPE_REVISION = {"classic": "classic-frozen-800-v1", "framed": "four-border-partial-initial-v1"}
DEFAULT_BOUNDS = ((800, 600), (3840, 2160))
SHA256_RE = re.compile(r"[0-9a-f]{64}")
RESOLUTION_RE = re.compile(r"[1-9][0-9]{2,4}x[1-9][0-9]{2,4}")


class DisplayPlanError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise DisplayPlanError(code, message)


def _ints(*values: int) -> None:
    _require(all(type(value) is int for value in values), "invalid_type", "Pixel and tile values must be integers, excluding booleans.")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


def _sha(value: str) -> str:
    _require(type(value) is str and SHA256_RE.fullmatch(value) is not None,
             "invalid_identity", "Expected a lowercase SHA-256 identity.")
    return value


def _source_hashes(sources: Mapping[str, str]) -> dict[str, str]:
    _require(isinstance(sources, Mapping) and bool(sources), "invalid_identity", "Source identities must not be empty.")
    result = {}
    for name, digest in sources.items():
        _require(type(name) is str and bool(name) and "\\" not in name and ":" not in name
                 and all(part not in ("", ".", "..") for part in name.split("/")),
                 "invalid_identity", "Source identities require canonical repository-relative paths.")
        result[name] = _sha(digest)
    return result


def parse_dimensions(resolution: str, bounds: tuple[tuple[int, int], tuple[int, int]] = DEFAULT_BOUNDS) -> tuple[int, int]:
    _require(type(resolution) is str and RESOLUTION_RE.fullmatch(resolution) is not None,
             "invalid_resolution", "Resolution must use canonical ASCII WxH spelling, such as 1280x720.")
    try:
        (minimum_w, minimum_h), (maximum_w, maximum_h) = bounds
    except (TypeError, ValueError) as exc:
        raise DisplayPlanError("invalid_bounds", "Expected two width/height pairs for resolution bounds.") from exc
    _ints(minimum_w, minimum_h, maximum_w, maximum_h)
    _require(0 < minimum_w <= maximum_w and 0 < minimum_h <= maximum_h,
             "invalid_bounds", "Resolution bounds are inverted or nonpositive.")
    width, height = map(int, resolution.split("x"))
    _require(minimum_w <= width <= maximum_w and minimum_h <= height <= maximum_h,
             "outside_policy", f"Resolution must be between {minimum_w}x{minimum_h} and {maximum_w}x{maximum_h}.")
    _require(width % 2 == 0 and height % 2 == 0, "odd_dimensions", "Both render dimensions must be even.")
    return width, height


def _rect_tuple(rect: Any) -> tuple[int, int, int, int]:
    return tuple(rect.as_tuple())


@dataclass(frozen=True)
class DisplayPlan:
    renderer: str
    resolution: str
    stage: str
    recipe_revision: str
    width: int
    height: int
    scaling_mode: str
    minimap_viewport: bool
    native_offset: tuple[int, int]
    terrain: tuple[int, int, int, int]
    full_tiles: tuple[int, int]
    coverage_tiles: tuple[int, int]
    partial_pixels: tuple[int, int]
    frame_bands: tuple[tuple[int, int, int, int], ...]
    action_cells: tuple[tuple[int, int, int, int], ...]
    minimap_right_anchor: int | None
    scalar_patch_count: int
    scalar_patch_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps({"schema": PLAN_SCHEMA, **asdict(self),
            "recipe_eligible": True, "candidate_built": False,
            "game_runtime_executed": False, "manual_input_proof": False, "promotion_ready": False,
            "map_policy": "native full loop requires world >= full_tiles; smaller worlds remain blocked",
            "coverage_policy": "clipped ceiling cells" if self.renderer == "framed" else "native full-tile grid; legacy strips unchanged"}))

    def build_identity(self, original_sha256: str, sources: Mapping[str, str]) -> str:
        state = asdict(self)
        state.pop("scaling_mode")
        return _digest({"schema": PLAN_SCHEMA, "display": state,
                        "original_sha256": _sha(original_sha256), "source_sha256": _source_hashes(sources)})

    def world_view(self, map_width: int, map_height: int, scroll_x: int = 0, scroll_y: int = 0) -> WorldPlan:
        _ints(map_width, map_height, scroll_x, scroll_y)
        _require(1 <= map_width <= 100 and 1 <= map_height <= 100,
                 "invalid_world", "The native world backing supports 1..100 tiles per dimension.")
        max_x, max_y = max(0, map_width - self.full_tiles[0]), max(0, map_height - self.full_tiles[1])
        clamped = min(max(scroll_x, 0), max_x), min(max(scroll_y, 0), max_y)
        return WorldPlan(self, (map_width, map_height), (scroll_x, scroll_y), clamped, (max_x, max_y))


def resolve_display_plan(*, renderer: str = "classic", resolution: str = "800x600", stage: str | None = None,
                         scaling_mode: str = "integer", minimap_viewport: bool | None = None,
                         bounds: tuple[tuple[int, int], tuple[int, int]] = DEFAULT_BOUNDS) -> DisplayPlan:
    _require(type(renderer) is str and renderer in RECIPE_REVISION, "unknown_profile", "Renderer must be classic or framed.")
    width, height = parse_dimensions(resolution, bounds)
    _require(scaling_mode == "integer", "unsupported_presentation", "Only the verified integer wrapper scaling mode is supported.")
    _require(minimap_viewport is None or type(minimap_viewport) is bool,
             "invalid_feature", "minimap_viewport must be an explicit boolean.")
    minimap = renderer == "framed" if minimap_viewport is None else minimap_viewport
    _require(renderer == "framed" or not minimap, "invalid_feature", "Minimap viewport correction requires Framed.")
    try:
        patcher = importlib.import_module("patch_clash95_hd")
        selected_stage = patcher.DEFAULT_STAGE if stage is None else stage
        profile = patcher.parse_resolution(resolution)
        if renderer == "framed":
            required_stage = patcher.DEFAULT_STAGE + "-combinedui-partialtiles-initialpaint-framed-validation"
            _require(stage in (None, required_stage), "unsupported_stage", "Framed cannot use a Classic or unrelated stage.")
            selected_stage = required_stage
            recipe = importlib.import_module("src.patcher.framed_recipe")
            viewport = importlib.import_module("src.patcher.framed_viewport").FramedViewport(width, height)
            patches = recipe.select_patches_for(recipe.patcher.parse_resolution(resolution))
            terrain, full, coverage, partial = _rect_tuple(viewport.terrain), viewport.full_tiles, viewport.ceil_tiles, viewport.partial_pixels
            bands, cells = tuple(map(_rect_tuple, viewport.frame_bands)), tuple(map(_rect_tuple, viewport.action_cells))
            minimap_anchor = viewport.minimap_right_anchor
        else:
            _require(type(selected_stage) is str and selected_stage in patcher.STAGE_GROUPS,
                     "unsupported_stage", f"Unknown Classic patch stage: {selected_stage!r}")
            patches = patcher.select_patches_for(selected_stage, profile)
            terrain = patcher.TILE_ORIGIN_X, patcher.TILE_ORIGIN_Y, profile.edge_x, profile.edge_y
            full = coverage = profile.tiles_x, profile.tiles_y
            partial = profile.partial_col_px, profile.partial_row_px
            bands, cells = (), ()
            minimap_anchor = width if "minimap-hd-right-anchor" in patcher.STAGE_GROUPS[selected_stage] else None
        encoded = [{"group": p.group, "offset": p.offset, "old": p.old.hex(), "new": p.new.hex()} for p in patches]
        _require(bool(encoded), "unsupported_stage", "The selected recipe contains no patches.")
        return DisplayPlan(renderer, resolution, selected_stage, RECIPE_REVISION[renderer], width, height,
                           scaling_mode, minimap, (profile.off_x, profile.off_y), terrain, full, coverage, partial,
                           bands, cells, minimap_anchor, len(encoded), _digest(encoded))
    except DisplayPlanError:
        raise
    except ImportError as exc:
        raise DisplayPlanError("missing_recipe", f"Required renderer source is unavailable: {exc}") from exc
    except (OSError, ValueError) as exc:
        raise DisplayPlanError("recipe_rejected", f"The selected renderer recipe rejected {resolution}: {exc}") from exc


def deployment_identity(build_id: str, wrapper_sha256: str, config_sha256: str) -> str:
    return _digest({"schema": PLAN_SCHEMA, "build_id": _sha(build_id),
                    "wrapper_sha256": _sha(wrapper_sha256), "config_sha256": _sha(config_sha256)})


@dataclass(frozen=True)
class WorldCell:
    column: int
    row: int
    world_x: int
    world_y: int
    rect: tuple[int, int, int, int]
    in_world: bool


@dataclass(frozen=True)
class WorldPlan:
    display: DisplayPlan
    size: tuple[int, int]
    requested_scroll: tuple[int, int]
    scroll: tuple[int, int]
    max_scroll: tuple[int, int]

    @property
    def native_full_loop_safe(self) -> bool:
        return all(self.scroll[i] + self.display.full_tiles[i] <= self.size[i] for i in (0, 1))

    def require_native_full_loop(self) -> None:
        _require(self.native_full_loop_safe, "small_world_unsupported",
                 f"{self.display.renderer} {self.display.resolution} requires at least "
                 f"{self.display.full_tiles[0]}x{self.display.full_tiles[1]} world tiles for the current full renderer. "
                 "A bounded small-world renderer has not been installed.")

    def cells(self) -> tuple[WorldCell, ...]:
        left, top, right, bottom = self.display.terrain
        return tuple(WorldCell(col, row, self.scroll[0] + col, self.scroll[1] + row,
            (left + 64 * col, top + 64 * row, min(left + 64 * col + 63, right), min(top + 64 * row + 63, bottom)),
            self.scroll[0] + col < self.size[0] and self.scroll[1] + row < self.size[1])
            for row in range(self.display.coverage_tiles[1]) for col in range(self.display.coverage_tiles[0]))

    def tile_at(self, x: int, y: int, *, excluded: tuple[tuple[int, int, int, int], ...] = ()) -> tuple[int, int] | None:
        _ints(x, y)
        left, top, right, bottom = self.display.terrain
        for rectangle in excluded:
            _validate_rect(rectangle)
        if not (left <= x <= right and top <= y <= bottom) or any(l <= x <= r and t <= y <= b for l, t, r, b in excluded):
            return None
        world_x, world_y = self.scroll[0] + (x - left) // 64, self.scroll[1] + (y - top) // 64
        return (world_x, world_y) if world_x < self.size[0] and world_y < self.size[1] else None

    def to_dict(self) -> dict[str, Any]:
        cells = self.cells()
        return {"map_size": list(self.size), "requested_scroll": list(self.requested_scroll), "scroll": list(self.scroll),
                "max_scroll": list(self.max_scroll), "scroll_was_clamped": self.requested_scroll != self.scroll,
                "native_full_loop_safe": self.native_full_loop_safe,
                "valid_cell_count": sum(cell.in_world for cell in cells),
                "outside_world_cell_count": sum(not cell.in_world for cell in cells),
                "bounded_renderer_installed": False}


def _validate_rect(rect: tuple[int, int, int, int]) -> None:
    _require(isinstance(rect, (tuple, list)) and len(rect) == 4, "invalid_rectangle", "Expected an inclusive L,T,R,B rectangle.")
    _ints(*rect)
    _require(rect[0] <= rect[2] and rect[1] <= rect[3], "invalid_rectangle", "Rectangle is empty or inverted.")


@dataclass(frozen=True)
class PresentationTransform:
    render_width: int
    render_height: int
    left: int
    top: int
    width: int
    height: int

    def __post_init__(self) -> None:
        _ints(self.render_width, self.render_height, self.left, self.top, self.width, self.height)
        _require(min(self.render_width, self.render_height, self.width, self.height) > 0,
                 "invalid_presentation", "Render and presentation dimensions must be positive.")

    @classmethod
    def integer_fit(cls, render_width: int, render_height: int, client_width: int, client_height: int,
                    left: int = 0, top: int = 0) -> PresentationTransform:
        _ints(render_width, render_height, client_width, client_height, left, top)
        _require(min(render_width, render_height, client_width, client_height) > 0,
                 "invalid_presentation", "Render and client dimensions must be positive.")
        scale = min(client_width // render_width, client_height // render_height)
        _require(scale >= 1, "presentation_too_small", "Integer scaling cannot fit the render surface inside this client area.")
        width, height = render_width * scale, render_height * scale
        return cls(render_width, render_height, left + (client_width - width) // 2,
                   top + (client_height - height) // 2, width, height)

    def render_point(self, x: int, y: int) -> tuple[int, int] | None:
        _ints(x, y)
        if not (self.left <= x < self.left + self.width and self.top <= y < self.top + self.height):
            return None
        return (x - self.left) * self.render_width // self.width, (y - self.top) * self.render_height // self.height

    def relative_sample(self, dx: int, dy: int, remainder: tuple[int, int] = (0, 0)) -> tuple[tuple[int, int], tuple[int, int]]:
        _require(isinstance(remainder, tuple) and len(remainder) == 2,
                 "invalid_remainder", "Relative input requires two integer remainder values.")
        _ints(dx, dy, *remainder)
        _require(abs(remainder[0]) < self.width and abs(remainder[1]) < self.height,
                 "invalid_remainder", "Remainders must belong to the current presentation geometry.")
        output, rest = [], []
        for delta, retained, numerator, denominator in ((dx, remainder[0], self.render_width, self.width),
                                                       (dy, remainder[1], self.render_height, self.height)):
            value = delta * numerator + retained
            whole = (abs(value) // denominator) * (-1 if value < 0 else 1)
            output.append(whole)
            rest.append(value - whole * denominator)
        return tuple(output), tuple(rest)


@dataclass(frozen=True)
class SurfaceLayout:
    width: int
    height: int
    pitch: int
    bytes_per_pixel: int = 1

    def __post_init__(self) -> None:
        _ints(self.width, self.height, self.pitch, self.bytes_per_pixel)
        _require(0 < self.width <= 32767 and 0 < self.height <= 32767 and self.bytes_per_pixel in (1, 2, 3, 4)
                 and abs(self.pitch) >= self.width * self.bytes_per_pixel,
                 "invalid_surface", "Surface dimensions, pixel format, or pitch are invalid.")
        _require(self.required_bytes <= 0x7FFFFFFF, "surface_overflow", "Surface addressing exceeds the bounded 32-bit range.")

    @property
    def required_bytes(self) -> int:
        return (self.height - 1) * abs(self.pitch) + self.width * self.bytes_per_pixel

    def row_offset(self, y: int) -> int:
        _ints(y)
        _require(0 <= y < self.height, "surface_bounds", "Scan line lies outside the surface.")
        return y * self.pitch if self.pitch > 0 else (self.height - 1 - y) * -self.pitch

    def byte_spans(self, rect: tuple[int, int, int, int], buffer_size: int) -> tuple[tuple[int, int], ...]:
        _validate_rect(rect)
        _ints(buffer_size)
        left, top, right, bottom = rect
        _require(buffer_size >= self.required_bytes and 0 <= left <= right < self.width and 0 <= top <= bottom < self.height,
                 "surface_bounds", "Rectangle or backing allocation is outside the surface.")
        return tuple((self.row_offset(y) + left * self.bytes_per_pixel, (right - left + 1) * self.bytes_per_pixel)
                     for y in range(top, bottom + 1))
