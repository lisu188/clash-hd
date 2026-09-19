"""Additive fourteenth RX section above the exact primary-v1 predecessor.

The only production caller is the new primary-text builder, which reconstructs the
primary candidate and obtains its source-bound emitter before using this private
format core. Layout checks alone do not authenticate bytes or prove runtime.
No inherited allocator, original relocation, or old section header is changed.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

from . import pe_extension as pe

CODE_RESERVATION = 0x20000


@dataclass(frozen=True)
class AllocationLayout:
    code_va: int
    code_rva: int
    code_header_offset: int


def allocation_layout(candidate: bytes) -> AllocationLayout:
    image = pe.inspect_pe(candidate)
    pe._require(len(image.sections) == 13 and tuple(s.name.rstrip(b'\0') for s in image.sections[-6:])
        == (b'.hdcode', b'.hdmodal', b'.hdstate', b'.hdarmy', b'.hdslots', b'.hdprim'),
        'exact thirteen-section primary layout required')
    pe._require(all(image.sections[index].characteristics == pe.RX_CODE for index in (-6,-5,-3,-2,-1))
        and image.sections[-4].characteristics == 0xC0000040, 'primary section protections differ')
    pe._require(image.section_alignment == 4096 and image.file_alignment == 512 and image.headers_size == 0x400,
        'primary allocation requires canonical 4096/512/1024 alignment')
    pe._require(all(a.rva + pe._align(a.memory_size,4096) == b.rva for a,b in zip(image.sections,image.sections[1:])),
        'primary sections have nonadjacent extents')
    slot = image.sections[-1].header_offset + 40
    pe._require(image.sections[-1].header_offset == 0x348 and slot == 0x370
        and slot + 40 <= image.headers_size and candidate[slot:slot+40] == bytes(40),
        'primary header is occupied or relocated')
    pe._u32(image.image_base + image.image_size + CODE_RESERVATION, 'primary image extent')
    return AllocationLayout(image.image_base + image.image_size,image.image_size,slot)


def _extend_verified_image(candidate, *, code, code_va, relocations, hooks, binding):
    """Checked PE operation after exact predecessor/emitter authentication.

    One declared five-byte CALL replacement is required. The cdecl argument
    adapter has no mutable state and preserves every primary-v1 hook.
    No HIGHLOW removal is accepted, including fields displaced by a hook.
    """
    layout = allocation_layout(candidate); before = pe.inspect_pe(candidate)
    pe._require(type(code_va) is int and code_va == layout.code_va, 'primary code address differs from allocation')
    pe._require(isinstance(code,bytes) and 0 < len(code) < CODE_RESERVATION, 'invalid immutable primary code size')
    pe._require(isinstance(relocations,(tuple,list)) and isinstance(hooks,(tuple,list)) and len(hooks) == 1,
        'one explicit primary-text hook and declared relocations required')
    pe._require(isinstance(binding,dict), 'primary source binding must be a dictionary')
    old_table, old_fields = pe._old_relocations(candidate,before)

    def target_ok(target,kind):
        return (code_va <= target < code_va + len(code) or any(s.rva <= target-before.image_base < s.rva+s.memory_size
            and (kind == 'abs32' or s.characteristics & 0x20000000) for s in before.sections))

    operands=[]; new_fields=[]; normalized=[]
    for row in relocations:
        pe._require(all(hasattr(row,k) for k in ('offset','kind','target','purpose')), 'malformed primary relocation')
        pe._require(type(row.offset) is int and 0 <= row.offset <= len(code)-4, 'primary relocation outside code')
        pe._u32(row.target,'primary relocation target')
        pe._require(row.kind in ('abs32','rel32') and isinstance(row.purpose,str) and row.purpose.strip(),
            'invalid primary relocation kind or purpose')
        pe._require(target_ok(row.target,row.kind), 'primary target unmapped or nonexecutable')
        value = row.target if row.kind == 'abs32' else (row.target-code_va-row.offset-4)&0xffffffff
        pe._require(struct.unpack_from('<I',code,row.offset)[0] == value, 'primary relocation operand differs')
        operands.append(row.offset)
        normalized.append(dict(offset=row.offset,kind=row.kind,target=row.target,purpose=row.purpose))
        if row.kind == 'abs32': new_fields.append(layout.code_rva+row.offset)
    operands.sort()
    pe._require(all(a+4 <= b for a,b in zip(operands,operands[1:])), 'overlapping primary relocation operands')
    for hook in hooks:
        pe._require(isinstance(hook,pe.HookPatch), 'primary hook requires HookPatch')
        pe._require(isinstance(hook.old, bytes) and isinstance(hook.new, bytes)
            and len(hook.old) == len(hook.new) == 5 and hook.old[:1] == hook.new[:1] == b'\xe8',
            'primary text hook must replace one five-byte CALL')
        pe._require(isinstance(hook.relocations,(tuple,list)), 'primary hook relocation sequence required')
        pe._require(len(hook.relocations) == 1
            and getattr(hook.relocations[0], 'kind', None) == 'rel32'
            and type(getattr(hook.relocations[0], 'offset', None)) is int
            and hook.relocations[0].offset == 1,
            'primary text CALL requires one declared rel32 displacement')
        for row in hook.relocations:
            pe._require(all(hasattr(row,k) for k in ('kind','target')), 'malformed primary hook target')
            pe._u32(row.target,'primary hook target')
            pe._require(row.kind in ('abs32','rel32') and target_ok(row.target,row.kind), 'primary hook target unmapped or nonexecutable')
    edits, hook_fields, hook_operands, removed = pe._prepare_hooks(candidate,before,hooks,(),old_fields,code_va,len(code))
    pe._require(not removed, 'primary patch cannot remove historical relocations')
    expected = tuple(old_fields)+tuple(new_fields)+tuple(hook_fields)
    table = pe._relocation_blocks(expected); table_offset = pe._align(len(code),4)
    payload = code+bytes(table_offset-len(code))+table
    raw_size = pe._align(len(payload),512)
    pe._require(raw_size <= CODE_RESERVATION, 'primary code and complete relocation directory exceed reservation')
    pe._u32(len(candidate)+raw_size, 'primary file extent')
    header = struct.pack('<8sIIIIIIHHI',b'.hdptxt',CODE_RESERVATION,layout.code_rva,raw_size,len(candidate),0,0,0,0,pe.RX_CODE)

    def change(offset,data,purpose):
        old=candidate[offset:offset+len(data)]
        pe._require(len(old)==len(data),'primary edit outside old image')
        edits.append(pe.ByteEdit(offset,offset,before.image_base+offset,old,data,purpose))

    change(before.pe_offset+6,struct.pack('<H',14),'NumberOfSections')
    change(before.optional_offset+4,struct.pack('<I',pe._u32(before.size_of_code+raw_size,'SizeOfCode')),'SizeOfCode')
    change(before.optional_offset+56,struct.pack('<I',layout.code_rva+CODE_RESERVATION),'SizeOfImage')
    change(before.optional_offset+136,struct.pack('<II',layout.code_rva+table_offset,len(table)),'complete merged primary relocations')
    change(layout.code_header_offset,header,'.hdptxt RX header')
    edits.append(pe.ByteEdit(len(candidate),layout.code_rva,code_va,b'',payload+bytes(raw_size-len(payload)),
        'append primary code and complete merged relocations'))
    spans=sorted((e.offset,e.offset+len(e.old)) for e in edits if e.old)
    pe._require(all(a[1]<=b[0] for a,b in zip(spans,spans[1:])), 'overlapping primary edits')
    output=bytearray(candidate)
    for edit in edits:
        pe._require(output[edit.offset:edit.offset+len(edit.old)]==edit.old and (edit.old or edit.offset==len(output)),
            'primary old-byte or append position mismatch')
        output[edit.offset:edit.offset+len(edit.old)]=edit.new
    image=bytes(output); after=pe.inspect_pe(image)
    pe._require(after.sections[:13]==before.sections,'historical section header changed')
    _,actual=pe._old_relocations(image,after)
    pe._require(sorted(actual)==sorted(expected),'merged primary HIGHLOW inventory differs')
    old_offset=before.file_offset(before.relocation_rva,before.relocation_size)
    pe._require(image[old_offset:old_offset+len(old_table)]==old_table,'historical relocation directory changed')
    metadata=dict(binding)
    metadata.update(schema='clash95_pe_modal_primary_text_extension_v1',input_sha256=pe._sha(candidate),
        output_sha256=pe._sha(image),code_va=code_va,code_rva=layout.code_rva,code_bytes=len(code),
        code_sha256=pe._sha(code),code_raw_bytes=raw_size,code_virtual_bytes=CODE_RESERVATION,
        code_characteristics=pe.RX_CODE,state_bytes=0,old_highlow_count=len(old_fields),
        new_highlow_count=len(new_fields)+len(hook_fields),removed_highlow=[],relocations=normalized,
        hook_relocations=hook_operands,relocation_rva=layout.code_rva+table_offset,relocation_bytes=len(table),
        old_relocation_sha256=pe._sha(old_table),merged_relocation_sha256=pe._sha(table),
        hooks=[e.metadata() for e in edits[:len(hooks)]],edits=[e.metadata() for e in edits],
        installation_ready=False,runtime_executed=False,manual_input_proof=False,promotion_ready=False)
    return pe.ExtensionResult(image,tuple(edits),metadata)
