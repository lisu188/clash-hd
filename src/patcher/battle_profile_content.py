"""Uninstalled, body-site tactical content reads with a separate status ABI.

These helpers are not native MOV replacements. They emit no replay, hooks,
continuation cancellation, clipping, provider validation or acceptance.
"""
from __future__ import annotations

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
SOURCE = "src/patcher/battle_profile_content.py"
LEASE = "src/patcher/battle_profile_stack_lease.py"
FIELD = "src/patcher/battle_profile_field_v2.py"
CONTEXT = "src/patcher/battle_profile_context.py"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
LEASE_SHA256 = "47d6ad4931aef39b58919dff4b22b41cce76b0abf39267237a704471331f834c"
PINNED_SOURCES = {
    LEASE: LEASE_SHA256,
    FIELD: "673a2170f77dc143a1d62745bf5879f23163e9cbcffa3f5549123c4cc81f8cbf",
    "src/patcher/battle_profile_field.py": "c329460fc7289d11ac10ddc33d26eb5ad158169ca976fee41ccd32fba6d97c88",
    "src/patcher/battle_profile_routing.py": "838d371bf837ab0098420e5589abc07d446a22bd6daa25ecab683e4725e25972",
    "src/patcher/battle_profile_lifecycle.py": "dccb907b09d002691cad679219942ac5a8ffcb2798af4c96b0b1768dbd9e9f44",
    CONTEXT: "be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/framed_battle_viewport.py": "8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6",
    "src/patcher/framed_battle_coordinates.py": "b67900d7399e0ce807d88a261c97942598beebfc28e2d78774cd109098f95142",
    "src/patcher/framed_battle_field.py": "f690865e615db65d02e8c59b5c43e0cfbaa1e371dd6502441d16e0d270a7196d",
    "src/patcher/framed_modal_canvas.py": "567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054",
    "src/patcher/framed_battle_hud.py": "3a6cb61a2ec2fcd0fa9c52c09a96e11a9a2d9f75cac6e3a2e826d5caa98a3ee3",
}
HELPER_BYTES, FIELD_BYTES, LEASE_BYTES, ROOT_STACK_BOUND = 640, 1280, 192, 0x10000
THREAD_IAT = 0x4EA4E8
FAMILIES = ("tile", "unit", "adjacent", "vertical", "count")
BODY_SP = dict(tile=-68, unit=-64, adjacent=-16, vertical=-8, count=-28)
TILE_UNIT_RETURNS = (0x4303B1,0x43041C,0x430491,0x4304F5,0x430531,
    0x43059B,0x43060F,0x43067E,0x4306E8,0x430AAA)
ADJACENT_UNIT_RETURNS = (0x42FCC4,0x42FD58,0x42FDF9,0x42FEFC,
    0x42FF20,0x42FF54,0x42FF75,0x42FFA4)
