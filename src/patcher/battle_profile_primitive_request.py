"""Uninstalled versioned continuation and primitive-request preparation.

Requests exist only in a new owning thunk frame. They do not admit sprite
storage, replay a native primitive, write pixels, or cancel provider work.
"""
from __future__ import annotations

import ast
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
SOURCE = 'src/patcher/battle_profile_primitive_request.py'
CONTINUATION = 'src/patcher/battle_profile_continuation.py'
CONTENT = 'src/patcher/battle_profile_content.py'
LEASE = 'src/patcher/battle_profile_stack_lease.py'
FIELD = 'src/patcher/battle_profile_field_v2.py'
CONTEXT = 'src/patcher/battle_profile_context.py'
CONTINUATION_SHA = '075bd62a8311f8cc761136bca21063813dfc874ce8d8a5bcf075ebdb664d811f'
CONTENT_SHA = '52f9ac7f8d52cb40638e91868910d6487cea083be0cc32e622d8fe4a3f8cf3d7'
BASE_SHA256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
THUNK_BYTES, HELPER_BYTES, REQUEST_BYTES = 116, 640, 64
TAG, SCHEMA = 0x50525131, 1
DENIED, PREPARED, MALFORMED, EMPTY, FAULT = 0, 1, 2, 3, 4
# Original indirect CALL, primitive, owning parent, actual callee-entry delta.
# A proposed five-byte CALL has its own genuine PC+5, never the old PC+3.
REQUEST_SITES = (
    (0x430035,'sprite','tile',100,'ff5734'),
    (0x4300F3,'sprite','tile',100,'ff5734'),
    (0x43024E,'sprite','tile',100,'ff5734'),
    (0x430349,'sprite','tile',100,'ff5734'),
    (0x430733,'sprite','tile',100,'ff5734'),
    (0x4307AA,'sprite','tile',100,'ff5734'),
    (0x43080C,'sprite','tile',100,'ff5734'),
    (0x430991,'sprite','tile',100,'ff5734'),
    (0x42FC1B,'sprite','unit',96,'ff5734'),
    (0x405552,'sprite','tracking',48,'ff5534'),
    (0x4055B3,'sprite','charge',60,'ff5734'),
    (0x430AD5,'line','tile',80,'ff5714'),
    (0x430B07,'line','tile',80,'ff5714'),
)
# Whole instruction-aligned argument-preparation windows, including CALL.
ARGUMENT_WINDOWS = (
    (0x42FFF9,0x430038,'7a5c4f0afa84d8f5cf475b9057593e9c16b9009df8bf951823ef17f3ae9ed62d',(196617,196642)),
    (0x4300B5,0x4300F6,'3920a15f9a3fa85ee400e24fe9d0ecff422c7a60a2bec49a7fef5a8825ee92d8',(196810,196832)),
    (0x430213,0x430251,'f3413b573911f1364ea45e9eca0d774fb1bf10de201755c0d495fd0b5059070f',(197157,197179)),
    (0x43030B,0x43034C,'daf8d990b55979654a95293efe9e448a6d86a74b314ec525a83460bf5c3c4a09',(197399,197416)),
    (0x4306F3,0x430736,'18b4c0fb8d0802c6f9c5adb03e9c4b1086f8a310966854906842a3dd60fe5a44',(198392,198399,198405,198437)),
    (0x43076C,0x4307AD,'29ec2ca0234ec4acef6196b569c34b1a4c092d8e57b27e600ceff4084b31da5b',(198516,198533)),
    (0x4307CE,0x43080F,'cf4986f568f3e45fe87bdfc3153096a7acd2b1af440e312d74f8a23c09017411',(198622,198639)),
    (0x430953,0x430994,'d8abd2877e52781af111a18059476c3e1f92055f1e9d62eb3162b215c43aa16d',(199016,199038)),
    (0x42FBDC,0x42FC1E,'6dd743e143ae74a1908c48bf43002b35e22be2a34a63763087645edf7e23f0e4',(195593,)),
    (0x405512,0x405555,'16f91a6a8e0b9b129323b02846cafeb703b97458ea9c835334638abf9bc2a2c2',(21786,21802)),
    (0x405577,0x4055B6,'4f4782f77db34ea044c48d9e96581e3703502ae5ce137242c6e7a0c02bbc9a6e',()),
    (0x430A96,0x430AD8,'2dda9b72729373ffcd8ed8d102ed253053af70a74fc0bf6771fa657ddae0620f',(199349,)),
    (0x430ACC,0x430B0A,'ff64ac66854ff3b59f20790c22294bdef17e458947ce81421659e758c37300ce',(199393,)),
)
FALSE_CLAIMS = ('installed','battle_installed','installation_ready','runtime_verified',
    'manual_input_verified','release_accepted','promotion_ready','provider_validity_verified',
    'sprite_storage_validity_verified','arena_drawing_verified','intra_decoder_cancellation',
    'native_primitive_replay_emitted','native_receiver_validity_verified','native_argument_validity_verified',
    'process_quit_closure_verified','writes_pixels','writes_headers','writes_owner_state')

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
    planned_hooks: tuple
    field_call_patches: tuple
    reused_blocks: tuple
    unsafe_va: int
    request_sites: tuple
    request_returns: tuple

