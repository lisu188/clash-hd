"""Original-bound 1080p/1440p/4K launcher successors.

Frozen predecessor recipes remain unchanged. These versioned candidates add
bounded framed-map guards where available and carry an independent, relocated
initial-image verifier. Construction never implies gameplay qualification.
"""
from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
import re
import struct

from . import hd_multires_bounded as bounded
from . import hd_multires_classic_bounded as classic_bounded
from . import pe_extension as pe

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/patcher/hd_multires_candidate.py"
PROFILES = ("classic", "framed", "completehd", "modalwidgets")
RESOLUTIONS = ("1920x1080", "2560x1440", "3840x2160")
REVISION = "hd_multires_v1"
ORIGINAL_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
STABLE_STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
                "presentbounds-minimapright-dynvswitch")
BUILDERS = {
    "classic": "src.patcher.classic_all_presets_candidate",
    "framed": "src.patcher.framed_all_presets_candidate",
    "completehd": "src.patcher.complete_hd_all_presets_candidate",
    "modalwidgets": "src.patcher.modal_widgets_all_presets_candidate",
}
HELPER_SOURCES = {
    "src/patcher/framed_camera.py": "f8caea185f3714a6924a4e4cb40aa049866fc7864afa41a66da1b56a93059ef8",
    "src/patcher/framed_bounded_paint.py": "981d946007b0438051dba033dce9e8e442cb7863ee49c547fbaad1e35d66cf1f",
    "src/patcher/framed_bounded_input.py": "8117232bb875b1a0f9fb179b7a77ec7325e633ce283574b7f9b8cc3d37589258",
}
_READ = re.compile(r"(by|wo|dwo)\(([0-9a-fA-F]{8})\)")
# The frozen Modal Widgets initial-image observer explicitly requires this
# native cursor descriptor to be zero before application code starts. Its
# .bss section has no file backing; it must not be read at file offset zero.
_MODAL_ZERO_BSS = ((0x545158, 12),)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stage(profile: str) -> str:
    _require(type(profile) is str and profile in PROFILES, "unsupported multi-resolution profile")
    return STABLE_STAGE + f"-{profile}-hd-multires-validation"


def bounded_small_world(profile: str) -> bool:
    """Source-installed capability, never a runtime or input acceptance badge."""
    stage(profile)
    return True


def _builder(profile: str):
    stage(profile)
    return importlib.import_module(BUILDERS[profile])


def _source(name: str) -> bytes:
    _require(type(name) is str and "\\" not in name and ":" not in name
             and all(p not in ("", ".", "..") for p in name.split("/")),
             "canonical repository-relative source required")
    path = ROOT / name
    _require(path.resolve() == path and path.is_file(), "noncanonical source path: " + name)
    return path.read_bytes()


def _source_hashes(profile: str) -> dict[str, str]:
    builder = _builder(profile)
    snapshots = builder._sources()
    result = {name: sha256(data) for name, data in snapshots.items()}
    constructor = BUILDERS[profile].replace(".", "/") + ".py"
    result[constructor] = sha256(_source(constructor))
    for name, expected in HELPER_SOURCES.items():
        data = _source(name)
        _require(sha256(data) == expected, "reviewed bounded helper source differs: " + name)
        result[name] = expected
    for name in (SOURCE, "src/patcher/hd_multires_bounded.py", "src/patcher/hd_multires_classic_bounded.py"):
        result[name] = sha256(_source(name))
    return dict(sorted(result.items()))


def _portable_predecessor(value):
    """Keep frozen provenance content, with checked location-independent paths.

    The historical scalar Framed recipe reports its local __file__ paths.
    A standalone one-file launcher extracts into a different directory on every
    invocation. Only the successor's copy of those three authenticated bindings
    is canonicalized; frozen builders and historical metadata stay intact.
    """
    bindings = {"patcher": "src/patcher/patch_clash95_hd.py",
                "framed_recipe": "src/patcher/framed_recipe.py",
                "framed_viewport": "src/patcher/framed_viewport.py"}
    if type(value) is list:
        return [_portable_predecessor(item) for item in value]
    if type(value) is not dict:
        return value
    result = {}
    for key, item in value.items():
        if key != "source_bindings":
            result[key] = _portable_predecessor(item)
            continue
        _require(type(item) is dict and set(item) == set(bindings),
                 "unknown predecessor source-binding inventory")
        result[key] = {}
        for label, relative in bindings.items():
            record = item[label]
            _require(type(record) is dict and set(record) == {"path", "sha256"}
                     and type(record["path"]) is str and Path(record["path"]) == ROOT / relative
                     and record["sha256"] == sha256(_source(relative)),
                     "predecessor source binding differs: " + label)
            result[key][label] = dict(path=relative, sha256=record["sha256"])
    return result


