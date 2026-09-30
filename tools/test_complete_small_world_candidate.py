#!/usr/bin/env python3
"""Complete small-world byte contracts and bounded x86 CPU fixtures.

Synthetic cases execute actual emitted helper bytes on artificial memory.
The optional original-backed lane constructs one modalwidgets1920 successor
in memory. No game, debugger, native compiler, output bundle or installation
is run. Drawing dependency returns are modeled; CPU results are not rendering,
authentic input, lifecycle, launcher acceptance or promotion evidence.
"""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import argparse
import io
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
from src.patcher import complete_small_world_candidate as tool
from src.patcher import ordinary_castle_entry_matrix as matrix
from src.patcher import framed_bounded_paint as paint
from src.patcher import framed_bounded_input as inputs
from src.patcher import framed_input as frozen
from src.patcher import framed_army_input as army
from src.patcher import framed_army_composition as composition
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_camera as camera
from src.patcher import pe_extension as pe
from src.patcher.framed_viewport import FramedViewport
import test_ordinary_castle_entry_matrix as matrix_fixture
import build_complete_small_world_candidate as cli
from test_pe_extension import independent_image, rebase

ORIGINAL = None
TOOLCHAIN = None
REQUIRE_MACHINE = False
SYNTHETIC_ONLY = False
FLAGS_MASK = 0xCD5


def _synthetic_image(profile):
    """Artificial PE shape, with original-like addresses but no game assets."""
    count = 16 if profile=='modalwidgets' else 12
    data = bytearray(1024); data[:2]=b'MZ'
    struct.pack_into('<I',data,0x3C,0x40); data[0x40:0x44]=b'PE\0\0'
    struct.pack_into('<HHIIIHH',data,0x44,0x14C,count,0,0,0,224,0x182)
    opt=0x58; struct.pack_into('<H',data,opt,0x10B)
    struct.pack_into('<III',data,opt+28,0x400000,4096,512)
    struct.pack_into('<I',data,opt+60,1024);struct.pack_into('<I',data,opt+92,16)
    rva,code_size=0x1000,0
    for n in range(count):
        name=('.text','.hdmodal','.hdstate','.hdcode','.hdarmy')[n] if n<5 else '.hdpblit' if n==count-1 else '.x'+str(n)
        raw_size=0x80000 if n==0 else 0x20000 if n==3 else 0x10000 if n==4 else 4096
        virtual=0x160000 if n==0 else raw_size
        flags=0xC0000040 if n==2 else pe.RX_CODE
        struct.pack_into('<8sIIIIIIHHI',data,0x138+40*n,name.encode(),virtual,rva,raw_size,len(data),0,0,0,0,flags)
        data.extend(bytes(raw_size));rva+=virtual
        if flags&0x20:code_size+=raw_size
    struct.pack_into('<I',data,opt+4,code_size);struct.pack_into('<I',data,opt+56,rva)
    last_rva=rva-4096;last_raw=len(data)-4096
    reloc=pe._relocation_blocks((0x1020,0x18786,0x23877))
    struct.pack_into('<II',data,opt+136,last_rva+0x800,len(reloc))
    data[last_raw+0x800:last_raw+0x800+len(reloc)]=reloc
    struct.pack_into('<I',data,1024+0x20,0xF1234567)
    return bytes(data)


