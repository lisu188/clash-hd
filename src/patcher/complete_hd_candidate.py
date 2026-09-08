"""One reproducible, unpromoted build path for the complete HD recipe.

The authenticated predecessor builders retain their exact bytes and protocols.
This adapter selects their framed/modal/army recipe with minimap correction;
it does not claim that the outstanding runtime defects have been repaired.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-completehd-validation"
)
REVISION = "complete_hd_v1"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602")
BUILDER_FILES = (
    "tools/build_partial_tile_candidate.py", "tools/build_framed_candidate.py",
    "tools/build_framed_modal_candidate.py", "tools/build_framed_army_candidate.py",
    "src/patcher/complete_hd_candidate.py",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def deterministic(value: Any) -> Any:
    """Drop only the predecessor's wall-clock stamp, never source identity."""
    if isinstance(value, dict):
        return {key: deterministic(item) for key, item in value.items() if key != "generated_at"}
    if isinstance(value, (list, tuple)):
        return [deterministic(item) for item in value]
    return value


def _address(view: Any, offset: int) -> tuple[int | None, int | None]:
    if offset < min(section.raw_offset for section in view.sections if section.raw_size):
        return offset, view.image_base + offset
    for section in view.sections:
        if section.raw_offset <= offset < section.raw_offset + section.raw_size:
            rva = section.rva + offset - section.raw_offset
            return rva, view.image_base + rva
    return None, None


def byte_records(original: bytes, candidate: bytes, view: Any) -> list[dict[str, Any]]:
    """Describe every changed file byte against the original, including append."""
    if len(candidate) < len(original):
        raise ValueError("complete-HD recipe must not truncate the original image")
    records: list[dict[str, Any]] = []
    position = 0
    while position < len(candidate):
        if position < len(original) and original[position] == candidate[position]:
            position += 1
            continue
        start = position
        # Small records remain inspectable, and never cross old/append boundary.
        limit = min(start + 64, len(candidate), len(original) if start < len(original) else len(candidate))
        while position < limit and (position >= len(original) or original[position] != candidate[position]):
            position += 1
        rva, va = _address(view, start)
        records.append({
            "offset": start, "file_offset": start, "rva": rva, "va": va,
            "old_hex": original[start:position].hex(), "new_hex": candidate[start:position].hex(),
            "group": "complete-hd-extension" if start >= len(original) else "complete-hd-integrated",
            "stage": STAGE,
            "rationale": "Source-verified framed, minimap, native-modal and army builder composition",
            "appended": start >= len(original),
        })
    return records


def apply_records(original: bytes, records: list[dict[str, Any]], *, expected_base_sha256: str | None = None) -> bytes:
    """Replay old-byte-checked edits; callers must also authenticate the base.

    Production callers provide the base digest or have just checked it. This
    primitive alone is not a candidate/evidence validator.
    """
    if expected_base_sha256 is not None and sha256(original) != expected_base_sha256:
        raise ValueError("byte replay original SHA-256 differs")
    output = bytearray(original)
    last_end = 0
    for record in records:
        offset = record["file_offset"]
        old, new = bytes.fromhex(record["old_hex"]), bytes.fromhex(record["new_hex"])
        if type(offset) is not int or offset < last_end or not new or record.get("stage") != STAGE:
            raise ValueError("invalid or overlapping complete-HD byte record")
        if old:
            if offset + len(old) > len(original) or len(old) != len(new) or output[offset:offset + len(old)] != old:
                raise ValueError(f"old bytes differ at file offset {offset:#x}")
            output[offset:offset + len(old)] = new
        elif offset == len(output) and offset >= len(original):
            output.extend(new)
        else:
            raise ValueError("appended byte record is not contiguous")
        last_end = offset + len(new)
    return bytes(output)