def render_probe(image: bytes, metadata: dict, inherited: str) -> tuple[str, dict]:
    """Check initial headers, executable sections and inherited literal reads.

    Loaded-image base comes from the PEB. HIGHLOW operands and ImageBase are
    compared against that base. No mutable data or runtime readiness is inferred.
    """
    view = pe.inspect_pe(image)
    _, fields = pe._old_relocations(image, view)
    ranges = [(0, view.headers_size)]
    ranges += [(s.rva, s.rva + s.raw_size) for s in view.sections
               if s.characteristics & 0x20000000 and s.raw_size]
    zero_ranges = []

    def expected_bytes(rva, size):
        if 0 <= rva and rva + size <= view.headers_size:
            return image[rva:rva + size]
        try:
            at = view.file_offset(rva, size)
            return image[at:at + size]
        except ValueError:
            va = view.image_base + rva
            sections = [s for s in view.sections if s.rva <= rva
                        and rva + size <= s.rva + s.memory_size]
            _require(metadata.get("profile") == "modalwidgets" and len(sections) == 1
                     and sections[0].raw_offset == 0 and sections[0].characteristics & 0x80
                     and any(a <= va and va + size <= a + n for a, n in _MODAL_ZERO_BSS),
                     "inherited read is not file-backed or an authenticated startup-zero descriptor")
            zero_ranges.append((rva, rva + size))
            return bytes(size)
    # Some frozen predecessors keep small authenticated code/data descriptors
    # outside executable sections; retain their literal-read coverage as well.
    for match in _READ.finditer(inherited):
        size = {"by": 1, "wo": 2, "dwo": 4}[match.group(1)]
        rva = int(match.group(2), 16) - view.image_base
        _require(rva >= 0, "inherited read precedes the authenticated image")
        try:
            expected_bytes(rva, size)
        except ValueError as exc:
            raise ValueError(f"inherited read is not file-backed in the final image: {match.group(0)}") from exc
        if not any(a <= rva and rva + size <= b for a, b in ranges):
            ranges.append((rva, rva + size))
    base_field = view.optional_offset + 28
    special = set(fields) | {base_field}
    expanded = []
    for start, end in ranges:
        for field in sorted(special):
            if field >= end:
                break
            if field + 4 > start:
                expected_bytes(field, 4)
                start, end = min(start, field), max(end, field + 4)
        expanded.append((start, end))
    merged = []
    for start, end in sorted(set(expanded)):
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    _require(not any(base_field < f + 4 and f < base_field + 4 for f in fields),
             "ImageBase overlaps HIGHLOW")
    lines = [".expr /s masm", "r @$t18=0", "r @$t19=0",
             ".if (@$ptrsize == 0n4) { r @$t19=dwo(@$peb+0n8) }",
             f".if ((@$t19 < 0x10000) | ((@$t19 & 0xffff) != 0) | (@$t19 > 0x{0x7ffe0000-view.image_size:08x})) {{ r @$t19=0 }}",
             ".echo HDMULTI_SCOPE initial_image_bytes_only runtime_verified=false"]
    pending = []
    chunks = comparisons = 0
    mask = "0x00000000`ffffffff"

    def flush():
        nonlocal chunks
        lines.append(f".if ((@$t19 != 0) & (@$t18 == 0n{chunks})) {{ .if ("
                     + " & ".join(pending)
                     + f") {{ r @$t18=0n{chunks+1} }} .else {{ .echo HDMULTI_CHUNK_{chunks}_BAD }} }}")
        chunks += 1
        pending.clear()

    def check(condition):
        nonlocal comparisons
        if pending and (len(pending) >= 24 or sum(map(len, pending)) + len(condition) + len(pending) * 4 > 3200):
            flush()
        pending.append(condition)
        comparisons += 1

    for start, end in merged:
        _require(not any(start < f + 4 and f < end and not (start <= f and f + 4 <= end)
                         for f in special), "partially covered relocated operand")
        at = start
        for stop in sorted(f for f in special if start <= f < end) + [end]:
            while at < stop:
                size = 4 if stop - at >= 4 else 2 if stop - at >= 2 else 1
                value = int.from_bytes(expected_bytes(at, size), "little")
                reader = {1: "by", 2: "wo", 4: "dwo"}[size]
                expression = f"{reader}(@$t19+0x{at:x})"
                check(f"(({expression} & {mask}) == 0x00000000`{value:08x})"
                      if size == 4 else f"({expression} == 0x{value:x})")
                at += size
            if stop != end:
                value = int.from_bytes(expected_bytes(at, 4), "little")
                # The loader changes HIGHLOW fields, not the preferred ImageBase
                # word in the optional header. PEB supplies the actual base.
                expected = (f"0x00000000`{value:08x}" if at == base_field else
                            f"((0x00000000`{value:08x}+@$t19-0x{view.image_base:x}) & {mask})")
                check(f"((dwo(@$t19+0x{at:x}) & {mask}) == {expected})")
                at += 4
    if pending:
        flush()
    marker = (f"HDMULTI_LOADED_BYTES_OK profile={metadata['profile']} resolution={metadata['resolution']} "
              f"stage={metadata['stage']} candidate_sha256={sha256(image)} revision={REVISION}")
    lines += [f".if ((@$t19 != 0) & (@$t18 == 0n{chunks})) {{ .echo {marker} }} .else {{ .echo HDMULTI_INCOMPLETE }}",
              ".echo HDMULTI_STOP initial byte verification supplies no route input or endurance acceptance"]
    _require(all(len(line.encode("ascii")) < 3800 for line in lines), "CDB command exceeds bounded line length")
    return "\r\n".join(lines) + "\r\n", dict(acceptance_marker=marker, required_chunks=chunks,
        comparison_count=comparisons, relocation_aware=True, initial_breakpoint_required=True,
        checked_ranges=[dict(rva=a, bytes=b-a) for a, b in merged],
        startup_zero_ranges=[dict(rva=a, bytes=b-a) for a, b in sorted(set(zero_ranges))],
        checked_bytes=sum(b-a for a, b in merged), runtime_observation_protocol=False)