def synthetic_parent(profile='modalwidgets',resolution='1920x1080'):
    """Real generated input/composition bytes in an explicitly artificial parent.

    Only original/builder audits needed to emit the *fixture's* predecessor are
    replaced. The successor's ancestry, six old spans, allocator and relocation
    authentication run unchanged. This parent is never sent to the public API.
    """
    width,height=map(int,resolution.split('x'));layout=FramedViewport(width,height)
    image=_synthetic_image(profile);view=pe.inspect_pe(image);data=bytearray(image)
    def put(va,value):
        offset=view.file_offset(va-view.image_base,len(value));data[offset:offset+len(value)]=value
    for _name,va,old,*_rest in (*frozen.CALL_SITES,*frozen.PANEL_SITES):put(va,bytes.fromhex(old))
    put(frozen.CLICK_GATE,bytes.fromhex('f6402c010f95c025ff000000c3'))
    put(frozen.MINIMAP_GATE,bytes.fromhex('31c0c3'))
    count=clip._Assembler(army.COUNT);count.emit('31c98d5006');count.label('loop')
    count.emit('66833aff');count.branch('0f84','done');count.emit('4183c21f83f90a')
    count.branch('0f8c','loop');count.label('done');count.emit('89c8c3');put(army.COUNT,count.finish())
    for va,old,*_ in army.HOOKS:put(va,bytes.fromhex(old))
    put(0x418784,bytes.fromhex('8b159469520085d20f841b020000'))
    code_base=view.image_base+view.sections[3].rva
    modal_base=view.image_base+view.sections[1].rva
    state=view.image_base+view.sections[2].rva
    with patch.object(clip,'verify_original'),patch.object(frozen,'NATIVE_CONTRACTS',()), \
            patch.object(frozen,'_native_highlow_vas',return_value=set()):
        ordinary=frozen.emit_input_bundle(bytes(data),base_va=code_base,width=width,height=height)
    code=bytearray(ordinary.code);relocations=list(ordinary.relocations)
    entries={'framed_input.'+name:va for name,va in ordinary.entries.items()}
    context=ordinary.entries['context_guard']-code_base
    context_end=ordinary.entries['pixel_guard']-code_base
    for name in ('composition_guard','frame_presentation.frame_presentation_admission'):
        at=len(code);entries[name]=code_base+at;code.extend(ordinary.code[context:context_end])
        relocations.extend(pe.CodeRelocation(r.offset-context+at,r.kind,r.target,r.purpose)
                           for r in ordinary.relocations if context<=r.offset<context_end)
    entries['edge']=code_base+len(code);edge=clip._Assembler(entries['edge'])
    edge.emit('833d');edge.absolute(clip.LOWER_ROW_OWNER_GLOBAL,'lower_row_owner');edge.emit('00')
    edge.branch('0f85','deny');edge.emit('b801000000c3');edge.label('deny');edge.emit('31c0c3')
    edge_at=len(code);code.extend(edge.finish())
    relocations.extend(pe.CodeRelocation(r.offset+edge_at,r.kind,r.target,r.purpose) for r in edge.relocations)
    for name,result in (('cell',2),('draw_frame',1),('present_map_rect',1)):
        entries[name]=code_base+len(code);code.extend(b'\xb8'+struct.pack('<I',result)+b'\xc3')
    entries['compose_panel']=code_base+len(code)
    code.extend(bytes.fromhex('6089e583ec0cc7451c0100000089ec61c3'))
    for kind,entry,reject in (('full_redraw','hook_framed_full_entry','framed_full_reject'),
                              ('initial_paint','initial_paint_admission','initial_admission_reject')):
        at=len(code);va=code_base+at;entries[entry]=va
        reject_va=va+camera.GATE_OFFSETS[kind]+124+16
        entries[reject]=reject_va
        if kind=='full_redraw':entries['framed_full_fallback']=reject_va
        prefix=camera._prefix(kind,va,entries)
        code.extend(prefix+camera.old_gate(layout,va+len(prefix),reject_va))
        reject_tail='c7451c0000000089ec619dc3' if kind=='full_redraw' else 'c744241c0000000061c3'
        code.extend(bytes(16));code.extend(bytes.fromhex(reject_tail))
        # Prefix absolute operands are explicit fixture bindings, not scanned addresses.
        targets=(clip.GAME_DATA_GLOBAL,) if kind=='full_redraw' else (0x527C24,clip.TILE_CALLBACK_GLOBAL,clip.GAME_DATA_GLOBAL)
        for target in targets:
            value=struct.pack('<I',target);positions=[i for i in range(len(prefix)-3) if prefix[i:i+4]==value]
            assert len(positions)==1
            relocations.append(pe.CodeRelocation(at+positions[0],'abs32',target,'fixture render prefix'))
    put(code_base,bytes(code))
    framed=dict(schema='clash95_pe_extension_v1',resolution=resolution,stage=camera.PARENT_STAGE,
                code_va=code_base,code_bytes=len(code),code_sha256=matrix.sha(code),entry_vas=entries,
                minimap_viewport=True,framed_validation=True,relocations=[vars(r) for r in relocations])
    # Authenticate the real matrix wrapper/caller shape, with an artificial body.
    modal=dict(schema='clash95_framed_modal_candidate_v1',resolution=resolution,
               modal_native_canvas_revision='framed_owned_native_modal_canvas_v1',
               modal_state_offsets=dict(matrix.canvas.STATE),modal_state_size=128,
               modal_entry_vas={'try_enter':modal_base,'root_entry':modal_base+0x79E},
               code_va=modal_base,state_va=state,base_candidate=framed,authenticated_legacy_continuations=[])
    enter,root=modal_base,modal_base+0x79E
    put(enter+0x6B,matrix.OWNER_CMP);put(enter+0x75,b'\x0f\x85'+struct.pack('<i',0x230-0x7B))
    put(enter+0x230,bytes.fromhex('c744241c00000000619dc3'))
    put(root,bytes.fromhex('9c608d442424e8')+struct.pack('<i',enter-root-11)+bytes.fromhex('619d5351525657e9')+struct.pack('<i',0x422185-root-23))
    put(0x422180,b'\xe9'+struct.pack('<i',root-0x422185))
    put(matrix.NATIVE_CALLER,bytes.fromhex('e811340000'));put(0x41ED54,bytes.fromhex('8b1dd89951008935d8995100'))
    pre_army=bytes(data);army_base=view.image_base+view.sections[4].rva
    from tools import build_framed_modal_candidate as modal_builder
    with patch.object(clip,'verify_original'),patch.object(army,'NATIVE_SPANS',()), \
            patch.object(frozen,'NATIVE_CONTRACTS',()),patch.object(frozen,'_native_highlow_vas',return_value=set()), \
            patch.object(modal_builder,'build_candidate',return_value=(pre_army,modal,'')):
        mouse=army.emit_army_input(pre_army,pre_army,base_va=army_base,width=width,height=height,minimap_viewport=True)
    put(army_base,mouse.code)
    composition_base=army_base+len(mouse.code)
    with patch.object(composition.extension,'_reconstruct_modal',return_value=(pre_army,modal,'')), \
            patch.object(composition.extension,'allocation_layout',return_value=SimpleNamespace(code_va=army_base,code_reservation=0x10000)):
        panel=composition.emit_army_composition(pre_army,pre_army,base_va=composition_base,width=width,height=height,
              minimap_viewport=True,owner_state_va=mouse.entries['owner_state'],draw_army_va=army_base+0xF000)
    put(composition_base,panel.code)
    for hook in (*mouse.hook_sites,*panel.hook_sites):put(hook.va,hook.new)
    absolute=[r.offset+code_base-view.image_base for r in relocations if r.kind=='abs32']
    absolute.extend(r.offset+army_base-view.image_base for r in mouse.relocations if r.kind=='abs32')
    absolute.extend(r.offset+composition_base-view.image_base for r in panel.relocations if r.kind=='abs32')
    removed=set(panel.removed_highlow_rvas)|{va-view.image_base for va in mouse.removed_highlow_vas}
    absolute=sorted(({0x1020}|set(absolute))-removed)
    table=pe._relocation_blocks(absolute)
    last=view.sections[-1];directory=last.rva+0x800
    assert len(table)<0x800
    put(view.image_base+directory,table);struct.pack_into('<II',data,view.optional_offset+136,directory,len(table))
    army_metadata=dict(schema='clash95_framed_army_candidate_v1',resolution=resolution,base_candidate=modal,
                       army_revision='framed_own_army_native_size_v1',code_va=army_base,code_bytes=len(mouse.code)+len(panel.code),
                       army_entry_vas={'input.'+name:va for name,va in mouse.entries.items()}|
                                      {'composition.'+name:va for name,va in panel.entries.items()},
                       army_contracts={'composition':panel.source_contract})
    native=matrix_fixture.typed_parent(profile,resolution)
    complete=native['base_candidate']
    if profile=='modalwidgets':
        for _ in range(4):complete=complete['base_candidate']
    complete['predecessor']=army_metadata
    pre_matrix=bytes(data)
    native['candidate_sha256']=matrix.sha(pre_matrix)
    admission=matrix.derive_admission(pre_matrix,pre_matrix,modal)
    parent,report=matrix.extend_tail(pre_matrix,admission,profile)
    metadata=dict(report,schema=matrix.SCHEMA,recipe_revision=matrix.REVISION,profile=profile,resolution=resolution,
                  stage=matrix.stage(profile),original_sha256=pe.ORIGINAL_SHA256,candidate_sha256=matrix.sha(parent),
                  base_candidate_sha256=matrix.sha(pre_matrix),base_stage=native['stage'],base_candidate=native,admission=asdict(admission),
                  source_hashes={matrix.SOURCE:matrix.sha((ROOT/matrix.SOURCE).read_bytes())},
                  validation_stage_only=True,runtime_executed=False,manual_input_proof=False,promotion_ready=False,
                  bounded_small_world_integrated=False,predecessor_probe_reusable=False)
    return parent,metadata


def synthetic_successor(profile='modalwidgets',resolution='1920x1080',*,probe=True):
    parent,metadata=synthetic_parent(profile,resolution)
    image,report=tool._upgrade_verified_parent(parent,metadata,profile,resolution)
    text=''
    if probe:
        text,contract=tool.render_probe(image,report)
        report=dict(report,probe_sha256=matrix.sha(text.encode()),probe_contract=contract)
    return parent,image,report,text


def require_machine_tools():
    try:
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, x86_const
        registers = ('EAX','EBX','ECX','EDX','ESI','EDI','EBP','ESP','EFLAGS','EIP')
        if not callable(Uc) or not all(type(value) is int for value in (
                UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,
                *(getattr(x86_const,'UC_X86_REG_'+name) for name in registers))):
            raise ImportError('Unicorn x86 API differs')
    except (ImportError, AttributeError) as error:
        raise ImportError('Unicorn x86 API unavailable') from error


