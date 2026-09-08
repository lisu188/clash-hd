"""Source-bound, uninstalled army RX/RW allocation atop the frozen modal image.

Only this new validation stage consumes zero header slots 2F8..347. The legacy
day diagnostic's header scratch 300..347 is retired for this stage; it must not
be used with its probe. Existing allocators, stages, sections and files are not
modified. Public construction returns bytes/edits only and never starts runtime.

Declared operands are validated, not discovered. The independent emitter must
prove complete abs32 metadata, native ABI, clipping and lifecycle semantics.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from pathlib import Path
import struct
import sys
import types
import uuid

from . import pe_extension as pe

ROOT=Path(__file__).resolve().parents[2]
BASE_STAGE=('gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-'
            'presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-'
            'framed-modalcanvas-validation')
STAGE=BASE_STAGE.removesuffix('-validation')+'-army-validation'
CODE_RESERVATION=0x20000
MAX_STATE_BYTES=0x100000
RW_DATA=0xC0000040
RETIRED_HEADER_SCRATCH=(0x300,0x348)
PINNED_SOURCES={
    'tools/build_framed_modal_candidate.py':'c2da86edc7fb6bc0e7c3ca5ecca6bf4688a33ffa8d574153dab463c4653da4fb',
    'src/patcher/framed_modal_canvas.py':'567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054',
    'src/patcher/pe_modal_extension.py':'a5ad4e32fc027df365f925e76d21ff4b6679825f1f2bbc20c58a52b35d95d623',
    'src/patcher/pe_extension.py':'4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27',
}


def _source(name,digest):
    path=(ROOT/name).resolve()
    pe._require(path==ROOT/name and path.is_relative_to(ROOT),'noncanonical army dependency path')
    data=path.read_bytes();pe._identity(data,digest,'army dependency '+name)
    return data


def _literals(data,*names):
    return {node.targets[0].id:ast.literal_eval(node.value) for node in ast.parse(data).body
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
            and node.targets[0].id in names}


class _LocalImports(ast.NodeTransformer):
    def __init__(self,prefix):self.prefix=prefix

    def visit_ImportFrom(self,node):
        if not node.level and node.module:
            if node.module in ('src','tools') or node.module.startswith(('src.','tools.')):
                node.module=self.prefix+'.'+node.module
            elif node.module in ('build_partial_tile_candidate','partial_tile_trace_probe'):
                node.module=self.prefix+'.tools.'+node.module
        return node


def _reconstruct_modal(original,resolution,minimap_viewport):
    """Compile verified byte snapshots into a private namespace, never pyc/cache.

    The existing canvas verifier reconstructs both minimap alternatives. Thus
    its optional minimap implementation is a source dependency even when the
    requested output has minimap_viewport=False; output identities stay distinct.
    """
    pins=dict(PINNED_SOURCES)
    sources={name:_source(name,digest) for name,digest in pins.items()}
    pins.update(_literals(sources['src/patcher/pe_modal_extension.py'],'PINNED_SOURCES')['PINNED_SOURCES'])
    sources.update({name:_source(name,digest) for name,digest in pins.items()})
    values=_literals(sources['tools/build_framed_candidate.py'],'PINNED_SOURCES','MINIMAP_SOURCE','MINIMAP_SOURCE_SHA256')
    pins.update(values['PINNED_SOURCES']);pins[values['MINIMAP_SOURCE']]=values['MINIMAP_SOURCE_SHA256']
    sources.update({name:_source(name,digest) for name,digest in pins.items()})
    prefix='_clash95_army_binding_'+uuid.uuid4().hex
    old_path=list(sys.path)
    try:
        for suffix,directory in (('',ROOT),('.src',ROOT/'src'),('.src.patcher',ROOT/'src/patcher'),('.tools',ROOT/'tools')):
            mod=types.ModuleType(prefix+suffix);mod.__path__=[str(directory)];sys.modules[mod.__name__]=mod
        def module(name):
            full=prefix+'.'+name.removesuffix('.py').replace('/','.')
            mod=types.ModuleType(full);mod.__file__=str(ROOT/name);mod.__package__=full.rpartition('.')[0]
            sys.modules[full]=mod
            tree=_LocalImports(prefix).visit(ast.parse(sources[name],mod.__file__))
            exec(compile(tree,mod.__file__,'exec'),mod.__dict__)
            return mod
        for stem in ('framed_viewport','patch_clash95_hd','partial_tile_clip','pe_extension',
                     'framed_recipe','partial_tile_hooks','four_sided_frame','framed_full_paint',
                     'initial_map_paint','framed_presentation','framed_input','framed_minimap'):
            module('src/patcher/'+stem+'.py')
        for name in ('tools/partial_tile_trace_probe.py','tools/build_partial_tile_candidate.py',
                     'tools/build_framed_candidate.py','src/patcher/pe_modal_extension.py',
                     'src/patcher/framed_modal_canvas.py','tools/build_framed_modal_candidate.py'):
            builder=module(name)
        pe._require(builder.STAGE==BASE_STAGE,'bound modal builder stage differs')
        image,metadata,_=builder.build_candidate(original,resolution,minimap_viewport=minimap_viewport)
        for name,digest in pins.items():
            pe._require(_source(name,digest)==sources[name],'army dependency changed during reconstruction')
        return image,metadata,pins
    finally:
        for name in list(sys.modules):
            if name==prefix or name.startswith(prefix+'.'):del sys.modules[name]
        sys.path[:]=old_path


@dataclass(frozen=True)
class AllocationLayout:
    code_va:int
    code_rva:int
    code_reservation:int
    state_va:int|None
    state_bytes:int
    code_header_offset:int
    state_header_offset:int|None


def allocation_layout(candidate:bytes,*,state_bytes:int=4096)->AllocationLayout:
    """File-format planning only; public extension also reconstructs the source."""
    base=pe.inspect_pe(candidate)
    pe._require(len(base.sections)==10 and tuple(s.name.rstrip(b'\0') for s in base.sections[-3:])
                ==(b'.hdcode',b'.hdmodal',b'.hdstate'),'expected exact ten-section modal layout')
    pe._require(base.sections[-3].characteristics==base.sections[-2].characteristics==pe.RX_CODE
                and base.sections[-1].characteristics==RW_DATA,'old extension protection differs')
    pe._require(base.section_alignment==4096 and base.file_alignment==512 and base.headers_size==0x400,
                'army allocation requires canonical 4096/512/1024 alignment')
    pe._require(all(a.rva+pe._align(a.memory_size,4096)==b.rva for a,b in zip(base.sections,base.sections[1:])),
                'input sections have a nonadjacent virtual extent')
    slot=base.sections[-1].header_offset+40
    pe._require(slot==0x2F8 and candidate[slot:0x348]==bytes(80),'army header slots are occupied or relocated')
    pe._require(type(state_bytes) is int and 0<=state_bytes<=MAX_STATE_BYTES and state_bytes%4096==0,
                'army RW size must be zero or bounded whole pages')
    pe._u32(base.image_base+base.image_size+CODE_RESERVATION+state_bytes,'army image extent')
    return AllocationLayout(base.image_base+base.image_size,base.image_size,CODE_RESERVATION,
                            base.image_base+base.image_size+CODE_RESERVATION if state_bytes else None,
                            state_bytes,slot,slot+40 if state_bytes else None)


def _target(base,target,kind,layout,code_size):
    if layout.code_va<=target<layout.code_va+code_size:return True
    if kind=='abs32' and layout.state_va is not None and layout.state_va<=target<layout.state_va+layout.state_bytes:return True
    return any(s.rva<=target-base.image_base<s.rva+s.memory_size
               and (kind=='abs32' or s.characteristics&0x20000000) for s in base.sections)


def _extend_verified_image(candidate,*,code,code_va,state_va,state_bytes,relocations,hooks,
                           removed_highlow_rvas,binding):
    """Private format core; arbitrary synthetic inputs do not reach public API."""
    layout=allocation_layout(candidate,state_bytes=state_bytes);base=pe.inspect_pe(candidate)
    pe._require(type(code_va) is int and code_va==layout.code_va and state_va==layout.state_va,
                'army code/state address differs from layout')
    pe._require(isinstance(code,bytes) and 0<len(code)<=CODE_RESERVATION,'invalid immutable army code size')
    pe._require(all(isinstance(rows,(tuple,list)) for rows in (relocations,hooks,removed_highlow_rvas)) and hooks,
                'explicit army hooks, relocations and removals are required')
    old_table,old_locations=pe._old_relocations(candidate,base)
    fields=[];normalized=[];added=[]
    for r in relocations:
        pe._require(all(hasattr(r,k) for k in ('offset','kind','target','purpose')),'malformed army relocation')
        pe._require(type(r.offset) is int and 0<=r.offset<=len(code)-4,'army relocation outside code')
        pe._u32(r.target,'army relocation target')
        pe._require(r.kind in ('abs32','rel32') and isinstance(r.purpose,str) and r.purpose.strip(),'invalid army relocation kind/purpose')
        pe._require(_target(base,r.target,r.kind,layout,len(code)),'army target unmapped or non-executable relative destination')
        value=r.target if r.kind=='abs32' else (r.target-code_va-r.offset-4)&0xFFFFFFFF
        pe._require(struct.unpack_from('<I',code,r.offset)[0]==value,'army relocation value differs')
        fields.append(r.offset);normalized.append(dict(offset=r.offset,kind=r.kind,target=r.target,purpose=r.purpose))
        if r.kind=='abs32':added.append(layout.code_rva+r.offset)
    fields.sort();pe._require(all(a+4<=b for a,b in zip(fields,fields[1:])),'overlapping army relocation fields')
    for hook in hooks:
        pe._require(isinstance(hook,pe.HookPatch),'army hook requires HookPatch')
        pe._require(isinstance(hook.relocations,(tuple,list)),'army hook relocation sequence missing')
        for r in hook.relocations:
            pe._require(all(hasattr(r,k) for k in ('kind','target')),'malformed army hook target')
            pe._u32(r.target,'army hook target')
            pe._require(r.kind in ('abs32','rel32') and _target(base,r.target,r.kind,layout,len(code)),
                        'army hook target unmapped or non-executable relative destination')
    view=base
    if state_bytes:
        view=replace(base,sections=base.sections+(pe.Section(b'.hdarw',layout.state_header_offset,
                     state_bytes,state_va-base.image_base,0,0,RW_DATA),))
    edits,hook_absolute,hook_fields,removed_rows=pe._prepare_hooks(candidate,view,hooks,removed_highlow_rvas,
                                                                 old_locations,code_va,len(code))
    removed=set(removed_highlow_rvas);retained=tuple(r for r in old_locations if r not in removed)
    expected=retained+tuple(added)+tuple(hook_absolute)
    table=pe._relocation_blocks(expected);table_offset=pe._align(len(code),4)
    payload=code+bytes(table_offset-len(code))+table;raw_size=pe._align(len(payload),512)
    pe._require(raw_size<=CODE_RESERVATION,'army code plus complete relocation directory exceeds reserved RX')
    state_raw=len(candidate)+raw_size
    pe._u32(state_raw+state_bytes,'army file size')
    code_header=struct.pack('<8sIIIIIIHHI',b'.hdarmy',CODE_RESERVATION,layout.code_rva,raw_size,len(candidate),0,0,0,0,pe.RX_CODE)
    def change(offset,data,purpose,rva=None):
        address=offset if rva is None else rva
        old=candidate[offset:offset+len(data)]
        pe._require(len(old)==len(data),'army edit outside old image')
        edits.append(pe.ByteEdit(offset,address,base.image_base+address,old,data,purpose))
    change(base.pe_offset+6,struct.pack('<H',11+bool(state_bytes)),'NumberOfSections')
    change(base.optional_offset+4,struct.pack('<I',pe._u32(base.size_of_code+raw_size,'SizeOfCode')),'SizeOfCode')
    if state_bytes:
        initialized=struct.unpack_from('<I',candidate,base.optional_offset+8)[0]
        change(base.optional_offset+8,struct.pack('<I',pe._u32(initialized+state_bytes,'SizeOfInitializedData')),'SizeOfInitializedData')
    change(base.optional_offset+56,struct.pack('<I',layout.code_rva+CODE_RESERVATION+state_bytes),'SizeOfImage')
    change(base.optional_offset+136,struct.pack('<II',layout.code_rva+table_offset,len(table)),'complete merged army relocations')
    change(layout.code_header_offset,code_header,'.hdarmy RX header; retired old diagnostic scratch')
    if state_bytes:
        header=struct.pack('<8sIIIIIIHHI',b'.hdarw',state_bytes,state_va-base.image_base,state_bytes,state_raw,0,0,0,0,RW_DATA)
        change(layout.state_header_offset,header,'.hdarw zero RW header; retired old diagnostic scratch')
    edits.append(pe.ByteEdit(len(candidate),layout.code_rva,code_va,b'',payload+bytes(raw_size-len(payload)),
                             'append army RX code and merged relocations'))
    if state_bytes:
        edits.append(pe.ByteEdit(state_raw,state_va-base.image_base,state_va,b'',bytes(state_bytes),'append zero army RW storage'))
    spans=sorted((e.offset,e.offset+len(e.old)) for e in edits if e.old)
    pe._require(all(a[1]<=b[0] for a,b in zip(spans,spans[1:])),'overlapping army edits')
    result=bytearray(candidate)
    for e in edits:
        pe._require(result[e.offset:e.offset+len(e.old)]==e.old and (e.old or e.offset==len(result)),
                    'army old-byte or append offset mismatch')
        result[e.offset:e.offset+len(e.old)]=e.new
    image=bytes(result);final=pe.inspect_pe(image)
    pe._require(final.sections[:10]==base.sections,'old section headers changed')
    pe._require(all(a.rva+pe._align(a.memory_size,4096)==b.rva for a,b in zip(final.sections,final.sections[1:])),
                'army output has nonadjacent virtual sections')
    _,actual=pe._old_relocations(image,final)
    pe._require(sorted(actual)==sorted(expected),'army merged HIGHLOW locations differ')
    old_reloc_offset=base.file_offset(base.relocation_rva,base.relocation_size)
    pe._require(image[old_reloc_offset:old_reloc_offset+len(old_table)]==old_table,'old relocation bytes overwritten')
    if state_bytes:pe._require(image[state_raw:]==bytes(state_bytes),'army RW initialization differs')
    metadata=dict(schema='clash95_pe_army_extension_v1',**binding,input_sha256=pe._sha(candidate),output_sha256=pe._sha(image),
        code_va=code_va,code_rva=layout.code_rva,code_sha256=pe._sha(code),code_bytes=len(code),code_raw_bytes=raw_size,
        code_virtual_bytes=CODE_RESERVATION,code_characteristics=pe.RX_CODE,state_va=state_va,state_bytes=state_bytes,
        state_raw_offset=state_raw if state_bytes else None,state_characteristics=RW_DATA if state_bytes else None,
        old_highlow_count=len(old_locations),retained_highlow_count=len(retained),new_highlow_count=len(added)+len(hook_absolute),
        old_relocation_sha256=pe._sha(old_table),merged_relocation_sha256=pe._sha(table),relocation_rva=layout.code_rva+table_offset,
        relocation_bytes=len(table),removed_highlow=removed_rows,relocations=normalized,hook_relocations=hook_fields,
        hooks=[e.metadata() for e in edits[:len(hooks)]],edits=[e.metadata() for e in edits],
        retired_header_scratch=dict(start=0x300,end_exclusive=0x348,legacy_day_diagnostic_allowed=False),
        installation_ready=False,runtime_executed=False,manual_input_proof=False,promotion_ready=False,
        limits='Source-bound storage and declared byte/operand integrity only. Emitter semantics, complete relocation inventory, '
               'new-stage probe excluding legacy header-scratch diagnostics, runtime and promotion remain separate.')
    return pe.ExtensionResult(image,tuple(edits),metadata)


def extend_modal_candidate_with_army(original,candidate,*,expected_candidate_sha256,resolution,minimap_viewport,
                                     validation_stage,code,code_va,state_va,state_bytes,relocations,hooks,removed_highlow_rvas):
    pe._identity(original,pe.ORIGINAL_SHA256,'original')
    pe._identity(candidate,expected_candidate_sha256,'modal input')
    pe._require(validation_stage==STAGE,'explicit army validation stage required')
    pe._require(type(minimap_viewport) is bool and isinstance(resolution,str),'explicit minimap choice and canonical resolution required')
    rebuilt,metadata,pins=_reconstruct_modal(original,resolution,minimap_viewport)
    pe._require(rebuilt==candidate,'input differs from entire source-reconstructed modal candidate')
    binding=dict(original_sha256=pe.ORIGINAL_SHA256,base_stage=BASE_STAGE,stage=STAGE,resolution=resolution,
                 minimap_viewport=minimap_viewport,source_sha256=pins,base_candidate_sha256=pe._sha(rebuilt),
                 base_modal_revision=metadata['modal_native_canvas_revision'])
    return _extend_verified_image(candidate,code=code,code_va=code_va,state_va=state_va,state_bytes=state_bytes,
        relocations=relocations,hooks=hooks,removed_highlow_rvas=removed_highlow_rvas,binding=binding)
