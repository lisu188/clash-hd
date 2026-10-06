"""Uninstalled, source-owned native continuation preparation.

Normal-return gates cannot cancel work inside a decoder/provider. Unknown
control stops at an explicit UNSAFE endpoint; it never borrows a native
epilogue. Planned hooks and field CALL substitutions are receipts only.
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

ROOT=Path(__file__).resolve().parents[2]
SOURCE='src/patcher/battle_profile_continuation.py'
CONTENT='src/patcher/battle_profile_content.py'
LEASE='src/patcher/battle_profile_stack_lease.py'
FIELD='src/patcher/battle_profile_field_v2.py'
CONTEXT='src/patcher/battle_profile_context.py'
BASE_SHA256='500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
CONTENT_SHA256='52f9ac7f8d52cb40638e91868910d6487cea083be0cc32e622d8fe4a3f8cf3d7'
THUNK_BYTES,HELPER_BYTES=52,640
GUARD_RET,OUTER_S,OUTER_SNAPSHOT=512,516,528
# Complete small old-byte windows: operand followed by exact scalar replay.
CONTENT_WINDOWS=(
    (0x43026F,'0fbf8441fe05000031ff'),(0x430375,'0fbfbc47fc05000083ffff'),
    (0x4303E7,'0fbfbc42fc05000039df'),(0x430459,'0fbfbc4200060000a160235100'),
    (0x4304B4,'0fbfbc42fe05000083ffff'),(0x43055A,'0fbfbc410006000083ffff'),
    (0x4305DA,'0fbfbc420006000039df'),(0x430649,'0fbfbc41fc05000039df'),
    (0x4306A7,'0fbfbc42fe05000083ffff'),(0x4302B4,'0fbf8401540300006bc058'),
    (0x43050A,'0fbf8401540300006bc058'),(0x42F7CF,'0fbf8401540300006bc058'),
    (0x42F84A,'0fbf825403000083f8ff'),(0x42F9AF,'668b825803000001d86bc028'),
    (0x42F9C3,'668b825a030000038738335100'),(0x42F9D7,'0fbf80fe05000083f8ff'),
    (0x42F9EC,'8a99560300003a9a56030000'),(0x42FC5F,'0fbf84025403000083f81b'),
    (0x42FC92,'0fbf8468fc05000083f8ff'),(0x42FCEA,'0fbf84680006000083f8ff'),
    (0x42FD26,'0fbf846afe05000083f8ff'),(0x42FD7F,'0fbf846afe05000083f8ff'),
    (0x42FDC0,'0fbf846afc05000083f8ff'),(0x42FE23,'0fbf846a0006000083f8ff'),
    (0x42FE68,'0fbf846afc05000083f8ff'),(0x42FEBB,'0fbf84680006000083f8ff'),
    (0x426F44,'0fbf8c59fe05000083f9ff'),(0x426F54,'8a9411560300003a5702'))
# PC after complete native normal RET, parent, exact whole replay window.
POST_WINDOWS=(
    (0x42F932,'unit','ba01000000'),(0x42F95B,'unit','89c685c90f852a010000'),
    (0x42FA7C,'unit','8b5dfc4383c708'),(0x42FBBD,'unit','e970fdffff'),
    (0x42FC1E,'unit','e90ffdffff'),(0x42FCC4,'adjacent','8b1548205300'),
    (0x42FD58,'adjacent','8b1548205300'),(0x42FDF9,'adjacent','8b042485c0'),
    (0x42FEFC,'adjacent','e904feffff'),(0x42FF20,'adjacent','e975feffff'),
    (0x42FF54,'adjacent','e9e5feffff'),(0x42FF75,'adjacent','e913ffffff'),
    (0x42FFA4,'adjacent','83c4045d5f'),(0x430038,'tile','8b55d0a148205300'),
    (0x4300F6,'tile','8b45eca304215300'),(0x430251,'tile','8b55f88d049500000000'),
    (0x4302DC,'tile','8b55f88d049500000000'),(0x43034C,'tile','8b5dfc31c9'),
    (0x430389,'tile','85c074243b3d60235100'),(0x4303B1,'tile','837dfc007e65'),
    (0x4303FA,'tile','85c0741e8b5df4'),(0x43041C,'tile','8b1548205300'),
    (0x43046F,'tile','85c0741e8b5df4'),(0x430491,'tile','8b55f885d2'),
    (0x4304C8,'tile','85c074298b1d60235100'),(0x4304F5,'tile','8b7de883ffff'),
    (0x430531,'tile','8b0d48205300'),(0x43056E,'tile','85c074298b1d60235100'),
    (0x43059B,'tile','8b1548205300'),(0x4305ED,'tile','85c0741e8b5df4'),
    (0x43060F,'tile','8b7dfc85ff'),(0x43065C,'tile','85c0741e8b5df4'),
    (0x43067E,'tile','8b1548205300'),(0x4306BB,'tile','85c074298b1d60235100'),
    (0x4306E8,'tile','8b45f83b05544e5100'),(0x430736,'tile','8b5de883fbff'),
    (0x4307AD,'tile','8b45e83b05581b5100'),(0x43080F,'tile','a1e4025200'),
    (0x43087D,'tile','e9d5f7ffff'),(0x430994,'tile','e9f8f7ffff'),
    (0x430AAA,'tile','e91df8ffff'),(0x430AD8,'tile','e954fdffff'),
    (0x430B0A,'tile','89ec5d5f5e'))
EPILOGUES=dict(tile='89ec5d5f5e595bc3',unit='89ec5d5f5ec20400',
    adjacent='83c4045d5f5ec3',vertical='5a59c3',count='83c4045d5f5e5a595bc3')
EPILOGUE_SITES=dict(tile=(0x430B0A,0x430B12),unit=(0x42FA8F,0x42FA97),
    adjacent=(0x42FED6,0x42FEDD),vertical=(0x42F7E5,0x42F7E8),count=(0x426F6B,0x426F75))
NATIVE_HIGHLOW=(0x430462,0x42F9CC,0x42FCC6,0x42FD5A,0x43003C,0x4300FA,0x43038F,
    0x43041E,0x4304CE,0x430533,0x430574,0x43059D,0x430680,0x4306C1,0x4306ED,0x4307B2,0x430810)

@dataclass(frozen=True)
class CodeEmission:
    base_va:int
    state_va:int
    code:bytes
    entries:tuple
    relocations:tuple
    width:int
    height:int
    private_entries:tuple
    planned_hooks:tuple
    field_call_patches:tuple
    reused_blocks:tuple
    unsafe_va:int

@dataclass(frozen=True)
class BattleProfileContinuationBundle:
    emission:CodeEmission
    content_bundle:object
    metadata_json:str
    hook_sites:tuple=()
    removed_highlow_rvas:tuple=()
    def metadata(self):return json.loads(self.metadata_json)

def _require(value,message):
    if not value:raise ValueError(message)

def _sha(data):return hashlib.sha256(data).hexdigest()

def _snapshot():
    _require(Path(__file__).resolve()==ROOT/SOURCE,'canonical continuation source required')
    content_path=ROOT/CONTENT; data=content_path.read_bytes()
    _require(_sha(data)==CONTENT_SHA256,'frozen checked content differs')
    tree=ast.parse(data);pins=next(n for n in tree.body if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='PINNED_SOURCES' for t in n.targets))
    # These symbolic keys/values are fixed by the whole frozen content digest.
    env={};constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and isinstance(node.value,ast.Constant):constants[target.id]=node.value.value
    for key,value in zip(pins.value.keys,pins.value.values):
        k=constants[key.id] if isinstance(key,ast.Name) else ast.literal_eval(key)
        v=constants[value.id] if isinstance(value,ast.Name) else ast.literal_eval(value)
        env[k]=v
    env[CONTENT]=CONTENT_SHA256;env[SOURCE]=None
    result={}
    for name,digest in env.items():
        path=ROOT/name
        _require(path.resolve(strict=True)==path and path.is_relative_to(ROOT),'canonical continuation dependency required')
        before=path.stat();raw=path.read_bytes();after=path.stat()
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
        _require(stamp(before)==stamp(after) and (digest is None or _sha(raw)==digest),'pinned continuation dependency differs: '+name)
        result[name]=(raw,stamp(after))
    return result

@contextmanager
def _modules(snapshot):
    prefix='_clash95_battle_continuation_'+uuid.uuid4().hex;saved_path=list(sys.path)
    try:
        for suffix in ('','.src','.src.patcher'):
            m=types.ModuleType(prefix+suffix);m.__path__=[];sys.modules[m.__name__]=m
            if suffix:
                par,_,leaf=m.__name__.rpartition('.');setattr(sys.modules[par],leaf,m)
        result={}
        for stem in ('framed_viewport','pe_extension','partial_tile_clip','framed_battle_viewport','framed_battle_coordinates',
            'framed_battle_field','framed_modal_canvas','framed_battle_hud','battle_profile_context','battle_profile_lifecycle',
            'battle_profile_routing','battle_profile_field','battle_profile_field_v2','battle_profile_stack_lease',
            'battle_profile_content','battle_profile_continuation'):
            name='src/patcher/'+stem+'.py';full=prefix+'.src.patcher.'+stem
            m=types.ModuleType(full);m.__file__=str(ROOT/name);m.__package__=full.rpartition('.')[0]
            m.__loaded_source_sha256__=_sha(snapshot[name][0]);sys.modules[full]=m
            setattr(sys.modules[m.__package__],stem,m)
            exec(compile(snapshot[name][0],m.__file__,'exec'),m.__dict__);result[name]=m
        yield result
    finally:
        for name in list(sys.modules):
            if name==prefix or name.startswith(prefix+'.'):del sys.modules[name]
        sys.path[:]=saved_path

def _replace_once(text,old,new):
    _require(text.count(old)==1,'frozen admission composition boundary differs')
    return text.replace(old,new)

def _guard_producer(content,source):
    """Fixed versioned composition of an authenticated source-owned guard.

    Its 640B ABI and payload dependencies remain unchanged. The two-CALL
    receipt is stronger than the predecessor body CALL receipt. No public
    entry or caller-selected offset bypasses the frozen guard.
    """
    tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_emit_code')
    text=ast.get_source_segment(source.decode(),node)
    text=_replace_once(text,'def _emit_code(plan,lease_emission,*,assembler_module):',
        'def _emit_guard(plan,lease_emission,*,assembler_module,guard_base,admission_sites,thunk_returns):')
    text=_replace_once(text,'base=(parent.base_va+len(parent.code)+15)&~15','base=guard_base')
    start=text.index('    for number,row in enumerate(SITES):\n');end=text.index('    # Only outer helper paths',start)
    text=text[:start]+text[end:]
    text=_replace_once(text,"tuple((f'site_{va:06x}',base+a.labels[f'site_{va:06x}']) for va,*_ in SITES)",'()')
    text=_replace_once(text,'extent(7,HELPER_BYTES+56,reject)','extent(7,HELPER_BYTES+96,reject)')
    text=_replace_once(text,'    get(7,NATIVE_S);extent(7,4,reject)\n',
        '    get(7,NATIVE_S);extent(7,4,reject);put(7,516)\n'
        '    get(0,HELPER_BYTES+36);put(0,512)\n'
        '    for off in range(0,52,4):get(0,HELPER_BYTES+40+off);put(0,528+off)\n')
    start=text.index('    for number,(va,raw,family,op,dx,dy) in enumerate(SITES):',text.index("a.label('admit_body')"))
    end=text.index("    jump(reject)\n    a.label('site_receipt.matched')",start)
    text=text[:start]+'''    for number,(va,family,role) in enumerate(admission_sites):
        get(0,SITE);cmp(0,number);ne(f'site_receipt.next.{number}')
        load(0,7,0);cmpva(0,va+5,'source-owned natural outer CALL return PC');ne(reject)
        get(0,512);cmpva(0,thunk_returns[number],'source-owned intrinsic thunk CALL return PC');ne(reject)
        imm(0,5 if family=='field' else FAMILIES.index(family));put(0,KIND)
        jump('site_receipt.matched');a.label(f'site_receipt.next.{number}')
'''+text[end:]
    text=_replace_once(text,"    for number,family in enumerate(FAMILIES):\n", "    for number,family in enumerate(FAMILIES+('field',)):\n")
    text=_replace_once(text,"        get(7,NATIVE_S);add(7,4-BODY_SP[family]);put(7,NATIVE_S)\n",
        "        get(7,NATIVE_S);add(7,4 if family=='field' else 4-BODY_SP[family]);put(7,NATIVE_S)\n")
    text=_replace_once(text,"    a.label('ancestry.count')\n",'''    a.label('ancestry.field')
    put(7,FIELD_EBP);extent(7,FIELD_BYTES+40,reject)
    get(0,INPUT+8);a.emit('39f8');ne(reject)
    get(0,SITE);cmp(0,len(admission_sites)-2);eq('field.mode.full')
    imm(0,1);jump('field.mode.done');a.label('field.mode.full');imm(0,0)
    a.label('field.mode.done');put(0,MODE);jump('field.owner')
    a.label('ancestry.count')
''')
    text=_replace_once(text,'    get(7,FIELD_EBP);load(0,7,FIELD_BYTES+8);put(0,LEASE_EBP)',
        "    a.label('field.owner');get(7,FIELD_EBP);load(0,7,FIELD_BYTES+8);put(0,LEASE_EBP)")
    text=_replace_once(text,"    load(0,7,44);a.emit('85c0');ne(reject);load(0,7,52);load(1,7,56);a.emit('39c8');ne(reject)\n",
        '''    load(0,7,44);a.emit('85c0');eq('lease.no.loss')
    cmp(0,2);ne(reject);get(0,SITE);cmp(0,29);a.branch('0f82',reject)
    load(0,7,48);cmp(0,2);ne(reject);jump('lease.loss.done')
    a.label('lease.no.loss');load(0,7,48);cmp(0,1);a.branch('0f87',reject)
    a.label('lease.loss.done');load(0,7,52);load(1,7,56);a.emit('39c8');ne(reject)
''')
    text=_replace_once(text,"cmp(0,0x10000);a.branch('0f83',reject);load(0,7,48);cmp(0,1);a.branch('0f87',reject)",
        "cmp(0,0x10000);a.branch('0f83',reject)")
    before_current='''    get(0,HELPER_BYTES+36);match(0,512);ne(reject)
    for off in range(0,52,4):get(0,HELPER_BYTES+40+off);match(0,528+off);ne(reject)
'''
    text=_replace_once(text,"    own('fixed_receipt');cmp(0,1);ne(reject)\n    get(7,LEASE_EBP)\n",
        "    own('fixed_receipt');cmp(0,1);ne(reject)\n"+before_current+"    get(7,LEASE_EBP)\n")
    # The current V2 check_invocation helper is callback-free. Before that
    # cached read, compare every owned local and control DWORD around Thread.
    text=_replace_once(text,"    a.emit('fcff15');address(THREAD_IAT,'fixed content owning ThreadId callback')\n",
        '''    a.emit('89ef');add(7,-784);extent(7,1520,reject)
    a.emit('81ec000300008d75fc89e7b9b9000000fcf3a5')
    a.emit('fcff15');address(THREAD_IAT,'fixed successor owning ThreadId callback')
    a.emit('508d7424048d7dfcb9b9000000fcf3a7');ne('callback.reject')
    a.emit('5881c400030000')
''')
    text=_replace_once(text,"    get(7,FIELD_EBP);load(0,7,1124);put(0,WORLD)\n",
        before_current+"    get(7,FIELD_EBP);load(0,7,1124);put(0,WORLD)\n")
    text=_replace_once(text,"    a.label(reject);a.emit('31c0c3')\n",
        # Thread may have changed the live input slot. Its original EAX is
        # snapshot DWORD 432, addressed at ESP+436 after pushing ThreadId.
        # Discard only our private snapshot and stop without using a changed
        # guard/native return word or claiming a healthy unwind.
        "    a.label('callback.reject');a.emit('8b8424b401000081c404030000');imm(2,0)\n"
        "    a.label('guard_callback_unsafe');a.emit('0f0b')\n"
        "    a.label(reject);get(0,INPUT+28);imm(2,0);a.label('guard_unsafe');a.emit('0f0b')\n")
    text=_replace_once(text,"('capture_inputs','capture_stack','admit_body','fixed_receipt')",
        "('capture_inputs','capture_stack','admit_body','fixed_receipt','guard_unsafe','guard_callback_unsafe')")
    scope=dict(content.__dict__);exec(compile(text,str(ROOT/SOURCE)+':fixed_guard','exec'),scope)
    return scope['_emit_guard']

def _payload_receipts(parent,content,assembler):
    _require(type(parent.code) is bytes and type(parent.entries) is tuple and type(parent.private_entries) is tuple,
        'immutable checked payload required')
    _require(tuple(dict(parent.entries))==tuple(f'site_{v:06x}' for v,*_ in content.SITES),'fixed payload entries required')
    private=dict(parent.private_entries);entries=dict(parent.entries);result=[]
    assembler.absolute_relocation_offsets(parent)
    for number,(va,*_) in enumerate(content.SITES):
        off=entries[f'site_{va:06x}']-parent.base_va
        raw=parent.code[off:off+69]
        _require(len(raw)==69 and raw[:11]==b'\x9c\x60\xfc\x81\xec'+struct.pack('<I',640)+b'\x89\xe5',
            'frozen payload frame prefix differs')
        _require(raw[16:27]==b'\xb8'+struct.pack('<I',number)+b'\x89\x85'+struct.pack('<I',200) and
            raw[52]==0xE8 and raw[57:63]==b'\x81\xf8\x01\0\0\0' and raw[63:65]==b'\x0f\x85',
            'frozen checked payload boundary differs')
        for at,target in ((off+12,private['capture_inputs']),(off+53,private['admit_body'])):
            rows=[r for r in parent.relocations if r.offset==at and r.kind=='rel32' and r.target==target]
            _require(len(rows)==1 and parent.base_va+at+4+struct.unpack_from('<i',parent.code,at)[0]==target,
                'frozen prefix relocation differs')
        result.append((va,entries[f'site_{va:06x}']+69))
    # Every reused payload and the shared finish are bound to the whole exact
    # privately reconstructed emission, not caller-provided booleans/labels.
    return tuple(result)

def _emit_code(plan,content_emission,lease_emission,field_emission,*,assembler_module):
    """Pure fixture boundary; production privately reconstructs all parents."""
    snapshot=_snapshot()
    with _modules(snapshot) as modules:
        content=modules[CONTENT];clip=assembler_module
        rx,state,width,height,field_check=content._layout(plan,lease_emission)
        private_clip=modules['src/patcher/partial_tile_clip.py']
        modal=None if plan['profile'] in ('classic','framed') else state-256
        life=modules['src/patcher/battle_profile_lifecycle.py']._emit_code(plan,modal_state_va=modal,assembler_module=private_clip)
        route=modules['src/patcher/battle_profile_routing.py']._emit_code(plan,life,modal_state_va=modal,assembler_module=private_clip)
        canonical_field=modules[FIELD]._emit_code(plan,route,assembler_module=private_clip)
        canonical_lease=modules[LEASE]._emit_code(plan,canonical_field,assembler_module=private_clip)
        expected=content._emit_code(plan,canonical_lease,assembler_module=private_clip)
        def rows(out):return tuple((r.offset,r.kind,r.target,r.purpose) for r in out.relocations)
        for supplied,canonical in ((field_emission,canonical_field),(lease_emission,canonical_lease)):
            _require(supplied.base_va==canonical.base_va and supplied.state_va==canonical.state_va and
                (supplied.width,supplied.height)==(canonical.width,canonical.height) and supplied.code==canonical.code and
                supplied.entries==canonical.entries and supplied.private_entries==canonical.private_entries and
                rows(supplied)==rows(canonical),'complete canonical continuation producer bytes/ABI required')
        _require(lease_emission.field_return_pcs==canonical_lease.field_return_pcs and
            lease_emission.lease_return_pcs==canonical_lease.lease_return_pcs,'complete source-owned native return layout required')
        _require(content_emission.base_va==expected.base_va and content_emission.state_va==expected.state_va and
            (content_emission.width,content_emission.height)==(expected.width,expected.height) and content_emission.code==expected.code and
            content_emission.entries==expected.entries and content_emission.private_entries==expected.private_entries and
            rows(content_emission)==rows(expected),'exact frozen content emission required')
        _require(field_emission.base_va+len(field_emission.code)<=lease_emission.base_va and
            field_emission.state_va==state and (field_emission.width,field_emission.height)==(width,height),
            'matching frozen field required')
        clip.absolute_relocation_offsets(field_emission)
        payloads=dict(_payload_receipts(content_emission,content,clip))
        base=(content_emission.base_va+len(content_emission.code)+15)&~15
        a=clip._Assembler(base);local_calls=[];hooks=[];thunk_returns=[]
        admissions=[(va,family,'content') for va,raw,family,*_ in content.SITES]
        admissions.append((0x42F956,'unit','count_entry'))
        admissions.extend((va,family,'post') for va,family,_ in POST_WINDOWS)
        # Authenticate the actual two V2 CALL instructions following Tile.
        post_calls=[]
        for mode,tile_pc in lease_emission.field_return_pcs:
            at=tile_pc-field_emission.base_va
            _require(field_emission.code[at:at+1]==b'\xe8','fixed post-Tile CALL opcode required')
            target=tile_pc+5+struct.unpack_from('<i',field_emission.code,at+1)[0]
            _require(target==dict(field_emission.private_entries)['same_invocation'] and len([r for r in field_emission.relocations if r.offset==at+1 and
                r.kind=='rel32' and r.target==target])==1,'fixed post-Tile complete receipt CALL required')
            post_calls.append((mode,tile_pc,at))
        _require(tuple(x[0] for x in post_calls)==(0,1),'two ordered post-Tile calls required')
        admissions.extend((pc,'field','field') for _,pc,_ in post_calls)
        def imm(reg,val):a.emit(f'{0xB8+reg:02x}');a.u32(val)
        def add(reg,val):a.emit(f'81{0xC0+reg:02x}');a.u32(val)
        def mem(op,reg,bas,off):
            a.emit(op+f'{0x80|(reg<<3)|bas:02x}')
            if bas==4:a.emit('24')
            a.u32(off)
        def get(reg,off):mem('8b',reg,5,off)
        def put(reg,off):mem('89',reg,5,off)
        def call(label):
            a.emit('e8');at=len(a.code);a.u32(0);a.fixups.append((at,label));local_calls.append((at,label))
        def transfer(target,purpose,opcode='e9'):
            a.emit(opcode);at=len(a.code);a.relocations.append(clip.Relocation(at,'rel32',target,purpose));a.u32(target-base-at-4)
        def normal_restore():a.emit('83c410619d8d642404')
        def replay(raw,va,relocs):
            """Only the fixed small instruction windows listed above."""
            pos=0
            while pos<len(raw):
                # All branch encodings in this bounded ledger are terminal or
                # have at most one fixed short condition before scalar replay.
                if raw[pos]==0xE9:
                    target=va+pos+5+struct.unpack_from('<i',raw,pos+1)[0]
                    transfer(target,'exact native scalar JMP replay');pos+=5;continue
                if 0x70<=raw[pos]<=0x7F:
                    target=va+pos+2+struct.unpack_from('<b',raw,pos+1)[0]
                    transfer(target,'exact native short condition replay','0f'+f'{raw[pos]+16:02x}');pos+=2;continue
                if raw[pos:pos+2] in (b'\x0f\x85',):
                    target=va+pos+6+struct.unpack_from('<i',raw,pos+2)[0]
                    transfer(target,'exact native condition replay',raw[pos:pos+2].hex());pos+=6;continue
                # Branch bytes occurring inside immediates must never be
                # interpreted as opcodes: the authored remainder instructions
                # have complete fixed operand lengths.
                size=_scalar_length(raw,pos)
                start=len(a.code);a.emit(raw[pos:pos+size].hex())
                for old in relocs:
                    if pos<=old<pos+size:
                        _require(old+4<=pos+size,'native relocation splits scalar instruction')
                        target=struct.unpack_from('<I',raw,old)[0]
                        a.relocations.append(clip.Relocation(start+old-pos,'abs32',target,'exact stolen native HIGHLOW replay'))
                pos+=size
        windows=dict(CONTENT_WINDOWS)
        native_highlow=set(NATIVE_HIGHLOW)
        for number,(va,family,role) in enumerate(admissions):
            name=f'adapter_{number}';a.label(name)
            # 16 explicit local bytes plus the original PUSHFD/PUSHAD receipt.
            a.emit('9c60fc83ec10c7042400000000c744240400000000c7442408');a.u32(number)
            a.emit('c744240c');a.u32(5 if family=='field' else content.FAMILIES.index(family))
            call('helper');thunk_returns.append(base+len(a.code))
            a.emit('83fa01');a.branch('0f84',name+'.valid')
            a.branch('e9','fault_dispatch')
            a.label(name+'.valid')
            if role=='content':
                operand=bytes.fromhex(content.SITES[number][1]);modrm=operand[2] if operand[0] in (0x0F,0x66) else operand[1]
                dest=(modrm>>3)&7;offset={0:44,1:40,2:36,3:32,5:24,6:20,7:16}[dest]
                if operand[0]==0x66:mem('66'+'89',0,4,offset)
                elif operand[0]==0x8A:mem('88',0,4,offset)
                else:mem('89',0,4,offset)
                normal_restore();raw=bytes.fromhex(windows[va]);tail=raw[len(operand):]
                replay(tail,va+len(operand),tuple(h-va-len(operand) for h in native_highlow if va+len(operand)<=h<va+len(raw)))
                transfer(va+len(raw),'exact guarded native scalar continuation')
            elif role=='count_entry':
                a.emit('83c410619d');transfer(0x426EF0,'guarded native Count entry with natural original return word')
            elif role=='post':
                normal_restore();raw=bytes.fromhex(next(raw for pc,fam,raw in POST_WINDOWS if pc==va))
                replay(raw,va,tuple(h-va for h in native_highlow if va<=h<va+len(raw)))
                transfer(va+len(raw),'exact post-normal-return continuation')
            else:
                a.emit('c744242c01000000');a.emit('83c410619dc3')
            if role!='field':
                old=bytes.fromhex(windows[va] if role=='content' else 'e8'+struct.pack('<i',0x426EF0-0x42F95B).hex() if role=='count_entry'
                    else next(raw for pc,fam,raw in POST_WINDOWS if pc==va))
                hooks.append((va,old,base+a.labels[name],role,tuple(h-0x400000 for h in native_highlow if va<=h<va+len(old))))
        a.label('fault_dispatch');a.emit('83fa02');a.branch('0f85','unsafe')
        a.emit('837c240401');a.branch('0f85','unsafe')
        a.emit('8b3c24c7472c02000000c7473002000000')
        for number,family in enumerate(content.FAMILIES+('field',)):
            a.emit('837c240c'+f'{number:02x}');a.branch('0f85','fault.next.'+family)
            if family=='field':a.emit('c744242c0000000083c410619dc3')
            else:normal_restore();a.emit(EPILOGUES[family])
            a.label('fault.next.'+family)
        a.label('unsafe');a.emit('0f0b')
        a.label('helper');a.emit('9c60fc81ec');a.u32(640);a.emit('89e5')
        transfer(dict(content_emission.private_entries)['capture_inputs'],'private frozen input capture','e8')
        get(0,688);put(0,200)
        a.emit('89e8');add(0,732);put(0,208)
        call('admit_body');a.emit('83f801');a.branch('0f85','helper.denied')
        # Only fully admitted own control can authorize normal cleanup.
        get(0,224);put(0,680);imm(0,1);put(0,684)
        for number,(va,family,role) in enumerate(admissions[:29]):
            get(0,200);a.emit('3d');a.u32(number);a.branch('0f85',f'payload.next.{number}')
            if role=='content':
                if va==0x42F9C3:
                    get(0,400);a.emit('a907000000');a.branch('0f85','helper.fault')
                    a.emit('83f840');a.branch('0f83','helper.fault')
                if va==0x42F9EC:
                    get(6,216);mem('8b',0,6,-28);a.emit('3daa020000');a.branch('0f83','helper.fault')
                    a.emit('31d2b91f000000f7f1');a.emit('85d2');a.branch('0f85','helper.fault')
                    a.emit('6bc01f');get(1,372);a.emit('01c8');mem('3b',0,5,420);a.branch('0f85','helper.fault')
                transfer(payloads[va],'authenticated checked payload and common 640B finish')
            elif role=='count_entry':
                get(0,428);get(7,372);a.emit('29f8');add(0,-852);a.emit('3daa020000');a.branch('0f83','helper.fault')
                a.emit('31d2b91f000000f7f1');a.emit('85d2');a.branch('0f85','helper.fault')
                get(0,428);mem('0fb7',1,0,4);mem('3b',1,7,804);a.branch('0f83','helper.fault')
                mem('0fb7',1,0,6);mem('3b',1,7,800);a.branch('0f83','helper.fault')
                imm(2,1);a.branch('e9','helper.finish')
            a.label(f'payload.next.{number}')
        get(7,224);mem('8b',0,7,44);a.emit('85c0');a.branch('0f85','helper.fault')
        get(0,428);imm(2,1);a.branch('e9','helper.finish')
        a.label('helper.denied');get(0,428);imm(2,0);a.label('helper_unsafe');a.emit('0f0b')
        a.label('helper.fault');get(0,428);imm(2,2)
        a.label('helper.finish')
        # Use the exact frozen common finish, which returns through our CALL.
        last=dict(content_emission.entries)[f'site_{content.SITES[-1][0]:06x}']-content_emission.base_va
        denied=last+69+struct.unpack_from('<i',content_emission.code,last+65)[0]
        _require(content_emission.code[denied:denied+6]==b'\xba\0\0\0\0\xe9','frozen denial finish branch differs')
        finish=denied+10+struct.unpack_from('<i',content_emission.code,denied+6)[0]
        _require(finish>=last and content_emission.code[finish:finish+6]==b'\x8b\x85\xac\x01\0\0',
            'frozen common finish boundary differs')
        transfer(content_emission.base_va+finish,'authenticated shared finish retaining rejection input')
        # Fixed guard producer supplies only source-owned body/control code.
        guard_base=(base+len(a.code)+5+15)&~15
        guard=_guard_producer(content,snapshot[CONTENT][0])(plan,lease_emission,assembler_module=clip,
            guard_base=guard_base,admission_sites=tuple(admissions),thunk_returns=tuple(thunk_returns))
        a.label('admit_body');transfer(dict(guard.private_entries)['admit_body'],'versioned natural two-CALL admission')
        code=bytes(a.finish())
        for off,label in local_calls:a.relocations.append(clip.Relocation(off,'rel32',base+a.labels[label],'private continuation '+label))
        _require(base+len(code)<=guard.base_va,'guard composition alignment differs')
        code+=b'\x90'*(guard.base_va-base-len(code))+guard.code
        offset=guard.base_va-base
        a.relocations.extend(clip.Relocation(r.offset+offset,r.kind,r.target,r.purpose) for r in guard.relocations)
        _require(base+len(code)<=rx+0x20000,'continuation exceeds unchanged RX reservation')
        patches=tuple((pc,field_emission.code[at:at+5],base+a.labels['adapter_'+str(len(admissions)-2+mode)])
            for mode,pc,at in post_calls)
        out=CodeEmission(base,state,code,tuple((f'adapter_{n}',base+a.labels[f'adapter_{n}']) for n in range(len(admissions))),
            tuple(a.relocations),width,height,(('helper',base+a.labels['helper']),('admit_body',base+a.labels['admit_body']),
                ('helper_unsafe',base+a.labels['helper_unsafe']),('guard_unsafe',dict(guard.private_entries)['guard_unsafe']),
                ('guard_callback_unsafe',dict(guard.private_entries)['guard_callback_unsafe'])),
            tuple(hooks),patches,tuple((va,payload,_sha(content_emission.code)) for va,payload in payloads.items()),base+a.labels['unsafe'])
        clip.absolute_relocation_offsets(out)
        _require(_snapshot()==snapshot,'continuation source changed during composition')
        return out

def _scalar_length(raw,pos):
    """Instruction lengths for this closed small replay ledger only."""
    tail=raw[pos:];op=tail[0]
    if op==0x3A:return 2 if tail[1]&0xC0==0xC0 else 6
    if op in (0x31,0x39,0x85,0x01):return 2 if tail[1]&0xC0==0xC0 else 7
    if op in (0x43,0x5D,0x5F,0x5E):return 1
    if op==0x83:return 4 if tail[1]==0x7D else 3
    if op==0x6B:return 3
    if op in (0xA1,0xA3,0xBA):return 5
    if op==0x03:return 6
    if op==0x3B:return 6
    if op==0x8B:return 3 if tail[1] in (0x45,0x55,0x5D,0x7D) else 3 if tail[1]==4 else 6
    if op==0x8D:return 7
    if op==0x89:return 2
    raise ValueError('unsupported scalar replay encoding')

def _authenticate_native(original,candidate,clip,content,lease,pe):
    inventory=content._authenticate_native(original,candidate,clip);lease._authenticate_native_abi(original,candidate,clip)
    windows=list(CONTENT_WINDOWS)+[(va,raw) for va,_,raw in POST_WINDOWS]
    windows.append((0x42F956,'e8'+struct.pack('<i',0x426EF0-0x42F95B).hex()))
    for image in (original,candidate):
        parsed=pe.inspect_pe(image);_,relocations=pe._old_relocations(image,parsed)
        actual={parsed.image_base+rva for rva in relocations if any(va<=parsed.image_base+rva<va+len(bytes.fromhex(raw)) for va,raw in windows)}
        _require(actual==set(NATIVE_HIGHLOW),'complete stolen native HIGHLOW inventory differs')
        for va,value in windows:
            raw=bytes.fromhex(value);at=clip.file_offset(image,va,len(raw))
            _require(image[at:at+len(raw)]==raw,'whole native continuation window differs')
        for family,(lo,hi) in EPILOGUE_SITES.items():
            raw=bytes.fromhex(EPILOGUES[family]);at=clip.file_offset(image,lo,len(raw))
            _require(len(raw)==hi-lo and image[at:at+len(raw)]==raw,'complete native cleanup epilogue differs')
    return inventory

def _emit_authenticated(original,profile,resolution):
    _require(type(original) is bytes and _sha(original)==BASE_SHA256,'exact continuation original required')
    snapshot=_snapshot()
    _require(globals().get('__loaded_source_sha256__')==_sha(snapshot[SOURCE][0]),'private continuation producer required')
    with _modules(snapshot) as modules:
        parent=modules[CONTENT].emit_battle_profile_content(original,profile,resolution)
        metadata=parent.metadata();plan=metadata['allocation_plan']
        context=modules[CONTEXT].build_parent_context(original,profile,resolution)
        _require(context.allocation_plan()==plan,'independent canonical continuation parent required')
        clip=modules['src/patcher/partial_tile_clip.py']
        _authenticate_native(original,context.candidate,clip,modules[CONTENT],modules[LEASE],modules['src/patcher/pe_extension.py'])
        field=parent.lease_bundle.field_bundle.emission
        emission=_emit_code(plan,parent.emission,parent.lease_bundle.emission,field,assembler_module=clip)
        result=dict(schema='clash95_battle_profile_continuation_v1',profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=plan['candidate_sha256'],allocation_plan=plan,
            source_hashes=metadata['source_hashes']|{name:_sha(data) for name,(data,_) in snapshot.items()},
            content_code_sha256=_sha(parent.emission.code),content_metadata_sha256=_sha(parent.metadata_json.encode()),
            code_va=emission.base_va,code_bytes=len(emission.code),code_sha256=_sha(emission.code),
            helper_frame_bytes=640,thunk_frame_bytes=52,private_callback_snapshot_bytes=768,
            maximum_owned_helper_stack_extent=1520,field_frame_bytes=1280,owning_lease_frame_bytes=192,
            planned_native_windows=[dict(va=va,rva=va-0x400000,file_offset=clip.file_offset(original,va,len(raw)),
                old_bytes=raw.hex(),new_bytes=(b'\xe8'+struct.pack('<i',target-va-5)+b'\x90'*(len(raw)-5)).hex(),
                target_va=target,role=role,removed_highlow_rvas=list(removed),group='battle_profile_continuation_preparation')
                for va,raw,target,role,removed in emission.planned_hooks],
            planned_field_calls=[dict(va=va,code_offset=va-field.base_va,owner='frozen field v2',
                old_bytes=raw.hex(),new_bytes=(b'\xe8'+struct.pack('<i',target-va-5)).hex(),target_va=target)
                for va,raw,target in emission.field_call_patches],
            reused_checked_payloads=[dict(native_va=va,payload_va=ptr,parent_code_sha256=digest) for va,ptr,digest in emission.reused_blocks],
            unsafe_va=emission.unsafe_va,unsafe_vas=[emission.unsafe_va]+[va for name,va in emission.private_entries if name.endswith('_unsafe')],
            unsafe_behavior='UD2 preparation endpoints; no native continuation or healthy unwind',
            denial_value='captured incoming EAX retained for modeled input/control denial; unknown control stops UNSAFE without a native return',fault_is_empty=False,
            unit_index_minus_one_record_proven=False,unit_type_minus_one_valid_record_count_allowed=True,
            count_entry_pre_read_guard_emitted=True,natural_two_call_ancestry=True,
            installed=False,battle_installed=False,expanded_battle_installed=False,source_candidate_installed=False,
            installation_ready=False,standalone_native_callsite_replacement_safe=False,preparation_only=True,
            runtime_executed=False,runtime_verified=False,manual_input_proof=False,manual_input_verified=False,
            promotion_ready=False,release_accepted=False,provider_validity_verified=False,native_receiver_validity_verified=False,
            native_argument_validity_verified=False,physical_only_clip_admission_verified=False,arena_intersection_verified=False,
            intra_decoder_cancellation=False,provider_early_cancellation=False,process_quit_closure_verified=False,
            non_draw_count_admission=False,thread_lifetime_runtime_verified=False,
            writes_owner_state=False,writes_headers=False,writes_pixels=False,heap_or_global_descriptor=False,
            rx_remaining_bytes=plan['rx']['va']+0x20000-emission.base_va-len(emission.code),
            limitations=[
                'These planned hooks and field CALL substitutions are uninstalled; no candidate or release gate is satisfied.',
                'Post-normal-return gates follow unchanged native primitive cleanup. They cannot stop reads inside RLE/provider callbacks or fatal native paths.',
                'Unknown ancestry/control never authorizes a native epilogue; the UNSAFE endpoint is an explicit unresolved installed failure policy.',
                'Unit index-1 reaches native Count with WORLD+821; that record domain is unproven and rejected, without empty/parity claims.',
                'Every original Unit caller predecessor/nonempty branch and provider producer invariant must be byte-backed before installation; no globally invalid sentinel claim is made.',
                'Count entry admission covers only Unit caller42F956; nondraw callers426F90 and431D75 remain untouched/unadmitted.',
                'Full atomic installation must still prove receiver/argument/provider lifetimes, terrain entry reads, arena clipping, animation/dialog/camera/input/quit families.',
                'Frozen field V2 remains unchanged; only a future installer applying both exact post-Tile CALL receipts can activate its loss-aware successor routing.',
                'Owning-thread snapshots do not establish runtime inter-thread immutability or native WORLD/provider allocation lifetime.',
            ])
        _require(_snapshot()==snapshot,'continuation source changed during public preparation')
    return BattleProfileContinuationBundle(emission,parent,json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))

def emit_battle_profile_continuation(original,profile,resolution):
    snapshot=_snapshot()
    with _modules(snapshot) as modules:result=modules[SOURCE]._emit_authenticated(original,profile,resolution)
    _require(_snapshot()==snapshot,'continuation source changed during public emission')
    return result