def inherited_parts(metadata):
    """Follow only the producer's typed parent chain, never a recursive search."""
    node = metadata['base_candidate']
    if node['schema'] == matrix.SCHEMA:
        node = node['base_candidate']
    profile, resolution = metadata['profile'], metadata['resolution']
    modal = matrix.modal_ancestor(node, profile, resolution)
    complete = node['base_candidate']
    if profile == 'modalwidgets':
        for kind in ('widgets','primary_text','primary','slots'):
            assert complete['schema'] == 'clash95_framed_modal_'+kind+'_candidate_v1'
            complete = complete['base_candidate']
    assert complete['schema'] == 1
    return modal['base_candidate'], complete['predecessor'], modal


class Machine:
    """Execute candidate PE bytes; only drawing/presentation returns are modeled."""
    HEAP, HEAP_SIZE = 0x10000000, 0xA0000
    STACK, STACK_SIZE, STOP = 0x20000000, 0x10000, 0x30000000
    GD, SURFACE, PIXELS, BUTTON = HEAP, HEAP+0x90000, HEAP+0x91000, HEAP+0x92000

    def __init__(self, image, metadata, *, delta=0, **options):
        require_machine_tools()
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, x86_const
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.regs = {name:getattr(x86_const,'UC_X86_REG_'+name) for name in
                     ('EAX','EBX','ECX','EDX','ESI','EDI','EBP','ESP','EFLAGS','EIP')}
        self.metadata, self.options, self.delta = metadata, options, delta
        self.width, self.height = map(int,metadata['resolution'].split('x'))
        self.framed, self.army, self.modal = inherited_parts(metadata)
        self.entries = self.framed['entry_vas']
        self.army_entries = self.army['army_entry_vas']
        memory, _sections, fields, _directory = independent_image(image)
        self.base = 0x400000+delta
        self.uc.mem_map(self.base,len(memory))
        self.uc.mem_write(self.base,bytes(rebase(memory,fields,delta)))
        self.uc.mem_map(self.HEAP,self.HEAP_SIZE)
        self.uc.mem_map(self.STACK,self.STACK_SIZE)
        self.uc.mem_map(self.STOP,4096)
        self.writes, self.calls, self.route, self.returned = [], [], None, False
        self._seed()
        self.uc.hook_add(UC_HOOK_MEM_WRITE,self._write)
        self.uc.hook_add(UC_HOOK_CODE,self._code)

    def read(self,address,size=4):
        return int.from_bytes(self.uc.mem_read(address,size),'little')

    def write(self,address,value,size=4):
        self.uc.mem_write(address,(value & ((1<<(8*size))-1)).to_bytes(size,'little'))

    def glob(self,address,value,size=4):
        self.write(address+self.delta,value,size)

    def _seed(self):
        c = self.options
        self.glob(clip.GAME_DATA_GLOBAL,0 if c.get('null_game') else self.GD)
        self.glob(clip.MAP_SURFACE_GLOBAL,0 if c.get('null_surface') else self.SURFACE)
        self.glob(clip.RENDER_DEVICE_GLOBAL,0x12345000)
        self.glob(clip.RENDER_HOOK_GLOBAL,c.get('render_hook',0x40AD40)+self.delta)
        self.glob(clip.LOWER_ROW_OWNER_GLOBAL,c.get('owner',0))
        self.glob(clip.POST_TILE_CALLBACK_GLOBAL,c.get('post',0))
        self.glob(clip.TILE_CALLBACK_GLOBAL,c.get('callback',0)+(self.delta if c.get('callback') else 0))
        player = c.get('player',0)
        self.glob(clip.CURRENT_PLAYER_GLOBAL,player)
        self.write(self.GD+0x222E0,c.get('world_width',10))
        self.write(self.GD+0x222E4,c.get('world_height',10))
        self.write(self.GD+0x222E8,c.get('scroll_x',0))
        self.write(self.GD+0x222EC,c.get('scroll_y',0))
        self.write(self.GD+0x23EC7,c.get('minimap_player',0))
        for p in range(5):
            self.write(self.GD+0x22313+1423*p,int(c.get('interactive',1)!=0))
            self.write(self.GD+0x2230F+1423*p,int(c.get('minimap_enabled',False)))
        self.write(self.SURFACE,c.get('surface_width',self.width),2)
        self.write(self.SURFACE+2,c.get('surface_height',self.height),2)
        self.write(self.SURFACE+4,0 if c.get('null_pixels') else self.PIXELS)
        self.write(self.SURFACE+0xB8,c.get('vtable',clip.MEMORY_VTABLE)+self.delta)
        self.glob(frozen.MOUSE_X,c.get('x',40)); self.glob(frozen.MOUSE_Y,c.get('y',24))
        self.glob(frozen.MOUSE_SHIFT,c.get('shift',0),1)
        self.glob(frozen.MINIMAP_ORIGIN,self.width-246,2)
        self.glob(frozen.MINIMAP_ORIGIN+2,16,2)
        self.glob(frozen.MINIMAP_SIZE,214,2); self.glob(frozen.MINIMAP_SIZE+2,214,2)
        self.write(self.BUTTON+0x2C,c.get('click',1),1)
        self.glob(clip.COMMAND_SPRITES_GLOBAL,self.PIXELS)
        self.glob(clip.TURN_SPRITES_GLOBAL,self.PIXELS)
        self.glob(clip.TOOLTIP_SURFACE_GLOBAL,0)
        self.glob(0x527C24,1)
        selected = c.get('selected',3)
        unit = self.GD+147174+725*max(0,min(selected,499))
        self.glob(army.SELECTED,selected); self.glob(army.PRIOR,c.get('prior',selected))
        self.glob(army.UNIT,unit+c.get('unit_offset',0))
        self.write(unit,c.get('unit_x',0),2); self.write(unit+2,c.get('unit_y',0),2)
        self.write(unit+4,c.get('unit_owner',player),1)
        for n in range(10):
            self.write(unit+6+31*n,c.get('squad_type',1) if n<c.get('count',2) else -1,2)
        if 'bad_slot' in c:self.write(unit+6+31*c['bad_slot'],c.get('bad_type',35),2)
        state = self.modal['state_va']+self.delta
        self.uc.mem_write(state,bytes(128))
        self.write(state+c.get('state_offset',0),c.get('state_value',0))

    def _write(self,_uc,_access,address,size,value,_data):
        if not self.STACK <= address < self.STACK+self.STACK_SIZE:
            self.writes.append((address,size,value))

    def _return(self,value):
        esp = self.uc.reg_read(self.regs['ESP'])
        self.uc.reg_write(self.regs['EAX'],value)
        self.uc.reg_write(self.regs['ESP'],esp+4)
        self.uc.reg_write(self.regs['EIP'],self.read(esp))

    def _code(self,_uc,address,_size,_data):
        if address == self.STOP:
            self.returned = True; self.uc.emu_stop(); return
        for va,label in ((frozen.CLICK_GATE,'native_click'),(frozen.MINIMAP_GATE,'native_minimap'),
                         (army.COUNT,'native_count')):
            if address == va+self.delta:
                self.calls.append((label,self.uc.reg_read(self.regs['EAX'])))
        if not getattr(self,'render',False):return
        for kind in ('full_redraw','initial_paint'):
            entry = self.entries['hook_framed_full_entry' if kind=='full_redraw' else 'initial_paint_admission']
            if address == entry+camera.GATE_OFFSETS[kind]+124+self.delta:
                self.route = kind+'.native_continuation'; self.uc.emu_stop(); return
        modeled = ('cell','draw_frame','compose_panel','present_map_rect')
        for name in modeled:
            if address == self.entries[name]+self.delta:
                self.calls.append((name,self.uc.reg_read(self.regs['EAX']),self.uc.reg_read(self.regs['EBX'])))
                if name == 'cell':
                    self.write(self.SURFACE+0xB8,0x76543210)
                    self.glob(clip.RENDER_DEVICE_GLOBAL,0x45678000)
                    value = 2
                else:value = 1
                if self.options.get('fail') == name:value = 0
                self._return(value); return

    def run(self,kind='ordinary',flags=0xED7):
        self.render = kind in ('admit_world','bounded_full','full_redraw','initial_paint')
        if kind == 'ordinary':entry = self.entries['framed_input.click_gate']
        elif kind == 'army':entry = self.army_entries['input.guarded_map_click']
        elif kind in ('full_redraw','initial_paint'):
            entry = self.entries['hook_framed_full_entry' if kind=='full_redraw' else 'initial_paint_admission']
        else:entry = self.metadata['helpers']['entry_vas'][kind]
        initial = dict(EAX=self.options.get('present',1) if self.render else self.BUTTON,
                       EBX=0x22334455,ECX=0x33445566,EDX=self.GD if kind=='admit_world' else 0x44556677,
                       ESI=0x55667788,EDI=0x66778899,EBP=0x778899AA,
                       ESP=self.STACK+0xC000,EFLAGS=flags)
        self.write(initial['ESP'],self.STOP)
        self.before_heap = bytes(self.uc.mem_read(self.HEAP,self.HEAP_SIZE))
        for name,value in initial.items():self.uc.reg_write(self.regs[name],value)
        self.uc.emu_start(entry+self.delta,self.STOP+1,count=300000)
        if not self.returned and self.route is None:raise AssertionError('bounded CPU execution did not reach a declared stop')
        final = {name:self.uc.reg_read(register) for name,register in self.regs.items()}
        # The inherited initial admission has PUSHAD without PUSHFD. Its
        # arithmetic flags are not an advertised ABI; DF and GPR/stack survive.
        flags_mask = 0x400 if kind=='initial_paint' else FLAGS_MASK
        preserved = (all(final[name]==initial[name] for name in ('EBX','ECX','EDX','ESI','EDI','EBP'))
                     and final['ESP']==initial['ESP']+4
                     and final['EFLAGS']&flags_mask==flags&flags_mask)
        return dict(result=final['EAX'],preserved=preserved,returned=self.returned,route=self.route,
                    calls=self.calls,writes=self.writes,
                    heap_unchanged=bytes(self.uc.mem_read(self.HEAP,self.HEAP_SIZE))==self.before_heap,
                    scroll=(self.read(self.GD+0x222E8),self.read(self.GD+0x222EC)),
                    vtable=self.read(self.SURFACE+0xB8),render=self.read(clip.RENDER_DEVICE_GLOBAL+self.delta))


