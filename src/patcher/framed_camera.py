"""Source-bound, equal-length camera-clamp upgrade for framed candidates."""
from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
import struct
import sys
from typing import Any

from . import pe_extension as pe
from .framed_viewport import FramedViewport

ROOT = Path(__file__).resolve().parents[2]
PARENT_BUILDER_SHA256 = "4178745fabb1e2270efcbdc72bf4999f97b0bca23bdad78db743a5db1b724d7a"
PARENT_STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
                "presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation")
STAGE = PARENT_STAGE.removesuffix("-validation") + "-camera-clamp-validation"
GAME_DATA_GLOBAL = 0x5202E4
MAP_DIMENSIONS = (0x222E0, 0x222E4)
MAP_SCROLL = (0x222E8, 0x222EC)
GATE_SIZE = 124
GATE_OFFSETS = {"full_redraw": 37, "initial_paint": 55}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _u32(value: int) -> bytes:
    require(type(value) is int and 0 <= value < 1 << 32, "value exceeds PE32 addressing")
    return struct.pack("<I", value)


class _Code:
    def __init__(self, va: int):
        _u32(va)
        self.va = va
        self.data = bytearray()

    def emit(self, value: str) -> None:
        self.data.extend(bytes.fromhex(value))

    def integer(self, value: int) -> None:
        self.data.extend(_u32(value))

    def branch(self, opcode: str, target: int) -> None:
        _u32(target)
        self.emit(opcode)
        delta = target - (self.va + len(self.data) + 4)
        require(-(1 << 31) <= delta < 1 << 31, "branch displacement exceeds rel32")
        self.data.extend(struct.pack("<i", delta))


def _geometry(layout: FramedViewport, va: int, reject_va: int) -> None:
    require(isinstance(layout, FramedViewport), "expected framed geometry")
    require(all(1 <= n <= 100 for n in layout.full_tiles), "viewport exceeds the native world backing")
    _u32(va)
    _u32(reject_va)
    require(va + GATE_SIZE < 1 << 32 and not va <= reject_va < va + GATE_SIZE,
            "invalid gate extent or rejection target")


def old_gate(layout: FramedViewport, va: int, reject_va: int) -> bytes:
    _geometry(layout, va, reject_va)
    a = _Code(va)
    for dimension, scroll, count in zip(MAP_DIMENSIONS, MAP_SCROLL, layout.full_tiles):
        a.emit("8b82"); a.integer(dimension)
        a.emit("83f801"); a.branch("0f8c", reject_va)
        a.emit("83f864"); a.branch("0f8f", reject_va)
        a.emit("3d"); a.integer(count); a.branch("0f8c", reject_va)
        a.emit("2d"); a.integer(count)
        a.emit("8b8a"); a.integer(scroll)
        a.emit("85c9"); a.branch("0f88", reject_va)
        a.emit("39c1"); a.branch("0f8f", reject_va)
    require(len(a.data) == GATE_SIZE, "legacy gate size differs")
    return bytes(a.data)


def camera_gate(layout: FramedViewport, va: int, reject_va: int) -> bytes:
    """EDX is gameData. Both dimensions pass before either scroll is stored."""
    _geometry(layout, va, reject_va)
    a = _Code(va)
    for dimension, count in zip(MAP_DIMENSIONS, layout.full_tiles):
        a.emit("8b82"); a.integer(dimension)
        a.emit("3d"); a.integer(count); a.branch("0f8c", reject_va)
        a.emit("83f864"); a.branch("0f8f", reject_va)
    for dimension, scroll, count in zip(MAP_DIMENSIONS, MAP_SCROLL, layout.full_tiles):
        a.emit("8b82"); a.integer(dimension)
        a.emit("2d"); a.integer(count)
        a.emit("8b8a"); a.integer(scroll)
        a.emit("85c9790231c939c17e0289c1898a"); a.integer(scroll)
    require(len(a.data) <= GATE_SIZE, "camera gate exceeds the authenticated allocation")
    a.data.extend(b"\x90" * (GATE_SIZE - len(a.data)))
    return bytes(a.data)


def _prefix(kind: str, va: int, entries: dict[str, int]) -> bytes:
    a = _Code(va)
    if kind == "full_redraw":
        a.emit("9c6089e583ec1055")
        a.branch("e8", entries["composition_guard"])
        a.emit("5d83f801"); a.branch("0f85", entries["framed_full_fallback"])
        reject = entries["framed_full_reject"]
    else:
        a.emit("60833d"); a.integer(0x527C24); a.emit("00")
        reject = entries["initial_admission_reject"]
        a.branch("0f84", reject)
        a.branch("e8", entries["composition_guard"])
        a.emit("83f801"); a.branch("0f85", reject)
        a.emit("833d"); a.integer(0x52698C); a.emit("00"); a.branch("0f85", reject)
    a.emit("8b15"); a.integer(GAME_DATA_GLOBAL)
    a.emit("85d2"); a.branch("0f84", reject)
    require(len(a.data) == GATE_OFFSETS[kind], "entry prefix size differs")
    return bytes(a.data)


