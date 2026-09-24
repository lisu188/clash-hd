"""Add native-size top/bottom sidebar anchors to the frozen expanded battle.

This successor preserves the old 1280x720 stage and combat/field geometry.
It installs no runtime input injection and makes no runtime acceptance claim.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import struct

from . import battle_hd_hud as hud
from . import partial_tile_clip as clip
from . import patch_clash95_hd as scalar
from . import pe_extension as pe
from .battle_hd_section import validate_spans

ROOT = Path(__file__).resolve().parents[2]
STAGE = scalar.BATTLE_HD_STAGE + '-edgecontrols-validation'
REVISION = 'expanded_battle_edge_controls_v1'
RESOLUTION = '1280x720'
BASE_SHA256 = '7d04fe9005515dad4e618df507103946265d7e2a6421287281c1fc5f112d1e47'
CURRENT_BASE_SHA256 = '99d92ec7c8f81debf60321dcc5c1b5872c96e3c485fa2bdd7d9332287b3c7e87'
# Preserve this recipe's published predecessor and output after the separate
# battle-input repair. These are exact current-to-frozen bytes, not a general
# downgrade path. Both complete image identities are required around the edits.
PREDECESSOR_RESTORATIONS = (
    pe.ByteEdit(0x05FE61, 0x060A61, 0x460A61,
        bytes.fromhex('e99a2a1000' + '90' * 33), bytes.fromhex('e9aa8d0800' + '90' * 33),
        'restore frozen dynamic-origin mouse hook'),
    pe.ByteEdit(0x060211, 0x060E11, 0x460E11,
        bytes.fromhex('e9ea251000' + '90' * 33), bytes.fromhex('e9aa8b0800' + '90' * 33),
        'restore frozen metadata-based cursor bounds hook'),
    pe.ByteEdit(0x12E200, 0x163400, 0x563400,
        bytes.fromhex('813dd8995100b0e84200750f68d0020000b900050000e9c365f8ffe9a065f8ff'), bytes(32),
        'restore zero padding occupied by the new cursor bounds helper'),
    pe.ByteEdit(0x12E300, 0x163500, 0x563500,
        bytes.fromhex('813dd8995100b0e84200752ba1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28e950d5efffe9d462f8ff'), bytes(60),
        'restore zero padding occupied by the new relative-input helper'),
)
# The four battle files have independently checked CRLF checkout and LF Git
# identities. Enumerate those exact byte sequences; never normalize runtime reads.
PINNED = {
    'src/patcher/battle_hd_hud.py': (
        'ad867f7627fc4720169ac653becceca4164c03d544a8d3a414a000b3bd47c9c9',
        'e77dd58d5348824abe626c450aae1f9277d8649eadf98115b84b6b83be12aa98',
    ),
    'src/patcher/battle_hd_core.py': (
        'fdc5c65197a4a94184380671638ffe448d3ba3c004dac236f10d7388e3079a72',
        '745c678ae47cb61deae02152d4e2b646dc03932804fd1c0775b192534b5bed0c',
    ),
    'src/patcher/battle_hd_layout.py': (
        '015e4832ae653dba789873b5b14e0768c9cb2b6c42d2d47425f53ae7de795f04',
        'bbeb0d55a9b8a45da76914faf857b7ec1f6294b5a247c9129d8e04a562029c99',
    ),
    'src/patcher/battle_hd_section.py': (
        '6705fdc01780bd8b4a4153dd2ed3788a827db427eb633fd3a14af650449c73a0',
        '798b8d738af7062717ff62ba04216124eb4685c1b454f86518dbc7c7c11a46ee',
    ),
    'src/patcher/patch_clash95_hd.py': (
        '38021e9a4d21bc9a8bf0c2f9b66379595509446b5177d6f91bab6f677b5e8106',
    ),
    'src/patcher/pe_extension.py': (
        '4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27',
    ),
    'src/patcher/partial_tile_clip.py': (
        '92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad',
    ),
}

# Source x,y,width,height,destination x,y. Pixels remain native size.
SIDEBAR_BLITS = ((480, 0, 160, 368, 1120, 0), (480, 368, 160, 112, 1120, 608))
GAP_FRAME_BLITS = ((480, 16, 16, 240, 1120, 368), (624, 16, 16, 240, 1264, 368))
FRAME_BLITS = (hud.FRAME_BLITS[0], *SIDEBAR_BLITS, *GAP_FRAME_BLITS, *hud.FRAME_BLITS[2:])
NATIVE_DESCRIPTORS = ((498, 370), (561, 370), (498, 401), (498, 432), (561, 401), (505, 0))
DESCRIPTORS = tuple((x + 640, y + (240 if i < 5 else 0)) for i, (x, y) in enumerate(NATIVE_DESCRIPTORS))
# Each named instruction restores native Y only; all widened X values stay.
RESTORE_Y = (
    0x42E183, 0x42E190, 0x42E212, 0x42E21F, 0x42E24D, 0x42E25C,
    0x42E28A, 0x42E299, 0x42E2C7, 0x42E2D6, 0x42E304, 0x42E313,
    0x42E341, 0x42E350, 0x42E37E, 0x42E38D,
    0x4311BA, 0x431304, 0x43134C, 0x4313A0, 0x4313E5, 0x431447,
    0x4314C1, 0x4316C5, 0x43170F, 0x431752, 0x4317A7,
    0x4317D1, 0x4317E0, 0x4317FE, 0x431803,
)
# Existing trampoline immediates that combine a native Y with widened X.
HELPER_Y = ((0x566361, 146, 26), (0x566371, 209, 89),
            (0x566381, 209, 89), (0x566386, 189, 69),
            (0x566391, 189, 69), (0x5663A1, 226, 106),
            (0x5663B1, 130, 10), (0x5663C1, 146, 26))
LIMITS = [
    '1280x720 only; expanded 17x7-capacity field and combat rules are inherited unchanged.',
    'Frozen predecessor retains historical mouse/cursor behavior; the separate September 24 input repairs are not included.',
    'This stage is separate from completehd/modalwidgets and requires an explicit matching runtime consumer.',
    'Inherited battle-stage relocation completeness is not established by preserving its old relocation table.',
    'Fresh native artwork, command/hover/input, entry/exit and final-wrapper evidence remain required.',
    'No runtime, manual-input, endurance or stable-promotion acceptance is inferred from this builder.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def emit_helpers(base_va):
    a = clip._Assembler(base_va)
    def transfer(target, purpose):
        a.emit('e8')
        a.relocations.append(clip.Relocation(len(a.code), 'rel32', target, purpose))
        a.u32((target - base_va - len(a.code) - 4) & 0xffffffff)
    def primary(reg):
        a.emit(reg); a.absolute(0x51D4C0, 'native primary surface')
    def copy(rect, target):
        sx, sy, width, height, dx, dy = rect
        a.emit('89f0')  # source is native scratch in ESI
        if target == 'primary': primary('ba')
        else: a.emit('8b15'); a.absolute(0x5202E0, 'current software surface')
        a.emit('bb'); a.u32(sx); a.emit('b9'); a.u32(sy)
        for value in (dy, dx, sy + height - 1, sx + width - 1): a.emit('68'); a.u32(value)
        transfer(0x4024E0, 'native rectangle copy')
    for name, rects in (('frame', FRAME_BLITS), ('stats', SIDEBAR_BLITS[:1])):
        a.label(name); a.emit('9c60')
        transfer(0x566000, 'inherited native frame scratch constructor')
        a.emit('89c685f6'); a.branch('0f84', name + '.done')
        if name == 'frame':
            primary('b8'); transfer(0x401E60, 'clear primary before complete frame')
        for rect in rects: copy(rect, 'primary' if name == 'frame' else 'software')
        if name == 'frame':
            a.emit('8b15'); a.absolute(0x5202E0, 'current software surface')
            a.emit('85d2'); a.branch('0f84', name + '.free')
            primary('b8'); a.emit('31db31c9')
            for value in (0, 0, 719, 1279): a.emit('68'); a.u32(value)
            transfer(0x4024E0, 'frame primary to software mirror')
        a.label(name + '.free')
        a.emit('89f08b8eb8000000ba02000000ff11')
        a.label(name + '.done'); a.emit('619dc3')
    code = a.finish()
    return clip.AdapterBundle(base_va, code, {name: base_va + a.labels[name] for name in ('frame', 'stats')},
                              tuple(a.relocations), 1280, 720)


def _sources():
    observed = {}
    for name, accepted in PINNED.items():
        actual = sha((ROOT / name).read_bytes())
        pe._require(actual in accepted, name + ' SHA-256 is not an enumerated source identity')
        observed[name] = actual
    observed['src/patcher/battle_hd_edge_controls.py'] = sha(Path(__file__).read_bytes())
    return observed


def _restore_frozen_predecessor(current):
    pe._identity(current, CURRENT_BASE_SHA256, 'reviewed current expanded battle')
    view = pe.inspect_pe(current)
    restored = bytearray(current)
    for edit in PREDECESSOR_RESTORATIONS:
        pe._require(view.image_base + edit.rva == edit.va
                    and view.file_offset(edit.rva, len(edit.old)) == edit.offset,
                    'frozen predecessor restoration address differs')
        pe._require(len(edit.old) == len(edit.new)
                    and restored[edit.offset:edit.offset + len(edit.old)] == edit.old,
                    'frozen predecessor restoration old bytes differ: ' + edit.purpose)
        restored[edit.offset:edit.offset + len(edit.new)] = edit.new
    base = bytes(restored)
    pe._identity(base, BASE_SHA256, 'frozen expanded battle predecessor')
    return base


def _frozen_patch_records(original, base, profile):
    # Preserve the published ordering and truthful original-to-predecessor
    # records, including the restored appended payload. The general patcher
    # continues to admit only its current complete 99d92ec7 installation.
    inherited = scalar.select_patches_for(scalar.DEFAULT_STAGE + '-castlecenter-all', profile)
    battle = scalar.battle_hd_patches()
    replaced = {('battle-hd-input', 0x05FE61), ('battle-hd-input', 0x060211)}
    pe._require(sum((p.group, p.offset) in replaced for p in battle) == 2,
                'reviewed battle input hook inventory differs')
    frozen = inherited + [replace(p, new_hex=base[len(original):].hex())
        if p.group == 'battle-hd-section' and p.offset == len(original) else p
        for p in battle if (p.group, p.offset) not in replaced]
    validate_spans(frozen)
    replay = bytearray(original)
    for patch in frozen:
        pe._require(replay[patch.offset:patch.offset + len(patch.old)] == patch.old,
                    'frozen inherited patch old bytes differ')
        replay[patch.offset:patch.offset + len(patch.new)] = patch.new
    pe._require(bytes(replay) == base, 'frozen inherited patch records do not replay predecessor')
    return frozen


def predecessor(original):
    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    sources = _sources()
    profile = scalar.parse_resolution(RESOLUTION)
    patches = scalar.select_patches_for(scalar.BATTLE_HD_STAGE, profile)
    base = _restore_frozen_predecessor(scalar.apply_patches(original, patches))
    return base, _frozen_patch_records(original, base, profile), sources


def edits_for(base, bundle):
    view = pe.inspect_pe(base)
    edits = []
    def add(va, old, new, purpose):
        offset = view.file_offset(va - view.image_base, len(old))
        pe._require(base[offset:offset + len(old)] == old, 'edge old bytes differ: ' + purpose)
        pe._require(old != new and len(old) == len(new), 'distinct equal-length edit required')
        edits.append(pe.ByteEdit(offset, va - view.image_base, va, old, new, purpose))
    records = {offset + 0x400C00: (bytes.fromhex(old), bytes.fromhex(new))
               for _, offset, old, new, _ in hud.HUD_PATCH_RECORDS}
    for va in RESTORE_Y:
        native, before = records[va]
        add(va, before, native, 'restore native top-sidebar Y instruction')
    for va, old, new in HELPER_Y:
        add(va, struct.pack('<I', old), struct.pack('<I', new), 'top-sidebar trampoline Y immediate')
    for i, ((x, y), (nx, ny)) in enumerate(zip(NATIVE_DESCRIPTORS, DESCRIPTORS)):
        add(0x514B78 + 53 * i, struct.pack('<ii', x + 640, y + 120), struct.pack('<ii', nx, ny),
            'command descriptor %d: shared draw/hit-test origin' % i)
    for i in range(6):
        va = 0x514DA4 + i * 4
        offset = view.file_offset(va - view.image_base, 4)
        x, y = struct.unpack_from('<HH', base, offset)
        old = bytes.fromhex(next(row[3] for row in hud.HUD_PATCH_RECORDS if row[1] == offset))
        add(va, old, struct.pack('<HH', x, y - 120), 'top stat icon draw/restore coordinates')
    for va, name in ((0x566110, 'frame'), (0x5662D0, 'stats')):
        original = next(bytes.fromhex(h) for _, address, _, h in hud.HUD_CODE_FRAGMENTS if address == va)
        pe._require(original[:3] == b'\x9c\x60\xe8', 'whole helper prologue contract differs')
        new = b'\xe9' + struct.pack('<i', bundle.entries[name] - va - 5) + b'\x90\x90'
        add(va, original[:7], new, 'tail-delegate whole old helper prologue to edge ' + name)
    spans = sorted((e.offset, e.offset + len(e.old)) for e in edits)
    pe._require(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), 'overlapping edge edits')
    _, locations = pe._old_relocations(base, view)
    pe._require(not any(e.rva < r + 4 and r < e.rva + len(e.old) for e in edits for r in locations),
                'edge edit overlaps inherited absolute relocation')
    return edits


def _probe(image, spans, digest):
    lines = ['.echo BATTLEEDGE_CONTRACT_BEGIN']
    view = pe.inspect_pe(image)
    for va, length in spans:
        offset = va - view.image_base if view.image_base <= va and va + length <= view.image_base + view.headers_size else view.file_offset(va - view.image_base, length)
        raw = image[offset:offset + length]
        comparisons = [f'(wo({va+i:08x}) != {int.from_bytes(raw[i:i+2], "little"):x})'
                       for i in range(0, len(raw) - 1, 2)]
        if len(raw) % 2: comparisons.append(f'(by({va+len(raw)-1:08x}) != {raw[-1]:x})')
        for start in range(0, len(comparisons), 24):
            lines.append('.if (' + ' | '.join(comparisons[start:start+24]) + ') { .echo BATTLEEDGE_CONTRACT_FAIL; q }')
    lines.append(f'.echo BATTLEEDGE_CONTRACT_PASS stage={STAGE} resolution={RESOLUTION} candidate_sha256={digest} revision={REVISION}')
    lines.append('.echo BATTLEEDGE_SCOPE runtime_accepted=false manual_input_proof=false promotion_ready=false')
    pe._require(max(map(len, lines)) < 4096, 'debugger command line too long')
    return '\n'.join(lines) + '\n'


def build_candidate(original, resolution=RESOLUTION):
    pe._require(resolution == RESOLUTION, 'edge-controls stage supports only canonical 1280x720')
    base, patches, sources = predecessor(original)
    before = pe.inspect_pe(base)
    bundle = emit_helpers(before.image_base + before.image_size)
    edits = edits_for(base, bundle)
    extension = pe._extend_verified_image(base, code=bundle.code, code_va=bundle.base_va,
        relocations=bundle.relocations, binding={'stage': STAGE, 'recipe_revision': REVISION})
    output = bytearray(extension.image)
    for edit in edits:
        pe._require(output[edit.offset:edit.offset + len(edit.old)] == edit.old, 'edge prewrite bytes changed')
        output[edit.offset:edit.offset + len(edit.new)] = edit.new
    image = bytes(output); after = pe.inspect_pe(image)
    pe._require(after.sections[:-1] == before.sections, 'existing section headers changed')
    last = after.sections[-1]
    spans = [(after.image_base, after.headers_size), (bundle.base_va, last.raw_size)]
    # Every inherited patch's final bytes, including the entire installed battle
    # section, plus complete native descriptor hit/draw routines and table.
    inherited_records = []
    for patch in patches:
        if patch.offset >= before.headers_size:
            section = next(s for s in before.sections if s.raw_offset and
                           s.raw_offset <= patch.offset < s.raw_offset + s.raw_size)
            va = before.image_base + section.rva + patch.offset - section.raw_offset
            spans.append((va, len(patch.new)))
        else:
            va = before.image_base + patch.offset
        inherited_records.append(dict(group=patch.group, offset=patch.offset, rva=va-before.image_base, va=va,
                                      old_hex=patch.old.hex(), new_hex=patch.new.hex(), purpose=patch.note))
    spans.extend(((0x4191F0, 0xC50), (0x514B78, 6 * 53 + 4), (0x42E160, 0x257), (0x430F80, 0x8B0)))
    probe = _probe(image, spans, sha(image))
    pe._require(_sources() == sources, 'recipe sources changed during construction')
    metadata = dict(schema='clash95_battle_edge_controls_candidate_v1', stage=STAGE, recipe_revision=REVISION,
        resolution=resolution, original_sha256=pe.ORIGINAL_SHA256, base_stage=scalar.BATTLE_HD_STAGE,
        base_candidate_sha256=sha(base), candidate_sha256=sha(image), source_hashes=sources,
        predecessor_reconstruction=dict(source_candidate_sha256=CURRENT_BASE_SHA256,
            result_candidate_sha256=BASE_SHA256, edits=[e.metadata() for e in PREDECESSOR_RESTORATIONS]),
        inherited_patch_count=len(patches), inherited_patch_records=inherited_records, extension=extension.metadata,
        edge_edits=[e.metadata() for e in edits], entry_vas=bundle.entries,
        sidebar_blits=SIDEBAR_BLITS, frame_blits=FRAME_BLITS, descriptor_origins=DESCRIPTORS,
        loaded_probe_spans=spans, probe_sha256=sha(probe.encode()),
        expanded_battle=True, runtime_executed=False, composition_proven=False,
        manual_input_proof=False, promotion_ready=False, limitations=LIMITS)
    return image, metadata, probe