def scalar_click(width,height,kind,c):
    """Independent integer geometry/ownership oracle; no producer helper calls."""
    if c.get('click',1)&1==0:return False
    if (c.get('null_game') or c.get('null_surface') or c.get('null_pixels') or
            c.get('surface_width',width)!=width or c.get('surface_height',height)!=height or
            c.get('vtable',0x50EE24)!=0x50EE24 or c.get('render_hook',0x40AD40)!=0x40AD40 or
            c.get('post',0)!=0 or c.get('callback',0) not in (0,0x425120,0x429EC0) or
            c.get('player',0) not in range(5) or c.get('minimap_player',0) not in range(5) or
            not c.get('interactive',1)):return False
    lower=c.get('owner',0)
    owned=(lower==1 and c.get('player',0) in range(4) and
           0<=c.get('selected',3)<500 and c.get('prior',c.get('selected',3))==c.get('selected',3) and
           c.get('unit_offset',0)==0 and c.get('unit_owner',c.get('player',0))==c.get('player',0) and
           0<=c.get('unit_x',0)<c.get('world_width',10) and
           0<=c.get('unit_y',0)<c.get('world_height',10) and
           2<=c.get('count',2)<=10 and 0<=c.get('squad_type',1)<=34 and
           (c.get('bad_slot',10)>=c.get('count',2) or 0<=c.get('bad_type',35)<=34) and
           c.get('state_value',0)==0)
    if (kind=='army' and not owned) or (lower!=0 and not owned):return False
    shift=c.get('shift',0)&31
    def signed(value):return (value&0x7FFFFFFF)-(value&0x80000000)
    x=signed(c.get('x',40))>>shift;y=signed(c.get('y',24))>>shift
    if not (32<=x<width-32 and 16<=y<height-16):return False
    if x>=width-224 and y>=height-80:return False
    if c.get('minimap_enabled') and width-246<=x<width-32 and 16<=y<230:return False
    if owned and 32<=x<=418 and height-82<=y<=height-17:return False
    mw,mh=c.get('world_width',10),c.get('world_height',10)
    sx,sy=c.get('scroll_x',0),c.get('scroll_y',0)
    return (1<=mw<=100 and 1<=mh<=100 and
            0<=sx<=max(0,mw-(width-64)//64) and 0<=sy<=max(0,mh-(height-32)//64) and
            sx+(x-32)//64<mw and sy+(y-16)//64<mh)


class PortableTests(unittest.TestCase):
    def test_unknown_original_unsupported_case_and_mutable_bytes_fail_before_parent(self):
        with patch.object(matrix,'build_candidate') as parent:
            for data,profile,resolution in ((b'unknown','modalwidgets','1920x1080'),
                    (bytearray(4),'completehd','800x600'),(None,'completehd','800x600'),
                    (b'unknown','classic','1920x1080'),(b'unknown','modalwidgets','3840x2160')):
                with self.subTest(profile=profile,resolution=resolution),self.assertRaises(ValueError):
                    tool.build_candidate(data,profile,resolution)
            parent.assert_not_called()

    def test_both_profiles_all_six_geometries_replay_exact_six_spans_and_preserve_old_bytes(self):
        for profile in matrix.PROFILES:
            for resolution in matrix.RESOLUTIONS:
                with self.subTest(profile=profile,resolution=resolution):
                    parent,image,metadata,_=synthetic_successor(profile,resolution,probe=False)
                    old=pe.inspect_pe(parent);new=pe.inspect_pe(image)
                    self.assertEqual(len(new.sections),16 if profile=='modalwidgets' else 12)
                    self.assertEqual(old.sections[:-1],new.sections[:-1])
                    self.assertEqual(set(metadata['spans']),{'render.full_redraw','render.initial_paint',
                        'input.ordinary.x','input.ordinary.y','input.army.x','input.army.y'})
                    rebuilt=bytearray(parent);changed=set()
                    for edit in metadata['edits']:
                        offset=edit['offset'];before=bytes.fromhex(edit['old_hex']);after=bytes.fromhex(edit['new_hex'])
                        self.assertEqual(bytes(rebuilt[offset:offset+len(before)]),before)
                        self.assertTrue(before or offset==len(rebuilt))
                        rebuilt[offset:offset+len(before)]=after
                        changed.update(range(offset,offset+len(before)))
                    self.assertEqual(bytes(rebuilt),image)
                    self.assertTrue(all(a==b or n in changed for n,(a,b) in enumerate(zip(parent,image))))
                    for name,span in metadata['spans'].items():
                        size=124 if name.startswith('render.') else 16
                        self.assertEqual((len(bytes.fromhex(span['old_hex'])),len(bytes.fromhex(span['new_hex']))),(size,size))
                        self.assertEqual(span['va']-old.image_base,span['rva'])
                        self.assertEqual(old.file_offset(span['rva'],size),span['offset'])
                    parent_meta=metadata['base_candidate']
                    gate=parent_meta['code_va'];size=parent_meta['code_bytes']
                    self.assertEqual(size,96)
                    at=old.file_offset(gate-old.image_base,size)
                    self.assertEqual(parent[at:at+size],image[at:at+size])
                    self.assertGreaterEqual(metadata['helpers']['base_va'],old.image_base+old.image_size)
                    self.assertEqual(new.sections[-1].characteristics,pe.RX_CODE)

    def test_typed_parent_identity_and_all_ancestor_schema_substitution_fail(self):
        parent,metadata=synthetic_parent()
        for field,value in (('schema','other'),('recipe_revision','other'),('stage','other'),
                            ('profile','completehd'),('resolution','1024x768'),('original_sha256','0'*64),
                            ('candidate_sha256','0'*64),('runtime_executed',True),('admission',{})):
            altered=deepcopy(metadata);altered[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                tool._upgrade_verified_parent(parent,altered,'modalwidgets','1920x1080')
        node=metadata['base_candidate'];path=[]
        while isinstance(node,dict):
            altered=deepcopy(metadata);cursor=altered['base_candidate']
            for key in path:cursor=cursor[key]
            cursor['schema']='untyped substitute'
            with self.subTest(path=path),self.assertRaises(ValueError):
                tool._upgrade_verified_parent(parent,altered,'modalwidgets','1920x1080')
            key='predecessor' if node.get('schema')==1 else 'base_candidate'
            node=node.get(key);path=path+[key]

    def test_source_drift_and_all_six_old_byte_mismatches_fail_with_updated_outer_hash(self):
        parent,metadata=synthetic_parent()
        altered=deepcopy(metadata);altered['source_hashes'][matrix.SOURCE]='0'*64
        with self.assertRaises(ValueError):tool._upgrade_verified_parent(parent,altered,'modalwidgets','1920x1080')
        _image,report=tool._upgrade_verified_parent(parent,metadata,'modalwidgets','1920x1080')
        native=restore_parent(parent,metadata)
        for name,span in report['spans'].items():
            changed=bytearray(parent);changed[span['offset']]^=1
            altered=deepcopy(metadata);altered['candidate_sha256']=matrix.sha(changed)
            changed_native=bytearray(native);changed_native[span['offset']]^=1
            altered['base_candidate_sha256']=matrix.sha(changed_native)
            altered['base_candidate']['candidate_sha256']=matrix.sha(changed_native)
            with self.subTest(span=name),self.assertRaisesRegex(ValueError,'old guard bytes|full inherited input world gate'):
                tool._upgrade_verified_parent(bytes(changed),altered,'modalwidgets','1920x1080')

        # Separately retain an outer-only mutation that must fail the exact
        # native replay digest, before any six-span comparison can run.
        framed,_army,_modal=inherited_parts(metadata)
        view=pe.inspect_pe(parent);changed=bytearray(parent)
        changed[view.file_offset(framed['entry_vas']['composition_guard']-view.image_base,1)]^=1
        altered=deepcopy(metadata);altered['candidate_sha256']=matrix.sha(changed)
        with self.assertRaisesRegex(ValueError,'parent replay SHA'):
            tool._upgrade_verified_parent(bytes(changed),altered,'modalwidgets','1920x1080')

    def test_merged_highlow_inventory_and_two_load_bases_wrap_high_bit_dwords(self):
        parent,image,metadata,_=synthetic_successor(probe=False)
        old_memory,_old_sections,old_fields,old_dir=independent_image(parent)
        memory,_sections,fields,directory=independent_image(image)
        helper=metadata['helpers'];records=helper['relocations']
        added=[helper['base_va']-0x400000+row['offset'] for row in records if row['kind']=='abs32']
        self.assertEqual(len(added),5);self.assertEqual(len(set(added)),5)
        self.assertEqual(set(fields),set(old_fields)|set(added))
        self.assertEqual(memory[old_dir[0]:sum(old_dir)],old_memory[old_dir[0]:sum(old_dir)])
        self.assertNotEqual(directory,old_dir)
        self.assertEqual(metadata['relocation_contract']['old_rvas'],list(old_fields))
        self.assertEqual(metadata['relocation_contract']['merged_rvas'],list(fields))
        self.assertEqual(struct.unpack_from('<I',memory,0x1020)[0],0xF1234567)
        for delta in (0x200000,0x80000000):
            relocated=rebase(memory,fields,delta)
            for field in fields:
                self.assertEqual(struct.unpack_from('<I',relocated,field)[0],
                                 (struct.unpack_from('<I',memory,field)[0]+delta)&0xFFFFFFFF)
            for row in records:
                field=helper['base_va']-0x400000+row['offset']
                if row['kind']=='rel32':self.assertEqual(relocated[field:field+4],memory[field:field+4])

    def test_final_probe_has_crlf_ordered_chunks_and_distinct_final_identity(self):
        _parent,image,metadata,probe=synthetic_successor()
        self.assertNotIn('\n',probe.replace('\r\n',''))
        self.assertIn(metadata['candidate_sha256'],probe)
        self.assertIn(metadata['stage'],probe)
        self.assertNotIn('.echo OCEM_CONTRACT_PASS ',probe)
        self.assertTrue(metadata['probe_contract']['initial_breakpoint_required'])
        self.assertTrue(metadata['probe_contract']['relocation_aware'])
        self.assertEqual(matrix.sha(probe.encode()),metadata['probe_sha256'])
        for field,value in (('schema',matrix.SCHEMA),('stage',matrix.stage('modalwidgets')),('candidate_sha256','0'*64)):
            changed=deepcopy(metadata);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):tool.render_probe(image,changed)
        for field in ('runtime_executed','manual_input_proof','promotion_ready','predecessor_probe_reusable'):
            self.assertIs(metadata[field],False)
        # An unaligned read after a HIGHLOW must stop at each contiguous
        # section edge; PEImage.file_offset deliberately requires one section.
        view=pe.inspect_pe(image)
        for checked in metadata['probe_contract']['checked_ranges']:
            start,end=checked['rva'],checked['rva']+checked['bytes']
            if start>=view.headers_size:
                self.assertEqual(sum(section.rva<=start and end<=section.rva+section.raw_size
                                     for section in view.sections if section.raw_offset),1)

    def test_inherited_hooks_prefixes_tail_and_highlow_conflicts_fail_closed(self):
        parent,metadata=synthetic_parent()
        framed,army_metadata,_modal=inherited_parts(dict(metadata,base_candidate=metadata['base_candidate']))
        lower_hook=army_metadata['army_contracts']['composition']['hooks'][1]['va']
        sites=(framed['entry_vas']['framed_input.pixel_guard'],lower_hook,
               metadata['code_va'],metadata['admission']['hook'])
        view=pe.inspect_pe(parent)
        for va in sites:
            changed=bytearray(parent);changed[view.file_offset(va-view.image_base,1)]^=1
            altered=deepcopy(metadata);altered['candidate_sha256']=matrix.sha(changed)
            with self.subTest(va=hex(va)),self.assertRaises(ValueError):
                tool._upgrade_verified_parent(bytes(changed),altered,'modalwidgets','1920x1080')
        old_table,old_fields=pe._old_relocations(parent,view)
        gate=framed['entry_vas']['framed_input.pixel_guard.minimap_clear']-view.image_base+24
        altered=deepcopy(metadata);altered['highlow_count']+=1
        with patch.object(pe,'_old_relocations',return_value=(old_table,tuple(sorted((*old_fields,gate))))),self.assertRaises(ValueError):
            tool._upgrade_verified_parent(parent,altered,'modalwidgets','1920x1080')
        altered=deepcopy(metadata);altered['highlow_count']-=1
        with self.assertRaises(ValueError):tool._upgrade_verified_parent(parent,altered,'modalwidgets','1920x1080')

    def test_source_inventory_paths_and_linked_ancestors_are_rejected(self):
        sources={matrix.SOURCE:matrix.sha((ROOT/matrix.SOURCE).read_bytes())}
        source=ROOT/matrix.SOURCE;original_is_symlink=Path.is_symlink
        for linked in (source,source.parent):
            with self.subTest(path=str(linked)),patch.object(Path,'is_symlink',
                    lambda path:True if path==linked else original_is_symlink(path)),self.assertRaises(ValueError):
                tool.source_hashes(sources)
        for name in ('../escape.py','src\\patcher\\framed_input.py',str(source)):
            with self.subTest(name=name),self.assertRaises(ValueError):tool._source_path(name)

    def test_required_machine_cli_missing_source_and_synthetic_selection_are_explicit(self):
        module=sys.modules[__name__]
        with patch.multiple(module,ORIGINAL=ORIGINAL,TOOLCHAIN=TOOLCHAIN,REQUIRE_MACHINE=REQUIRE_MACHINE,SYNTHETIC_ONLY=SYNTHETIC_ONLY), \
                patch.object(sys,'argv',[__file__,'--require-machine-tools']),redirect_stderr(io.StringIO()), \
                patch.object(tool,'build_candidate') as build:
            with self.assertRaises(SystemExit) as error:main()
        self.assertEqual(error.exception.code,2);build.assert_not_called()


class CLITests(unittest.TestCase):
    def fixture(self):
        temporary=tempfile.TemporaryDirectory(prefix='clash-smallworld-source-fixture-')
        self.addCleanup(temporary.cleanup)
        root=Path(temporary.name).resolve()
        original=root/'original.bin';original.write_bytes(b'Artificial original; never executable')
        output=root/'new-output'/'candidate.exe'
        return original,output

    @staticmethod
    def fake_bundle():
        metadata=dict(stage='artificial-validation',profile='modalwidgets',resolution='1920x1080',
                      candidate_sha256=matrix.sha(b'Artificial non-executable fixture'),runtime_executed=False,
                      manual_input_proof=False,promotion_ready=False,
                      source_hashes={tool.SOURCE:matrix.sha((ROOT/tool.SOURCE).read_bytes())})
        return b'Artificial non-executable fixture',metadata,'.echo artificial\r\n'

    def test_reserve_threshold_headroom_and_invalid_payload_fail_closed(self):
        _original,output=self.fixture()
        for free,payload in ((100,0),(101,1),(500,400)):
            with self.subTest(free=free,payload=payload),patch.object(cli.shutil,'disk_usage',
                    return_value=SimpleNamespace(total=1000,free=free)),self.assertRaisesRegex(ValueError,'reserve'):
                cli.disk_preflight(output,payload)
        for payload in (-1,True,1.5):
            with self.subTest(payload=payload),self.assertRaises(ValueError):cli.disk_preflight(output,payload)
        with patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(total=1000,free=501)):
            cli.disk_preflight(output,400)
        self.assertFalse(output.parent.exists())

    def test_initial_low_disk_prevents_builder_and_mkdir(self):
        original,output=self.fixture()
        with patch.object(cli,'checked_output',return_value=output),patch.object(cli.shutil,'disk_usage',
                return_value=SimpleNamespace(total=1000,free=100)),patch.object(tool,'build_candidate') as build, \
                self.assertRaisesRegex(ValueError,'reserve'):
            cli.write_candidate(original,output,'modalwidgets','1920x1080')
        build.assert_not_called();self.assertFalse(output.parent.exists())

    def test_bundle_headroom_after_build_prevents_any_output(self):
        original,output=self.fixture();before=original.read_bytes()
        with patch.object(cli,'checked_output',return_value=output),patch.object(pe,'ORIGINAL_SHA256',matrix.sha(before)), \
                patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(total=1000,free=500)), \
                patch.object(tool,'build_candidate',return_value=self.fake_bundle()) as build, \
                self.assertRaisesRegex(ValueError,'reserve'):
            cli.write_candidate(original,output,'modalwidgets','1920x1080')
        build.assert_called_once();self.assertFalse(output.parent.exists());self.assertEqual(original.read_bytes(),before)

    def test_existing_bundle_member_and_original_destination_prevent_builder(self):
        for member in ('exe','candidate.json','cdb','original'):
            original,output=self.fixture();target=original if member=='original' else output
            path=target if member in ('exe','original') else target.with_suffix('.'+member)
            path.parent.mkdir(parents=True,exist_ok=True)
            if member!='original':path.write_bytes(b'Retained artificial fixture')
            before=original.read_bytes()
            with patch.object(cli,'checked_output',return_value=target),patch.object(tool,'build_candidate') as build, \
                    patch.object(cli,'_original') as read_original,patch.object(cli.complete,'_write_bundle') as write_bundle, \
                    self.assertRaises(FileExistsError):cli.write_candidate(original,target,'modalwidgets','1920x1080')
            build.assert_not_called();read_original.assert_not_called();write_bundle.assert_not_called()
            self.assertEqual(original.read_bytes(),before)

    def test_invalid_path_links_and_unknown_original_prevent_builder_and_write(self):
        original,output=self.fixture()
        for path in (ROOT/'forbidden.exe',output.with_suffix('.txt')):
            with self.subTest(path=str(path)),self.assertRaises(ValueError):cli.checked_output(path)
        original_is_symlink=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda path:True if path==original else original_is_symlink(path)), \
                self.assertRaisesRegex(ValueError,'symbolic links'):cli._plain_path(original)
        with patch.object(cli,'checked_output',return_value=output),patch.object(cli.shutil,'disk_usage',
                return_value=SimpleNamespace(total=100000,free=50000)),patch.object(tool,'build_candidate') as build, \
                patch.object(cli.complete,'_write_bundle') as write_bundle,self.assertRaises(ValueError):
            cli.write_candidate(original,output,'modalwidgets','1920x1080')
        build.assert_not_called();write_bundle.assert_not_called();self.assertFalse(output.parent.exists())

    def test_original_changed_during_build_is_rejected_before_mkdir_or_write(self):
        original,output=self.fixture();before=original.read_bytes()
        def build(*_args):
            original.write_bytes(before+b' changed during artificial build')
            return self.fake_bundle()
        with patch.object(cli,'checked_output',return_value=output),patch.object(pe,'ORIGINAL_SHA256',matrix.sha(before)), \
                patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(total=100000,free=50000)), \
                patch.object(tool,'build_candidate',side_effect=build),patch.object(cli.complete,'_write_bundle') as writer, \
                self.assertRaises(ValueError):cli.write_candidate(original,output,'modalwidgets','1920x1080')
        writer.assert_not_called();self.assertFalse(output.parent.exists())

    def test_preflight_has_no_output_and_source_replacement_is_rejected(self):
        original,output=self.fixture();before=original.read_bytes()
        with patch.object(pe,'ORIGINAL_SHA256',matrix.sha(before)),patch.object(tool,'build_candidate',return_value=self.fake_bundle()), \
                patch.object(cli.complete,'_write_bundle') as writer, \
                redirect_stdout(io.StringIO()):
            cli.main(['--original',str(original),'--profile','modalwidgets','--resolution','1920x1080','--preflight'])
        writer.assert_not_called();self.assertFalse(output.parent.exists())
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            cli.main(['--original',str(original),'--profile','modalwidgets','--resolution','1920x1080','--preflight','--output',str(output)])
        bundle=self.fake_bundle();bundle[1]['source_hashes'][tool.SOURCE]='0'*64
        with patch.object(cli,'checked_output',return_value=output),patch.object(pe,'ORIGINAL_SHA256',matrix.sha(before)), \
                patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(total=100000,free=50000)), \
                patch.object(tool,'build_candidate',return_value=bundle),self.assertRaisesRegex(ValueError,'source changed'):
            cli.write_candidate(original,output,'modalwidgets','1920x1080')
        self.assertFalse(output.parent.exists());self.assertEqual(original.read_bytes(),before)


