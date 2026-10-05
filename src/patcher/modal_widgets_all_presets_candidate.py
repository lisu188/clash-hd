"""Source-bound nine-preset Modal Widgets successor, with no runtime or writer.

Reconstruct Complete HD once, then authenticate and replay the slots, primary,
quantity-text and descriptor-bound layers. Frozen public recipes are unchanged.
The returned probe is an initial-image, preferred-address observer; it is not a
loader-rebased verifier, modal-route observation or evidence of acceptance.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import struct
from typing import Any

from . import complete_hd_all_presets_candidate as parent
from . import owned_modal_all_presets_emit as adapters

ROOT = Path(__file__).resolve().parents[2]
STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
         "presentbounds-minimapright-dynvswitch-modalwidgets-allpresets-validation")
REVISION = "modal_widgets_all_presets_v1"
RESOLUTIONS = parent.RESOLUTIONS
BASE_SHA256 = parent.BASE_SHA256
FALSE_CLAIMS = parent.FALSE_CLAIMS + ("primary_composition_proven", "expanded_battle_installed",
                                      "launcher_registered", "matrix_registered")
LAYERS = (
    ("slots", b".hdslots", (0x432C0B,), "owned_barracks_dirty_slots_all_presets_v1"),
    ("primary", b".hdprim", (0x401E30, 0x432F94, 0x432F5C, 0x4331D5, 0x433273), "owned_modal_primary_all_presets_v1"),
    ("text", b".hdptxt", (0x432C66,), "owned_modal_primary_text_all_presets_v1"),
    ("widgets", b".hdwgt", (0x419D63, 0x419D8C), REVISION),
)
PREDICATE = re.compile(r"\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)")
sha256, _require = parent.sha256, parent._require


def _stage(kind: str) -> str:
    return STAGE if kind == "widgets" else STAGE.removesuffix("-validation") + "-" + kind + "-validation"


def _sources() -> dict[str, bytes]:
    sources = adapters._sources()
    for name in ("src/patcher/owned_modal_all_presets_emit.py", "src/patcher/modal_widgets_all_presets_candidate.py"):
        path = ROOT / name
        _require(path.resolve() == path and path.is_relative_to(ROOT), "noncanonical successor source path")
        sources[name] = path.read_bytes()
    _require(Path(__file__).resolve() == ROOT / "src/patcher/modal_widgets_all_presets_candidate.py"
             and Path(adapters.__file__).resolve() == ROOT / "src/patcher/owned_modal_all_presets_emit.py"
             and Path(parent.__file__).resolve() == ROOT / "src/patcher/complete_hd_all_presets_candidate.py"
             and adapters.parent is parent and parent.ROOT == ROOT,
             "noncanonical successor module path")
    return sources


def byte_records(original: bytes, candidate: bytes, view: Any) -> list[dict[str, Any]]:
    records = parent.byte_records(original, candidate, view)
    for row in records:
        row.update(stage=STAGE, group="modal-widgets-all-presets-extension" if row["appended"]
                   else "modal-widgets-all-presets-integrated",
                   rationale="Exact all-preset parent and frozen modal ownership, ABI and geometry reconstruction")
    return records


def apply_records(original: bytes, records: list[dict[str, Any]], *, expected_base_sha256: str, view: Any) -> bytes:
    _require(type(records) is list and all(type(row) is dict and row.get("stage") == STAGE for row in records),
             "successor byte-record stage differs")
    rows = deepcopy(records)
    for row in rows:
        row["stage"] = parent.STAGE
    return parent.apply_records(original, rows, expected_base_sha256=expected_base_sha256, view=view)


def _extension(modules: dict[str, Any], kind: str) -> Any:
    name = "tools/build_framed_modal_widgets_candidate.py" if kind == "widgets" else (
        "src/patcher/pe_modal_" + {"slots": "slots", "primary": "primary", "text": "primary_text"}[kind] + "_extension.py")
    return modules[name]


def _audit_layer(candidate: bytes, context: dict[str, Any], kind: str, pe: Any) -> tuple[bytes, dict[str, Any]]:
    """Undo every edit, then independently audit allocation and HIGHLOW ownership."""
    index = next(i for i, row in enumerate(LAYERS) if row[0] == kind)
    _, name, sites, revision = LAYERS[index]
    _require(type(context) is dict and context.get("stage") == _stage(kind)
             and context.get("recipe_revision") == revision and context.get("resolution") in RESOLUTIONS
             and context.get("candidate_sha256") == context.get("output_sha256") == sha256(candidate)
             and context.get("original_sha256") == BASE_SHA256
             and all(context.get(key) is False for key in FALSE_CLAIMS), "successor identity or acceptance differs")
    before_bytes = parent._undo_edits(candidate, context, pe)
    predecessor = context.get("base_candidate")
    _require(type(predecessor) is dict and predecessor.get("candidate_sha256") == sha256(before_bytes)
             and context.get("base_candidate_sha256") == sha256(before_bytes)
             and context.get("base_stage") == predecessor.get("stage"), "successor predecessor identity differs")
    before, after = pe.inspect_pe(before_bytes), pe.inspect_pe(candidate)
    code = after.sections[-1]
    _require(len(before.sections) == 11 + index and len(after.sections) == 12 + index
             and after.sections[:-1] == before.sections and code.name.rstrip(b"\0") == name
             and code.characteristics == parent.RX and code.virtual_size == 0x20000
             and code.raw_offset == len(before_bytes) and code.raw_offset + code.raw_size == len(candidate)
             and code.rva == before.image_size and code.header_offset == 0x320 + 40 * index
             and (after.section_alignment, after.file_alignment, after.headers_size) == (4096, 512, 1024)
             and after.image_size == code.rva + 0x20000
             and after.size_of_code == before.size_of_code + code.raw_size
             and all(a.rva + pe._align(a.memory_size, 4096) == b.rva
                     for a, b in zip(after.sections, after.sections[1:])), "successor allocation or protection differs")
    _require(context.get("state_bytes") == 0 and type(context.get("state_bytes")) is int
             and context.get("state_va") is context.get("state_raw_offset") is context.get("state_characteristics") is None,
             "successor must not allocate mutable state")
    size = context.get("code_bytes")
    _require(type(size) is int and 0 < size < 4096 and context.get("code_va") == after.image_base + code.rva
             and context.get("code_rva") == code.rva and context.get("code_raw_bytes") == code.raw_size
             and context.get("code_virtual_bytes") == 0x20000 and context.get("code_characteristics") == parent.RX
             and context.get("code_sha256") == sha256(candidate[code.raw_offset:code.raw_offset + size]),
             "successor code identity differs")
    hooks = context.get("hooks")
    _require(type(hooks) is list and tuple(row.get("va") for row in hooks) == sites,
             "exact successor hook inventory required")
    hook_spans, by_va = [], {}
    for row in hooks:
        offset, rva, va = row.get("offset"), row.get("rva"), row.get("va")
        old, new = parent._hex(row.get("old_hex")), parent._hex(row.get("new_hex"))
        _require(type(offset) is type(rva) is type(va) is int and bool(old) and len(old) == len(new)
                 and va == after.image_base + rva and before.file_offset(rva, len(old)) == offset
                 and before_bytes[offset:offset + len(old)] == old and candidate[offset:offset + len(new)] == new,
                 "successor installed hook differs")
        _require(any(s.characteristics & 0x20000000 and s.rva <= rva and rva + len(new) <= s.rva + s.raw_size
                     for s in before.sections), "successor hook outside inherited RX memory")
        hook_spans.append((rva, rva + len(new)))
        by_va[va] = row
    hook_spans.sort()
    _require(all(a[1] <= b[0] for a, b in zip(hook_spans, hook_spans[1:])), "successor hooks overlap")
    old_table, old_fields = pe._old_relocations(before_bytes, before)
    _require(context.get("removed_highlow") == [] and not any(start < rva + 4 and rva < end
             for rva in old_fields for start, end in hook_spans), "successor cannot displace inherited HIGHLOW")
    fields, hook_fields = context.get("relocations"), context.get("hook_relocations")
    _require(type(fields) is list and type(hook_fields) is list, "successor declared operands missing")
    absolute, operands = [], []
    for row, native in [(row, False) for row in fields] + [(row, True) for row in hook_fields]:
        offset, target, form = row.get("offset"), row.get("target"), row.get("kind")
        _require(type(offset) is type(target) is int and 0 <= target < 2**32 and form in ("abs32", "rel32")
                 and type(row.get("purpose")) is str and row["purpose"].strip(), "invalid successor operand")
        if native:
            hook = by_va.get(row.get("hook_va"))
            _require(hook is not None and 0 <= offset <= len(parent._hex(hook["new_hex"])) - 4
                     and row.get("rva") == hook["rva"] + offset, "successor hook operand mapping differs")
            rva = hook["rva"] + offset
        else:
            _require(0 <= offset <= size - 4, "successor code operand exceeds payload")
            rva = code.rva + offset
        relative = target - after.image_base
        _require(any(s.rva <= relative < s.rva + s.memory_size and (form == "abs32" or s.characteristics & 0x20000000)
                     for s in after.sections), "successor operand target is unowned or non-executable")
        expected = target if form == "abs32" else (target - after.image_base - rva - 4) & 0xFFFFFFFF
        _require(struct.unpack_from("<I", candidate, after.file_offset(rva, 4))[0] == expected,
                 "successor declared operand differs")
        operands.append(rva)
        if form == "abs32":
            absolute.append(rva)
    operands.sort()
    _require(all(a + 4 <= b for a, b in zip(operands, operands[1:]))
             and len(set(old_fields) | set(absolute)) == len(old_fields) + len(absolute), "successor operand overlap or alias")
    table, actual = pe._old_relocations(candidate, after)
    expected_fields = sorted(set(old_fields) | set(absolute))
    _require(list(actual) == expected_fields and table == pe._relocation_blocks(expected_fields)
             and context.get("old_relocation_sha256") == sha256(old_table)
             and context.get("merged_relocation_sha256") == sha256(table)
             and context.get("old_highlow_count") == len(old_fields)
             and context.get("new_highlow_count") == len(absolute), "successor complete HIGHLOW inventory differs")
    table_at = pe._align(size, 4)
    _require(after.relocation_rva == code.rva + table_at and context.get("relocation_rva") == after.relocation_rva
             and context.get("relocation_bytes") == after.relocation_size
             and candidate[code.raw_offset + size:code.raw_offset + table_at] == bytes(table_at - size)
             and candidate[code.raw_offset + table_at + len(table):] == bytes(code.raw_size - table_at - len(table))
             and candidate[before.file_offset(before.relocation_rva, len(old_table)):
                           before.file_offset(before.relocation_rva, len(old_table)) + len(old_table)] == old_table,
             "successor relocation directory or padding differs")
    return before_bytes, dict(section_name=name.decode(), hook_count=len(hooks), code_bytes=size,
                              merged_highlow_count=len(actual), new_state_bytes=0)


def _build_layer(original, base, context, kind, modules, pe, source_hashes):
    """Only invoked with the reconstructed, audited immediate predecessor."""
    width, height = map(int, context["resolution"].split("x"))
    extension = _extension(modules, kind)
    layout = extension.allocation_layout(base)
    code_va = layout[0] if kind == "widgets" else layout.code_va
    bundle = adapters._emit(modules, kind, original, base, context, base_va=code_va, width=width, height=height)
    revision = next(row[3] for row in LAYERS if row[0] == kind)
    binding = dict(original_sha256=BASE_SHA256, base_stage=context["stage"], stage=_stage(kind),
                   resolution=context["resolution"], base_candidate_sha256=sha256(base), recipe_revision=revision)
    result = extension._extend_verified_image(base, code=bundle.code, code_va=code_va,
        relocations=bundle.relocations, hooks=bundle.hook_sites, binding=binding)
    owner = context["predecessor"]["base_candidate"] if kind == "slots" else None
    entries = owner["modal_entry_vas"] if owner else context["modal_entry_vas"]
    metadata = dict(result.metadata, candidate_sha256=sha256(result.image), base_candidate=context,
        source_hashes=source_hashes, modal_state_va=bundle.modal_state_va, modal_entry_vas=entries,
        state_bytes=0, state_va=None, state_raw_offset=None, state_characteristics=None,
        layer_kind=kind, layer_entries=dict(bundle.entries), layer_contract=bundle.source_contract,
        validation_stage_only=True, **{key: False for key in FALSE_CLAIMS})
    _require(bundle.candidate_sha256 == sha256(base)
             and bundle.source_contract["predecessor_stage"] == context["stage"]
             and bundle.source_contract["predecessor_revision"] == context["recipe_revision"],
             "successor emitter predecessor binding differs")
    return result.image, metadata, bundle


def _authenticate_context(original, candidate, context, complete_image, complete_context, modules, pe, source_hashes):
    """Reverse/re-emit every layer against an exact, independently built parent.

    Synthetic private-format fixtures cannot enter the public constructor: that
    boundary always verifies original identity and supplies the real parent.
    """
    chain, current, manifest = [], candidate, context
    while manifest.get("recipe_revision") != parent.REVISION:
        kind = manifest.get("layer_kind")
        _require(kind in tuple(row[0] for row in LAYERS), "unknown successor ancestry")
        before, audit = _audit_layer(current, manifest, kind, pe)
        chain.append((current, manifest, kind, audit))
        current, manifest = before, manifest["base_candidate"]
        _require(len(chain) <= 4, "successor ancestry is too deep")
    _require(current == complete_image and _canonical(manifest) == _canonical(complete_context)
             and complete_context.get("candidate_sha256") == sha256(complete_image), "exact all-preset Complete HD parent required")
    _require([row[2] for row in reversed(chain)] == [row[0] for row in LAYERS[:len(chain)]],
             "successor layer order differs")
    for expected_image, expected_context, kind, _ in reversed(chain):
        rebuilt, rebuilt_context, _ = _build_layer(original, current, manifest, kind, modules, pe, source_hashes)
        _require(rebuilt == expected_image and _canonical(rebuilt_context) == _canonical(expected_context),
                 "exact source-emitted successor layer reconstruction differs")
        current, manifest = rebuilt, rebuilt_context
    return [row[3] for row in reversed(chain)]


def _canonical(value):
    """Compare exact JSON types, avoiding Python's True==1 and integer==float."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("noncanonical successor metadata") from error


