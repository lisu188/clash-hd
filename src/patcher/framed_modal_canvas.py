"""Emit an uninstalled, owned native canvas for the framed castle lifecycle.

No image or process is written. The caller must separately install all six
hooks and allocate STATE_SIZE zero bytes in a mapped RW section. Code is RX.
Native background loading requires a real640 stride; changing a header on an
HD allocation is deliberately not this contract. Primary-only modal overlays
and natural/manual input remain separate from the physical-memory mirror.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import struct

from . import partial_tile_clip as clip
from . import pe_extension as pe
from .framed_viewport import FramedViewport

STATE_SIZE = 128
STATE = dict(phase=0, physical=4, native=8, saved_render=12, root_esp=16,
             owner_tid=20, enter_status=24, mirror_status=28, leave_status=32,
             fault=36, allocations=40, frees=44, mirrors=48,
             pending_header=52, pending_pixels=56, native_pixels=60,
             physical_pixels=64)
MAP = 0x5202E0
RENDER = 0x511230
PRIMARY = 0x51D4C0
HOOK_OWNER = 0x5199D8
MEMORY_VTABLE = 0x50EE24
PRIMARY_VTABLE = 0x50EEC4
THREAD_IAT = 0x4EA4E8
ALLOC = 0x473FF0
FREE = 0x4740DD
BASE_CTOR = 0x401E00
DTOR = 0x403E50
NATIVE_PIXELS = 640 * 480
SITES = (("root_entry",0x422180,5),("overview_draw",0x422020,5),
         ("full_blit",0x401E30,5),("overview_wrapper",0x51B6D0,6),
         ("action_wrapper",0x51BC20,6),("leave_before_map",0x4224B2,5))


@dataclass(frozen=True)
class ModalCanvasBundle(clip.AdapterBundle):
    hook_sites: tuple[pe.HookPatch, ...] = ()
    state_va: int = 0
    state_size: int = STATE_SIZE
    state_offsets: dict[str,int] = field(default_factory=dict)
    observer_vas: dict[str,int] = field(default_factory=dict)
    candidate_sha256: str = ""
    source_contract: dict = field(default_factory=dict)


def _read(image: bytes, va: int, size: int) -> bytes:
    offset=clip.file_offset(image,va,size)
    return image[offset:offset+size]


def _verify(original: bytes, candidate: bytes, width: int, height: int) -> dict:
    clip.verify_original(original)
    # Reconstruct only existing frozen builders. No guessed identity or new
    # recipe is accepted from selected matching byte spans alone.
    from tools import build_framed_candidate as builder
    matched=[]
    for minimap in (False,True):
        image,metadata,_=builder.build_candidate(original,f"{width}x{height}",minimap_viewport=minimap)
        if image==candidate:matched.append((minimap,metadata))
    if len(matched)!=1:raise ValueError("exact existing framed candidate reconstruction required")
    checks={0x422180:"5351525657",0x422020:"5351525657",
            0x4224B2:"e88988feff",0x401E00:"83c008c740fc00000000668950f8668958fae839140700",
            0x4057D0:"015004c3",0x461C70:"e968240100",
            0x403E50:"535189c189d3f6c3047533",0x473FF0:"5351525657060fa00fa85583ec04",
            0x4740DD:"5351525689c685c00f84f1000000",
            0x4224C4:"83c4205d5f5e5a595bc3",0x42286B:"83c4205d5f5e5a595bc3"}
    spans=[]
    for va,value in checks.items():
        expected=bytes.fromhex(value)
        if _read(original,va,len(expected))!=expected or _read(candidate,va,len(expected))!=expected:
            raise ValueError(f"native canvas ABI differs at{va:08x}")
        spans.append(dict(va=va,length=len(expected),hex=value))
    action_pointer=_read(candidate,0x435DAA,5)
    if action_pointer[0]!=0xBB:raise ValueError('old action callback binding differs')
    action_va=struct.unpack_from('<I',action_pointer,1)[0]
    if action_va not in (0x51316F,0x51BC20):raise ValueError('unknown original/relocated action wrapper')
    for va,target in ((0x51B6D0,0x422020),(action_va,0x435B90)):
        expected=b'\x60\xe8'+struct.pack('<i',target-va-6)
        if _read(candidate,va,6)!=expected:raise ValueError("old centering wrapper prerequisite differs")
    if _read(candidate,0x401E30,5)!=b'\xe9'+struct.pack('<i',0x4E9920-0x401E35):
        raise ValueError("old native/HD blitter prerequisite differs")
    # Import directory names, rather than an assumed host DLL address, bind TID.
    data=pe.inspect_pe(original)
    rva,size=struct.unpack_from('<II',original,data.optional_offset+96+8)
    start=data.file_offset(rva,size);found=[]
    for pos in range(start,start+size,20):
        oft,stamp,chain,name,iat=struct.unpack_from('<5I',original,pos)
        if not any((oft,stamp,chain,name,iat)):break
        index=0
        while True:
            entry=struct.unpack_from('<I',original,data.file_offset((oft or iat)+4*index,4))[0]
            if not entry:break
            if not entry & 0x80000000:
                off=data.file_offset(entry+2,1);end=original.index(0,off)
                if original[off:end]==b'GetCurrentThreadId':found.append(0x400000+iat+4*index)
            index+=1
    if found!=[THREAD_IAT]:raise ValueError("native thread identity import differs")
    return dict(minimap_viewport=matched[0][0],native_spans=spans,old_action_wrapper_va=action_va,
                primary_only_layers_proven=False,manual_input_proof=False,
                all_six_hooks_required=True,zero_initialized_rw_state_required=True,
                supported_root_return_vas=[0x4224CD,0x422874],
                restore_before_map_call_va=0x4224B2,
                limitation="Unknown reentry/ownership or process-terminating failure is not successful cleanup.")


def emit_modal_canvas(original: bytes, candidate: bytes, *, base_va: int,
                      state_va: int, width: int, height: int) -> ModalCanvasBundle:
    """Prepare six indivisible hooks and explicit RX code/RW state metadata.

    Public try_enter(EAX=root entry ESP), mirror(), try_leave(EAX=exit-hook
    entry ESP) return0/1 and preserve non-EAX GPRs, EFLAGS and caller ESP.
    All mutations require the owner OS thread. A failed active-state check
    latches fault and never frees/copies through an unverified pointer.
    Root entry replays five native PUSHes; observer metadata replaces the old
    post-first-PUSH debugger contract. The root exit is a CALL hook which
    restores/frees then tail-calls native40AD40, preserving its return value.
    """
    layout=FramedViewport(width,height)
    if type(base_va) is not int or type(state_va) is not int or not 0x10000<=base_va<0x7FFE0000:
        raise ValueError("invalid explicit code/state allocation")
    if state_va!=base_va+0x20000 or state_va%4096 or base_va%4096:
        raise ValueError("state must be a separate aligned RW page at code+128KiB")
    contract=_verify(original,candidate,width,height)
    a=clip._Assembler(base_va);observers={}
    def absolute(value,purpose):a.absolute(value,purpose)
    def call(va,purpose):
        a.emit('e8');p=len(a.code);a.relocations.append(clip.Relocation(p,'rel32',va,purpose));a.u32(va-base_va-p-4)
    def jump(va,purpose):
        a.emit('e9');p=len(a.code);a.relocations.append(clip.Relocation(p,'rel32',va,purpose));a.u32(va-base_va-p-4)
    def st(name):return state_va+STATE[name]
    def load(name):a.emit('a1');absolute(st(name),'state.'+name)
    def store(name):a.emit('a3');absolute(st(name),'state.'+name)
    def imm(name,value):a.emit('c705');absolute(st(name),'state.'+name);a.u32(value)
    def inc(name):a.emit('ff05');absolute(st(name),'state.'+name)
    def cmp_state(name,value):a.emit('813d');absolute(st(name),'state.'+name);a.u32(value)
    def mov_abs(reg,value,purpose):a.emit(f'{0xb8+reg:02x}');absolute(value,purpose)
    def read_abs(reg,address,purpose):
        a.emit('8b'+f'{(reg<<3)|5:02x}');absolute(address,purpose)
    def write_abs(reg,address,purpose):
        a.emit('89'+f'{(reg<<3)|5:02x}');absolute(address,purpose)
    def thread():a.emit('ff15');absolute(THREAD_IAT,'GetCurrentThreadId IAT')
    def result(value):a.emit('c744241c');a.u32(value);a.emit('619dc3')
    def header(reg,w,h,reject):
        # reg=ESI or EDI, exact existing constructed memory object.
        a.emit(f'85{0xc0+reg*9:02x}');a.branch('0f84',reject)
        a.emit('6681'+f'{0x38+reg:02x}'+struct.pack('<H',w).hex());a.branch('0f85',reject)
        a.emit('6681'+f'{0x78+reg:02x}'+'02'+struct.pack('<H',h).hex());a.branch('0f85',reject)
        a.emit('83'+f'{0x78+reg:02x}'+'0400');a.branch('0f84',reject)
        a.emit('81'+f'{0xb8+reg:02x}'+'b8000000');absolute(MEMORY_VTABLE,'native memory vtable');a.branch('0f85',reject)
    def primary(reject):
        read_abs(6,PRIMARY,'primary dimensions')
        a.emit('81fe');a.u32(width|(height<<16));a.branch('0f85',reject)
        a.emit('813d');absolute(PRIMARY+0xB8,'primary vtable field');absolute(PRIMARY_VTABLE,'primary vtable');a.branch('0f85',reject)
        a.emit('833d');absolute(PRIMARY+0xD4,'primary depth');a.emit('08');a.branch('0f85',reject)
        read_abs(6,PRIMARY+0xBC,'primary backend');a.emit('85f6');a.branch('0f84',reject)
        a.emit('83bea400000000');a.branch('0f84',reject)
    def valid_active(reject):
        thread();a.emit('3b05');absolute(st('owner_tid'),'state.owner_tid');a.branch('0f85',reject)
        read_abs(6,st('physical'),'state.physical');header(6,width,height,reject)
        read_abs(7,st('native'),'state.native');header(7,640,480,reject)
        # The authenticated nonallocating member constructor set +AC to null.
        # This private memory canvas never acquires a COM interface to release.
        a.emit('83bfac00000000');a.branch('0f85',reject)
        a.emit('3b3d');absolute(MAP,'map surface');a.branch('0f85',reject)
        a.emit('39fe');a.branch('0f84',reject)
        a.emit('8b56043b15');absolute(st('physical_pixels'),'state.physical_pixels');a.branch('0f85',reject)
        a.emit('8b4f043b0d');absolute(st('native_pixels'),'state.native_pixels');a.branch('0f85',reject)
        # Exact entered/allocated pointers, nonwrapping half-open intervals,
        # and disjoint ownership before any copying or native destruction.
        a.emit('89d005');a.u32(width*height);a.branch('0f82',reject)
        a.emit('89cb81c3');a.u32(NATIVE_PIXELS);a.branch('0f82',reject)
        a.emit('39c1');a.branch('0f83',reject+'.disjoint')
        a.emit('39da');a.branch('0f82',reject)
        a.label(reject+'.disjoint')
        primary(reject)

    a.label('try_enter');a.emit('9c60')
    imm('enter_status',0);cmp_state('phase',0);a.branch('0f85','enter.reentry')
    cmp_state('fault',0);a.branch('0f85','enter.reject')
    read_abs(6,MAP,'map surface');header(6,width,height,'enter.reject')
    a.emit('813d');absolute(HOOK_OWNER,'render owner');absolute(0x40AD40,'ordinary map owner');a.branch('0f85','enter.reject')
    for address in (clip.LOWER_ROW_OWNER_GLOBAL,clip.POST_TILE_CALLBACK_GLOBAL):
        a.emit('833d');absolute(address,'lower/post callback prerequisite');a.emit('00');a.branch('0f85','enter.reject')
    primary('enter.reject')
    thread();a.emit('85c0');a.branch('0f84','enter.reject')
    read_abs(6,MAP,'map surface');read_abs(7,RENDER,'render device')
    a.emit('39f7');a.branch('0f84','enter.render_ok')
    a.emit('81ff');absolute(PRIMARY,'physical primary');a.branch('0f85','enter.reject')
    a.label('enter.render_ok')
    # Stage all resources privately; no game-global pointer has changed.
    a.emit('b8bc000000');call(ALLOC,'nonfatal header allocation');a.emit('85c0');a.branch('0f84','enter.reject');store('pending_header')
    a.emit('b8');a.u32(NATIVE_PIXELS);call(ALLOC,'nonfatal pixel allocation');a.emit('85c0');a.branch('0f84','enter.rollback');store('pending_pixels')
    a.emit('89c731c0b9');a.u32(NATIVE_PIXELS//4);a.emit('fcf3ab')
    load('pending_header');a.emit('ba80020000bbe0010000');call(BASE_CTOR,'native nonallocating base constructor')
    read_abs(2,st('pending_pixels'),'state.pending_pixels');a.emit('895004c780b8000000');absolute(MEMORY_VTABLE,'native memory vtable');store('native')
    load('pending_pixels');store('native_pixels')
    read_abs(0,MAP,'map surface');store('physical');a.emit('8b4004');store('physical_pixels')
    read_abs(0,RENDER,'render device');store('saved_render')
    a.emit('8b44241c');store('root_esp');thread();store('owner_tid')
    load('native');write_abs(0,MAP,'map surface');write_abs(0,RENDER,'render device')
    imm('pending_header',0);imm('pending_pixels',0);imm('phase',1);imm('enter_status',1);imm('leave_status',0);inc('allocations');result(1)
    a.label('enter.rollback');load('pending_header');call(FREE,'rollback unconstructed header');imm('pending_header',0);imm('pending_pixels',0)
    a.branch('e9','enter.reject')
    a.label('enter.reentry');imm('fault',5)
    a.label('enter.reject');result(0)

    a.label('mirror');a.emit('9c60');imm('mirror_status',0);cmp_state('phase',1);a.branch('0f85','mirror.inactive')
    valid_active('mirror.reject')
    # Actual independent row strides, no native allocator/callback and no
    # primary/backbuffer scratch. Zero all physical pixels, then copy640 rows.
    read_abs(7,st('physical'),'state.physical');a.emit('8b7f0489fb31c0b9');a.u32(width*height//4);a.emit('fcf3ab')
    a.emit('b9');a.u32(width*height%4);a.emit('f3aa')
    a.emit('89df81c7');a.u32(((height-480)//2)*width+(width-640)//2)
    read_abs(6,st('native'),'state.native');a.emit('8b7604ba e0010000')
    a.label('mirror.row');a.emit('b9a0000000f3a581c7');a.u32(width-640);a.emit('4a');a.branch('0f85','mirror.row')
    imm('mirror_status',1);inc('mirrors');result(1)
    a.label('mirror.reject');imm('fault',2)
    a.label('mirror.inactive');result(0)

    a.label('try_leave');a.emit('9c60');imm('leave_status',0);cmp_state('phase',1);a.branch('0f85','leave.inactive')
    valid_active('leave.reject')
    load('root_esp');a.emit('83e83c3b44241c');a.branch('0f85','leave.reject')
    # Restore borrowed globals BEFORE destruction and BEFORE native map draw.
    load('physical');write_abs(0,MAP,'map surface');load('saved_render');write_abs(0,RENDER,'render device')
    load('native');imm('phase',0);imm('native',0);a.emit('ba02000000');call(DTOR,'owned scalar memory-surface destruction')
    for name in ('physical','saved_render','root_esp','owner_tid','native_pixels','physical_pixels'):imm(name,0)
    imm('leave_status',1);inc('frees');result(1)
    a.label('leave.reject');imm('fault',3)
    a.label('leave.inactive');result(0)

    # Selection helper for wrapper paths. It never allocates or changes
    # pointers. Invalid active state remains failed; outside uses old code.
    a.label('is_active');a.emit('9c60');cmp_state('phase',1);a.branch('0f85','active.no')
    valid_active('active.bad');result(1)
    a.label('active.bad');imm('fault',4)
    a.label('active.no');result(0)
    def select(active,inactive):
        a.emit('9c60');a.branch('e8','is_active');a.emit('85c0');a.branch('0f84',inactive)
        a.emit('619d');a.branch('e9',active)
    a.label('root_entry');a.emit('9c608d442424');a.branch('e8','try_enter');a.emit('619d5351525657')
    observers['root_after_replayed_pushes']=base_va+len(a.code);jump(0x422185,'root native continuation')
    a.label('overview_draw');select('draw.active','draw.fallback.saved')
    a.label('draw.fallback.saved');a.emit('619d');a.branch('e9','draw.native')
    a.label('draw.active');a.branch('e8','draw.native');a.emit('9c60');a.branch('e8','mirror');a.emit('619d')
    observers['overview_after_native_draw']=base_va+len(a.code);a.emit('c3')
    a.label('draw.native');a.emit('5351525657');jump(0x422025,'native overview body')
    a.label('full_blit');a.emit('9c60');read_abs(0,st('native'),'state.native');a.emit('3b44241c');a.branch('0f85','blit.done')
    a.branch('e8','mirror');a.label('blit.done');a.emit('619d');jump(0x4E9920,'old HD-aware primary blit')
    for name,va,target in (('overview_wrapper',0x51B6D0,0x422020),('action_wrapper',contract['old_action_wrapper_va'],0x435B90)):
        a.label(name);select(name+'.active',name+'.fallback.saved')
        a.label(name+'.fallback.saved');a.emit('619d60');call(target,name+' old first call');jump(va+6,name+' old continuation')
        a.label(name+'.active');a.emit('60');call(target,name+' native work');a.emit('61c3')
    a.label('leave_before_map');a.emit('9c608d442424');a.branch('e8','try_leave');a.emit('619d')
    observers['before_restored_map_redraw']=base_va+len(a.code);jump(0x40AD40,'native map redraw after release')
    code=a.finish()
    if len(code)>=0x20000:raise ValueError('modal code overlaps separately allocated state')
    entries={name:base_va+offset for name,offset in a.labels.items() if '.' not in name}
    sites=[]
    for name,va,length in SITES:
        if name=='action_wrapper':va=contract['old_action_wrapper_va']
        old=_read(candidate,va,length);entry=entries[name]
        opcode=b'\xe8' if name=='leave_before_map' else b'\xe9'
        new=opcode+struct.pack('<i',entry-va-5)+b'\x90'*(length-5)
        sites.append(pe.HookPatch(clip.file_offset(candidate,va,length),va-0x400000,va,old,new,
            'modal_canvas.'+name,(pe.CodeRelocation(1,'rel32',entry,'modal_canvas.'+name),)))
    bundle=ModalCanvasBundle(base_va,code,entries,tuple(a.relocations),width,height,False,
        tuple(sites),state_va,STATE_SIZE,dict(STATE),observers,hashlib.sha256(candidate).hexdigest(),contract)
    clip.absolute_relocation_offsets(bundle)
    return bundle