class CPUAssertions:
    def execute(self,kind='ordinary',*,delta=0,flags=0xED7,**options):
        machine=Machine(self.image,self.metadata,delta=delta,**options)
        result=machine.run(kind,flags)
        if kind in ('ordinary','army'):
            self.assertTrue(result['preserved'],(kind,options,result))
            self.assertEqual(result['writes'],[],(kind,options))
            self.assertTrue(result['heap_unchanged'],(kind,options))
            self.assertEqual(result['calls'][0],('native_click',machine.BUTTON))
            self.assertEqual(result['result'],int(scalar_click(machine.width,machine.height,kind,options)),(kind,options,result))
        elif result['returned']:
            self.assertTrue(result['preserved'],(kind,options,result))
        return result

    def test_integrated_ordinary_dormant_single_squad_and_private_owned_multi_squad(self):
        for delta in (0,0x2000000):
            for flags in (0x202,0xED7):
                for world in ((1,1),(10,10),(10,60),(60,10),(60,60)):
                    for kind,extra in (('ordinary',dict(owner=0,selected=0,count=1)),
                                       ('ordinary',dict(owner=1,count=2)),('army',dict(owner=1,count=2))):
                        with self.subTest(delta=delta,world=world,kind=kind,owner=extra['owner']):
                            result=self.execute(kind,delta=delta,flags=flags,world_width=world[0],world_height=world[1],**extra)
                            self.assertEqual(result['result'],1)
                            if kind=='army' or extra['owner']==1:self.assertIn('native_count',[row[0] for row in result['calls']])

    def test_world_cells_frame_backing_minimap_action_bar_and_stale_scroll(self):
        w,h=map(int,self.metadata['resolution'].split('x'))
        cases=[dict(x=31,y=24),dict(x=40,y=15),dict(x=w-32,y=24),dict(x=40,y=h-16),
               dict(x=96,y=24,world_width=1,world_height=1),dict(x=40,y=80,world_width=1,world_height=1),
               dict(x=w-224,y=h-80,world_width=60,world_height=60),
               dict(x=w-246,y=16,minimap_enabled=True,world_width=60,world_height=60),
               dict(x=w-247,y=16,minimap_enabled=True,world_width=60,world_height=60),
               dict(scroll_x=1,world_width=10),dict(scroll_x=-1),dict(scroll_y=1,world_height=10),
               dict(world_width=0),dict(world_height=101),dict(x=-1),dict(y=-1),
               dict(x=80,y=48,shift=1),dict(x=0xFFFFFFFF,shift=31)]
        for kind,owner in (('ordinary',0),('ordinary',1),('army',1)):
            for case in cases:
                with self.subTest(kind=kind,owner=owner,case=case):self.execute(kind,owner=owner,**case)
        for kind in ('ordinary','army'):
            for x,y in ((32,h-82),(418,h-17),(419,h-82),(32,h-83)):
                with self.subTest(kind=kind,point=(x,y)):
                    self.execute(kind,owner=1,x=x,y=y,world_width=60,world_height=60)

    def test_resolution_derived_bottom_partial_row_stays_inside_real_world(self):
        width,height=map(int,self.metadata['resolution'].split('x'))
        full_x,full_y=(width-64)//64,(height-32)//64
        ceil_x,ceil_y=(width-64+63)//64,(height-32+63)//64
        self.assertGreater((height-32)%64,0)
        self.assertEqual(ceil_y,full_y+1)
        for kind,owner in (('ordinary',0),('army',1)):
            for world_height,y,allowed in ((ceil_y,height-17,1),(full_y,height-17,0),
                                           (ceil_y,height-16,0)):
                with self.subTest(kind=kind,world_height=world_height,y=y):
                    result=self.execute(kind,owner=owner,x=width-225,y=y,
                                        world_width=ceil_x,world_height=world_height)
                    self.assertEqual(result['result'],allowed)

    def test_native_click_precedes_null_context_and_unapproved_army_owners_reject(self):
        for kind in ('ordinary','army'):
            result=self.execute(kind,owner=1,click=0,null_game=True)
            self.assertEqual(result['calls'],[('native_click',Machine.BUTTON)])
        self.assertEqual(self.execute('army',owner=1,count=10)['result'],1)
        cases=(dict(owner=0),dict(owner=2),dict(owner=1,count=1),dict(owner=1,count=10,bad_slot=9),
               dict(owner=1,player=4),dict(owner=1,unit_owner=1),dict(owner=1,prior=4),
               dict(owner=1,unit_offset=1),dict(owner=1,selected=500),dict(owner=1,squad_type=35),
               dict(owner=1,state_value=1),dict(owner=1,state_value=1,state_offset=8),
               dict(owner=1,state_value=1,state_offset=36),dict(owner=1,state_value=1,state_offset=52),
               dict(owner=1,state_value=1,state_offset=56),dict(owner=1,unit_x=10))
        for case in cases:
            with self.subTest(case=case):self.assertEqual(self.execute('army',**case)['result'],0)

    def test_bounded_camera_clamp_validates_both_dimensions_before_writing(self):
        result=self.execute('admit_world',world_width=1,world_height=1,scroll_x=0x7FFFFFFF,scroll_y=-1)
        self.assertEqual((result['result'],result['scroll']),(2,(0,0)))
        self.assertEqual({address for address,_size,_value in result['writes']},{Machine.GD+0x222E8,Machine.GD+0x222EC})
        for case in (dict(world_width=0),dict(world_height=101)):
            result=self.execute('admit_world',scroll_x=7,scroll_y=8,**case)
            self.assertEqual((result['result'],result['scroll'],result['writes']),(0,(7,8),[]))

    def test_bounded_renderer_owned_admission_and_all_failure_restoration(self):
        for owner in (0,1):
            for fail in (None,'cell','draw_frame','compose_panel','present_map_rect'):
                with self.subTest(owner=owner,fail=fail):
                    result=self.execute('bounded_full',owner=owner,fail=fail,scroll_x=99,scroll_y=-1)
                    self.assertEqual(result['result'],int(fail is None))
                    self.assertEqual(result['scroll'],(0,0))
                    self.assertEqual((result['vtable'],result['render']),(clip.MEMORY_VTABLE,0x12345000))
                    allowed={Machine.GD+0x222E8,Machine.GD+0x222EC,Machine.SURFACE+0xB8,clip.RENDER_DEVICE_GLOBAL}
                    self.assertLessEqual({address for address,_size,_value in result['writes']},allowed)
        for case in (dict(owner=2),dict(owner=1,unit_owner=1),dict(surface_width=640),dict(post=1)):
            result=self.execute('bounded_full',scroll_x=7,scroll_y=8,**case)
            self.assertEqual((result['result'],result['scroll'],result['writes']),(0,(7,8),[]))

    def test_actual_dispatches_route_fitting_world_and_clamp_small_world(self):
        for kind in ('full_redraw','initial_paint'):
            normal=self.execute(kind,world_width=60,world_height=60,scroll_x=99,scroll_y=-1)
            fw,fh=(int(self.metadata['resolution'].split('x')[0])-64)//64,(int(self.metadata['resolution'].split('x')[1])-32)//64
            self.assertEqual((normal['route'],normal['scroll']),(kind+'.native_continuation',(60-fw,0)))
            small=self.execute(kind,world_width=1,world_height=1,scroll_x=99,scroll_y=-1)
            self.assertEqual(small['scroll'],(0,0))
            if kind=='full_redraw':self.assertEqual((small['result'],small['returned']),(1,True))
            else:self.assertEqual(small['route'],kind+'.native_continuation')
        for kind in ('full_redraw','initial_paint'):
            result=self.execute(kind,world_width=0,scroll_x=7,scroll_y=8)
            self.assertEqual((result['result'],result['writes'],result['scroll']),(0,[],(7,8)))