def _audit_hook_chain(complete_image, candidate, complete_context, layers, pe):
    """Only the inherited 401E30 full-blit span can be replaced by primary."""
    inherited = complete_context["predecessor"]
    hooks = inherited["base_candidate"]["hooks"] + inherited["hooks"]
    view = pe.inspect_pe(candidate)
    spans = {row["va"]: row for row in hooks}
    overlaps = []
    for layer in layers:
        for row in layer["hooks"]:
            for old in list(spans.values()):
                if max(row["va"], old["va"]) >= min(row["va"] + len(parent._hex(row["new_hex"])),
                                                               old["va"] + len(parent._hex(old["new_hex"]))):
                    continue
                _require(layer["layer_kind"] == "primary" and row["va"] == old["va"] == 0x401E30
                         and row["old_hex"] == old["new_hex"], "unsupported native hook overlap")
                overlaps.append(row["va"])
            spans[row["va"]] = row
    _require(overlaps == [0x401E30] and 0x4224B2 in spans, "full-blit replacement or root restore inventory differs")
    for row in spans.values():
        new = parent._hex(row["new_hex"])
        offset = view.file_offset(row["va"] - view.image_base, len(new))
        _require(candidate[offset:offset + len(new)] == new, "final inherited/native hook differs")
    root = spans[0x4224B2]
    offset = view.file_offset(0x4224B2 - view.image_base, len(parent._hex(root["new_hex"])))
    _require(candidate[offset:offset + len(parent._hex(root["new_hex"]))]
             == complete_image[offset:offset + len(parent._hex(root["new_hex"]))], "root exit/restore changed")
    return dict(native_hook_count=len(spans), permitted_overlap_va=0x401E30, root_restore_preserved=True)