def _upgrade_verified_parent(parent: bytes, metadata: dict[str, Any], resolution: str):
    """Private byte operation. Public callers must construct the parent from the original."""
    from . import patch_clash95_hd as patcher
    profile = patcher.parse_resolution(resolution)
    require(profile.key == resolution, "resolution must use canonical WxH spelling")
    layout = FramedViewport(profile.width, profile.height)
    require(metadata.get("stage") == PARENT_STAGE and metadata.get("resolution") == resolution
            and metadata.get("minimap_viewport") is True and metadata.get("framed_validation") is True
            and metadata.get("output_sha256") == sha(parent), "parent candidate identity differs")
    image = pe.inspect_pe(parent)
    code_va, code_size = metadata.get("code_va"), metadata.get("code_bytes")
    _u32(code_va)
    require(type(code_size) is int and code_size > 0, "missing parent payload size")
    section = image.sections[-1]
    require(section.name.rstrip(b"\0") == b".hdcode" and section.characteristics == pe.RX_CODE
            and code_va == image.image_base + section.rva and code_size <= section.raw_size,
            "parent extension layout differs")
    code_offset = image.file_offset(code_va - image.image_base, code_size)
    require(metadata.get("extension_payload_size") == code_size
            and metadata.get("extension_payload_sha256") == metadata.get("code_sha256")
            == sha(parent[code_offset:code_offset + code_size]), "parent payload identity differs")
    entries = metadata.get("entry_vas")
    names = ("composition_guard", "hook_framed_full_entry", "framed_full_fallback", "framed_full_reject",
             "initial_paint_admission", "initial_admission_reject")
    require(isinstance(entries, dict) and all(type(entries.get(name)) is int
            and code_va <= entries[name] < code_va + code_size for name in names), "parent entries are incomplete")
    reloc_raw, locations = pe._old_relocations(parent, image)
    relocations = metadata.get("relocations")
    require(isinstance(relocations, list), "parent relocation inventory is missing")
    edits = []
    for kind, entry, reject in (("full_redraw", "hook_framed_full_entry", "framed_full_reject"),
                                ("initial_paint", "initial_paint_admission", "initial_admission_reject")):
        entry_va = entries[entry]
        prefix = _prefix(kind, entry_va, entries)
        va = entry_va + len(prefix)
        require(va + GATE_SIZE <= code_va + code_size, "camera span exceeds payload")
        offset = image.file_offset(va - image.image_base, GATE_SIZE)
        require(parent[offset - len(prefix):offset] == prefix, "authenticated entry prefix differs")
        old, new = old_gate(layout, va, entries[reject]), camera_gate(layout, va, entries[reject])
        require(parent[offset:offset + GATE_SIZE] == old, "camera old-byte gate differs")
        rva = va - image.image_base
        require(not any(rva < field + 4 and field < rva + GATE_SIZE for field in locations),
                "camera gate intersects a HIGHLOW relocation")
        for row in relocations:
            require(isinstance(row, dict) and type(row.get("offset")) is int,
                    "parent code relocation record is malformed")
            field = code_va + row["offset"]
            require(not va < field + 4 or not field < va + GATE_SIZE,
                    "camera gate intersects a declared relocation")
        edits.append({"name": kind, "offset": offset, "rva": rva, "va": va,
                      "old_hex": old.hex(), "new_hex": new.hex(), "reject_va": entries[reject],
                      "continuation_va": va + GATE_SIZE, "group": "framed-camera-clamp",
                      "stage": STAGE, "rationale": "Validate both world dimensions, then clamp both camera axes before native tile pointer formation."})
    edits.sort(key=lambda row: row["offset"])
    require(edits[0]["offset"] + GATE_SIZE <= edits[1]["offset"], "camera spans overlap")
    result = bytearray(parent)
    for row in edits:
        offset = row["offset"]
        require(bytes(result[offset:offset + GATE_SIZE]).hex() == row["old_hex"], "old bytes changed before application")
        result[offset:offset + GATE_SIZE] = bytes.fromhex(row["new_hex"])
    result = bytes(result)
    require(pe.inspect_pe(result) == image and pe._old_relocations(result, image) == (reloc_raw, locations),
            "camera patch changed PE layout or relocations")
    report = {"schema": "clash95_framed_camera_v1", "stage": STAGE, "parent_stage": PARENT_STAGE,
              "resolution": resolution, "parent_sha256": sha(parent), "output_sha256": sha(result),
              "camera_clamp": True, "minimap_viewport": True, "full_tiles": list(layout.full_tiles),
              "edits": edits, "code_va": code_va, "code_bytes": code_size,
              "extension_payload_sha256": sha(result[code_offset:code_offset + code_size]),
              "relocation_directory_sha256": sha(reloc_raw), "highlow_count": len(locations),
              "parent_build": metadata, "game_runtime_executed": False, "manual_input_proof": False,
              "validation_stage_only": True, "promotion_ready": False, "parent_probe_reusable": False,
              "limits": "Only camera recovery in existing guarded initial/full redraw paths. No small-world renderer, live resolution switch, new input transform, or runtime validation. Parent metadata describes the intermediate image; apply camera edits afterwards. Parent probes/evidence do not apply to this stage."}
    return result, report


def source_status() -> dict[str, Any]:
    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    from run_framed_offline_tests import source_preflight
    status = source_preflight(ROOT)
    require(status.get("passed") is True and status.get("builder_sha256") == PARENT_BUILDER_SHA256,
            "reviewed framed builder or implementation sources changed")
    return status


def build_candidate(original: bytes, resolution: str):
    require(type(original) is bytes and sha(original) == pe.ORIGINAL_SHA256, "unknown original executable SHA-256")
    status = source_status()
    builder = importlib.import_module("build_framed_candidate")
    require(Path(builder.__file__).resolve() == ROOT / "tools/build_framed_candidate.py", "unexpected parent builder module")
    parent, metadata, _ = builder.build_candidate(original, resolution, minimap_viewport=True)
    image, report = _upgrade_verified_parent(parent, metadata, resolution)
    report["original_sha256"] = sha(original)
    report["source_sha256"] = {"tools/build_framed_candidate.py": status["builder_sha256"],
        **{name: row["actual_sha256"] for name, row in status["checks"].items()},
        "src/patcher/framed_camera.py": sha(Path(__file__).read_bytes())}
    return image, report
