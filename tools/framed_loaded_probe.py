"""Generate a read-only, relocation-aware byte gate for the final bounded stage."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import framed_bounded_input as bounded
from src.patcher import framed_camera as camera
from src.patcher import framed_recipe as recipe
from src.patcher import pe_extension as pe

MAX_COMMAND_BYTES = 3800
CHECKS_PER_COMMAND = 16


@dataclass(frozen=True)
class Check:
    rva: int
    size: int
    value: int
    relocated: bool
    loader_image_base: bool = False

    def expression(self, preferred_base: int) -> str:
        read = {1: "by", 2: "wo", 4: "dwo"}[self.size]
        expected = (f"((0x{self.value:08x} + @$t19 - 0x{preferred_base:08x}) & 0xffffffff)"
                    if self.relocated or self.loader_image_base else f"0x{self.value:0{self.size * 2}x}")
        return f"({read}(@$t19 + 0x{self.rva:08x}) == {expected})"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def source_identities() -> dict[str, str]:
    status = bounded.source_status()
    identities = {"tools/build_framed_candidate.py": status["builder_sha256"],
                  **{name: row["actual_sha256"] for name, row in status["checks"].items()}}
    for name in ("framed_camera", "framed_bounded_paint", "framed_bounded_input"):
        path = ROOT / "src" / "patcher" / f"{name}.py"
        identities[path.relative_to(ROOT).as_posix()] = _sha(path.read_bytes())
    return identities


def _offset(image: pe.PEImage, rva: int, size: int) -> int:
    if 0 <= rva and rva + size <= image.headers_size:
        return rva
    return image.file_offset(rva, size)


def _rva(image: pe.PEImage, offset: int, size: int) -> int:
    _require(type(offset) is int and type(size) is int and offset >= 0 and size > 0,
             "invalid file span")
    if offset + size <= image.headers_size:
        return offset
    matches = [s.rva + offset - s.raw_offset for s in image.sections if s.raw_offset
               and s.raw_offset <= offset and offset + size <= s.raw_offset + s.raw_size]
    _require(len(matches) == 1, "file span has no unique loaded mapping")
    return matches[0]


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if result and start <= result[-1][1]:
            result[-1] = result[-1][0], max(result[-1][1], end)
        else:
            result.append((start, end))
    return result


def _checks(data: bytes, image: pe.PEImage, spans: list[tuple[int, int]],
            relocations: tuple[int, ...]) -> tuple[list[Check], list[tuple[int, int]]]:
    fields = sorted(relocations)
    _require(all(a + 4 <= b for a, b in zip(fields, fields[1:])),
             "overlapping HIGHLOW fields")
    base_field = image.optional_offset + 28
    _require(not any(base_field < field + 4 and field < base_field + 4 for field in fields),
             "ImageBase header overlaps a HIGHLOW relocation")
    fields = sorted([*fields, base_field])
    ranges = _merge(spans)
    ranges = _merge(ranges + [(field, field + 4) for field in fields
                    if any(start < field + 4 and field < end for start, end in ranges)])
    checks: list[Check] = []
    for start, end in ranges:
        _require(0 <= start < end <= image.image_size, "loaded span exceeds image")
        _offset(image, start, end - start)
        within = [field for field in fields if start <= field < end]
        at = start
        for stop in within + [end]:
            while at < stop:
                size = 4 if stop - at >= 4 else 2 if stop - at >= 2 else 1
                offset = _offset(image, at, size)
                checks.append(Check(at, size, int.from_bytes(data[offset:offset + size], "little"), False))
                at += size
            if stop != end:
                offset = _offset(image, at, 4)
                checks.append(Check(at, 4, int.from_bytes(data[offset:offset + 4], "little"),
                                    at != base_field, at == base_field))
                at += 4
    return checks, ranges


def _contract(data: bytes, report: dict[str, Any], scalar_patches) -> tuple[pe.PEImage, list[Check], dict[str, Any]]:
    _require(type(data) is bytes and isinstance(report, dict), "invalid final candidate")
    _require(report.get("schema") == "clash95_bounded_input_v1" and report.get("stage") == bounded.STAGE
             and report.get("output_sha256") == _sha(data), "final candidate identity differs")
    profile = recipe.patcher.parse_resolution(report.get("resolution", ""))
    _require(profile.key == report.get("resolution"), "noncanonical final resolution")
    _require(report.get("original_sha256") == pe.ORIGINAL_SHA256, "original identity missing or different")
    _require(report.get("source_sha256") == source_identities(), "final source identities differ")
    for field in ("camera_clamp", "bounded_small_world_paint", "small_world_input_enabled", "minimap_viewport", "validation_stage_only"):
        _require(report.get(field) is True, f"required final feature missing: {field}")
    for field in ("game_runtime_executed", "manual_input_proof", "promotion_ready", "parent_probe_reusable"):
        _require(report.get(field) is False, f"invalid evidence boundary: {field}")
    image = pe.inspect_pe(data)
    code_va, code_size = report.get("code_va"), report.get("code_bytes")
    _require(type(code_va) is int and type(code_size) is int and code_size > 0, "invalid code extent")
    code_rva = code_va - image.image_base
    section = image.sections[-1]
    _require(section.name.rstrip(b"\0") == b".hdcode" and section.characteristics == pe.RX_CODE
             and section.rva == code_rva and code_size <= section.raw_size, "final code section differs")
    code_offset = _offset(image, code_rva, code_size)
    _require(_sha(data[code_offset:code_offset + code_size]) == report.get("code_sha256"), "final payload hash differs")
    parent = report.get("parent_build")
    _require(isinstance(parent, dict) and parent.get("stage") == bounded.bounded.STAGE
             and parent.get("output_sha256") == report.get("parent_sha256")
             and parent.get("resolution") == profile.key and parent.get("code_va") == code_va
             and parent.get("code_bytes") == code_size, "bounded parent identity differs")
    restored = bytearray(data)
    used: set[int] = set()
    edits = report.get("edits")
    _require(isinstance(edits, list) and len(edits) == 2, "final input edits missing")
    for edit in edits:
        _require(isinstance(edit, dict), "invalid input edit")
        offset, rva = edit.get("offset"), edit.get("rva")
        old, new = bytes.fromhex(edit.get("old_hex", "")), bytes.fromhex(edit.get("new_hex", ""))
        _require(len(old) == len(new) == bounded.LIMIT_BYTES and type(rva) is int
                 and type(offset) is int and edit.get("va") == image.image_base + rva
                 and offset == _offset(image, rva, len(new))
                 and data[offset:offset + len(new)] == new, "final input edit bytes or mapping differ")
        positions = set(range(offset, offset + len(new)))
        _require(not positions & used, "overlapping input edits")
        used.update(positions)
        restored[offset:offset + len(old)] = old
    _require(_sha(bytes(restored)) == report.get("parent_sha256"), "final input edits do not reconstruct parent")
    spans = [(0, image.headers_size), (code_rva, code_rva + code_size)]
    hooks = parent.get("hooks")
    _require(isinstance(hooks, list) and bool(hooks), "installed hook inventory missing")
    for hook in hooks:
        _require(isinstance(hook, dict), "invalid hook")
        new = bytes.fromhex(hook.get("new_hex", ""))
        rva, offset = hook.get("rva"), hook.get("offset")
        _require(type(rva) is int and type(offset) is int and bool(new)
                 and hook.get("va") == image.image_base + rva and offset == _offset(image, rva, len(new))
                 and data[offset:offset + len(new)] == new, "installed hook bytes or mapping differ")
        spans.append((rva, rva + len(new)))
    patches = list(scalar_patches)
    _require(bool(patches), "scalar recipe is empty")
    for patch in patches:
        rva = _rva(image, patch.offset, len(patch.new))
        spans.append((rva, rva + len(patch.new)))
    table, fields = pe._old_relocations(data, image)
    _require(report.get("highlow_count") == len(fields)
             and report.get("relocation_directory_sha256") == _sha(table), "relocation directory identity differs")
    checks, ranges = _checks(data, image, spans, fields)
    facts = {"schema": "clash95_bounded_loaded_probe_v1", "stage": bounded.STAGE,
             "resolution": profile.key, "candidate_sha256": _sha(data), "original_sha256": pe.ORIGINAL_SHA256,
             "preferred_image_base": image.image_base, "size_of_image": image.image_size,
             "source_sha256": report["source_sha256"], "generator_sha256": _sha(Path(__file__).read_bytes()),
             "checked_ranges": [{"rva": start, "bytes": end - start} for start, end in ranges],
             "checked_bytes": sum(end - start for start, end in ranges), "check_count": len(checks),
             "relocated_checks": sum(check.relocated for check in checks),
             "loader_image_base_rva": image.optional_offset + 28,
             "loader_image_base_policy": "ImageBase equals actual loaded base at initial breakpoint",
             "hook_count": len(hooks),
             "scalar_patch_count": len(patches), "game_runtime_executed": False,
             "manual_input_proof": False, "promotion_ready": False,
             "scope": "Loaded PE headers (ImageBase normalized to actual load address), every selected scalar patch span, every installed hook, and complete final injected code. Not a whole-process hash, gameplay test or rendering/input proof."}
    encoded = json.dumps(facts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    facts["contract_id"] = _sha(encoded)
    return image, checks, facts


def render_probe(data: bytes, report: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    _require(type(data) is bytes and isinstance(report, dict), "invalid final candidate")
    profile = recipe.patcher.parse_resolution(report.get("resolution", ""))
    patches = recipe.select_patches_for(profile)
    image, checks, facts = _contract(data, report, patches)
    chunks = [checks[i:i + CHECKS_PER_COMMAND] for i in range(0, len(checks), CHECKS_PER_COMMAND)]
    prefix = f"BNDLOAD contract={facts['contract_id']} candidate={facts['candidate_sha256']}"
    lines = [".expr /s masm", "r @$t18 = 0", "r @$t19 = 0",
             f".echo {prefix} stage={bounded.STAGE} resolution={facts['resolution']}",
             ".if (@$ptrsize == 0n4) { r @$t19 = dwo(@$peb + 0n8); }",
             f".if ((@$t19 < 0x10000) | ((@$t19 & 0xffff) != 0) | (@$t19 > 0x{(1 << 32) - image.image_size:08x})) {{ r @$t19 = 0; }}"]
    for index, chunk in enumerate(chunks):
        conditions = " & ".join(check.expression(image.image_base) for check in chunk)
        lines.append(f".if ((@$t19 != 0) & (@$t18 == 0n{index})) {{ .if ({conditions}) {{ r @$t18 = @$t18 + 1; }} .else {{ .echo BNDLOAD_MISMATCH chunk={index}; }} }}")
    lines.append(f'.if ((@$t19 != 0) & (@$t18 == 0n{len(chunks)})) {{ .echo {prefix} result=pass chunks={len(chunks)}; }} .else {{ .echo {prefix} result=fail; }}')
    lines.append(".echo BNDLOAD_STOP target remains paused, no route or gameplay evidence produced")
    _require(all(len(line.encode("ascii")) < MAX_COMMAND_BYTES for line in lines), "CDB command exceeds bounded length")
    text = "\r\n".join(lines) + "\r\n"
    return text, {**facts, "probe_sha256": _sha(text.encode("ascii")), "required_chunks": len(chunks),
                  "debugger_scratch": ["$t18", "$t19"], "requires": "x86 CDB at the initial process breakpoint, before other probes or target initialization"}