@dataclass(frozen=True)
class BattleProfilePrimitiveRequestBundle:
    emission: CodeEmission
    continuation_bundle: object
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()
    def metadata(self): return json.loads(self.metadata_json)

def _require(ok,message):
    if not ok: raise ValueError(message)

def _sha(data): return hashlib.sha256(data).hexdigest()

def _snapshot():
    root=Path(__file__).resolve().parents[2]
    name='src/patcher/battle_profile_primitive_request.py'
    _require(Path(__file__).resolve()==root/name,'canonical request producer required')
    frozen=root/'src/patcher/battle_profile_content.py'; data=frozen.read_bytes()
    _require(_sha(data)==CONTENT_SHA,'frozen content source differs')
    tree=ast.parse(data); constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant):
            for target in node.targets:
                if isinstance(target,ast.Name): constants[target.id]=node.value.value
    pins=next(n for n in tree.body if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='PINNED_SOURCES' for t in n.targets))
    literal=lambda n: constants[n.id] if isinstance(n,ast.Name) else ast.literal_eval(n)
    env={literal(k):literal(v) for k,v in zip(pins.value.keys,pins.value.values)}
    env.update({CONTENT:CONTENT_SHA,CONTINUATION:CONTINUATION_SHA,name:None})
    result={}
    for path,digest in env.items():
        target=root/path; _require(target.resolve(strict=True)==target and target.is_relative_to(root),'noncanonical dependency')
        before=target.stat(); raw=target.read_bytes(); after=target.stat()
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
        _require(stamp(before)==stamp(after) and (digest is None or _sha(raw)==digest),'pinned request source differs: '+path)
        result[path]=(raw,stamp(after))
    return result

@contextmanager
def _modules(snapshot):
    prefix='_clash95_primitive_request_'+uuid.uuid4().hex; saved=sys.path[:]
    try:
        for suffix in ('','.src','.src.patcher'):
            m=types.ModuleType(prefix+suffix);m.__path__=[];sys.modules[m.__name__]=m
            if suffix:
                parent,_,leaf=m.__name__.rpartition('.');setattr(sys.modules[parent],leaf,m)
        result={}
        for stem in ('framed_viewport','pe_extension','partial_tile_clip','framed_battle_viewport',
            'framed_battle_coordinates','framed_battle_field','framed_modal_canvas','framed_battle_hud',
            'battle_profile_context','battle_profile_lifecycle','battle_profile_routing','battle_profile_field',
            'battle_profile_field_v2','battle_profile_stack_lease','battle_profile_content',
            'battle_profile_continuation','battle_profile_primitive_request'):
            name='src/patcher/'+stem+'.py';full=prefix+'.src.patcher.'+stem
            m=types.ModuleType(full);m.__file__=str(ROOT/name);m.__package__=full.rpartition('.')[0]
            m.__loaded_source_sha256__=_sha(snapshot[name][0]);sys.modules[full]=m
            setattr(sys.modules[m.__package__],stem,m)
            exec(compile(snapshot[name][0],m.__file__,'exec'),m.__dict__);result[name]=m
        yield result
    finally:
        for name in list(sys.modules):
            if name==prefix or name.startswith(prefix+'.'):del sys.modules[name]
        sys.path[:]=saved

