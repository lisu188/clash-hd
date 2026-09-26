"""Clip only the five native full-map presentation calls to live surface extents."""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import struct

from . import partial_tile_clip as clip
from . import pe_extension as pe
from . import patch_clash95_hd as scalar

ROOT = Path(__file__).resolve().parents[2]
REVISION = 'native_map_present_bounds_v1'
BLIT = 0x4024E0
MAP = 0x5202E0
PRIMARY = 0x51D4C0
FULL_START, FULL_END = 0x418700, 0x418A90
BLIT_SIZE = 867
BLIT_SHA256 = '29c70320d733412798da7d41c77f2ab310987ad58dfef89a88f3459cfcd350a8'
PINNED = {
    'src/patcher/patch_clash95_hd.py': '38021e9a4d21bc9a8bf0c2f9b66379595509446b5177d6f91bab6f677b5e8106',
    'src/patcher/pe_extension.py': '4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27',
    'src/patcher/partial_tile_clip.py': '92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad',
    'src/patcher/classic_menu_candidate.py': '0f32f76ab321cf4793020064a7491fb0e7b8a9c4a1ed0f9c73a81e34f6538473',
    'tools/build_framed_candidate.py': 'fbe2f2c571154312329ab23603d8de45fb8ec5fafcdfd10bad4049876dfb14bc',
    'src/patcher/complete_hd_candidate.py': 'e406149480e9cdf1ba0314f5e9ae735d7b587f61772afac4b0b9e7ce9fd3bd06',
    'tools/build_framed_modal_widgets_candidate.py': '2ff2b1923f4220de862e9dac46f5238db3954122c5e451e8e2a15408fd041ba6',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def emit_guard(base_va: int, *, map_pointer: int = MAP, primary: int = PRIMARY,
               native_blit: int = BLIT) -> clip.AdapterBundle:
    for address in (base_va, map_pointer, primary, native_blit):
        pe._require(type(address) is int and 0x10000 <= address < 0x7FFE0000, 'bounded x86 address required')
    a = clip._Assembler(base_va)
    a.label('present')
    a.emit('9c6089e5837d1400'); a.branch('0f85', 'native')
    a.emit('8b751c85f6'); a.branch('0f84', 'native')
    a.emit('3b35'); a.absolute(map_pointer, 'live map surface pointer'); a.branch('0f85', 'native')
    a.emit('0fb745100fb74d3039c8'); a.branch('0f85', 'native')
    a.emit('0fb75d180fb74d3439cb'); a.branch('0f85', 'native')
    a.emit('0fb70e0fb73d'); a.absolute(primary, 'live primary width')
    a.emit('39f90f47cf85c9'); a.branch('0f84', 'empty')
    a.emit('39c8'); a.branch('0f83', 'empty')
    a.emit('490fb7552839c2'); a.branch('0f82', 'empty')
    a.emit('39ca0f47d1895528')
    a.emit('0fb74e020fb73d'); a.absolute(primary + 2, 'live primary height')
    a.emit('39f90f47cf85c9'); a.branch('0f84', 'empty')
    a.emit('39cb'); a.branch('0f83', 'empty')
    a.emit('490fb7552c39da'); a.branch('0f82', 'empty')
    a.emit('39ca0f47d189552c')
    a.label('native')
    a.emit('89ec619d')
    a.emit('e9')
    a.relocations.append(clip.Relocation(len(a.code), 'rel32', native_blit, 'unchanged native rectangle blitter'))
    a.u32(native_blit - base_va - len(a.code) - 4)
    a.label('empty')
    a.emit('c7451c0000000089ec619dc21000')
    code = a.finish()
    pe._require(len(code) < 512, 'presentation adapter exceeds bound')
    result = clip.AdapterBundle(base_va, code, {'present': base_va}, tuple(a.relocations), 0, 0)
    clip.absolute_relocation_offsets(result)
    return result


def predecessor(original: bytes, profile: str, resolution: str):
    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    scalar.parse_resolution(resolution)
    for name, digest in PINNED.items():
        pe._identity((ROOT / name).read_bytes(), digest, name)
    sources = dict(PINNED)
    if profile == 'classic':
        from . import classic_menu_candidate as menu
        if menu.supports(resolution):
            image, metadata, probe = menu.build_candidate(original, resolution)
        else:
            selected = scalar.select_patches_for(scalar.DEFAULT_STAGE, scalar.parse_resolution(resolution))
            scalar.validate_input(original, selected)
            image = scalar.apply_patches(original, selected)
            metadata = dict(stage=scalar.DEFAULT_STAGE, recipe_revision='classic-frozen-800-v1', source_hashes=PINNED)
            probe = ''
    elif profile == 'framed':
        module = importlib.import_module('tools.build_framed_candidate')
        image, metadata, probe = module.build_candidate(original, resolution, minimap_viewport=True)
        metadata = dict(metadata, recipe_revision='four-border-partial-initial-v1')
    elif profile == 'completehd':
        module = importlib.import_module('src.patcher.complete_hd_candidate')
        image, metadata, probe = module.build_candidate(original, resolution)
    elif profile == 'modalwidgets':
        module = importlib.import_module('tools.build_framed_modal_widgets_candidate')
        image, metadata, probe = module.build_candidate(original, resolution)
    else:
        raise ValueError('Unknown exact launcher profile')
    sources.update(metadata.get('source_hashes', metadata.get('source_sha256', {})))
    sources['src/patcher/native_present_bounds.py'] = sha(Path(__file__).read_bytes())
    for name, digest in sources.items():
        pe._identity((ROOT / name).read_bytes(), digest, name)
    return image, metadata, probe, sources


def append_section(candidate: bytes, bundle: clip.AdapterBundle, hooks: tuple[pe.HookPatch, ...], binding: dict):
    before = pe.inspect_pe(candidate)
    count = len(before.sections)
    slot = before.sections[-1].header_offset + 40
    pe._require(7 <= count <= 15 and slot + 40 <= before.headers_size, 'no empty PE section header slot')
    pe._require(candidate[slot:slot + 40] == bytes(40), 'nonzero section-header reservation')
    pe._require((before.section_alignment, before.file_alignment, before.headers_size) == (4096, 512, 1024), 'unsupported PE alignment')
    pe._require(max(s.raw_offset + s.raw_size for s in before.sections if s.raw_offset) == len(candidate), 'file overlay is not allowed')
    pe._require(bundle.base_va == before.image_base + before.image_size, 'extension address differs from prepared image')
    old_table, old_fields = pe._old_relocations(candidate, before)
    normalized = []
    absolute = []
    for r in bundle.relocations:
        pe._require(r.kind in ('abs32', 'rel32') and 0 <= r.offset <= len(bundle.code) - 4, 'bad relocation')
        pe._require(before.contains_memory(r.target - before.image_base), 'adapter references an unmapped native address')
        expected = r.target if r.kind == 'abs32' else (r.target - bundle.base_va - r.offset - 4) & 0xFFFFFFFF
        pe._require(struct.unpack_from('<I', bundle.code, r.offset)[0] == expected, 'relocation bytes differ')
        normalized.append(dict(offset=r.offset, kind=r.kind, target=r.target, purpose=r.purpose))
        if r.kind == 'abs32': absolute.append(before.image_size + r.offset)
    edits, added, hook_rows, removed = pe._prepare_hooks(candidate, before, hooks, (), old_fields, bundle.base_va, len(bundle.code))
    pe._require(not added and not removed, 'presentation CALL patches must preserve old absolute relocations')
    table = pe._relocation_blocks(tuple(old_fields) + tuple(absolute))
    table_at = pe._align(len(bundle.code), 4)
    payload = bundle.code + bytes(table_at - len(bundle.code)) + table
    size = pe._align(len(payload), 512)
    virtual_size = pe._align(len(payload), 4096)
    header = struct.pack('<8sIIIIIIHHI', b'.hdpblit', virtual_size, before.image_size, size, len(candidate), 0, 0, 0, 0, pe.RX_CODE)
    for offset, new, purpose in (
        (before.pe_offset + 6, struct.pack('<H', count + 1), 'NumberOfSections'),
        (before.optional_offset + 4, struct.pack('<I', before.size_of_code + size), 'SizeOfCode'),
        (before.optional_offset + 56, struct.pack('<I', before.image_size + virtual_size), 'SizeOfImage'),
        (before.optional_offset + 136, struct.pack('<II', before.image_size + table_at, len(table)), 'complete HIGHLOW directory'),
        (slot, header, 'presentation adapter section header'),
    ):
        edits.append(pe.ByteEdit(offset, offset, before.image_base + offset, candidate[offset:offset + len(new)], new, purpose))
    edits.append(pe.ByteEdit(len(candidate), before.image_size, bundle.base_va, b'', payload + bytes(size - len(payload)), 'append guarded native presentation'))
    spans = sorted((e.offset, e.offset + len(e.old)) for e in edits if e.old)
    pe._require(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), 'overlapping edits')
    output = bytearray(candidate)
    for edit in edits:
        pe._require(output[edit.offset:edit.offset + len(edit.old)] == edit.old and (edit.old or edit.offset == len(output)), 'old bytes or append position differ')
        output[edit.offset:edit.offset + len(edit.old)] = edit.new
    image = bytes(output)
    after = pe.inspect_pe(image)
    pe._require(after.sections[:-1] == before.sections, 'existing section changed')
    _, fields = pe._old_relocations(image, after)
    pe._require(sorted(fields) == sorted(tuple(old_fields) + tuple(absolute)), 'merged relocation list differs')
    offset = before.file_offset(before.relocation_rva, before.relocation_size)
    pe._require(image[offset:offset + len(old_table)] == old_table, 'old relocation bytes changed')
    metadata = dict(binding, candidate_sha256=sha(image), base_candidate_sha256=sha(candidate),
        code_va=bundle.base_va, code_bytes=len(bundle.code), entry_vas=bundle.entries, relocations=normalized,
        new_highlow_count=len(absolute), hooks=[h.metadata() for h in edits[:len(hooks)]],
        edits=[e.metadata() for e in edits], runtime_executed=False, promotion_ready=False)
    return image, metadata