def _build_candidate(original: bytes, resolution: str, *, profile: str):
    _require(type(original) is bytes and sha256(original) == ORIGINAL_SHA256,
             "unknown original executable SHA-256; no override exists")
    _require(type(resolution) is str and resolution in RESOLUTIONS,
             "only 1920x1080, 2560x1440 and 3840x2160 are admitted")
    selected_stage = stage(profile)
    before = _source_hashes(profile)
    image, predecessor, inherited = _builder(profile).build_candidate(original, resolution)
    _require(predecessor.get("candidate_sha256") == sha256(image)
             and predecessor.get("probe_sha256") == sha256(inherited.encode())
             and predecessor.get("resolution") == resolution,
             "predecessor bundle identity differs")
    parent_sha = sha256(image)
    capability = dict(bounded_small_world_integrated=False, small_world_input_enabled=False,
                      camera_clamp=False, runtime_executed=False, manual_input_proof=False,
                      promotion_ready=False)
    if profile == "classic":
        image, capability = classic_bounded.integrate(image, predecessor, original=original,
            profile=profile, resolution=resolution, selected_stage=selected_stage)
    elif bounded_small_world(profile):
        image, capability = bounded.integrate(image, predecessor, profile=profile,
                                              resolution=resolution, selected_stage=selected_stage)
    records_builder = importlib.import_module("src.patcher.framed_all_presets_candidate")
    view = pe.inspect_pe(image)
    records = records_builder.byte_records(original, image, view)
    _require(records_builder.apply_records(original, records, expected_base_sha256=ORIGINAL_SHA256,
                                           view=view) == image, "full original-to-final replay differs")
    metadata = dict(schema="clash95_hd_multires_candidate_v1", profile=profile, resolution=resolution,
        stage=selected_stage, recipe_revision=REVISION, original_sha256=ORIGINAL_SHA256,
        base_sha256=ORIGINAL_SHA256, candidate_sha256=sha256(image), candidate_bytes=len(image),
        source_hashes=before, patch_records=records, predecessor=_portable_predecessor(predecessor),
        predecessor_source_path_scope="canonical_repository_relative_v1",
        predecessor_candidate_sha256=parent_sha, predecessor_probe_sha256=sha256(inherited.encode()),
        bounded_small_world_integrated=capability["bounded_small_world_integrated"],
        small_world_input_enabled=capability["small_world_input_enabled"], bounded_world=capability,
        expanded_battle_installed=False, validation_stage_only=True, launcher_registered=True,
        installation_ready=False, runtime_verified=False, runtime_executed=False,
        manual_input_proof=False, promotion_ready=False,
        limitations=["Candidate preparation and source-installed guards are not verified gameplay.",
                     "Expanded battle, native screen continuity, final composition, human input and endurance remain unqualified.",
                     "Classic and framed map guards are source-installed; native callback lifetime and device behavior still require measured evidence.",
                     "Historical predecessor probes and observations cannot qualify this successor."])
    probe, contract = render_probe(image, metadata, inherited)
    metadata.update(probe_sha256=sha256(probe.encode()), probe_contract=contract)
    _require(before == _source_hashes(profile), "source changed during candidate construction")
    return image, metadata, probe


if not globals().get("_HD_MULTIRES_PRIVATE", False):
    _issuer_path = ROOT / "src/patcher/hd_multires_issuer.py"
    _issuer_source = _issuer_path.read_bytes()
    _issuer_values = {"__file__": str(_issuer_path), "__name__": "_clash95_hd_canonical_issuer", "__package__": None}
    exec(compile(_issuer_source, str(_issuer_path), "exec"), _issuer_values)
    # The returned closures retain private factory globals, not this mutable
    # module's aliases, maps, helpers or imported constructor functions.
    build_candidate, source_hashes = _issuer_values["create_issuer"]()