def _replace(text,old,new):
    _require(text.count(old)==1,'fixed shared composition boundary differs: '+old[:70])
    return text.replace(old,new)

def _request_guard(content,source,continuation):
    # The frozen producer is privately reconstructed. Extend its typed ABI;
    # every old family remains admitted through the same stronger control path.
    # Capture the exact generated function source using the fixed producer's
    # compile boundary; no public function object or caller table is authority.
    captured={}
    class Capture:
        def __call__(self,text,filename,mode):
            captured['text']=text;return compile(text,filename,mode)
    scope=dict(continuation.__dict__);scope['compile']=Capture()
    tree=ast.parse((ROOT/CONTINUATION).read_bytes())
    factory=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_guard_producer')
    exec(compile(ast.get_source_segment((ROOT/CONTINUATION).read_text(),factory),str(ROOT/SOURCE)+':guard_factory','exec'),scope)
    scope['_guard_producer'](content,source)
    text=captured['text']
    text=_replace(text,'extent(7,HELPER_BYTES+96,reject)','extent(7,HELPER_BYTES+192,reject)')
    text=_replace(text,'extent(7,4,reject);put(7,516)','extent(7,36,reject);put(7,516)')
    text=_replace(text,'for off in range(0,52,4):get(0,HELPER_BYTES+40+off);put(0,528+off)',
        'for off in range(0,116,4):get(0,HELPER_BYTES+40+off);put(0,528+off if off<112 else 520)')
    _require(text.count('for off in range(0,52,4):get(0,HELPER_BYTES+40+off);match(0,528+off)')==2,
        'two fixed outer control comparisons required')
    text=text.replace('for off in range(0,52,4):get(0,HELPER_BYTES+40+off);match(0,528+off)',
        'for off in range(0,116,4):get(0,HELPER_BYTES+40+off);match(0,528+off if off<112 else 520)')
    text=_replace(text,'for number,family in enumerate(FAMILIES+(\'field\',)):',
        'get(0,INPUT+8);put(0,192)\n    for number,family in enumerate(FAMILIES+(\'field\',)):')
    text=_replace(text,"        jump('ancestry.'+family);a.label(f'body_delta.next.{number}')",
        "        get(0,SITE);cmp(0,74);a.branch('0f83','ancestry.request')\n"
        "        jump('ancestry.'+family);a.label(f'body_delta.next.{number}')")
    text=_replace(text,"    a.label('ancestry.field')",_ancestry_source()+"    a.label('ancestry.field')")
    text=_replace(text,"cmp(0,len(admission_sites)-2);eq('field.mode.full')",
        "cmp(0,72);eq('field.mode.full')")
    # Each ancestor EBP role remains separately checked; effect EBP is native
    # clip/vtable data, while its saved parent EBP supplies parent ancestry.
    text=text.replace('get(0,INPUT+8);a.emit(\'39c8\')','get(0,192);a.emit(\'39c8\')')
    text=text.replace("get(0,INPUT+8);a.emit('39f8')","get(0,192);a.emit('39f8')")
    text=_replace(text,'add(7,-784);extent(7,1520,reject)','add(7,-880);extent(7,1712,reject)')
    text=_replace(text,'81ec000300008d75fc89e7b9b9000000fcf3a5','81ec600300008d75fc89e7b9d1000000fcf3a5')
    text=_replace(text,'508d7424048d7dfcb9b9000000fcf3a7','508d7424048d7dfcb9d1000000fcf3a7')
    text=_replace(text,'5881c400030000','5881c460030000')
    text=_replace(text,'8b8424b401000081c404030000','8b8424b401000081c464030000')
    env=dict(content.__dict__);env['REQUEST_SITES']=REQUEST_SITES
    exec(compile(text,str(ROOT/SOURCE)+':shared_guard','exec'),env)
    return env['_emit_guard']