VERTICAL_RETURNS = (0x430389,0x4303FA,0x43046F,0x4304C8,0x43056E,0x4305ED,0x43065C,0x4306BB)
NEIGHBORS = ((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
# VA, exact whole operand, family, operation, first/second neighbor delta.
# The value/status helper ABI differs deliberately from these native destinations.
SITES = (
    (0x43026F,"0fbf8441fe050000","tile","occupant",0,0),
    (0x430375,"0fbfbc47fc050000","tile","occupant",0,-1),
    (0x4303E7,"0fbfbc42fc050000","tile","occupant",-1,-1),
    (0x430459,"0fbfbc4200060000","tile","occupant",1,1),
    (0x4304B4,"0fbfbc42fe050000","tile","occupant",-1,0),
    (0x43055A,"0fbfbc4100060000","tile","occupant",0,1),
    (0x4305DA,"0fbfbc4200060000","tile","occupant",-1,1),
    (0x430649,"0fbfbc41fc050000","tile","occupant",1,-1),
    (0x4306A7,"0fbfbc42fe050000","tile","occupant",1,0),
    (0x4302B4,"0fbf840154030000","tile","type",0,0),
    (0x43050A,"0fbf840154030000","tile","type",0,0),
    (0x42F7CF,"0fbf840154030000","vertical","type",0,0),
    (0x42F84A,"0fbf8254030000","unit","unit_type",0,0),
    (0x42F9AF,"668b8258030000","unit","coordinate",4,0),
    (0x42F9C3,"668b825a030000","unit","coordinate",6,0),
    (0x42F9D7,"0fbf80fe050000","unit","occupant",0,0),
    (0x42F9EC,"8a9956030000","unit","owner",0,0),
    (0x42FC5F,"0fbf840254030000","adjacent","type",0,0),
    (0x42FC92,"0fbf8468fc050000","adjacent","occupant",0,-1),
    (0x42FCEA,"0fbf846800060000","adjacent","occupant",0,1),
    (0x42FD26,"0fbf846afe050000","adjacent","occupant",-1,0),
    (0x42FD7F,"0fbf846afe050000","adjacent","occupant",1,0),
    (0x42FDC0,"0fbf846afc050000","adjacent","occupant",-1,-1),
    (0x42FE23,"0fbf846a00060000","adjacent","occupant",-1,1),
    (0x42FE68,"0fbf846afc050000","adjacent","occupant",1,-1),
    (0x42FEBB,"0fbf846800060000","adjacent","occupant",1,1),
    (0x426F44,"0fbf8c59fe050000","count","occupant",0,0),
    (0x426F54,"8a941156030000","count","owner",0,0),
)
NATIVE_SPANS = {
    "vertical": (0x42F7C0,0x42F7E8,"82e9165b68b4db486eda8a8e0a0a81e1cd9f48b6d22964f0c4b9f3ae5e8922e9"),
    "adjacent": (0x42FC30,0x42FFB0,"fa35bb975c69093e4a0e0af71943d54edbb12af250821f4b462b0dae4052dfc8"),
    "count": (0x426EF0,0x426F75,"a97ca326a029c59233d0e8881e5eed3004c8e168d24fd7248a5a78c48c65cf90"),
}
PROLOGUES = ((0x42FFB0,"535156575589e583ec308945f88955fc"),
    (0x42F820,"56575589e583ec3489c6"),
    (0x42FC30,"56575583ec0489042489d589de89cf"),
    (0x42F7C0,"515289c2"),(0x426EF0,"53515256575583ec0489c7"))
EXTRA_CALLS = tuple((pc,0x42F7C0) for pc in VERTICAL_RETURNS)+((0x42F95B,0x426EF0),
    (0x426F95,0x426EF0),(0x431D7A,0x426EF0))

@dataclass(frozen=True)
class CodeEmission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int
    private_entries: tuple

@dataclass(frozen=True)
class BattleProfileContentBundle:
    emission: CodeEmission
    lease_bundle: object
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)

def _require(condition,message):
    if not condition:
        raise ValueError(message)

def _sha(data):
    return hashlib.sha256(data).hexdigest()

def _snapshot():
    _require(Path(__file__).resolve() == ROOT/SOURCE,"canonical content source required")
    result={}
    for name,digest in dict(PINNED_SOURCES,**{SOURCE:None}).items():
        path=ROOT/name
        _require(path.resolve(strict=True) == path and path.is_relative_to(ROOT),"canonical content dependency required")
        before=path.stat(); data=path.read_bytes(); after=path.stat()
        stamp=lambda row:(row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns)
        _require(stamp(before) == stamp(after) and (digest is None or _sha(data) == digest),
                 "pinned content source differs: "+name)
        result[name]=(data,stamp(after))
    return result

@contextmanager
def _modules(snapshot):
    prefix="_clash95_battle_content_"+uuid.uuid4().hex
    saved_path=list(sys.path)
    try:
        for suffix in ("",".src",".src.patcher"):
            module=types.ModuleType(prefix+suffix); module.__path__=[]
            sys.modules[module.__name__]=module
            if suffix:
                parent,_,leaf=module.__name__.rpartition("."); setattr(sys.modules[parent],leaf,module)
        result={}
        for stem in ("framed_viewport","pe_extension","partial_tile_clip","framed_battle_viewport",
                     "framed_battle_coordinates","framed_battle_field","framed_modal_canvas",
                     "framed_battle_hud","battle_profile_context","battle_profile_lifecycle",
                     "battle_profile_routing","battle_profile_field","battle_profile_field_v2",
                     "battle_profile_stack_lease","battle_profile_content"):
            name="src/patcher/"+stem+".py"; full=prefix+".src.patcher."+stem
            module=types.ModuleType(full); module.__file__=str(ROOT/name); module.__package__=full.rpartition(".")[0]
            module.__loaded_source_sha256__=_sha(snapshot[name][0]); sys.modules[full]=module
            setattr(sys.modules[module.__package__],stem,module)
            exec(compile(snapshot[name][0],module.__file__,"exec"),module.__dict__); result[name]=module
        yield result
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix+"."):del sys.modules[name]
        sys.path[:]=saved_path