def build_candidate(original: bytes, profile: str, resolution: str):
    base, parent, old_probe, sources = predecessor(original, profile, resolution)
    view = pe.inspect_pe(base)
    offset = view.file_offset(BLIT - view.image_base, BLIT_SIZE)
    pe._identity(base[offset:offset + BLIT_SIZE], BLIT_SHA256, 'unchanged native rectangle blitter')
    before = pe.inspect_pe(original)
    start = before.file_offset(FULL_START - before.image_base, FULL_END - FULL_START)
    body = original[start:start + FULL_END - FULL_START]
    calls = []
    for i in range(len(body) - 4):
        if body[i] == 0xE8 and FULL_START + i + 5 + struct.unpack_from('<i', body, i + 1)[0] == BLIT:
            calls.append(FULL_START + i)
    pe._require(len(calls) == 5, 'expected exactly five original full-map presentation calls')
    bundle = emit_guard(view.image_base + view.image_size)
    hooks = []
    for va in calls:
        pos = view.file_offset(va - view.image_base, 5)
        expected = b'\xe8' + struct.pack('<i', BLIT - va - 5)
        pe._require(base[pos:pos + 5] == expected, 'native full-map presentation CALL differs')
        new = b'\xe8' + struct.pack('<i', bundle.base_va - va - 5)
        hooks.append(pe.HookPatch(pos, va - view.image_base, va, expected, new, 'clip native map-to-primary self-aligned presentation',
            (pe.CodeRelocation(1, 'rel32', bundle.base_va, 'bounded native map presentation'),)))
    stage = parent['stage'].removesuffix('-validation') + '-nativepresent-validation'
    image, metadata = append_section(base, bundle, tuple(hooks), dict(schema='native_map_present_bounds_v1',
        stage=stage, recipe_revision=REVISION, base_stage=parent['stage'], base_recipe_revision=parent['recipe_revision'],
        resolution=resolution, profile=profile, original_sha256=pe.ORIGINAL_SHA256))
    metadata.update(source_hashes=sources, base_candidate=parent, inherited_probe_sha256=sha(old_probe.encode()),
        probe_inheritance='Predecessor probe retained by identity only; a composed full-stage verifier is not claimed',
        policy='Only native full-map map-to-primary identity copies are clipped to both live surfaces; other calls delegate unchanged',
        gameplay_verified=False, manual_input_proof=False)
    checks = []
    after = pe.inspect_pe(image)
    spans = [(h.va, image[h.offset:h.offset + 5]) for h in hooks]
    last = after.sections[-1]
    spans += [(after.image_base, image[:after.headers_size]), (bundle.base_va, image[last.raw_offset:last.raw_offset + last.raw_size])]
    for va, data in spans:
        clauses = [f'(by({va + i:08x}) != {b:x})' for i, b in enumerate(data)]
        for i in range(0, len(clauses), 80):
            checks.append('.if (' + ' | '.join(clauses[i:i + 80]) + ') { .echo NATIVEPRESENT_FAIL; q }')
    checks.append(f'.echo NATIVEPRESENT_PASS candidate_sha256={sha(image)} stage={stage} resolution={resolution}')
    probe = '\n'.join(checks) + '\n'
    metadata['probe_sha256'] = sha(probe.encode())
    pe._require(sources == {name: sha((ROOT / name).read_bytes()) for name in sources}, 'source changed during build')
    return image, metadata, probe