def _ancestry_source():
    return '''    a.label('ancestry.request')
    get(7,516)
    for i,(pc,primitive,owner,delta,raw) in enumerate(REQUEST_SITES):
        get(0,SITE);cmp(0,74+i);ne(f'request.ancestry.next.{i}')
        add(7,delta)
        if owner in ('tile','unit'):
            jump('ancestry.'+owner)
        else:
            record(7,4,reject)
            add(7,-12);record(7,4,reject);get(7,516);add(7,delta)
            load(0,7,-12);put(0,192)
            if owner=='tracking':
                get(0,INPUT+8);cmpva(0,0x50EE24,'tracking native memory vtable EBP');ne(reject)
                load(0,7,0)
                cmpva(0,0x43087D,'native tracking Tile return');eq('request.tracking.tile')
                returns(0,(0x42FA7C,0x42FBBD),'request.tracking.unit');jump(reject)
            else:
                get(6,516);load(0,6,8);match(0,INPUT+8);ne(reject)
                load(0,7,0);cmpva(0,0x42F932,'native charge Unit return');ne(reject)
                add(7,100);jump('ancestry.unit')
        a.label(f'request.ancestry.next.{i}')
    jump(reject)
    a.label('request.tracking.tile');imm(0,0);put(0,KIND);add(7,92);jump('ancestry.tile')
    a.label('request.tracking.unit');add(7,88);jump('ancestry.unit')
'''

