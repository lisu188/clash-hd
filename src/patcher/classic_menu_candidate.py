"""Add a menu-only descriptor bound to an exact Classic validation candidate."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct

from . import patch_clash95_hd as scalar
from . import partial_tile_clip as clip
from . import pe_extension as pe

ROOT = Path(__file__).resolve().parents[2]
STAGE = scalar.DEFAULT_STAGE + '-menuwidgets-validation'
REVISION = 'classic_menu_widgets_v1'
BASE_SHA256 = pe.ORIGINAL_SHA256
MIN_WIDTH = 1144
MENU_SPRITES = 0x543D74
TABLES = ((0x5181C0, 6), (0x518338, 2), (0x5184F0, 4), (0x518690, 6), (0x518808, 2))
SITES = (('single', 0x419D60, 18, 3), ('list', 0x419D80, 64, 12))
PREFIXES = (b'\x81\x38', b'\x81\x39')
PINNED = {
    'src/patcher/patch_clash95_hd.py': '05f31359f93a0eb0b319679ee524b21c05cd3e86e485b7ebb92afc8e6da29f31',
    'src/patcher/pe_extension.py': '4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27',
    'src/patcher/partial_tile_clip.py': '92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad',
    'src/patcher/framed_viewport.py': '1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42',
}
SOURCE = 'src/patcher/classic_menu_candidate.py'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def supports(resolution):
    try:
        profile = scalar.parse_resolution(resolution)
    except (ValueError, TypeError):
        return False
    return profile.width >= MIN_WIDTH


def source_status():
    checks = {name: sha((ROOT / name).read_bytes()) == digest for name, digest in PINNED.items()}
    return dict(passed=all(checks.values()), checks=checks, runtime_executed=False)


def emit_guards(*, base_va, width, height, records, holder=MENU_SPRITES):
    profile = scalar.parse_resolution(f'{width}x{height}')
    pe._require(type(width) is int and type(height) is int and type(base_va) is int
                and type(holder) is int and 0x10000 <= base_va < 0x7FFE0000
                and 0x10000 <= holder < 0x7FFE0000 and base_va % 4096 == 0,
                'bounded integer code and sprite-holder addresses required')
    pe._require(isinstance(records, tuple) and 1 <= len(records) <= 20 and len(set(records)) == len(records),
                'unique bounded native menu records required')
    for record in records:
        pe._require(isinstance(record, tuple) and len(record) == 3 and all(type(value) is int for value in record),
                    'menu record must be exact x/y/callback integers')
        x, y, callback = record
        pe._require(profile.off_x <= x < profile.off_x + 640 and profile.off_y <= y < profile.off_y + 480
                    and 0x10000 <= callback < 0x7FFE0000, 'menu record lies outside native centered area')
    a = clip._Assembler(base_va)
    for name, register in (('single', 0), ('list', 1)):
        a.label(name)
        a.emit('6089' + bytes([0xC2 + (register << 3)]).hex())
        a.emit('817a0c'); a.absolute(holder, 'native menu sprite-set holder')
        a.branch('0f85', name + '.legacy')
        for index, (x, y, callback) in enumerate(records):
            next_row = name + f'.next{index}'
            a.emit('813a'); a.u32(x); a.branch('0f85', next_row)
            a.emit('817a04'); a.u32(y); a.branch('0f85', next_row)
            a.emit('817a20'); a.absolute(callback, 'source-pinned menu action callback')
            a.branch('0f84', name + '.menu')
            a.label(next_row)
        a.label(name + '.legacy'); a.emit('61' + PREFIXES[(0, 1).index(register)].hex()); a.u32(640); a.emit('c3')
        a.label(name + '.menu'); a.emit('61' + PREFIXES[(0, 1).index(register)].hex()); a.u32(width); a.emit('c3')
    code = a.finish()
    pe._require(len(code) < 4096, 'menu guards exceed one code page')
    result = clip.AdapterBundle(base_va, code, {name: base_va + a.labels[name] for name in ('single', 'list')},
                                tuple(a.relocations), width, height)
    clip.absolute_relocation_offsets(result)
    return result


def _native_records(original, base, profile):
    before, after = pe.inspect_pe(original), pe.inspect_pe(base)
    records, receipts = [], []
    for address, count in TABLES:
        size = count * 53 + 4
        old_offset = before.file_offset(address - before.image_base, size)
        new_offset = after.file_offset(address - after.image_base, size)
        old, new = original[old_offset:old_offset+size], base[new_offset:new_offset+size]
        pe._require(old[-4:] == new[-4:] == b'\xff' * 4, 'source menu terminator differs')
        for index in range(count):
            a, b = old[index*53:(index+1)*53], new[index*53:(index+1)*53]
            x, y = struct.unpack_from('<ii', a)
            shifted = (x + profile.off_x, y + profile.off_y)
            holder, callback = struct.unpack_from('<I', a, 12)[0], struct.unpack_from('<I', a, 32)[0]
            pe._require(0 <= x < 640 and 0 <= y < 480 and holder == MENU_SPRITES
                        and struct.unpack_from('<ii', b) == shifted and a[8:] == b[8:],
                        f'exact centered source menu record differs: table={address:x} row={index} holder={holder:x}')
            pe._require(any(s.rva <= callback-before.image_base < s.rva+s.memory_size
                            and s.characteristics & 0x20000000 for s in before.sections),
                        'native menu callback is not executable')
            records.append((*shifted, callback))
        receipts.append(dict(va=address, bytes=size, original_sha256=sha(old), predecessor_sha256=sha(new)))
    pe._require(len(records) == 20, 'menu record inventory differs')
    return tuple(dict.fromkeys(records)), receipts


def loaded_probe(candidate, metadata, spans):
    clauses = []
    for address, data in spans:
        for offset, byte in enumerate(data):
            clauses.append(f'(by({address + offset:08x}) != {byte:x})')
    lines = []
    for start in range(0, len(clauses), 90):
        lines.append('.if (' + ' | '.join(clauses[start:start+90]) + ') { .echo CLASSICMENU_CONTRACT_FAIL; q }')
    lines.extend((f'.echo CLASSICMENU_CONTRACT_PASS stage={STAGE} resolution={metadata["resolution"]} '
                  f'candidate_sha256={sha(candidate)} revision={REVISION}',
                  '.echo CLASSICMENU_SCOPE menu_descriptors_only gameplay_verified=false promotion_ready=false'))
    result = '\n'.join(lines) + '\n'
    pe._require(all(len(line.encode('ascii')) < 4096 for line in result.splitlines()), 'probe line exceeds CDB limit')
    return result


def build_candidate(original, resolution):
    pe._identity(original, BASE_SHA256, 'original')
    profile = scalar.parse_resolution(resolution)
    pe._require(profile.width >= MIN_WIDTH, 'menu correction is only selected where the native bound clips shifted controls')
    for name, digest in PINNED.items():
        pe._identity((ROOT / name).read_bytes(), digest, name)
    sources = dict(PINNED) | {SOURCE: sha(Path(__file__).read_bytes())}
    patches = scalar.select_patches_for(scalar.DEFAULT_STAGE, profile)
    scalar.validate_input(original, patches)
    base = scalar.apply_patches(original, patches)
    view = pe.inspect_pe(base)
    pe._require(len(view.sections) == 7, 'exact seven-section Classic predecessor required')
    records, tables = _native_records(original, base, profile)
    bundle = emit_guards(base_va=view.image_base+view.image_size, width=profile.width, height=profile.height, records=records)
    hooks, windows = [], []
    for index, (name, address, size, offset) in enumerate(SITES):
        raw = view.file_offset(address-view.image_base, size)
        expected = original[raw:raw+size]
        pe._require(base[raw:raw+size] == expected, 'Classic dispatcher changed outside menu-only extension')
        old = expected[offset:offset+6]
        pe._require(old == PREFIXES[index] + struct.pack('<I',640), 'exact native CMP instruction required')
        va = address+offset; target=bundle.entries[name]
        hooks.append(pe.HookPatch(raw+offset, va-view.image_base, va, old,
            b'\xe8'+struct.pack('<i',target-va-5)+b'\x90', 'classic_menu.'+name,
            (pe.CodeRelocation(1,'rel32',target,'menu-only descriptor bound'),)))
        windows.append(dict(va=address, bytes=size, predecessor_sha256=sha(expected)))
    result = pe._extend_verified_image(base, code=bundle.code, code_va=bundle.base_va,
        relocations=bundle.relocations, hooks=tuple(hooks), binding=dict(stage=STAGE, recipe_revision=REVISION,
        base_stage=scalar.DEFAULT_STAGE, resolution=resolution, original_sha256=BASE_SHA256,
        base_candidate_sha256=sha(base)))
    metadata = dict(result.metadata, schema='clash95_classic_menu_candidate_v1', candidate_sha256=sha(result.image),
        source_hashes=sources, menu_records=[dict(x=x,y=y,callback=cb) for x,y,cb in records],
        menu_tables=tables, dispatcher_windows=windows, entry_vas=bundle.entries,
        patch_records=[dict(group=p.group,offset=p.offset,old_hex=p.old.hex(),new_hex=p.new.hex()) for p in patches],
        policy='Only exact original menu/campaign/multiplayer/options/load x/y/callback records with the native menu holder use the physical bound; every other descriptor retains signed x<640.',
        runtime_executed=False, gameplay_verified=False, manual_input_proof=False, promotion_ready=False)
    spans = [(view.image_base, result.image[:view.headers_size])]
    for patch in patches:
        rva = next(s.rva + patch.offset-s.raw_offset for s in view.sections
                   if s.raw_offset and s.raw_offset <= patch.offset and patch.offset+len(patch.new) <= s.raw_offset+s.raw_size)
        spans.append((view.image_base+rva, result.image[patch.offset:patch.offset+len(patch.new)]))
    for address, size in [(r['va'],r['bytes']) for r in tables+windows]:
        off=view.file_offset(address-view.image_base,size)
        spans.append((address,result.image[off:off+size]))
    spans.append((bundle.base_va,result.image[result.metadata['append_offset']:]))
    probe = loaded_probe(result.image, metadata, spans)
    metadata['probe_sha256'] = sha(probe.encode())
    pe._require(sources == {name:sha((ROOT/name).read_bytes()) for name in sources}, 'menu source changed during build')
    return result.image, metadata, probe


def write_candidate(original, output, resolution):
    from . import complete_hd_candidate as complete
    output = Path(output).resolve()
    pe._require(output.is_absolute() and output.suffix.lower()=='.exe' and not output.is_relative_to(ROOT)
                and output.is_relative_to(Path('C:/ClashTests').resolve()), 'external C:/ClashTests candidate required')
    paths = (output,output.with_suffix('.candidate.json'),output.with_suffix('.cdb'))
    pe._require(all(not path.exists() for path in paths), 'candidate or sidecar exists')
    image,metadata,probe=build_candidate(Path(original).read_bytes(),resolution)
    output.parent.mkdir(parents=True,exist_ok=True)
    complete._write_bundle(paths,(image,(json.dumps(metadata,indent=2)+'\n').encode(),probe.encode()))
    return metadata
