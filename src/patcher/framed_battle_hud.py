"""Uninstalled tactical HUD ownership, native backing and edge-copy substrate.

These descriptors are NOT an atomic battle patch. The source-authenticated
runner entry/allocation/free hooks bind a real private640 backing to one native
battle lifetime. A mandatory external integration gate keeps field admission
closed until the HUD draw/input/presentation hook set is complete. No file or
game is run by this emitter; the original/candidate are reconstructed first.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct

from . import framed_battle_field as field_source
from . import framed_modal_canvas as native
from . import partial_tile_clip as clip
from . import pe_extension as pe
from .framed_battle_viewport import TacticalViewport

ROOT = Path(__file__).resolve().parents[2]
STATE_SIZE = 128
# Keep shared lifecycle fields at the already tested modal layout. State pages
# are separate; no code here writes the castle canvas state.
STATE = dict(native.STATE, battle=68, binds=72)
BATTLE = 0x532048
BATTLE_OWNER = 0x42E8B0
ROOT_PROLOGUE = bytes.fromhex('56575581ec9c000000')
PINNED_SOURCES = dict(field_source.PINNED_SOURCES, **{
    'src/patcher/framed_battle_field.py': '42642812d504250ca237bb765506aa73da2af66ea641daa4e3fadaaba4e6995c',
    'src/patcher/framed_modal_canvas.py': '567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054',
})
# These exact boundaries come from continuous objdump decoding from42E9E0.
SITES = {
    'root_entry': (0x42E9E0, ROOT_PROLOGUE.hex()),
    'bind_allocation': (0x42EC90, '833d4820530000'),
    'initial_frame_target': (0x42EB6E, '892d30125100'),
    'initial_widgets_target': (0x42EF71, '892d30125100'),
    'leave_before_free': (0x42F531, 'e8a74b0400'),
}


@dataclass(frozen=True)
class BattleHudBundle(clip.AdapterBundle):
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()
    state_va: int = 0
    state_size: int = STATE_SIZE
    state_offsets: dict = field(default_factory=dict)
    candidate_sha256: str = ''
    source_contract: dict = field(default_factory=dict)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    for name, expected in PINNED_SOURCES.items():
        if sha((ROOT/name).read_bytes()) != expected:
            raise ValueError('reviewed battle HUD dependency differs: '+name)
    return dict(PINNED_SOURCES)


def composition_rectangles(width, height):
    """Exact native-art copies; source/destination inclusive, no scaling.

    The initial physical clear owns inert padding. Later copies touch only
    chrome and admitted HUD slices, leaving every arena pixel unchanged.
    Mid-edge artwork repeats; corners retain their original source pixels.
    """
    layout = TacticalViewport(width, height, 20)
    rows = []
    def add(l,t,r,b,x,y): rows.append((l,t,r,b,x,y))
    # Left band including its original corners.
    add(0,0,31,15,0,0)
    for y in range(16,height-16,448):
        count=min(448,height-16-y); add(0,16,31,15+count,0,y)
    add(0,464,31,479,0,height-16)
    # The native top/bottom middle is448 pixels wide. HUD owns the right160.
    for x in range(32,width-160,448):
        count=min(448,width-160-x)
        add(32,0,31+count,15,x,0)
        add(32,464,31+count,479,x,height-16)
    # The HUD slices include top/right/bottom corner artwork. Repeat only the
    # narrow native right edge through the decorative vertical HUD gap.
    for y in range(368,height-112,352):
        count=min(352,height-112-y); add(624,16,639,15+count,width-16,y)
    for part in layout.hud_slices:
        s,d=part.source,part.destination
        add(s.left,s.top,s.right,s.bottom,d.left,d.top)
    return tuple(rows)


def integration_required():
    return {
        'initial_present': 'Replace42F2F5->51BA00 with physical frame/HUD composition and full physical->primary copy, preserving native460EA0 cursor restore.',
        'hud_stats': 'Scope430F80 E0/render to native backing; route4317EE dirty,431819 copy,431823 cursor restore and431842->4229A0 status text. Restore all borrowed globals at every return.',
        'redraw_owner': 'Route42E8B0 frame/widgets into native backing; call widened field with physical E0; compose chrome/HUD afterward. Preserve palette405020.',
        'overlay_animation': 'Route42DEFE primary render assignment and compose each42E02A->42E02D sprite draw, plus42E139 backing restoration. Do not defer all15 animation steps until function return.',
        'hover_and_input': 'Transform only admitted HUD slices for42E160 and descriptor polling. Preserve physical cursor coordinates outside scoped native input. Replace centered wrappers42E4ED/42E501.',
        'saved_views': 'Initial X writers42F208 and42F22B must use max(0,actual_columns-visible_columns); originals compute actual_columns-7 at42F5E4/42F5F7. Y remains0.',
        'atomic_build': 'Install ownership, routed drawing, field, input and presentation together under a new validation stage. Supply integration_va only after all hook/byte/relocation contracts are checked.',
    }


def emit_battle_hud(original: bytes, candidate: bytes, *, base_va: int,
                    state_va: int, width: int, height: int, integration_va: int,
                    minimap_viewport: bool = True) -> BattleHudBundle:
    """Emit helpers and five uninstalled lifecycle/target descriptors.

    try_enter(EAX=root native entryESP), try_bind(EAX=allocated battle pointer,
    EDX=runner bodyESP), try_leave(EAX=free-CALL entryESP), field_admission(),
    target_hud() and compose_chrome() return EAX0/1. Other GPRs,ESP,EFLAGS/DF
    are preserved; native calls see DF0. Phase1 owns the private HUD; phase2
    additionally binds the exact source-observed native battle allocation.
    Entry leaves game globals/pixels unchanged. Bind clears physical pixels
    once, before the first native field draw; later composition preserves them.
    integration_va must be an ABI-preserving EAX0/1 helper proving the complete
    installed split. No always-pass production helper is supplied here.
    """
    TacticalViewport(width,height,20)
    if (any(type(x) is not int for x in (base_va,state_va,integration_va)) or
            base_va%4096 or state_va!=base_va+0x20000 or
            not 0x10000<=base_va<0x7FF90000 or
            not 0x10000<=integration_va<0x7FFF0000):
        raise ValueError('explicit separate RX/RW and integration allocations required')
    if type(original) is not bytes or type(candidate) is not bytes or type(minimap_viewport) is not bool:
        raise ValueError('immutable exact images and boolean minimap required')
    clip.verify_original(original); sources=verify_sources()
    from tools import build_framed_army_candidate as builder
    expected,metadata,_=builder.build_candidate(original,f'{width}x{height}',minimap_viewport=minimap_viewport)
    if candidate!=expected: raise ValueError('whole current army candidate required')
    modal_state=metadata['base_candidate']['state_va']
    image=pe.inspect_pe(candidate)
    for va,value in SITES.values():
        if any(native._read(x,va,len(bytes.fromhex(value)))!=bytes.fromhex(value) for x in (original,candidate)):
            raise ValueError('native runner hook boundary differs')
    # Reuse exact authenticated nonallocating constructor/scalar destructor ABI.
    for va,value in ((0x401E00,'83c008c740fc00000000668950f8668958fae839140700'),
                     (0x403E50,'535189c189d3f6c3047533'),
                     (0x42F5B3,'81c49c0000005d5f5ec20400')):
        if any(native._read(x,va,len(bytes.fromhex(value)))!=bytes.fromhex(value) for x in (original,candidate)):
            raise ValueError('native backing/lifetime ABI differs')
    a=clip._Assembler(base_va)
    def absval(value,purpose): a.absolute(value,purpose)
    def st(name): return state_va+STATE[name]
    def load(name): a.emit('a1'); absval(st(name),'state.'+name)
    def store(name): a.emit('a3'); absval(st(name),'state.'+name)
    def imm(name,value): a.emit('c705');absval(st(name),'state.'+name);a.u32(value)
    def inc(name): a.emit('ff05');absval(st(name),'state.'+name)
    def cmp_state(name,value): a.emit('813d');absval(st(name),'state.'+name);a.u32(value)
    def read(reg,address,purpose): a.emit('8b'+f'{(reg<<3)|5:02x}');absval(address,purpose)
    def write(reg,address,purpose): a.emit('89'+f'{(reg<<3)|5:02x}');absval(address,purpose)
    def transfer(opcode,target,purpose):
        a.emit(opcode);pos=len(a.code);a.relocations.append(clip.Relocation(pos,'rel32',target,purpose));a.u32(target-base_va-pos-4)
    def call(target,purpose): transfer('e8',target,purpose)
    def jump(target,purpose): transfer('e9',target,purpose)
    def thread(): a.emit('ff15');absval(native.THREAD_IAT,'native thread identity IAT')
    def save(): a.emit('9c60fc')
    def result(value): a.emit('c744241c');a.u32(value);a.emit('619dc3')
    def nz(name): a.branch('0f85',name)
    def zero(name): a.branch('0f84',name)
    def header(reg,w,h,reject):
        a.emit('81'+f'{0xf8+reg:02x}'+'00000100');a.branch('0f82',reject)
        a.emit('81'+f'{0xf8+reg:02x}'+'44ffff7f');a.branch('0f87',reject)
        a.emit('f7'+f'{0xc0+reg:02x}'+'03000000');nz(reject)
        a.emit('81'+f'{0x38+reg:02x}');a.u32(w|(h<<16));nz(reject)
        a.emit('81'+f'{0xb8+reg:02x}'+'b8000000');absval(native.MEMORY_VTABLE,'native memory vtable');nz(reject)
        a.emit('8b'+f'{0x40+reg:02x}'+'043d00000100');a.branch('0f82',reject)
        a.emit('3d');a.u32(0x80000000-w*h);a.branch('0f87',reject)
    def castle_inactive(reject):
        for key in ('phase','fault','native','physical','pending_header','pending_pixels'):
            a.emit('833d');absval(modal_state+native.STATE[key],'castle state.'+key);a.emit('00');nz(reject)
    def primary(reject):
        a.emit('813d');absval(native.PRIMARY,'physical primary dimensions');a.u32(width|(height<<16));nz(reject)
        a.emit('813d');absval(native.PRIMARY+0xB8,'physical primary vtable');absval(native.PRIMARY_VTABLE,'native primary vtable');nz(reject)
        a.emit('833d');absval(native.PRIMARY+0xD4,'physical primary depth');a.emit('08');nz(reject)
    def owned(reject,bound=False):
        cmp_state('phase',2 if bound else 1)
        a.branch('0f85' if bound else '0f82',reject)
        if not bound: cmp_state('phase',2);a.branch('0f87',reject)
        cmp_state('fault',0);nz(reject)
        thread();a.emit('3b05');absval(st('owner_tid'),'state.owner_tid');nz(reject)
        castle_inactive(reject);primary(reject)
        read(6,st('physical'),'state.physical');header(6,width,height,reject)
        a.emit('3b35');absval(native.MAP,'physical E0');nz(reject)
        a.emit('3b05');absval(st('physical_pixels'),'state.physical_pixels');nz(reject)
        read(7,st('native'),'state.native');header(7,640,480,reject)
        a.emit('3b05');absval(st('native_pixels'),'state.native_pixels');nz(reject)
        a.emit('83bfac00000000');nz(reject)
        a.emit('39f7');zero(reject)
        a.emit('813d');absval(native.HOOK_OWNER,'native render owner');absval(BATTLE_OWNER,'native battle owner');nz(reject)
        if bound:
            load('battle');a.emit('3b05');absval(BATTLE,'native battle allocation');nz(reject)
        # Entered pointer identities and half-open pixel intervals must remain
        # disjoint before copying or destruction through the private object.
        read(2,st('physical_pixels'),'state.physical_pixels');a.emit('81c2');a.u32(width*height)
        read(1,st('native_pixels'),'state.native_pixels');a.emit('39d1');a.branch('0f83',reject+'.separate')
        a.emit('81c1');a.u32(640*480);a.emit('3b0d');absval(st('physical_pixels'),'state.physical_pixels');a.branch('0f87',reject)
        a.label(reject+'.separate')

    a.label('try_enter');save();imm('enter_status',0)
    cmp_state('phase',0);nz('enter.reentry');cmp_state('fault',0);nz('enter.reject')
    castle_inactive('enter.reject');primary('enter.reject')
    a.emit('833d');absval(BATTLE,'native battle allocation');a.emit('00');nz('enter.reject')
    a.emit('813d');absval(native.HOOK_OWNER,'native render owner');absval(0x40AD40,'native map owner');nz('enter.reject')
    read(6,native.MAP,'physical E0');header(6,width,height,'enter.reject')
    read(7,native.RENDER,'render device');a.emit('39f7');zero('enter.render_ok')
    a.emit('81ff');absval(native.PRIMARY,'physical primary');nz('enter.reject')
    a.label('enter.render_ok');thread();a.emit('85c0');zero('enter.reject')
    call(integration_va,'required complete battle integration');a.emit('83f801');nz('enter.reject')
    a.emit('b8bc000000');call(native.ALLOC,'nonfatal header allocation');a.emit('85c0');zero('enter.reject');store('pending_header')
    a.emit('b800b00400');call(native.ALLOC,'nonfatal pixel allocation');a.emit('85c0');zero('enter.rollback');store('pending_pixels')
    a.emit('89c731c0b9002c0100f3ab')
    load('pending_header');a.emit('ba80020000bbe0010000');call(native.BASE_CTOR,'nonallocating native base constructor')
    read(2,st('pending_pixels'),'state.pending_pixels');a.emit('895004c780b8000000');absval(native.MEMORY_VTABLE,'native memory vtable');store('native')
    load('pending_pixels');store('native_pixels');read(0,native.MAP,'physical E0');store('physical');a.emit('8b4004');store('physical_pixels')
    read(0,native.RENDER,'render device');store('saved_render');a.emit('8b44241c');store('root_esp');thread();store('owner_tid')
    imm('pending_header',0);imm('pending_pixels',0);imm('phase',1);imm('leave_status',0);imm('enter_status',1);inc('allocations');result(1)
    a.label('enter.rollback');load('pending_header');call(native.FREE,'rollback private header');imm('pending_header',0)
    a.branch('e9','enter.reject');a.label('enter.reentry');imm('fault',5)
    a.label('enter.reject');result(0)

    a.label('try_bind');save();cmp_state('phase',1);nz('bind.reject');owned('bind.reject')
    load('root_esp');a.emit('2da80000003b442414');nz('bind.reject')
    a.emit('8b44241c3b05');absval(BATTLE,'native battle allocation');nz('bind.reject')
    a.emit('3d00000100');a.branch('0f82','bind.reject');a.emit('3d84f0ff7f');a.branch('0f87','bind.reject')
    store('battle');imm('phase',2);inc('binds')
    # Native frame artwork already resides in the private backing. Clear only
    # once at the exact post-allocation boundary, before native field drawing.
    read(7,st('physical_pixels'),'state.physical_pixels');a.emit('31c0b9');a.u32(width*height//4);a.emit('f3abb9');a.u32(width*height%4);a.emit('f3aa');result(1)
    a.label('bind.reject');result(0)

    a.label('target_hud');save();owned('target.reject');load('native');write(0,native.RENDER,'render device');result(1)
    a.label('target.reject');result(0)

    a.label('field_admission');save();owned('active.reject',True)
    load('battle');a.emit('83b82003000007');nz('active.reject')
    a.emit('8b902403000083fa01');a.branch('0f82','active.reject');a.emit('83fa14');a.branch('0f87','active.reject')
    call(integration_va,'required complete battle integration');a.emit('83f801');nz('active.reject');result(1)
    a.label('active.reject');result(0)

    a.label('compose_chrome');save();owned('compose.reject',True)
    for index,(l,t,r,b,x,y) in enumerate(composition_rectangles(width,height)):
        read(6,st('native_pixels'),'state.native_pixels');a.emit('81c6');a.u32(t*640+l)
        read(7,st('physical_pixels'),'state.physical_pixels');a.emit('81c7');a.u32(y*width+x)
        a.emit('ba');a.u32(b-t+1);a.label('copy.'+str(index))
        a.emit('b9');a.u32(r-l+1);a.emit('f3a481c6');a.u32(640-(r-l+1));a.emit('81c7');a.u32(width-(r-l+1));a.emit('4a');nz('copy.'+str(index))
    imm('mirror_status',1);inc('mirrors');result(1)
    a.label('compose.reject');result(0)

    a.label('try_leave');save();imm('leave_status',0);owned('leave.reject',True)
    load('root_esp');a.emit('2dac0000003b44241c');nz('leave.reject')
    load('saved_render');write(0,native.RENDER,'render device')
    load('native');imm('phase',0);imm('native',0);a.emit('ba02000000');call(native.DTOR,'owned private backing destructor')
    for key in ('physical','physical_pixels','native_pixels','saved_render','owner_tid','root_esp','battle'):imm(key,0)
    imm('leave_status',1);inc('frees');result(1)
    a.label('leave.reject');result(0)

    a.label('root_entry');a.emit('9c608d442424');a.branch('e8','try_enter');a.emit('619d');a.emit(ROOT_PROLOGUE.hex());jump(0x42E9E9,'native root continuation')
    a.label('bind_allocation');a.emit('9c608d542424');read(0,BATTLE,'native battle allocation');a.branch('e8','try_bind');a.emit('619d833d');absval(BATTLE,'native battle allocation');a.emit('00');jump(0x42EC97,'native allocation predicate continuation')
    for key,va in (('initial_frame_target',0x42EB6E),('initial_widgets_target',0x42EF71)):
        a.label(key);a.emit('9c60');a.branch('e8','target_hud');a.emit('83f801');zero(key+'.done')
        a.emit('892d');absval(native.RENDER,'native render fallback')
        a.label(key+'.done');a.emit('619d');jump(va+6,'native '+key+' continuation')
    a.label('leave_before_free');a.emit('9c608d442424');a.branch('e8','try_leave');a.emit('619d');jump(native.FREE,'native battle allocation free')
    code=a.finish()
    if len(code)>=0x20000 or base_va<=integration_va<state_va+STATE_SIZE:
        raise ValueError('code/state/integration allocations overlap')
    entries={key:base_va+offset for key,offset in a.labels.items() if '.' not in key}
    hooks=[];removed=[]
    for key,(va,value) in SITES.items():
        old=bytes.fromhex(value);target=entries[key];op=b'\xe8' if key=='leave_before_free' else b'\xe9'
        new=op+struct.pack('<i',target-va-5)+b'\x90'*(len(old)-5)
        hooks.append(pe.HookPatch(clip.file_offset(candidate,va,len(old)),va-0x400000,va,old,new,'battle HUD '+key,
            (pe.CodeRelocation(1,'rel32',target,key),)))
        removed.extend(va-0x400000+x for x in clip._original_highlow_fields(original,va,len(old)))
    contract=dict(revision='framed_battle_hud_substrate_v1',source_sha256=metadata['source_sha256']|sources,
        root_prologue=ROOT_PROLOGUE.hex(),root_body_esp_delta=-168,free_call_esp_delta=-172,
        native_root_return=0x42F5BC,native_root_stack_cleanup=4,modal_state_va=modal_state,
        integration_va=integration_va,composition_rectangles=composition_rectangles(width,height),
        integration_required=integration_required(),preserves_native_art_scale=True,
        repeat_draw_does_not_clear_field=True,installed=False,runtime_executed=False,
        pixels_verified=False,input_proof=False,promotion_ready=False)
    bundle=BattleHudBundle(base_va,code,entries,tuple(a.relocations),width,height,
        hook_sites=tuple(hooks),removed_highlow_rvas=tuple(removed),state_va=state_va,
        state_offsets=dict(STATE),candidate_sha256=sha(candidate),source_contract=contract)
    clip.absolute_relocation_offsets(bundle);verify_sources();return bundle