def build_candidate(original: bytes, resolution: str) -> tuple[bytes, dict[str, Any], str]:
    if sha256(original) != BASE_SHA256:
        raise ValueError("unknown original executable SHA-256; complete-HD has no override")
    if resolution not in RESOLUTIONS:
        raise ValueError("complete-HD validation supports only its six fixture resolutions")
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    import build_framed_army_candidate as army
    from src.patcher import pe_extension as pe

    before = {name: sha256((ROOT / name).read_bytes()) for name in BUILDER_FILES}
    candidate, predecessor, inherited_probe = army.build_candidate(original, resolution, minimap_viewport=True)
    digest = sha256(candidate)
    if predecessor.get("output_sha256") != digest or predecessor.get("resolution") != resolution:
        raise ValueError("predecessor returned an inconsistent candidate identity")
    marker = (
        f".echo COMPLETEHD_CONTRACT_PASS stage={STAGE} resolution={resolution} "
        f"candidate_sha256={digest} revision={REVISION}"
    )
    # Insert after the existing loaded-byte checks, before the initial observer.
    inherited_marker = (
        f".echo PTILE_CONTRACT_PASS stage={army.STAGE} resolution={resolution} candidate_sha256={digest}"
    )
    if inherited_probe.splitlines().count(inherited_marker) != 1:
        raise ValueError("predecessor probe contract changed")
    probe = inherited_probe.replace(inherited_marker, marker + "\n" + inherited_marker, 1)
    sources = dict(predecessor["source_sha256"])
    for name, expected in sources.items():
        if sha256((ROOT / name).read_bytes()) != expected:
            raise ValueError(f"source changed during complete-HD build: {name}")
    if before != {name: sha256((ROOT / name).read_bytes()) for name in BUILDER_FILES}:
        raise ValueError("builder changed during complete-HD build")
    sources.update(before)
    records = byte_records(original, candidate, pe.inspect_pe(candidate))
    if apply_records(original, records, expected_base_sha256=BASE_SHA256) != candidate:
        raise ValueError("complete-HD byte manifest does not reproduce candidate")
    metadata = {
        "schema": 1, "stage": STAGE, "resolution": resolution,
        "recipe_revision": REVISION, "base_sha256": BASE_SHA256,
        "candidate_sha256": digest, "candidate_bytes": len(candidate),
        "source_hashes": sources, "patch_records": records,
        "probe_sha256": sha256(probe.encode("utf-8")),
        "probe_contract": {
            "complete_marker": marker.removeprefix(".echo "),
            "inherited_marker": inherited_marker.removeprefix(".echo "),
            "inherited_stage": army.STAGE,
            "requires_loaded_byte_checks": True,
            "all_inherited_checks_required": True,
        },
        "predecessor": deterministic(predecessor),
        "features": {"framed_map": True, "minimap_viewport": True, "native_modal_canvas": True,
                     "army_panel": True, "centered_native_battle": True, "expanded_battle": False},
        "validation_stage_only": True, "runtime_executed": False,
        "manual_input_proof": False, "promotion_ready": False,
        "limitations": ["Inherited runtime/visual failures remain unresolved until new bound evidence passes.",
                        "Build and byte integrity do not establish rendering, input, continuity or endurance."],
    }
    return candidate, metadata, probe


def _write_bundle(paths: tuple[Path, ...], payloads: tuple[bytes, ...]) -> None:
    """Exclusive creation; on failure remove only this invocation's file IDs."""
    from contextlib import ExitStack
    import os
    owned: list[tuple[Path, int, int]] = []
    try:
        with ExitStack() as stack:
            streams = []
            for path in paths:
                stream = stack.enter_context(path.open("xb"))
                identity = os.fstat(stream.fileno())
                owned.append((path, identity.st_dev, identity.st_ino))
                streams.append(stream)
            for stream, data in zip(streams, payloads):
                stream.write(data)
    except BaseException:
        for path, device, inode in reversed(owned):
            try:
                current = path.stat(follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (device, inode):
                    path.unlink()
            except FileNotFoundError:
                pass
        raise


def write_candidate(original_path: Path, output: Path, resolution: str) -> dict[str, Any]:
    """Write a new candidate bundle only inside C:/ClashTests, never overwrite."""
    output = Path(output).resolve()
    allowed = Path("C:/ClashTests").resolve()
    if not output.is_relative_to(allowed) or output.suffix.lower() != ".exe":
        raise ValueError("complete-HD candidates must be named .exe files under C:/ClashTests")
    paths = (output, output.with_suffix(".candidate.json"), output.with_suffix(".cdb"))
    if any(path.exists() for path in paths):
        raise FileExistsError("complete-HD candidate bundle already exists; choose a new name")
    candidate, manifest, probe = build_candidate(Path(original_path).read_bytes(), resolution)
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_bundle(paths, (candidate, (json.dumps(manifest, indent=2) + "\n").encode(), probe.encode()))
    return manifest


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--stage", choices=[STAGE], default=STAGE)
    parser.add_argument("--resolution", choices=RESOLUTIONS, default="800x600")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight:
        if args.output:
            parser.error("--preflight does not write output")
        candidate, manifest, _ = build_candidate(args.input.read_bytes(), args.resolution)
    else:
        if not args.output:
            parser.error("--output is required unless --preflight is selected")
        manifest = write_candidate(args.input, args.output, args.resolution)
    print(json.dumps({key: manifest[key] for key in (
        "stage", "resolution", "candidate_sha256", "candidate_bytes", "runtime_executed", "promotion_ready"
    )}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