def _layout(plan,parent):
    _require(type(plan) is dict and plan.get("allocation_plan_only") is True and plan.get("battle_installed") is False,
             "uninstalled content plan required")
    profile,resolution=plan['profile'],plan['resolution']
    _require(profile in ("classic","framed","completehd","modalwidgets") and type(resolution) is str,
             "fixed content selectors required")
    width,height=map(int,resolution.split('x'))
    _require(resolution == f"{width}x{height}" and (width,height) in ((800,600),(1024,768),(1280,720),(1280,960),
        (1366,768),(1920,1080),(2560,1440),(3440,1440),(3840,2160)),"canonical content preset required")
    rx,state=plan['rx']['va'],plan['rw']['va']
    _require(type(rx) is type(state) is int and rx%4096 == 0 and state%4 == 0 and
        plan['rx']['virtual_reservation'] == 0x20000 and plan['rw']['used_bytes'] == 128 and
        plan['rw']['page_bytes'] == 4096 and plan['rx']['characteristics'] == 0x60000020 and
        plan['rw']['characteristics'] == 0xC0000040 and rx-plan['rx']['rva'] == 0x400000,
        "unchanged content allocation required")
    _require((profile in ('classic','framed') and state == rx+0x20000 and plan['rw']['page_offset'] == 0 and
              plan['rw']['allocation'] == 'fresh_zero_page') or
             (profile in ('completehd','modalwidgets') and (state-256)%4096 == 0 and plan['rw']['page_offset'] == 256 and
              plan['rw']['allocation'] == 'reserved_existing_modal_page'),"content state ownership differs")
    _require(type(parent.code) is bytes and 0 < len(parent.code) < 0x20000 and rx <= parent.base_va and
        parent.base_va%16 == 0 and parent.base_va+len(parent.code) < rx+0x20000 and parent.state_va == state and
        (parent.width,parent.height) == (width,height) and type(parent.entries) is tuple and
        type(parent.private_entries) is tuple and type(parent.field_return_pcs) is tuple and
        type(parent.lease_return_pcs) is tuple,"matching immutable lease required")
    names=('leased_draw_full','leased_draw_incremental','check_tile','check_unit','check_adjacent',
           'check_tracking_effect','check_charge_effect','check_sprite','check_line','guarded_sprite','guarded_line')
    _require(tuple(dict(parent.entries)) == names and len(parent.entries) == len(names) and
        tuple(dict(parent.private_entries)) == ('discover_and_check','check_fixed_receipt') and
        all(type(v) is int and parent.base_va <= v < parent.base_va+len(parent.code)
            for _,v in parent.entries+parent.private_entries),"canonical lease entries required")
    calls=[]; offsets=set()
    for row in parent.relocations:
        _require(row.offset not in offsets and 0 <= row.offset <= len(parent.code)-4,"lease relocation inventory differs")
        offsets.add(row.offset)
        if row.kind == 'abs32':_require(struct.unpack_from('<I',parent.code,row.offset)[0] == row.target,"lease absolute operand differs")
        else:
            _require(row.kind == 'rel32' and row.offset > 0 and parent.code[row.offset-1] == 0xE8 and
                parent.base_va+row.offset+4+struct.unpack_from('<i',parent.code,row.offset)[0] == row.target,
                "lease CALL operand differs")
            if row.purpose == 'private authenticated V2 complete receipt':calls.append(row.target)
    _require(len(calls) == 1 and rx <= calls[0] < parent.base_va and
        tuple(mode for mode,_ in parent.field_return_pcs) == (0,1) and
        tuple(mode for mode,_ in parent.lease_return_pcs) == (0,1) and
        all(rx <= pc < parent.base_va for _,pc in parent.field_return_pcs) and
        all(parent.base_va <= pc < parent.base_va+len(parent.code) for _,pc in parent.lease_return_pcs),
        "fixed field and lease receipts required")
    return rx,state,width,height,calls[0]