def _probe(base, candidate, complete_context, inherited, layers, modules, pe, producer_digest):
    """Rebind all ancestor image predicates and retire their success identities."""
    text = modules["tools/build_framed_modal_primary_text_candidate.py"]
    checks = modules["tools/build_framed_modal_candidate.py"] if "tools/build_framed_modal_candidate.py" in modules else None
    # The parent's private namespace already contains the checked-line helper.
    if checks is None:
        prefix = text.__name__.split(".", 1)[0]
        import sys
        checks = sys.modules[prefix + ".tools.build_framed_modal_candidate"]
    _require(type(inherited) is str and sha256(inherited.encode()) == complete_context["probe_sha256"],
             "exact Complete HD probe identity required")
    before, after = pe.inspect_pe(base), pe.inspect_pe(candidate)
    changed = set()
    for layer in layers:
        for row in layer["edits"]:
            changed.update(range(row["va"], row["va"] + len(parent._hex(row["old_hex"]))))
    count = 0
    def rebind(match):
        nonlocal count
        kind, address, expected = match.groups()
        va, size = int(address, 16), 2 if kind == "wo" else 1
        old = text.loaded_bytes(base, before, va, size)
        new = text.loaded_bytes(candidate, after, va, size)
        _require(int.from_bytes(old, "little") == int(expected, 16), "inherited loaded predicate differs")
        _require(all(a == b or va + index in changed for index, (a, b) in enumerate(zip(old, new))),
                 "loaded predicate changed outside authenticated edits")
        count += 1
        return f'({kind}({address}) != {int.from_bytes(new, "little"):x})'
    rebound = PREDICATE.sub(rebind, inherited)
    _require(count > 0, "inherited loaded predicates missing")
    parent_marker = ".echo " + complete_context["probe_contract"]["complete_marker"]
    _require(rebound.splitlines().count(parent_marker) == 1, "exact Complete HD marker required")
    spans = [(after.image_base, candidate[:after.headers_size])]
    spans += [(after.image_base + section.rva, candidate[section.raw_offset:section.raw_offset + section.raw_size])
              for section in after.sections[-4:]]
    for layer in layers:
        spans += [(row["va"], parent._hex(row["new_hex"])) for row in layer["hooks"]]
    primary = modules["src/patcher/framed_modal_primary.py"]
    for va, size in ([(0x432940, 1006), (primary.HD_BLIT, 96)]
                     + [(v, n) for v, n, _ in primary.NATIVE_SPANS + primary.CURSOR_CONTEXT_SPANS]
                     + [(v, 12) for v in primary.CURSOR_DESCRIPTORS]
                     + [(v, n) for v, n, _ in modules["src/patcher/framed_modal_primary_text.py"].NATIVE_SPANS]
                     + [(row["va"], row["size"]) for row in layers[-1]["layer_contract"]["native_spans"]]):
        spans.append((va, text.loaded_bytes(candidate, after, va, size)))
    spans.append((primary.CURSOR_STARTUP_DESCRIPTOR, bytes(12)))
    quantity = modules["src/patcher/framed_modal_primary_text.py"]
    spans.append((quantity.TEXT_FORMAT, text.loaded_bytes(candidate, after, quantity.TEXT_FORMAT, 3)))
    new_checks = [line.replace("MCANVAS_CONTRACT_FAIL", "MODAL_ALL_PRESETS_CONTRACT_FAIL")
                  for line in checks._checked_lines(spans)]
    resolution, digest = layers[-1]["resolution"], sha256(candidate)
    marker = (f"MODAL_WIDGETS_ALL_PRESETS_CONTRACT_PASS stage={STAGE} resolution={resolution} "
              f"candidate_sha256={digest} revision={REVISION} producer_sha256={producer_digest}")
    result, retired = [], []
    for line in rebound.splitlines():
        if line == parent_marker:
            result.extend(new_checks)
            result.append(".echo " + marker)
        if line.startswith(".echo ") and "_CONTRACT_PASS" in line:
            retired.append(line)
        else:
            result.append(line)
    _require(len(retired) >= 3 and all(len(line.encode("ascii")) < 4096 for line in result),
             "inherited success inventory or debugger line limit differs")
    probe = "\n".join(result) + "\n"
    _require(probe.count("_CONTRACT_PASS") == 1, "ancestor success marker survived")
    return probe, dict(complete_marker=marker, preferred_address_only=True, initial_map_only=True,
        requires_loaded_byte_checks=True, all_inherited_checks_required=True, inherited_predicate_count=count,
        retired_ancestor_markers=retired, inherited_probe_sha256=sha256(inherited.encode()),
        scope="Initial ordinary-map image at preferred addresses only; modal routes, loader rebasing, input and endurance require independent evidence")