def _append_requests(a,base,content_emission,admissions,thunk_returns,local_calls,clip,width):
    def imm(r,v):a.emit(f'{0xB8+r:02x}');a.u32(v)
    def mem(op,r,b,o):
        a.emit(op+f'{0x80|(r<<3)|b:02x}');
        if b==4:a.emit('24')
        a.u32(o)
    def get(r,o):mem('8b',r,5,o)
    def put(r,o):mem('89',r,5,o)
    def load(r,b,o):mem('8b',r,b,o)
    def cmp(r,v):a.emit(f'81{0xF8+r:02x}');a.u32(v)
    def call(label):
        a.emit('e8');at=len(a.code);a.u32(0);a.fixups.append((at,label));local_calls.append((at,label))
    def transfer(target,purpose):
        a.emit('e9');at=len(a.code);a.relocations.append(clip.Relocation(at,'rel32',target,purpose));a.u32(target-base-at-4)
    def branch(op,label):a.branch(op,label)
    def result(status):imm(2,status);branch('e9','request.finish')
    _require(len(admissions)==len(thunk_returns)==74,'fixed predecessor adapter inventory differs')
    returns=[]
    for i,(pc,kind,parent,delta,raw) in enumerate(REQUEST_SITES):
        n=74+i;admissions.append((pc,'tile' if parent=='tile' else 'unit','request'))
        a.label('adapter_'+str(n))
        a.emit('9c60fc83ec50c7042400000000c744240400000000c7442408');a.u32(n)
        a.emit('c744240c');a.u32(0 if parent=='tile' else 1)
        call('request.helper');thunk_returns.append(base+len(a.code))
        # Query result only. Its prepared request is live at ESP+16..80.
        # Preserve caller EAX, all other registers, flags, arguments and ESP.
        mem('89',2,4,100);a.label('request.return.'+str(i))
        returns.append(base+len(a.code));a.emit('83c450619dc3')
    a.label('request.helper');a.emit('9c60fc81ec');a.u32(640);a.emit('89e5')
    a.emit('e8');at=len(a.code);target=dict(content_emission.private_entries)['capture_inputs']
    a.relocations.append(clip.Relocation(at,'rel32',target,'frozen input capture for new owning request'));a.u32(target-base-at-4)
    get(0,688);put(0,200);a.emit('8d85');a.u32(796);put(0,208)
    call('admit_body');cmp(0,1);branch('0f85','request.unsafe')
    get(0,428);get(7,220);load(1,7,1040);a.emit('39c8');branch('0f85','request.fault')
    cmp(0,0x51D4C0); # This image VA immediate is separately relocated.
    a.relocations.append(clip.Relocation(len(a.code)-4,'abs32',0x51D4C0,'reject literal primary receiver'))
    branch('0f84','request.fault')
    # Once the callback-free guard has returned, its old lease snapshot is
    # dead. This versioned scratch lifetime reuses128..192, disjoint from the
    # live ancestry EBP192/input400/outer528..640 plus flags520. The published
    # request has its own new thunk interval16..80, never old field padding.
    for off in range(128,192,4):imm(0,0);put(0,off)
    for off,value in ((128,TAG),(132,SCHEMA),(136,64)):imm(0,value);put(0,off)
    get(0,428);put(0,148)
    get(0,420);put(0,144)
    get(0,416);put(0,152);get(0,424);put(0,156)
    get(7,372);load(0,7,804);cmp(0,(width-192)//64);branch('0f86','request.columns')
    imm(0,(width-192)//64);a.label('request.columns');a.emit('c1e00683c01f');put(0,196)
    for i,(pc,kind,*_) in enumerate(REQUEST_SITES):
        get(0,200);cmp(0,74+i);branch('0f85','request.site.next.'+str(i))
        imm(0,1 if kind=='sprite' else 2);put(0,140)
        branch('e9','request.'+kind);a.label('request.site.next.'+str(i))
    branch('e9','request.unsafe')
    a.label('request.sprite');get(7,516)
    for off in range(0,28,4):load(0,7,4+off);put(0,160+off)
    for off in (160,164,168,172):get(0,off);cmp(0,0xFFFFFFFF);branch('0f85','request.finite')
    imm(0,32);put(0,160);imm(0,16);put(0,164);get(0,196);put(0,168);imm(0,463);put(0,172)
    result(PREPARED)
    a.label('request.finite')
    get(0,160);mem('3b',0,5,168);branch('0f8f','request.malformed')
    get(0,164);mem('3b',0,5,172);branch('0f8f','request.malformed')
    for off,low in ((160,32),(164,16)):
        get(0,off);cmp(0,low);branch('0f8d','request.lower.'+str(off));imm(0,low);put(0,off);a.label('request.lower.'+str(off))
    get(0,168);mem('3b',0,5,196);branch('0f8e','request.right');get(0,196);put(0,168);a.label('request.right')
    get(0,172);cmp(0,463);branch('0f8e','request.bottom');imm(0,463);put(0,172);a.label('request.bottom')
    get(0,160);mem('3b',0,5,168);branch('0f8f','request.empty')
    get(0,164);mem('3b',0,5,172);branch('0f8f','request.empty');result(PREPARED)
    a.label('request.line')
    # Preserve native uint16 conversion and native axis selection by Y only.
    get(0,420);a.emit('25ffff0000');put(0,160)
    get(0,416);a.emit('25ffff0000');put(0,164)
    get(0,424);a.emit('25ffff0000');put(0,168)
    get(7,516);load(0,7,4);a.emit('25ffff0000');put(0,172)
    load(0,7,8);put(0,176)
    get(0,164);mem('3b',0,5,172);branch('0f85','request.vertical')
    get(0,160);mem('3b',0,5,168);branch('0f87','request.malformed')
    get(0,164);cmp(0,16);branch('0f82','request.empty');cmp(0,463);branch('0f87','request.empty')
    get(0,160);cmp(0,32);branch('0f83','request.line.left');imm(0,32);put(0,160);a.label('request.line.left')
    get(0,196);get(1,176);a.emit('f7c100010000');branch('0f84','request.line.right.bound');a.emit('40')
    a.label('request.line.right.bound');get(1,168);a.emit('39c1');branch('0f86','request.line.right.done');put(0,168)
    a.label('request.line.right.done');branch('e9','request.line.nonempty')
    a.label('request.vertical')
    get(0,164);mem('3b',0,5,172);branch('0f87','request.malformed')
    get(0,160);cmp(0,32);branch('0f82','request.empty');mem('3b',0,5,196);branch('0f87','request.empty')
    get(0,164);cmp(0,16);branch('0f83','request.line.top');imm(0,16);put(0,164);a.label('request.line.top')
    imm(0,463);get(1,176);a.emit('f7c100010000');branch('0f84','request.line.bottom.bound');a.emit('40')
    a.label('request.line.bottom.bound');get(1,172);a.emit('39c1');branch('0f86','request.line.bottom.done');put(0,172)
    a.label('request.line.bottom.done')
    get(0,164);get(1,172);branch('e9','request.line.compare')
    a.label('request.line.nonempty');get(0,160);get(1,168)
    a.label('request.line.compare');a.emit('39c8');branch('0f87','request.empty')
    get(1,176);a.emit('f7c100010000');branch('0f84','request.line.prepared')
    # Choose the original native axis, then reload its endpoint for the
    # dashed exclusive-end equality test. Absolute coordinates stay intact.
    get(1,416);a.emit('81e1ffff0000');get(3,516);load(3,3,4);a.emit('81e3ffff0000')
    a.emit('39d9');branch('0f85','request.line.dashed.vertical');get(1,168);branch('e9','request.line.dashed.compare')
    a.label('request.line.dashed.vertical');get(1,172)
    a.label('request.line.dashed.compare');a.emit('39c8');branch('0f84','request.empty')
    a.label('request.line.prepared');result(PREPARED)
    a.label('request.empty');result(EMPTY)
    a.label('request.malformed');result(MALFORMED)
    a.label('request.fault');imm(2,FAULT);branch('e9','request.finish.no.record')
    a.label('request.finish');put(2,188)
    for off in range(0,64,4):get(0,128+off);put(0,696+off)
    a.label('request.finish.no.record');get(0,428)
    # Exact shared content finish restores this helper and returns to its own
    # thunk; it never consumes or rewrites a native argument/return word.
    last=dict(content_emission.entries)[f'site_426f54']-content_emission.base_va
    denied=last+69+struct.unpack_from('<i',content_emission.code,last+65)[0]
    finish=denied+10+struct.unpack_from('<i',content_emission.code,denied+6)[0]
    transfer(content_emission.base_va+finish,'request returns through fixed 640B common finish')
    a.label('request.unsafe');a.emit('0f0b')
    return tuple(returns)

def _compose(modules,snapshot,plan,checked,lease,field,assembler):
    continuation=modules[CONTINUATION];content=modules[CONTENT]
    tree=ast.parse(snapshot[CONTINUATION][0]);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_emit_code')
    text=ast.get_source_segment(snapshot[CONTINUATION][0].decode(),node)
    text=_replace(text,'def _emit_code(','def _emit_composed(')
    text=text.replace('83ec10','83ec50').replace('83c410','83c450')
    text=_replace(text,'offset={0:44,1:40,2:36,3:32,5:24,6:20,7:16}[dest]',
        'offset={0:108,1:104,2:100,3:96,5:88,6:84,7:80}[dest]')
    text=text.replace('c744242c','c744246c')
    text=_replace(text,'add(0,732)','add(0,796)')
    text=_replace(text,'guard_base=(base+len(a.code)+5+15)&~15',
        'request_returns=_append_requests(a,base,content_emission,admissions,thunk_returns,local_calls,clip,width)\n'
        '        guard_base=(base+len(a.code)+5+15)&~15')
    text=_replace(text,'_guard_producer(content,snapshot[CONTENT][0])',
        '_request_guard(content,snapshot[CONTENT][0],continuation_authority)')
    text=_replace(text,"str(len(admissions)-2+mode)",'str(72+mode)')
    text=_replace(text,"base+a.labels['unsafe'])",
        "base+a.labels['unsafe'],REQUEST_SITES,request_returns)")
    text=_replace(text,"('helper_unsafe',base+a.labels['helper_unsafe']),",
        "('request_helper',base+a.labels['request.helper']),('request_unsafe',base+a.labels['request.unsafe']),"
        "('helper_unsafe',base+a.labels['helper_unsafe']),")
    env=dict(continuation.__dict__)
    env.update(CodeEmission=CodeEmission,_append_requests=_append_requests,_request_guard=_request_guard,
        REQUEST_SITES=REQUEST_SITES,continuation_authority=continuation)
    exec(compile(text,str(ROOT/SOURCE)+':versioned_continuation','exec'),env)
    return env['_emit_composed'](plan,checked,lease,field,assembler_module=assembler)

def _emit_code(plan,content_emission,lease_emission,field_emission,*,assembler_module):
    """Pure synthetic boundary; immutable parents are independently rebuilt."""
    snapshot=_snapshot()
    with _modules(snapshot) as modules:
        out=_compose(modules,snapshot,plan,content_emission,lease_emission,field_emission,assembler_module)
    _require(_snapshot()==snapshot,'request sources changed during composition')
    return out

def _authenticate_native(original,candidate,modules):
    clip=modules['src/patcher/partial_tile_clip.py'];pe=modules['src/patcher/pe_extension.py']
    modules[CONTINUATION]._authenticate_native(original,candidate,clip,modules[CONTENT],modules[LEASE],pe)
    for image in (original,candidate):
        parsed=pe.inspect_pe(image);_,relocs=pe._old_relocations(image,parsed)
        for pc,kind,parent,delta,raw in REQUEST_SITES:
            at=clip.file_offset(image,pc,3);_require(image[at:at+3]==bytes.fromhex(raw),'primitive CALL bytes differ')
        for lo,hi,digest,expected in ARGUMENT_WINDOWS:
            at=clip.file_offset(image,lo,hi-lo)
            _require(_sha(image[at:at+hi-lo])==digest,'whole primitive argument window differs')
            actual=tuple(sorted(r for r in relocs if lo<=parsed.image_base+r<hi))
            _require(actual==expected,'complete argument HIGHLOW inventory differs')

def _emit_authenticated(original,profile,resolution):
    snapshot=_snapshot()
    _require(globals().get('__loaded_source_sha256__')==_sha(snapshot[SOURCE][0]),'private request producer required')
    _require(type(original) is bytes and _sha(original)==BASE_SHA256,'exact original required')
    with _modules(snapshot) as modules:
        predecessor=modules[CONTINUATION].emit_battle_profile_continuation(original,profile,resolution)
        parent=predecessor.content_bundle;metadata=predecessor.metadata();plan=metadata['allocation_plan']
        context=modules[CONTEXT].build_parent_context(original,profile,resolution)
        _require(context.allocation_plan()==plan,'independent parent/allocation required')
        _authenticate_native(original,context.candidate,modules)
        clip=modules['src/patcher/partial_tile_clip.py']
        out=_compose(modules,snapshot,plan,parent.emission,parent.lease_bundle.emission,parent.lease_bundle.field_bundle.emission,clip)
        result=dict(schema='clash95_battle_profile_primitive_request_v1',profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=plan['candidate_sha256'],allocation_plan=plan,
            source_hashes=metadata['source_hashes']|{n:_sha(v[0]) for n,v in snapshot.items()},
            predecessor_code_sha256=_sha(predecessor.emission.code),predecessor_metadata_sha256=_sha(predecessor.metadata_json.encode()),
            code_va=out.base_va,code_bytes=len(out.code),code_sha256=_sha(out.code),
            helper_frame_bytes=640,thunk_frame_bytes=116,request_frame_bytes=64,
            callback_snapshot_bytes=864,maximum_owned_helper_stack_extent=1712,
            field_frame_bytes=1280,lease_frame_bytes=192,owner_page_bytes=4096,
            request_lifetime='owning thunk ESP+16..80 before its RET only; never caller authority',
            request_fields=['tag','schema','bytes','kind','incoming_edx','receiver_eax','incoming_ebx','incoming_ecx',
                'left_or_start_x','top_or_start_y','right_or_end_x','bottom_or_end_y','extra0','extra1','extra2','status'],
            request_statuses=dict(denied=0,prepared=1,malformed=2,empty=3,fault=4),
            denial_behavior='unknown ancestry/control stops exact UNSAFE UD2 before request publication',
            request_sites=[dict(pc=pc,kind=kind,parent=parent,callee_entry_delta=delta,
                old_call_bytes=raw,native_return_pc=pc+3,query_return_pc=pc+5) for pc,kind,parent,delta,raw in REQUEST_SITES],
            argument_windows=[dict(start=lo,end=hi,sha256=digest,highlow_rvas=list(rs)) for lo,hi,digest,rs in ARGUMENT_WINDOWS],
            shared_guard_count=1,baseline_adapter_count=74,request_adapter_count=13,
            versioned_planned_continuation_windows=[dict(va=va,rva=va-0x400000,
                file_offset=clip.file_offset(original,va,len(raw)),old_bytes=raw.hex(),
                new_bytes=(b'\xe8'+struct.pack('<i',target-va-5)+b'\x90'*(len(raw)-5)).hex(),
                target_va=target,role=role,removed_highlow_rvas=list(removed))
                for va,raw,target,role,removed in out.planned_hooks],
            versioned_planned_field_calls=[dict(va=va,old_bytes=raw.hex(),
                new_bytes=(b'\xe8'+struct.pack('<i',target-va-5)).hex(),target_va=target)
                for va,raw,target in out.field_call_patches],
            rx_used_bytes=out.base_va+len(out.code)-plan['rx']['va'],
            rx_remaining_bytes=plan['rx']['va']+0x20000-out.base_va-len(out.code),
            unsafe_vas=[out.unsafe_va]+[va for name,va in out.private_entries if name.endswith('_unsafe')],
            preparation_only=True,baseline_scalar_continuation_replay_emitted=True,
            request_intersection_source_verified=True,physical_request_receiver_checked=True,
            limitations=[
                'No hook, field CALL substitution, native primitive replay or candidate installation is emitted.',
                'Prepared/empty requests do not admit sprite objects, payload bounds, allocation provenance or provider lifetime.',
                'A five-byte query CALL differs from the original three-byte indirect CALL; whole pre/post adapters must be installed atomically by a future reviewed version.',
                'No native continuation is replayed after a request. Its record expires with the owning thunk RET.',
                'The baseline continuation retains its reviewed scalar replay; requests emit no native primitive or provider replay.',
                'Native receiver/argument validity, sprite/provider ownership and process-quit closure require future installed families.',
                'Line requests retain unsigned16 conversion, Y-only native axis selection, inclusive plain/exclusive dashed ends and absolute dash phase; no line is drawn.',
                'Unknown control remains UNSAFE, not a healthy native unwind. Intracallback/provider cancellation and fatal shutdown are unresolved.',
                'Inter-thread immutability, native content/provider ownership, Unit predecessor invariants and full battle integration remain unproved.',
            ],**{name:False for name in FALSE_CLAIMS})
    _require(_snapshot()==snapshot,'request sources changed during public emission')
    return BattleProfilePrimitiveRequestBundle(out,predecessor,json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))

def emit_battle_profile_primitive_request(original,profile,resolution):
    snapshot=_snapshot()
    with _modules(snapshot) as modules:result=modules['src/patcher/battle_profile_primitive_request.py']._emit_authenticated(original,profile,resolution)
    _require(_snapshot()==snapshot,'request source changed during dispatch')
    return result