def _emit_code(plan,lease_emission,*,assembler_module):
    """Pure fixture boundary. EAX=value, EDX=0 denied/1 valid/2 fault.

    Incoming EAX survives every rejection. No native instruction is replayed.
    Future adapters must preserve each original full/subregister destination
    and handle status before a native continuation; none is installed here.
    """
    parent=lease_emission
    rx,state,width,height,field_check=_layout(plan,parent)
    base=(parent.base_va+len(parent.code)+15)&~15
    a=assembler_module._Assembler(base); private_calls=[]
    SITE,KIND,NATIVE_S,TILE_S,UNIT_S,FIELD_EBP,LEASE_EBP,ROOT_ESP,MODE=200,204,208,212,216,220,224,228,232
    ROWS,ROW_COUNT,WORLD,X,Y,INDEX,EA=240,368,372,376,380,384,388
    INPUT=400
    offsets={0:28,1:24,2:20,3:16,4:12,5:8,6:4,7:0}
    def address(value,purpose):a.absolute(value,purpose)
    def imm(reg,value):a.emit(f'{0xB8+reg:02x}');a.u32(value)
    def mem(op,reg,bas,off):
        a.emit(op+f'{0x80|(reg<<3)|bas:02x}')
        if bas == 4:a.emit('24')
        a.u32(off)
    def get(reg,off):mem('8b',reg,5,off)
    def put(reg,off):mem('89',reg,5,off)
    def load(reg,bas,off=0):mem('8b',reg,bas,off)
    def match(reg,off):mem('3b',reg,5,off)
    def cmp(reg,value):a.emit(f'81{0xF8+reg:02x}');a.u32(value)
    def cmpva(reg,value,purpose):a.emit(f'81{0xF8+reg:02x}');address(value,purpose)
    def add(reg,value):a.emit(f'81{0xC0+reg:02x}');a.u32(value)
    def ne(label):a.branch('0f85',label)
    def eq(label):a.branch('0f84',label)
    def jump(label):a.branch('e9',label)
    def read(reg,va,purpose):a.emit('8b'+f'{5|(reg<<3):02x}');address(va,purpose)
    def call(target,purpose):
        a.emit('e8');at=len(a.code);a.relocations.append(assembler_module.Relocation(at,'rel32',target,purpose));a.u32(target-base-at-4)
    def own(label):
        a.emit('e8');at=len(a.code);a.u32(0);a.fixups.append((at,label));private_calls.append((at,label))
    def extent(reg,count,reject):
        a.emit(f'f7{0xC0+reg:02x}03000000');ne(reject)
        get(2,ROOT_ESP);a.emit('89d1');add(1,-ROOT_STACK_BOUND)
        a.emit(f'39{0xC8+reg:02x}');a.branch('0f82',reject)
        a.emit(f'89{0xC0|(reg<<3):02x}');add(0,count);a.branch('0f82',reject)
        a.emit('39d0');a.branch('0f87',reject)
    def record(reg,count,reject):
        _require(reg == 7 and 0 < count <= 12 and count%4 == 0,'fixed stack receipt span required')
        imm(3,count);own('capture_stack');cmp(0,1);ne(reject)
    def returns(reg,values,label):
        for value in values:cmpva(reg,value,'fixed native body ancestry return PC');eq(label)
    def operand(row):
        raw=bytes.fromhex(row[1]);start=2 if raw[:2] == b'\x0f\xbf' else 2 if raw[0] == 0x66 else 1
        modrm=raw[start];bas=modrm&7;pos=start+1
        if bas == 4:
            sib=raw[pos];pos+=1;bas=sib&7;index=(sib>>3)&7;scale=sib>>6
            get(0,INPUT+offsets[bas]);get(1,INPUT+offsets[index]);a.emit('c1e1'+f'{scale:02x}'+'01c8')
        else:get(0,INPUT+offsets[bas])
        add(0,struct.unpack_from('<i',raw,pos)[0]);put(0,EA)
    def result(status):
        imm(2,status);jump('finish_valid' if status == 1 else 'finish_rejected')
    for number,row in enumerate(SITES):
        va,raw,family,op,dx,dy=row;name=f'site_{va:06x}'
        a.label(name);a.emit('9c60fc81ec');a.u32(HELPER_BYTES);a.emit('89e5')
        own('capture_inputs')
        imm(0,number);put(0,SITE);imm(0,FAMILIES.index(family));put(0,KIND)
        a.emit('89e8');add(0,HELPER_BYTES+36);put(0,NATIVE_S)
        own('admit_body');cmp(0,1);ne(name+'.denied')
        operand(row);get(7,WORLD)
        if op == 'occupant':
            if family in ('tile','adjacent'):
                get(6,TILE_S);load(0,6,-28);add(0,dx);put(0,X);load(0,6,-24);add(0,dy);put(0,Y)
            elif family == 'unit':
                get(6,UNIT_S);load(0,6,-64);put(0,X)
                get(0,EA);a.emit('29f8');add(0,-1534);get(1,X);a.emit('6bc92829c8')
                a.emit('a901000000');ne(name+'.fault');a.emit('d1f8');put(0,Y)
            else:
                get(0,INPUT+24);a.emit('29f8');a.emit('85c0');a.branch('0f88',name+'.outside')
                a.emit('31d2b928000000f7f1');a.emit('85d2');ne(name+'.fault');put(0,X)
                get(0,INPUT+16);put(0,Y)
            # Geometry was compared by the full current receipt; these bounds
            # precede every occupancy/unit/type/owner payload read.
            get(0,X);a.emit('85c0');a.branch('0f88',name+'.outside');load(1,7,804)
            a.emit('39c8');a.branch('0f83',name+'.outside')
            get(2,Y);a.emit('85d2');a.branch('0f88',name+'.outside');load(1,7,800)
            a.emit('39ca');a.branch('0f83',name+'.outside')
            get(0,X);a.emit('6bc028');get(2,Y);a.emit('8d0450');a.emit('01f8');add(0,1534);match(0,EA);ne(name+'.fault')
            a.emit('0fbf00');cmp(0,0xFFFFFFFF);eq(name+'.valid');cmp(0,22);a.branch('0f83',name+'.fault')
        else:
            if op == 'owner' and family == 'count':
                get(0,INPUT+24);a.emit('31d2b91f000000f7f1');a.emit('85d2');ne(name+'.fault')
            elif op == 'owner':get(0,INPUT+28)
            elif op == 'coordinate':
                get(6,UNIT_S);load(0,6,-28);a.emit('31d2b91f000000f7f1');a.emit('85d2');ne(name+'.fault')
            elif family == 'unit':get(0,INPUT+4)
            elif family == 'vertical':get(0,INPUT+20)
            elif family == 'adjacent':read(0,0x512360,'native active moving-unit index')
            else:get(6,TILE_S);load(0,6,-44)
            cmp(0,22);a.branch('0f83',name+'.fault');put(0,INDEX);a.emit('6bc01f01f8')
            offset=854 if op == 'owner' else 852+dx if op == 'coordinate' else 852
            add(0,offset);match(0,EA);ne(name+'.fault')
            if op == 'owner':a.emit('0fb600')
            elif op == 'coordinate':
                a.emit('0fb700');load(1,7,804 if dx == 4 else 800)
                a.emit('39c8');a.branch('0f83',name+'.fault')
            else:
                a.emit('0fbf00')
                if op == 'unit_type':cmp(0,0xFFFFFFFF);eq(name+'.valid')
                cmp(0,35);a.branch('0f83',name+'.fault')
        a.label(name+'.valid');result(1)
        if op == 'occupant':a.label(name+'.outside');imm(0,0xFFFFFFFF);result(1)
        a.label(name+'.fault');result(2)
        a.label(name+'.denied');result(0)

    # Only outer helper paths jump here, after every private CALL returned.
    # The common epilogue never consumes a private helper's return address.
    a.label('finish_rejected');get(0,INPUT+28)
    a.label('finish_valid');put(0,464);put(2,468)
    # Restore this helper's owned PUSHFD/PUSHAD receipt even if a modeled
    # callback altered a saved input slot. Native ancestor return slots are
    # never repaired or used for an unchecked unwind.
    for off in range(0,36,4):get(0,INPUT+off);put(0,HELPER_BYTES+off)
    get(0,464);put(0,HELPER_BYTES+28);get(2,468);put(2,HELPER_BYTES+20)
    a.emit('81c4');a.u32(HELPER_BYTES);a.emit('619dc3')
    a.label('capture_inputs')
    for off in range(0,36,4):get(0,HELPER_BYTES+off);put(0,INPUT+off)
    a.emit('c3')
    a.label('capture_stack')
    # Only authenticated body admission calls this private EBP-relative
    # helper. Every failure returns0 locally with its CALL still balanced.
    put(7,456);put(3,472)
    a.emit('f7c703000000');ne('capture_stack.reject')
    get(2,ROOT_ESP);a.emit('89d1');add(1,-ROOT_STACK_BOUND)
    a.emit('39cf');a.branch('0f82','capture_stack.reject')
    a.emit('89f801d8');a.branch('0f82','capture_stack.reject')
    a.emit('39d0');a.branch('0f87','capture_stack.reject')
    a.label('capture_stack.word');load(0,7,0);get(1,ROW_COUNT);cmp(1,16);a.branch('0f83','capture_stack.reject')
    a.emit('8db4cd');a.u32(ROWS);mem('89',7,6,0);mem('89',0,6,4)
    add(1,1);put(1,ROW_COUNT);add(7,4);a.emit('83eb04');ne('capture_stack.word')
    get(7,456);imm(0,1);a.emit('c3')
    a.label('capture_stack.reject');get(7,456);a.emit('31c0c3')
    a.label('admit_body');reject='admit.reject'
    read(0,state,'content fixed owner phase');cmp(0,2);ne(reject)
    read(0,state+36,'content fixed owner fault');a.emit('85c0');ne(reject)
    read(0,state+16,'content fixed owning root');put(0,ROOT_ESP)
    a.emit('a903000000');ne(reject);cmp(0,ROOT_STACK_BOUND);a.branch('0f86',reject)
    cmp(0,0x7FFF0000);a.branch('0f83',reject)
    a.emit('89ef');add(7,-16);extent(7,HELPER_BYTES+56,reject)
    get(7,NATIVE_S);extent(7,4,reject)
    imm(0,0);put(0,ROW_COUNT)
    put(0,UNIT_S);put(0,EA)
    # The CALL at a native operand site is a FUTURE adapter contract. The
    # original instruction remains unmodified by this preparation.
    for number,(va,raw,family,op,dx,dy) in enumerate(SITES):
        get(0,SITE);cmp(0,number);ne(f'site_receipt.next.{number}')
        load(0,7,0);cmpva(0,va+5,'fixed proposed body CALL return PC');ne(reject)
        jump('site_receipt.matched');a.label(f'site_receipt.next.{number}')
    jump(reject)
    a.label('site_receipt.matched');record(7,4,reject)
    for number,family in enumerate(FAMILIES):
        get(0,KIND);cmp(0,number);ne(f'body_delta.next.{number}')
        get(7,NATIVE_S);add(7,4-BODY_SP[family]);put(7,NATIVE_S)
        jump('ancestry.'+family);a.label(f'body_delta.next.{number}')
    jump(reject)
    a.label('ancestry.count')
    record(7,4,reject);get(7,NATIVE_S);load(0,7,0);cmpva(0,0x42F95B,'draw-only native Count caller');ne(reject)
    a.emit('89f9');add(1,56);get(0,INPUT+8);a.emit('39c8');ne(reject)
    add(7,-24);record(7,4,reject);get(7,NATIVE_S);load(0,7,-24);a.emit('89f9');add(1,56);a.emit('39c8');ne(reject)
    # Input pointer authority is numeric; no record payload is read here.
    get(0,INPUT+0);put(0,INDEX)
    get(7,NATIVE_S);add(7,68);jump('ancestry.unit')
    a.label('ancestry.vertical')
    record(7,4,reject);get(7,NATIVE_S);load(0,7,0);returns(0,VERTICAL_RETURNS,'vertical.tile');jump(reject)
    a.label('vertical.tile');add(7,72);jump('ancestry.tile')
    a.label('ancestry.unit')
    put(7,UNIT_S);record(7,4,reject)
    get(7,UNIT_S);add(7,-64);record(7,4,reject)
    get(7,UNIT_S);add(7,-28);record(7,4,reject)
    get(7,UNIT_S)
    load(0,7,0);returns(0,TILE_UNIT_RETURNS,'unit.tile');returns(0,ADJACENT_UNIT_RETURNS,'unit.adjacent');jump(reject)
    a.label('unit.tile');add(7,-12);record(7,4,reject);get(7,UNIT_S);add(7,76);jump('ancestry.tile')
    a.label('unit.adjacent');add(7,-12);record(7,4,reject);get(7,UNIT_S);add(7,24);jump('ancestry.adjacent')
    a.label('ancestry.adjacent')
    put(7,EA);record(7,4,reject);get(7,EA);load(0,7,0);cmpva(0,0x4302DC,'native Adjacent Tile caller');ne(reject)
    add(7,-16);record(7,4,reject);get(7,EA)
    add(7,-12);record(7,4,reject);get(7,EA);add(7,72);jump('ancestry.tile')
    a.label('ancestry.tile')
    put(7,TILE_S);record(7,4,reject);get(7,TILE_S);load(0,7,0)
    cmpva(0,parent.field_return_pcs[0][1],'canonical full field Tile return PC');eq('tile.full')
    cmpva(0,parent.field_return_pcs[1][1],'canonical incremental field Tile return PC');ne(reject)
    imm(0,1);jump('tile.mode');a.label('tile.full');imm(0,0)
    a.label('tile.mode');put(0,MODE);get(7,TILE_S);add(7,4);put(7,FIELD_EBP);extent(7,FIELD_BYTES+40,reject)
    get(7,TILE_S);add(7,-28);record(7,12,reject)
    get(7,TILE_S);load(0,7,-20);get(1,FIELD_EBP);a.emit('39c8');ne(reject)
    get(7,FIELD_EBP);add(7,1132);record(7,8,reject)
    get(7,TILE_S);get(6,FIELD_EBP)
    load(0,7,-28);load(1,6,1132);a.emit('39c8');ne(reject)
    load(0,7,-24);load(1,6,1136);a.emit('39c8');ne(reject)
    get(0,SITE);cmp(0,9);eq('tile.index.receipt');cmp(0,10);ne('tile.index.done')
    a.label('tile.index.receipt');get(7,TILE_S);add(7,-44);record(7,4,reject)
    a.label('tile.index.done')
    # Distinguish saved caller EBP from actual live EBP at each body family.
    get(0,KIND);cmp(0,0);eq('ebp.tile');cmp(0,1);eq('ebp.unit');cmp(0,2);eq('ebp.adjacent');cmp(0,3);eq('ebp.tile')
    get(7,UNIT_S);add(7,-12);jump('ebp.compare')
    a.label('ebp.tile');get(7,TILE_S);add(7,-20);jump('ebp.compare')
    a.label('ebp.unit');get(7,UNIT_S);add(7,-12);jump('ebp.compare')
    a.label('ebp.adjacent');get(7,TILE_S);load(7,7,-24)
    a.label('ebp.compare');get(0,INPUT+8);a.emit('39f8');ne(reject)
    # Verify original caller EBP slots separately, including Unit via Adjacent.
    get(0,UNIT_S);a.emit('85c0');eq('unit.saved.done')
    a.emit('89c7');load(0,7,0);returns(0,TILE_UNIT_RETURNS,'unit.saved.tile')
    get(6,TILE_S);load(1,6,-24);jump('unit.saved.compare')
    a.label('unit.saved.tile');get(1,TILE_S);add(1,-20)
    a.label('unit.saved.compare');load(0,7,-12);a.emit('39c8');ne(reject)
    a.label('unit.saved.done')
    get(0,EA);a.emit('85c0');eq('adjacent.saved.done')
    a.emit('89c7');load(0,7,-16);get(6,TILE_S);load(1,6,-28);a.emit('39c8');ne(reject)
    load(0,7,-12);get(1,TILE_S);add(1,-20);a.emit('39c8');ne(reject)
    a.label('adjacent.saved.done')
    get(7,FIELD_EBP);load(0,7,FIELD_BYTES+8);put(0,LEASE_EBP)
    a.emit('89f9');add(1,FIELD_BYTES+40);a.emit('39c8');ne(reject)
    a.emit('89c7');extent(7,LEASE_BYTES+40,reject)
    for off,value in ((0,0x534C4231),(4,1),(8,LEASE_BYTES)):
        load(0,7,off);cmp(0,value);ne(reject)
    load(0,7,12);cmpva(0,parent.base_va,'fixed lease source VA');ne(reject)
    load(0,7,16);cmpva(0,parent.base_va+len(parent.code),'fixed lease source end');ne(reject)
    load(0,7,20);match(0,ROOT_ESP);ne(reject)
    load(0,7,24);read(1,state+20,'fixed content owner thread');a.emit('39c8');ne(reject);a.emit('85c0');eq(reject)
    get(6,FIELD_EBP);load(1,6,20);a.emit('39c8');ne(reject)
    load(0,7,28);a.emit('89f1');add(1,FIELD_BYTES+36);a.emit('39c8');ne(reject)
    load(0,7,36);a.emit('89f9');add(1,LEASE_BYTES+36);a.emit('39c8');ne(reject)
    load(0,7,60);load(1,7,LEASE_BYTES+36);a.emit('39c8');ne(reject)
    load(0,7,64);load(1,7,LEASE_BYTES+8);a.emit('39c8');ne(reject)
    load(0,7,40);match(0,MODE);ne(reject)
    get(0,MODE);a.emit('85c0');eq('lease.mode.full');a.emit('b9');address(parent.lease_return_pcs[1][1],'fixed lease field return PC');jump('lease.mode.compare')
    a.label('lease.mode.full');a.emit('b9');address(parent.lease_return_pcs[0][1],'fixed lease field return PC')
    a.label('lease.mode.compare')
    load(0,7,32);a.emit('39c8');ne(reject);load(0,6,FIELD_BYTES+36);a.emit('39c8');ne(reject)
    load(0,7,44);a.emit('85c0');ne(reject);load(0,7,52);load(1,7,56);a.emit('39c8');ne(reject)
    cmp(0,0x10000);a.branch('0f83',reject);load(0,7,48);cmp(0,1);a.branch('0f87',reject)
    for off in range(68,LEASE_BYTES,4):load(0,7,off);a.emit('85c0');ne(reject)
    for off in range(0,LEASE_BYTES,4):load(0,7,off);put(0,off)
    own('fixed_receipt');cmp(0,1);ne(reject)
    a.emit('fcff15');address(THREAD_IAT,'fixed content owning ThreadId callback')
    match(0,24);ne(reject)
    own('fixed_receipt');cmp(0,1);ne(reject)
    get(7,LEASE_EBP)
    for off in range(0,LEASE_BYTES,4):load(0,7,off);match(0,off);ne(reject)
    for off in (LEASE_BYTES+36,LEASE_BYTES+8):
        load(0,7,off);match(0,60 if off == LEASE_BYTES+36 else 64);ne(reject)
    get(7,FIELD_EBP);load(0,7,FIELD_BYTES+36);match(0,32);ne(reject)
    load(0,7,FIELD_BYTES+8);match(0,LEASE_EBP);ne(reject)
    for off in range(0,36,4):get(0,HELPER_BYTES+off);match(0,INPUT+off);ne(reject)
    for n in range(16):
        get(0,ROW_COUNT);cmp(0,n);a.branch('0f86',f'rows.done.{n}')
        get(7,ROWS+8*n);extent(7,4,reject);load(0,7,0);match(0,ROWS+8*n+4);ne(reject);a.label(f'rows.done.{n}')
    a.emit('55');get(5,FIELD_EBP);call(field_check,'private current V2 complete content receipt');a.emit('5d');cmp(0,1);ne(reject)
    get(7,FIELD_EBP);load(0,7,1124);put(0,WORLD)
    # Count's own input record is checked numerically, before any added payload.
    get(0,KIND);cmp(0,4);ne('count.input.done');get(0,INPUT+0);get(1,WORLD);a.emit('29c8');add(0,-852)
    cmp(0,22*31);a.branch('0f83',reject);a.emit('31d2b91f000000f7f1');a.emit('85d2');ne(reject)
    a.label('count.input.done');imm(0,1);a.emit('c3')
    a.label(reject);a.emit('31c0c3')
    a.label('fixed_receipt');get(6,FIELD_EBP)
    blocks=((state,128,0),(0x51D4C0,216,640))
    if plan['profile'] not in ('classic','framed'):blocks+=((state-256,128,128),)
    for pointer,count,slot in blocks:
        label=f'fixed.block.{slot}'
        a.emit('be');address(pointer,'fixed content block before cached heap')
        get(7,FIELD_EBP);add(7,slot);imm(3,count//4)
        a.label(label);load(0,6,0);mem('3b',0,7,0);ne('fixed.reject')
        add(6,4);add(7,4);a.emit('4b');ne(label)
    get(6,FIELD_EBP)
    for n,pointer in enumerate((0x5202E0,0x511230,0x5199D8,0x526994,0x526990,0x532048,THREAD_IAT)):
        read(0,pointer,'fixed content global before cached heap');mem('3b',0,6,1152 if pointer == 0x511230 else 1040+4*n);ne('fixed.reject')
    imm(0,1);a.emit('c3');a.label('fixed.reject');a.emit('31c0c3')
    code=bytes(a.finish())
    for off,label in private_calls:a.relocations.append(assembler_module.Relocation(off,'rel32',base+a.labels[label],'private content helper '+label))
    _require(base+len(code) <= rx+0x20000,'content exceeds unchanged RX reservation')
    emission=CodeEmission(base,state,code,tuple((f'site_{va:06x}',base+a.labels[f'site_{va:06x}']) for va,*_ in SITES),
        tuple(a.relocations),width,height,tuple((name,base+a.labels[name]) for name in ('capture_inputs','capture_stack','admit_body','fixed_receipt')))
    assembler_module.absolute_relocation_offsets(emission)
    return emission

def _authenticate_native(original,candidate,clip):
    inventory=[]
    for is_parent,image in ((False,original),(True,candidate)):
        for name,(lo,hi,digest) in NATIVE_SPANS.items():
            at=clip.file_offset(image,lo,hi-lo);_require(_sha(image[at:at+hi-lo]) == digest,'native content span differs: '+name)
        for va,value in PROLOGUES:
            raw=bytes.fromhex(value);at=clip.file_offset(image,va,len(raw));_require(image[at:at+len(raw)] == raw,'native content prologue differs')
        for pc,target in EXTRA_CALLS:
            at=clip.file_offset(image,pc-5,5);raw=image[at:at+5]
            _require(raw[:1] == b'\xe8' and pc+struct.unpack_from('<i',raw,1)[0] == target,'native content CALL differs')
        for va in (0x513334,0x514500):
            at=clip.file_offset(image,va,64);_require(image[at:at+64] == struct.pack('<16i',*(v for pair in NEIGHBORS for v in pair)),
                'native complete neighbor table differs')
        for va,value,family,operation,dx,dy in SITES:
            raw=bytes.fromhex(value);at=clip.file_offset(image,va,len(raw));_require(image[at:at+len(raw)] == raw,'native whole content operand differs')
            if not is_parent:
                modrm=raw[2] if raw[:2] == b'\x0f\xbf' else raw[2] if raw[0] == 0x66 else raw[1]
                inventory.append(dict(va=va,bytes=len(raw),old_bytes=value,sha256=_sha(raw),family=family,
                    operation=operation,body_sp_delta=BODY_SP[family],proposed_call_return_pc=va+5,
                    native_destination_register=(modrm>>3)&7,native_destination_bits=8 if raw[0] == 0x8A else 16 if raw[0] == 0x66 else 32,
                    native_flags_unchanged=True,neighbor_delta=[dx,dy] if operation == 'occupant' and family in ('tile','adjacent') else None))
    return inventory

def _emit_authenticated(original,profile,resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256,'exact content original required')
    snapshot=_snapshot()
    _require(globals().get('__loaded_source_sha256__') == _sha(snapshot[SOURCE][0]),'private content producer required')
    with _modules(snapshot) as modules:
        parent=modules[LEASE].emit_battle_profile_stack_lease(original,profile,resolution)
        metadata=parent.metadata();plan=metadata['allocation_plan']
        context=modules[CONTEXT].build_parent_context(original,profile,resolution)
        _require(context.allocation_plan() == plan and metadata['source_hashes'][LEASE] == LEASE_SHA256 and
            metadata['field_frame_bytes'] == FIELD_BYTES and metadata['owning_lease_frame_bytes'] == LEASE_BYTES,
            'exact canonical content parent required')
        clip=modules['src/patcher/partial_tile_clip.py']
        inventory=_authenticate_native(original,context.candidate,clip)
        emission=_emit_code(plan,parent.emission,assembler_module=clip)
        result=dict(schema='clash95_battle_profile_content_v1',profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=plan['candidate_sha256'],parent_stage=plan['parent_stage'],
            parent_revision=plan['parent_revision'],canonical_probe_sha256=plan['canonical_probe_sha256'],allocation_plan=plan,
            source_hashes=metadata['source_hashes']|{name:_sha(data) for name,(data,_) in snapshot.items()},
            lease_code_sha256=_sha(parent.emission.code),lease_metadata_sha256=_sha(parent.metadata_json.encode()),
            code_va=emission.base_va,code_bytes=len(emission.code),code_sha256=_sha(emission.code),
            helper_frame_bytes=HELPER_BYTES,helper_maximum_intrinsic_stack_bytes=HELPER_BYTES+52,
            field_frame_bytes=FIELD_BYTES,owning_lease_frame_bytes=LEASE_BYTES,
            native_operands=inventory,native_spans=NATIVE_SPANS,native_neighbors=NEIGHBORS,
            helper_abi=dict(value='EAX',status='EDX',denied=0,valid=1,fault=2,reject_value='incoming EAX preserved'),
            outside_zero_payload_reads=True,current_geometry_header_admission=True,unit_indices=[0,21],unit_types=[0,34],owner_byte_domain=[0,255],
            absent_unit_type_sentinel=-1,absent_unit_type_consumer_va=0x42F84A,
            coordinate_bounds_checked=True,coordinate_bounds='record+4 below current columns; record+6 below current rows',
            malformed_is_empty=False,installed=False,battle_installed=False,expanded_battle_installed=False,
            runtime_executed=False,manual_input_proof=False,installation_ready=False,preparation_only=True,
            writes_owner_state=False,writes_headers=False,writes_pixels=False,heap_or_global_descriptor=False,
            native_body_callsite_admission_installed=False,native_instruction_replay=False,native_continuation_cancellation=False,
            count_entry_record_guard_installed=False,non_draw_count_admission=False,provider_validity_verified=False,
            native_receiver_validity_verified=False,native_argument_validity_verified=False,
            standalone_native_callsite_replacement_safe=False,physical_only_clip_admission_verified=False,
            arena_intersection_verified=False,runtime_verified=False,manual_input_verified=False,promotion_ready=False,
            release_accepted=False,source_candidate_installed=False,thread_lifetime_runtime_verified=False,
            rx_remaining_bytes=plan['rx']['va']+0x20000-emission.base_va-len(emission.code),
            entries=dict(emission.entries),private_entries=dict(emission.private_entries),
            limitations=[
                'These EAX-value/EDX-status preparation helpers are not native MOV/MOVSX replacements; future adapters must handle status and preserve full or partial native destinations before continuing.',
                'No CALL adapters are installed. Synthetic body CALLs model fixed native SP/EBP/return receipts and do not prove that an original body or installed callsite ran.',
                'Count admission covers only native Unit draw caller42F95B; crowding426F95 and idle431D7A remain unadmitted and untouched.',
                'Original Count input coordinate reads426EFD and later input-owner reads require a future entry/continuation family before whole-function safety can be claimed.',
                'Status2 does not stop frozen V2 nextTile, native Unit/Tile continuations or intra-RLE/provider work; no failure cancellation or cleanup replay is emitted.',
                'Owning-thread receipts and bounded reads do not prove native inter-thread WORLD allocation lifetime or immutable contents at runtime.',
                'Provider assets, receiver/argument validity, physical-only arena clipping, process quit and atomic installation remain unverified.',
            ])
        _require(_snapshot() == snapshot,'content source changed during emission')
    return BattleProfileContentBundle(emission,parent,json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))

def emit_battle_profile_content(original,profile,resolution):
    snapshot=_snapshot()
    with _modules(snapshot) as modules:result=modules[SOURCE]._emit_authenticated(original,profile,resolution)
    _require(_snapshot() == snapshot,'content source changed during public emission')
    return result
