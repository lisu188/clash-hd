"""Authenticate a battle parent and plan allocations, without emitting patches.

The four fixed all-preset constructors run twice from pinned source snapshots
in separate namespaces. A caller's bytes, metadata or probe cannot select a
recipe or substitute for reconstruction. The returned plan installs nothing,
writes no file, and establishes no runtime or expanded-battle acceptance.

Existing modal state reuse is bounded by the frozen state layout, its exact
owner metadata and every active HIGHLOW reference into that page. This is a
source-declared operand inventory, not discovery of undeclared instructions
or a proof of dynamic pointer arithmetic, loader behavior or lifetime.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/patcher/battle_profile_context.py"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
STABLE_STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
                "presentbounds-minimapright-dynvswitch")
PROFILES = ("classic", "framed", "completehd", "modalwidgets")
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
               "1920x1080", "2560x1440", "3440x1440", "3840x2160")
RX = 0x60000020
RW = 0xC0000040
CODE_RESERVATION = 0x20000
STATE_PAGE_BYTES = 4096
BATTLE_STATE_OFFSET = 0x100
BATTLE_STATE_BYTES = 128
INHERITED_STATE_BYTES = 128
# Source paths and identities are selected here, never by a caller manifest.
ENTRYPOINTS = {
    "classic": ("src/patcher/classic_all_presets_candidate.py", "classic_all_presets_v1",
                "29a4e16cbe649d1801317f61b0a85d968a0a8e6f37032dfe4552203f64110f26"),
    "framed": ("src/patcher/framed_all_presets_candidate.py", "framed_all_presets_v1",
               "19aff1e4ed6ab34fe2ab209921ae1f5e950805a7b553965df0faa805939451a2"),
    "completehd": ("src/patcher/complete_hd_all_presets_candidate.py", "complete_hd_all_presets_v1",
                   "856de49937c5d66b83a3dc7d5d22c94503fd2890147781580635eeabb7a91043"),
    "modalwidgets": ("src/patcher/modal_widgets_all_presets_candidate.py", "modal_widgets_all_presets_v1",
                     "9c7abbcbb137b75ece5d45d2b13496f04a72b90bf13654af1c3c11f1015cf2fe"),
}
FOUNDATION_PINS = {
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/framed_battle_viewport.py": "8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6",
}
ADAPTER_SOURCE = "src/patcher/owned_modal_all_presets_emit.py"
ADAPTER_SHA256 = "6089243ccd79a8b312ca39dcdbdfaa2aad631637898cf8063b393db119a05f3c"
FALSE_CLAIMS = ("battle_installed", "expanded_battle_installed", "installation_ready", "runtime_executed",
                "manual_input_proof", "promotion_ready", "release_accepted")


@dataclass(frozen=True)
class BattleProfileContext:
    """Immutable result with typed parent encoding and ordinary JSON plan.

    Future installers must reauthenticate; this dataclass is not authority.
    """
    candidate: bytes
    parent_metadata_json: str
    canonical_probe: str
    allocation_plan_json: str

    def allocation_plan(self):
        return json.loads(self.allocation_plan_json)

    def parent_metadata(self):
        # Frozen modal emitters retain a few tuple-valued contract fields.
        # Preserve them rather than silently normalizing them into lists.
        return _restore_metadata(json.loads(self.parent_metadata_json))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _canonical(value):
    """Exact JSON types: booleans, integers and floats are not interchangeable."""
    def checked(item, depth=0):
        _require(depth < 64, "metadata nesting is excessive")
        if type(item) is dict:
            _require(all(type(key) is str for key in item), "metadata keys must be strings")
            for value in item.values():
                checked(value, depth + 1)
        elif type(item) is list:
            for value in item:
                checked(value, depth + 1)
        else:
            _require(type(item) in (str, int, float, bool, type(None)), "metadata requires exact JSON types")
    checked(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError, RecursionError) as error:
        raise ValueError("noncanonical metadata") from error


def _typed_metadata(value, depth=0):
    """Lossless typed tree for frozen Python metadata, including tuples."""
    _require(depth < 64, "metadata nesting is excessive")
    kind = type(value)
    if kind is dict:
        _require(all(type(key) is str for key in value), "metadata keys must be strings")
        payload = [[key, _typed_metadata(value[key], depth + 1)] for key in sorted(value)]
    elif kind in (list, tuple):
        payload = [_typed_metadata(item, depth + 1) for item in value]
    else:
        _require(kind in (str, int, float, bool, type(None)), "metadata requires exact scalar types")
        _canonical(value)
        payload = value
    return [kind.__name__, payload]


def _typed_canonical(value):
    return json.dumps(_typed_metadata(value), separators=(",", ":"), allow_nan=False)


def _restore_metadata(tree, depth=0):
    _require(depth < 64 and type(tree) is list and len(tree) == 2, "typed metadata tree differs")
    tag, payload = tree
    _require(type(tag) is str, "typed metadata tag differs")
    if tag == "dict":
        _require(type(payload) is list and all(type(row) is list and len(row) == 2
                 and type(row[0]) is str for row in payload), "typed dictionary differs")
        _require(len({row[0] for row in payload}) == len(payload), "typed dictionary keys duplicate")
        return {key: _restore_metadata(value, depth + 1) for key, value in payload}
    if tag in ("list", "tuple"):
        _require(type(payload) is list, "typed sequence differs")
        rows = [_restore_metadata(value, depth + 1) for value in payload]
        return tuple(rows) if tag == "tuple" else rows
    scalar = {"str": str, "int": int, "float": float, "bool": bool, "NoneType": type(None)}
    _require(tag in scalar and type(payload) is scalar[tag], "typed scalar differs")
    _canonical(payload)
    return payload


def _selector(profile, resolution):
    _require(type(profile) is str and profile in PROFILES, "unknown fixed battle profile")
    _require(type(resolution) is str and resolution in RESOLUTIONS, "only nine canonical battle presets admitted")
    return ENTRYPOINTS[profile]


def _read_source(name, digest=None):
    path = ROOT / name
    _require(path.resolve(strict=True) == path and path.is_relative_to(ROOT), "noncanonical source path: " + name)
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
    _require(stamp(before) == stamp(after), "source changed while reading: " + name)
    _require(digest is None or sha256(data) == digest, "pinned source differs: " + name)
    return data, stamp(after)


def _literal(source, name):
    assignments = [node.value for node in ast.parse(source).body if isinstance(node, ast.Assign)
                   and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                   and node.targets[0].id == name]
    _require(len(assignments) == 1, "one frozen literal required: " + name)
    try:
        return ast.literal_eval(assignments[0])
    except (TypeError, ValueError) as error:
        raise ValueError("frozen literal is not static: " + name) from error


def _source_snapshot(profile):
    _require(Path(__file__).resolve() == ROOT / SOURCE, "noncanonical battle context module")
    entry, _, digest = ENTRYPOINTS[profile]
    pins = dict(FOUNDATION_PINS, **{entry: digest})
    roots = [entry]
    if profile == "modalwidgets":
        complete, _, complete_digest = ENTRYPOINTS["completehd"]
        pins.update({complete: complete_digest, ADAPTER_SOURCE: ADAPTER_SHA256})
        roots = [complete, ADAPTER_SOURCE]
    snapshots, stamps = {}, {}
    for name in roots:
        data, stamp = _read_source(name, pins[name])
        snapshots[name], stamps[name] = data, stamp
        declared = _literal(data, "PINNED_SOURCES")
        _require(type(declared) is dict and all(type(k) is type(v) is str and len(v) == 64
                 for k, v in declared.items()), "fixed producer dependency pins required")
        for dependency, dependency_digest in declared.items():
            _require(dependency not in pins or pins[dependency] == dependency_digest, "conflicting frozen source pins")
            pins[dependency] = dependency_digest
    for name, source_digest in pins.items():
        snapshots[name], stamps[name] = _read_source(name, source_digest)
    snapshots[SOURCE], stamps[SOURCE] = _read_source(SOURCE)
    return snapshots, stamps


def _unchanged(snapshots, stamps):
    for name, data in snapshots.items():
        current, stamp = _read_source(name, sha256(data))
        _require(current == data and stamp == stamps[name], "source snapshot changed: " + name)


@contextmanager
def _private_modules(profile, snapshots):
    """Ignore public module aliases/functions; compile the pinned snapshots."""
    prefix = "_clash95_battle_parent_" + uuid.uuid4().hex
    saved_path = list(sys.path)
    try:
        for suffix in ("", ".src", ".src.patcher", ".tools"):
            package = types.ModuleType(prefix + suffix)
            package.__path__ = []
            sys.modules[package.__name__] = package
            if suffix:
                owner, _, leaf = package.__name__.rpartition(".")
                setattr(sys.modules[owner], leaf, package)
        order = list(FOUNDATION_PINS)
        if profile == "modalwidgets":
            order += [ENTRYPOINTS["completehd"][0], ADAPTER_SOURCE]
        order.append(ENTRYPOINTS[profile][0])
        modules = {}
        for name in order:
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__ = str(ROOT / name)
            module.__package__ = full.rpartition(".")[0]
            sys.modules[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)
            exec(compile(snapshots[name], module.__file__, "exec"), module.__dict__)
            _require(Path(module.__file__).resolve() == ROOT / name and module.__name__ == full,
                     "private source module identity differs")
            modules[name] = module
        yield modules
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]
        sys.path[:] = saved_path


def _reconstruct(original, profile, resolution, snapshots):
    entry, revision, _ = _selector(profile, resolution)
    with _private_modules(profile, snapshots) as modules:
        constructor = modules[entry]
        _require(constructor.ROOT == ROOT and constructor.BASE_SHA256 == BASE_SHA256
                 and constructor.STAGE == STABLE_STAGE + "-" + profile + "-allpresets-validation"
                 and constructor.REVISION == revision and constructor.RESOLUTIONS == RESOLUTIONS,
                 "fixed parent constructor constants differ")
        result = constructor.build_candidate(original, resolution)
    _require(type(result) is tuple and len(result) == 3 and type(result[0]) is bytes
             and type(result[1]) is dict and type(result[2]) is str, "parent bundle types differ")
    return result


def _authenticate_bundle(original, profile, resolution, bundle, expected, snapshots):
    """Pure comparison boundary, independently supplied by fixed reconstruction."""
    entry, revision, _ = _selector(profile, resolution)
    _require(type(bundle) is tuple and len(bundle) == 3 and type(bundle[0]) is bytes
             and type(bundle[1]) is dict and type(bundle[2]) is str, "immutable parent bundle required")
    image, metadata, probe = bundle
    _require(image == expected[0] and _typed_canonical(metadata) == _typed_canonical(expected[1])
             and probe == expected[2], "independent full parent reconstruction differs")
    _require(metadata.get("stage") == STABLE_STAGE + "-" + profile + "-allpresets-validation"
             and metadata.get("recipe_revision") == revision and metadata.get("resolution") == resolution
             and metadata.get("base_sha256") == sha256(original) == BASE_SHA256
             and metadata.get("candidate_sha256") == sha256(image)
             and type(metadata.get("candidate_bytes")) is int and metadata["candidate_bytes"] == len(image)
             and metadata.get("probe_sha256") == sha256(probe.encode()), "parent identity differs")
    if profile in ("classic", "framed"):
        _require(metadata.get("profile") == ("classic" if profile == "classic" else "Framed"), "parent profile differs")
    _require(all(metadata.get(key) is False for key in
             ("installation_ready", "runtime_executed", "manual_input_proof", "promotion_ready", "expanded_battle_installed")),
             "parent acceptance must remain false")
    _require(metadata.get("validation_stage_only") is True, "parent must remain validation only")
    expected_pins = {name: sha256(data) for name, data in snapshots.items()
                     if name not in (SOURCE, "src/patcher/framed_battle_viewport.py")}
    # The foundation helpers are extra pins. A parent must declare every one
    # of its own producer dependencies, with exactly the authenticated hashes.
    actual_pins = metadata.get("source_hashes")
    _require(type(actual_pins) is dict and actual_pins and entry in actual_pins
             and all(type(k) is type(v) is str and k in snapshots and sha256(snapshots[k]) == v
                     for k, v in actual_pins.items())
             and all(actual_pins.get(k) == v for k, v in expected_pins.items()), "parent producer source inventory differs")


def _json_dicts(value):
    if type(value) is dict:
        yield value
        for item in value.values():
            yield from _json_dicts(item)
    elif type(value) in (list, tuple):
        for item in value:
            yield from _json_dicts(item)


def _modal_owner(metadata, profile):
    context = metadata
    if profile == "modalwidgets":
        context = context["predecessor"]
        for _ in range(5):
            if context.get("recipe_revision") == "complete_hd_all_presets_v1":
                break
            context = context["base_candidate"]
        _require(context.get("recipe_revision") == "complete_hd_all_presets_v1", "unknown modal ancestry")
    return context["predecessor"]["base_candidate"]


def _state_inventory(candidate, metadata, profile, view, pe, snapshots):
    """Check source-declared fields and all active fixups to the existing page."""
    state = next((s for s in view.sections if s.name.rstrip(b"\0") == b".hdstate"), None)
    _require(state is not None and state.characteristics == RW
             and state.virtual_size == state.raw_size == STATE_PAGE_BYTES
             and candidate[state.raw_offset:state.raw_offset + state.raw_size] == bytes(STATE_PAGE_BYTES),
             "inherited RW state allocation or zero initialization differs")
    source = snapshots["src/patcher/framed_modal_canvas.py"]
    _require(_literal(source, "STATE_SIZE") == INHERITED_STATE_BYTES, "inherited state size differs")
    # The frozen declaration is dict(field=offset), deliberately parsed without
    # executing an untrusted state-layout helper or taking a caller override.
    tree = ast.parse(source)
    node = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "STATE" for t in n.targets))
    _require(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict"
             and not node.args and all(k.arg is not None for k in node.keywords), "frozen state layout declaration differs")
    offsets = {k.arg: ast.literal_eval(k.value) for k in node.keywords}
    _require(len(offsets) == len(node.keywords) and len(set(offsets.values())) == len(offsets)
             and all(type(n) is int and n % 4 == 0 and 0 <= n <= INHERITED_STATE_BYTES - 4 for n in offsets.values()),
             "inherited state field extent differs")
    owner = _modal_owner(metadata, profile)
    page_va = view.image_base + state.rva
    _require(type(owner) is dict and owner.get("state_va") == page_va
             and owner.get("state_bytes") == STATE_PAGE_BYTES and owner.get("state_raw_offset") == state.raw_offset
             and _canonical(owner.get("modal_state_offsets")) == _canonical(offsets), "modal state owner differs")
    declared = {}
    for item in _json_dicts(metadata):
        code_va = item.get("code_va")
        if type(code_va) is not int:
            continue
        for row in item.get("relocations", []):
            if row.get("kind") != "abs32" or type(row.get("target")) is not int:
                continue
            target = row["target"]
            if page_va <= target < page_va + STATE_PAGE_BYTES:
                _require(type(row.get("offset")) is int and target - page_va in offsets.values(),
                         "unowned inherited state reference")
                rva = code_va - view.image_base + row["offset"]
                _require(rva not in declared or declared[rva] == target, "conflicting inherited state operands")
                declared[rva] = target
    _, fixups = pe._old_relocations(candidate, view)
    observed = {}
    for rva in fixups:
        target = struct.unpack_from("<I", candidate, view.file_offset(rva, 4))[0]
        if page_va <= target < page_va + STATE_PAGE_BYTES:
            _require(target - page_va in offsets.values(), "active fixup escapes inherited state fields")
            observed[rva] = target
    _require(bool(observed) and observed == declared, "complete inherited state fixup inventory differs")
    for rva in observed:
        _require(any(s.characteristics == RX and s.rva <= rva and rva + 4 <= s.rva + s.raw_size
                     for s in view.sections), "state operand is outside owned RX code")
    _require(INHERITED_STATE_BYTES <= BATTLE_STATE_OFFSET
             and BATTLE_STATE_OFFSET + BATTLE_STATE_BYTES <= state.raw_size, "battle state reservation overlaps inherited fields")
    return dict(page_va=page_va, page_rva=state.rva, page_raw_offset=state.raw_offset,
                inherited_extent=[page_va, page_va + INHERITED_STATE_BYTES], inherited_fields=offsets,
                active_state_fixup_count=len(observed),
                active_state_fixups=[dict(rva=rva, target=observed[rva]) for rva in sorted(observed)],
                inventory_scope="pinned source-declared fields and active HIGHLOW operands; dynamic lifetime unproven")


def _allocation_plan(original, candidate, metadata, profile, resolution, snapshots, pe, geometry):
    """Pure format planning after parent authentication; never installation."""
    before, view = pe.inspect_pe(original), pe.inspect_pe(candidate)
    _require(len(before.sections) == 7 and view.sections[:7] == before.sections
             and (view.image_base, view.section_alignment, view.file_alignment, view.headers_size)
                 == (0x400000, 4096, 512, 1024), "historical PE section ownership differs")
    width, height = map(int, resolution.split("x"))
    suffix = () if profile == "classic" and width < 1144 else (b".hdcode",)
    if profile in ("completehd", "modalwidgets"):
        suffix = (b".hdcode", b".hdmodal", b".hdstate", b".hdarmy")
        if profile == "modalwidgets":
            suffix += (b".hdslots", b".hdprim", b".hdptxt", b".hdwgt")
    appended = view.sections[7:]
    _require(tuple(s.name.rstrip(b"\0") for s in appended) == suffix
             and all(s.characteristics == (RW if s.name.rstrip(b"\0") == b".hdstate" else RX) for s in appended),
             "profile-specific historical sections or permissions differ")
    _require(all(a.rva + pe._align(a.memory_size, 4096) == b.rva for a, b in zip(view.sections, view.sections[1:])),
             "historical virtual section extents are not adjacent")
    slot = view.sections[-1].header_offset + 40
    fresh_state = profile in ("classic", "framed")
    limit = 0x300 if fresh_state else 0x400
    count = 2 if fresh_state else 1
    expected_slot = (0x280 if not suffix else 0x2A8) if fresh_state else (0x320 if profile == "completehd" else 0x3C0)
    _require(slot == expected_slot and slot + count * 40 <= min(limit, view.headers_size)
             and candidate[slot:slot + count * 40] == bytes(count * 40), "unused battle header slots or scratch bounds differ")
    if not fresh_state:
        owner = _modal_owner(metadata, profile)
        army = metadata if profile == "completehd" else None
        if army is None:
            context = metadata["predecessor"]
            while context.get("recipe_revision") != "complete_hd_all_presets_v1":
                context = context["base_candidate"]
            army = context
        _require(army["predecessor"].get("retired_header_scratch") ==
                 dict(start=0x300, end_exclusive=0x348, legacy_day_diagnostic_allowed=False),
                 "owned-modal header scratch retirement differs")
        _require(owner.get("state_bytes") == STATE_PAGE_BYTES, "owned-modal state page missing")
    code_va = view.image_base + view.image_size
    _require(code_va + CODE_RESERVATION + (STATE_PAGE_BYTES if fresh_state else 0) < 0x80000000,
             "planned battle allocation exceeds x86 user range")
    inventory = None if fresh_state else _state_inventory(candidate, metadata, profile, view, pe, snapshots)
    state_va = code_va + CODE_RESERVATION if fresh_state else inventory["page_va"] + BATTLE_STATE_OFFSET
    arenas = []
    for columns in range(1, 21):
        layout = geometry.TacticalViewport(width, height, columns)
        arenas.append(dict(world_columns=columns, visible_columns=layout.visible_columns,
            max_scroll_x=layout.max_scroll_x, arena=list(layout.arena.as_tuple()),
            gutter_before_hud=layout.hud.left - layout.arena.right - 1))
    maximum = geometry.TacticalViewport(width, height, 20)
    return dict(schema="clash95_battle_profile_context_v1", profile=profile, resolution=resolution,
        parent_stage=metadata["stage"], parent_revision=metadata["recipe_revision"],
        original_sha256=sha256(original), candidate_sha256=sha256(candidate), parent_bytes=len(candidate),
        canonical_probe_sha256=metadata["probe_sha256"],
        source_hashes={name: sha256(data) for name, data in snapshots.items()},
        allocation_plan_only=True, parent_reconstruction_passed=True, **{key: False for key in FALSE_CLAIMS},
        rx=dict(va=code_va, rva=view.image_size, header_offset=slot, raw_offset=len(candidate),
                virtual_reservation=CODE_RESERVATION, characteristics=RX, code_and_relocations_unemitted=True),
        rw=dict(va=state_va, used_bytes=BATTLE_STATE_BYTES, characteristics=RW,
                allocation="fresh_zero_page" if fresh_state else "reserved_existing_modal_page",
                header_offset=slot + 40 if fresh_state else None,
                page_bytes=STATE_PAGE_BYTES, zero_initialization_required=True,
                page_offset=0 if fresh_state else BATTLE_STATE_OFFSET,
                raw_offset=None if fresh_state else inventory["page_raw_offset"] + BATTLE_STATE_OFFSET,
                fresh_raw_offset_unresolved=fresh_state),
        inherited_state_inventory=inventory, original_sections_preserved=True,
        header_slots_zero=True, scratch_limit=limit, future_section_count=len(view.sections) + count,
        geometry=dict(origin=[32, 16], tile_pixels=64, rows=7, maximum_columns=20,
                      native_sprite_scale_required=True, hud=list(maximum.hud.as_tuple()),
                      hud_slices=[dict(source=list(part.source.as_tuple()), destination=list(part.destination.as_tuple()))
                                  for part in maximum.hud_slices],
                      arenas=arenas, unused_space_must_reject_input=True),
        limitations=["Allocation plan only; no code, headers, state, hooks or relocations installed.",
                     "Future installation must reauthenticate the parent and its complete atomic battle recipe.",
                     "State reuse authenticates declared operands; dynamic arithmetic, owner/thread/lifetime and loader behavior need separate verification.",
                     "Animation, dialogs/results, exceptional exits, restoration and every runtime acceptance lane remain unimplemented."])


def _context(original, profile, resolution, supplied=None):
    _selector(profile, resolution)
    _require(type(original) is bytes and sha256(original) == BASE_SHA256, "exact original executable required; no override")
    snapshots, stamps = _source_snapshot(profile)
    bundle = _reconstruct(original, profile, resolution, snapshots) if supplied is None else supplied
    expected = _reconstruct(original, profile, resolution, snapshots)
    _authenticate_bundle(original, profile, resolution, bundle, expected, snapshots)
    _unchanged(snapshots, stamps)
    with _private_modules(profile, snapshots) as modules:
        plan = _allocation_plan(original, bundle[0], bundle[1], profile, resolution, snapshots,
                                modules["src/patcher/pe_extension.py"], modules["src/patcher/framed_battle_viewport.py"])
    _unchanged(snapshots, stamps)
    return BattleProfileContext(bundle[0], _typed_canonical(bundle[1]), bundle[2], _canonical(plan))


def build_parent_context(original: bytes, profile: str, resolution: str) -> BattleProfileContext:
    return _context(original, profile, resolution)


def authenticate_parent(original: bytes, candidate: bytes, metadata: dict, canonical_probe: str,
                        *, profile: str, resolution: str) -> BattleProfileContext:
    return _context(original, profile, resolution, (candidate, metadata, canonical_probe))
