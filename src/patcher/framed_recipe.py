"""Source-bound scalar/data recipe for an uninstalled four-sided-frame base.

The protected patcher and its combined stage remain unchanged. Only explicit
source-declared terrain, scroll, command-coordinate and minimap slots change.
This module returns in-memory bytes; it has no executable output or runtime
path. Its base still contains the old C5 and owner-copy implementations and
must not be treated as an installed or accepted framed stage.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import struct

from . import patch_clash95_hd as patcher
from .framed_viewport import FramedViewport


SOURCE_STAGE = patcher.DEFAULT_STAGE + "-combinedui-validation"
FRAME_BASE_STAGE = patcher.DEFAULT_STAGE + "-combinedui-framed-base-validation"
PATCHER_SHA256 = "05f31359f93a0eb0b319679ee524b21c05cd3e86e485b7ebb92afc8e6da29f31"
TABLE_SHA256 = "6683ee66851d23a28d856a8576e6b58c9b1285e0766bb592b9cdb0847bc8c55c"

# Each entry names an existing recipe, not a byte-pattern search over an image.
# The registered source formula and encoding are checked before use.
_VALUE_GROUPS = (
    ("main-loops", "TX", (0x6423, 0x674B, 0x683A, 0x6907, 0x69CF, 0x6AC1, 0x6BEF)),
    ("main-loops", "TY", (0x63E9, 0x66F7, 0x6814, 0x68E1, 0x69A9, 0x6A93, 0x6B9F)),
    ("full-redraw-12x9", "TX", (0x17B70, 0x17DFF)),
    ("full-redraw-12x9", "TY-1", (0x17B81,)),
    ("full-redraw-present-bounds-800", "EDGEX", (0x17CDE, 0x17D6C, 0x17D82, 0x17E68)),
    ("full-redraw-present-bounds-800", "EDGEY", (0x17D99, 0x17E5E)),
    ("helpers", "TX", (0x7080, 0x71D5, 0xEF4E, 0xF35B, 0x17EA6, 0x17EDB,
                          0x18009, 0x18067, 0x18112)),
    ("helpers", "TY", (0x70B4, 0x7268, 0xEF66, 0xF39E, 0x17EB3, 0x18016, 0x18080, 0x1812A)),
    ("helpers", "-TX", (0x7087, 0xEF9D)),
    ("helpers", "-TY", (0x70BB, 0xEF6D)),
    ("helpers", "TX//2", (0xEF01,)),
    ("helpers", "TY//2", (0xEF18,)),
    ("helpers", "TY-1", (0x17ECC, 0x17EEC)),
    ("helpers", "-(TY+1)", (0x18087, 0x18131)),
    ("helpers", "-(TX+1)", (0x180C2, 0x18163)),
)
VALUE_SITES = {(group, offset): formula
               for group, formula, offsets in _VALUE_GROUPS for offset in offsets}
COMMAND_OFFSETS = (0x10FF40, 0x10FF75, 0x10FFAA, 0x10FFDF, 0x110014, 0x110049)
SPLICE_FORMULAS = {
    ("map-surface-upgrade-scrollclamp", 0xE8C80): ("TX", "TY"),
    ("helpers", 0xD0B0): ("TX",),
    ("helpers", 0xD0DA): ("TY",),
    ("helpers", 0xD124): ("TY",),
    ("minimap-hd-right-anchor", 0xC790): ("W",),
    **{("selected-unit-command-panel-right-bottom", offset):
       (("W-192", "W-128", "W-64")[index % 3], "H-72" if index < 3 else "H-40")
       for index, offset in enumerate(COMMAND_OFFSETS)},
}


class FramedRecipeError(ValueError):
    """The protected source or an explicit framed recipe contract changed."""


@dataclass(frozen=True)
class FramedCandidate:
    image: bytes
    patches: tuple[patcher.Patch, ...]
    metadata: dict
    installation_ready: bool = False


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FramedRecipeError(message)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_contract() -> None:
    _require(_digest(Path(patcher.__file__).read_bytes()) == PATCHER_SHA256,
             "protected patcher source SHA-256 differs")
    canonical = "\n".join(f"{p.group}|{p.offset:06X}|{p.old_hex}|{p.new_hex}|{p.note}"
                          for p in patcher.PATCHES)
    _require(_digest(canonical.encode("utf-8")) == TABLE_SHA256,
             "protected patch table identity differs")
    _require(FRAME_BASE_STAGE not in patcher.STAGE_GROUPS,
             "framed base must remain separate from installed patcher stages")


def _profile(profile: patcher.ResolutionProfile) -> FramedViewport:
    _require(isinstance(profile, patcher.ResolutionProfile), "expected a canonical ResolutionProfile")
    _require(type(profile.width) is int and type(profile.height) is int,
             "resolution dimensions must be integers, excluding booleans")
    # Revalidate in case a caller bypassed the frozen dataclass constructor.
    patcher.ResolutionProfile(profile.width, profile.height)
    return FramedViewport(profile.width, profile.height)


def _values(layout: FramedViewport) -> dict[str, int]:
    tx, ty = layout.full_tiles
    return {"TX": tx, "TY": ty, "TY-1": ty - 1, "-TX": -tx, "-TY": -ty,
            "TX//2": tx // 2, "TY//2": ty // 2, "-(TY+1)": -(ty + 1), "-(TX+1)": -(tx + 1),
            "EDGEX": layout.terrain.left + 64 * tx - 1,
            "EDGEY": layout.terrain.top + 64 * ty - 1,
            "W": layout.minimap_right_anchor,
            "W-192": layout.width - 224, "W-128": layout.width - 160, "W-64": layout.width - 96,
            "H-72": layout.height - 80, "H-40": layout.height - 48}


def _encoded(value: int, width: int, signed: bool, label: str) -> bytes:
    _require(type(value) is int and width in (1, 2, 4), "invalid source immediate encoding")
    try:
        return value.to_bytes(width, "little", signed=signed)
    except OverflowError as exc:
        raise FramedRecipeError(f"{label}: {value} does not fit signed={signed} width={width}") from exc


def _recipe(profile: patcher.ResolutionProfile):
    _source_contract()
    layout = _profile(profile)
    combined = tuple(patcher.select_patches_for(SOURCE_STAGE, profile))
    baseline = {(p.group, p.offset): p for p in combined}
    _require(len(baseline) == len(combined), "duplicate combined patch site")
    legacy = {(p.group, p.offset): p for p in patcher.PATCHES}
    selected = set(VALUE_SITES) | set(SPLICE_FORMULAS)
    _require(selected <= baseline.keys(), "missing required framed source recipe site")
    relevant_values = {key for key in baseline if key[0] in
                       {"main-loops", "full-redraw-12x9", "helpers", "full-redraw-present-bounds-800"}
                       and patcher.RECIPES.get(key, patcher.Recipe("")).kind == "value"}
    _require(relevant_values == VALUE_SITES.keys(), "terrain scalar recipe inventory differs")
    values = _values(layout)
    replacements = {}
    slots = []
    for key in sorted(selected):
        patch = baseline[key]
        source = legacy[key]
        recipe = patcher.RECIPES.get(key)
        _require(recipe is not None and patch.old == source.old,
                 f"source bytes or recipe missing at {key}")
        data = bytearray(patch.new)
        occupied = set()

        def record(at: int, width: int, signed: bool, formula: str) -> None:
            _require(0 <= at < at + width <= len(data), "framed slot exceeds its patch")
            positions = set(range(at, at + width))
            _require(not occupied & positions, "overlapping framed source slots")
            occupied.update(positions)
            expected_legacy = _encoded(patcher.FORMULAS[formula](patcher.PROFILE_800), width, signed, formula)
            expected_combined = _encoded(patcher.FORMULAS[formula](profile), width, signed, formula)
            _require(source.new[at:at + width] == expected_legacy,
                     f"legacy formula bytes differ at {key} +{at}")
            _require(patch.new[at:at + width] == expected_combined,
                     f"combined formula bytes differ at {key} +{at}")
            encoded = _encoded(values[formula], width, signed, "framed " + formula)
            data[at:at + width] = encoded
            slots.append(dict(group=patch.group, patch_file_offset=patch.offset,
                              file_offset=patch.offset + at, offset_in_patch=at, width=width, signed=signed,
                              source_formula=formula, source_value=int.from_bytes(expected_combined, "little", signed=signed),
                              framed_value=values[formula], original_hex=patch.old[at:at + width].hex(),
                              combined_old_hex=expected_combined.hex(), new_hex=encoded.hex(),
                              changed=encoded != expected_combined))

        if key in VALUE_SITES:
            formula = VALUE_SITES[key]
            _require(recipe.kind == "value" and recipe.value == formula,
                     f"terrain source formula differs at {key}")
            _require(len(patch.new) == (4 if formula in ("EDGEX", "EDGEY") else 1)
                     and recipe.signed == (formula not in ("EDGEX", "EDGEY")),
                     f"terrain immediate encoding differs at {key}")
            record(0, len(patch.new), recipe.signed, formula)
        else:
            _require(recipe.kind == "splice", f"source splice recipe differs at {key}")
            wanted = SPLICE_FORMULAS[key]
            fields = tuple(slot for slot in recipe.slots if slot.value in wanted)
            _require(tuple(slot.value for slot in fields) == wanted,
                     f"framed splice formula inventory differs at {key}")
            for slot in fields:
                pattern = bytes.fromhex(slot.pattern)
                _require(slot.count == 1 and 0 <= slot.at < slot.at + slot.width <= len(pattern),
                         f"source splice bounds/count differs at {key}")
                _require((slot.width, slot.signed) == ((1, True) if slot.value in ("TX", "TY") else (4, False)),
                         f"source splice immediate encoding differs at {key}")
                positions = [at for at in range(len(source.new) - len(pattern) + 1)
                             if source.new[at:at + len(pattern)] == pattern]
                _require(len(positions) == slot.count, f"source splice pattern missing or ambiguous at {key}")
                record(positions[0] + slot.at, slot.width, slot.signed, slot.value)
        changed = bytes(data) != patch.new
        replacements[key] = (replace(patch, new_hex=bytes(data).hex(),
                                     note=patch.note + " [framed base: explicit terrain/control scalar slots]")
                             if changed else patch)
    patches = tuple(replacements.get((p.group, p.offset), p) for p in combined)
    _require(len(patches) == len(combined), "framed selection changed patch count")
    for old, new in zip(combined, patches):
        _require((old.group, old.offset, old.old_hex, len(old.new)) ==
                 (new.group, new.offset, new.old_hex, len(new.new)), "framed recipe changed patch identity or size")
    return patches, combined, tuple(sorted(slots, key=lambda slot: slot["file_offset"])), layout


def select_patches_for(profile: patcher.ResolutionProfile) -> tuple[patcher.Patch, ...]:
    """Return original-to-framed base records; verify input before applying them.

    Existing C5 and owner-copy bytes are preserved, not accepted as the final
    framed renderer. Physical surface/input/menu recipes are passed through.
    """
    return _recipe(profile)[0]


def _apply_verified(original: bytes, patches: tuple[patcher.Patch, ...]) -> bytes:
    occupied = set()
    for patch in patches:
        width = len(patch.old)
        _require(width == len(patch.new) and 0 <= patch.offset <= len(original) - width,
                 "patch size or range differs")
        span = set(range(patch.offset, patch.offset + width))
        _require(not occupied & span, "overlapping source patch records")
        occupied.update(span)
        _require(original[patch.offset:patch.offset + width] == patch.old,
                 f"original old bytes differ at 0x{patch.offset:X}")
    return patcher.apply_patches(original, patches)


def _address(original: bytes, offset: int, size: int) -> tuple[int, int]:
    # The entire original is SHA-authenticated before parsing these PE fields.
    pe = struct.unpack_from("<I", original, 0x3C)[0]
    count, optional = struct.unpack_from("<H", original, pe + 6)[0], struct.unpack_from("<H", original, pe + 20)[0]
    image_base = struct.unpack_from("<I", original, pe + 24 + 28)[0]
    matches = []
    for index in range(count):
        pos = pe + 24 + optional + 40 * index
        rva, raw_size, raw = struct.unpack_from("<III", original, pos + 12)
        if raw and raw <= offset and offset + size <= raw + raw_size:
            matches.append(rva + offset - raw)
    _require(len(matches) == 1, "patch does not map to one file-backed PE section")
    return matches[0], image_base + matches[0]


def _highlow_rvas(original: bytes) -> set[int]:
    """Inspect loader fields in the already SHA-authenticated original."""
    pe = struct.unpack_from("<I", original, 0x3C)[0]
    count, optional = struct.unpack_from("<H", original, pe + 6)[0], struct.unpack_from("<H", original, pe + 20)[0]
    directory_rva, size = struct.unpack_from("<II", original, pe + 24 + 96 + 5 * 8)
    matches = []
    for index in range(count):
        pos = pe + 24 + optional + 40 * index
        rva, raw_size, raw = struct.unpack_from("<III", original, pos + 12)
        if raw and rva <= directory_rva and directory_rva + size <= rva + raw_size:
            matches.append(raw + directory_rva - rva)
    _require(len(matches) == 1, "original relocation directory is not file-backed")
    pos, end = matches[0], matches[0] + size
    result = set()
    while pos < end:
        _require(pos + 8 <= end, "truncated relocation block")
        page, block = struct.unpack_from("<II", original, pos)
        _require(block >= 8 and block % 2 == 0 and pos + block <= end, "invalid relocation block")
        for field in range(pos + 8, pos + block, 2):
            value = struct.unpack_from("<H", original, field)[0]
            kind = value >> 12
            _require(kind in (0, 3), "unexpected original relocation kind")
            if kind == 3:
                target = page + (value & 0xFFF)
                _require(target not in result, "duplicate original HIGHLOW field")
                result.add(target)
        pos += block
    return result


def canonical_candidate(original: bytes, width: int, height: int) -> FramedCandidate:
    """Verify known original + every old byte, return bytes and provenance only."""
    _require(type(original) is bytes and _digest(original) == patcher.EXPECTED_SHA256,
             "original executable SHA-256 mismatch")
    _require(type(width) is int and type(height) is int, "integer resolution dimensions required")
    patches, combined, slots, layout = _recipe(patcher.ResolutionProfile(width, height))
    source_image = _apply_verified(original, combined)
    image = _apply_verified(original, patches)
    # Prove all candidate differences from the combined base are exactly the
    # bytes in the declared scalar/data fields, including unchanged slot bytes.
    expected = bytearray(source_image)
    highlow = _highlow_rvas(original)
    for slot in slots:
        start = slot["file_offset"]
        _require(source_image[start:start + slot["width"]].hex() == slot["combined_old_hex"],
                 "source slot does not match verified combined image")
        expected[start:start + slot["width"]] = bytes.fromhex(slot["new_hex"])
        slot["rva"], slot["va"] = _address(original, start, slot["width"])
        _require(not any(slot["rva"] < field + 4 and field < slot["rva"] + slot["width"] for field in highlow),
                 "framed scalar slot overlaps an original HIGHLOW field")
    _require(bytes(expected) == image and len(image) == len(original),
             "framed candidate differs outside declared scalar slots")
    records = []
    for patch in patches:
        rva, va = _address(original, patch.offset, len(patch.old))
        records.append(dict(group=patch.group, file_offset=patch.offset, rva=rva, va=va,
                            old_hex=patch.old_hex, new_hex=patch.new_hex, rationale=patch.note))
    source_bindings = {name: dict(path=str(path.resolve()), sha256=_digest(path.read_bytes()))
                       for name, path in (("patcher", Path(patcher.__file__)),
                                          ("framed_recipe", Path(__file__)),
                                          ("framed_viewport", Path(__file__).with_name("framed_viewport.py")))}
    metadata = dict(schema_version=1, base_stage=FRAME_BASE_STAGE, source_stage=SOURCE_STAGE,
                    resolution=layout.resolution, original_sha256=_digest(original),
                    source_candidate_sha256=_digest(source_image), candidate_sha256=_digest(image),
                    source_bindings=source_bindings,
                    layout=dict(profile="native_four_border_tiles_v1", insets=[32, 16, 32, 16],
                                surface=list(layout.surface.as_tuple()), terrain=list(layout.terrain.as_tuple()),
                                full_tiles=list(layout.full_tiles), ceil_tiles=list(layout.ceil_tiles),
                                partial_pixels=list(layout.partial_pixels),
                                command_cells=[list(cell.as_tuple()) for cell in layout.action_cells],
                                minimap_exclusive_right=layout.minimap_right_anchor),
                    patches=records, declared_slots=list(slots),
                    changed_slots=[slot for slot in slots if slot["changed"]],
                    original_highlow_count=len(highlow), scalar_highlow_overlap=False,
                    installation_ready=False, frame_drawing_installed=False, input_hooks_installed=False,
                    presentation_installed=False, preserved_unaccepted_owner_groups=["right-bottom-compose-proof"],
                    limits="Scalar/data base only; old C5 and modal owner copies retained. Requires separate frame, input, terrain clipping, owner and presentation integration; no runtime or promotion proof.")
    metadata["patch_manifest_sha256"] = _digest(json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return FramedCandidate(image, patches, metadata)