def build_candidate(original: bytes, resolution: str) -> tuple[bytes, dict[str, Any], str]:
    _require(type(original) is bytes and sha256(original) == BASE_SHA256,
             "unknown original executable SHA-256; successor has no override")
    _require(type(resolution) is str and resolution in RESOLUTIONS, "only the nine canonical validation presets are admitted")
    sources = _sources()
    source_hashes = {name: sha256(data) for name, data in sources.items()}
    producer_digest = sha256(sources["src/patcher/modal_widgets_all_presets_candidate.py"]
                             + sources["src/patcher/owned_modal_all_presets_emit.py"])
    with adapters._producer(sources) as (modules, pe, geometry):
        bound_parent = modules["src/patcher/complete_hd_all_presets_candidate.py"]
        _require(bound_parent.REVISION == parent.REVISION and bound_parent.STAGE == parent.STAGE
                 and bound_parent.RESOLUTIONS == RESOLUTIONS, "private parent identity differs")
        complete_image, complete_context, inherited = bound_parent.build_candidate(original, resolution)
        parent._audit_final(original, complete_image, complete_context["predecessor"], resolution, pe, geometry)
        base, context, layers, bundles = complete_image, complete_context, [], []
        for kind, _, _, _ in LAYERS:
            _authenticate_context(original, base, context, complete_image, complete_context, modules, pe, source_hashes)
            base, context, bundle = _build_layer(original, base, context, kind, modules, pe, source_hashes)
            layers.append(context)
            bundles.append(bundle)
        audits = _authenticate_context(original, base, context, complete_image, complete_context, modules, pe, source_hashes)
        hooks = _audit_hook_chain(complete_image, base, complete_context, layers, pe)
        view = pe.inspect_pe(base)
        state = next(section for section in view.sections if section.name.rstrip(b"\0") == b".hdstate")
        _require(state.characteristics == parent.RW and state.virtual_size == state.raw_size == 4096
                 and base[state.raw_offset:state.raw_offset + state.raw_size] == bytes(4096), "inherited zero modal state differs")
        records = byte_records(original, base, view)
        _require(apply_records(original, records, expected_base_sha256=BASE_SHA256, view=view) == base,
                 "complete original-to-final replay differs")
        probe, contract = _probe(complete_image, base, complete_context, inherited, layers, modules, pe, producer_digest)
    _require(_sources() == sources, "successor source changed during reconstruction")
    metadata = dict(schema="clash95_modal_widgets_all_presets_candidate_v1", stage=STAGE, recipe_revision=REVISION,
        resolution=resolution, base_sha256=BASE_SHA256, candidate_sha256=sha256(base), candidate_bytes=len(base),
        source_hashes=source_hashes, producer_sha256=producer_digest, patch_records=records,
        predecessor=context, structural_gate=dict(section_count=15, modal_state_bytes=4096, layers=audits, **hooks),
        probe_sha256=sha256(probe.encode()), probe_contract=contract, validation_stage_only=True,
        features=dict(complete_hd=True, modal_slots=True, modal_primary=True, modal_primary_text=True,
                      modal_widget_bounds=True, expanded_battle=False), **{key: False for key in FALSE_CLAIMS},
        limitations=["Source construction, byte replay and PE ownership do not establish runtime or stable acceptance.",
                     "Preferred-address initial-map predicates are not loader-rebased or complete modal-route verifiers.",
                     "Primary composition, native input, modal restoration, final wrapper and endurance require fresh evidence.",
                     "Expanded battle is uninstalled; custom dimensions and 802x602 are not admitted.",
                     "Launcher advertisement and runtime matrix acceptance remain separate; source authentication supplies no acceptance."])
    return base, metadata, probe