class SyntheticCPUTests(CPUAssertions,unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:require_machine_tools()
        except ImportError:
            if REQUIRE_MACHINE:raise AssertionError('--require-machine-tools requires Unicorn')
            raise unittest.SkipTest('Unicorn unavailable; use --toolchain or --require-machine-tools')
        cls.parent,cls.image,cls.metadata,_=synthetic_successor(probe=False)

    def test_802_partial_last_pixels_have_real_world_cells_and_reject_outside_world(self):
        _parent,image,metadata,_=synthetic_successor('completehd','802x602',probe=False)
        fw,fh=(802-64)//64,(602-32)//64
        for kind,owner in (('ordinary',0),('army',1)):
            for x,y in ((769,300),(400,585),(770,300),(400,586)):
                case=dict(owner=owner,x=x,y=y,world_width=fw+1,world_height=fh+1)
                result=Machine(image,metadata,**case).run(kind)
                self.assertEqual(result['result'],int(scalar_click(802,602,kind,case)))
                self.assertTrue(result['preserved']);self.assertEqual(result['writes'],[])
            result=Machine(image,metadata,owner=owner,x=769,y=300,world_width=fw,world_height=fh).run(kind)
            self.assertEqual(result['result'],0)


class OriginalCPUTests(CPUAssertions,unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if ORIGINAL is None:raise unittest.SkipTest('--source-exe required; original-backed CPU integration not run')
        try:require_machine_tools()
        except ImportError:
            if REQUIRE_MACHINE:raise AssertionError('--require-machine-tools requires Unicorn')
            raise unittest.SkipTest('Unicorn unavailable; use --toolchain or --require-machine-tools')
        cls.original=Path(ORIGINAL).read_bytes()
        cls.image,cls.metadata,cls.probe=tool.build_candidate(cls.original,'modalwidgets','1920x1080')
        cls.parent=restore_parent(cls.image,cls.metadata)

    def test_actual_source_original_parent_helper_and_scope_identities(self):
        self.assertEqual(matrix.sha(self.original),pe.ORIGINAL_SHA256)
        self.assertEqual(self.metadata['schema'],'clash95_complete_small_world_candidate_v1')
        self.assertEqual(self.metadata['recipe_revision'],'complete_small_world_v1')
        self.assertEqual(self.metadata['stage'],matrix.stage('modalwidgets').removesuffix('-validation')+'-smallworld-validation')
        self.assertEqual(matrix.sha(self.parent),self.metadata['base_candidate_sha256'])
        self.assertEqual(self.metadata['base_candidate']['schema'],matrix.SCHEMA)
        self.assertEqual(matrix.sha(self.image),self.metadata['candidate_sha256'])
        self.assertEqual(matrix.sha(self.probe.encode()),self.metadata['probe_sha256'])
        self.assertEqual(Path(ORIGINAL).read_bytes(),self.original)
        for source,digest in self.metadata['source_hashes'].items():
            self.assertEqual(matrix.sha((ROOT/source).read_bytes()),digest)
        for name in ('runtime_executed','manual_input_proof','promotion_ready','predecessor_probe_reusable'):
            self.assertIs(self.metadata[name],False)


def restore_parent(image,metadata):
    restored=bytearray(image)
    for row in reversed(metadata['edits']):
        offset=row['offset'];old=bytes.fromhex(row['old_hex']);new=bytes.fromhex(row['new_hex'])
        if restored[offset:offset+len(new)]!=new:raise ValueError('declared successor bytes differ')
        if not old:
            if offset+len(new)!=len(restored):raise ValueError('unreported appended bytes')
            del restored[offset:]
        else:restored[offset:offset+len(new)]=old
    parent=bytes(restored)
    if matrix.sha(parent)!=metadata['base_candidate_sha256']:raise ValueError('exact matrix parent SHA differs')
    return parent


def main():
    global ORIGINAL,TOOLCHAIN,REQUIRE_MACHINE,SYNTHETIC_ONLY
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-exe',type=Path)
    parser.add_argument('--toolchain',type=Path)
    parser.add_argument('--require-machine-tools',action='store_true')
    parser.add_argument('--synthetic-only',action='store_true')
    args,remaining=parser.parse_known_args()
    if args.synthetic_only and args.source_exe is not None:parser.error('--synthetic-only cannot use --source-exe')
    if args.require_machine_tools and not args.synthetic_only and args.source_exe is None:
        parser.error('--require-machine-tools requires --source-exe or --synthetic-only')
    ORIGINAL,TOOLCHAIN,REQUIRE_MACHINE,SYNTHETIC_ONLY=args.source_exe,args.toolchain,args.require_machine_tools,args.synthetic_only
    if TOOLCHAIN:sys.path.insert(0,str(TOOLCHAIN))
    if REQUIRE_MACHINE:
        try:require_machine_tools()
        except ImportError:parser.error('--require-machine-tools requires Unicorn')
    if SYNTHETIC_ONLY:
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                                 for cls in (PortableTests,CLITests,SyntheticCPUTests))
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
    unittest.main(argv=[sys.argv[0],*remaining],verbosity=2)


if __name__=='__main__':main()

