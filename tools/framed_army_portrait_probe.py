#!/usr/bin/env python3
"""Pure preparation of two actual native portrait toggles, with bound commands.

The frozen selection-v3 preparation establishes real army3 first. Its copied
observers use a distinct baseline namespace and its final stop becomes a measured
baseline snapshot; no old HOST_READY is emitted before continued execution.
Only controlled mouse/button/stack writes are added. Selected indices, squads,
visibility, flags and native predicate results are never forced.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct

import framed_army_selection_probe as base

ROOT=base.ROOT
BASE_SHA256='52b517b641ca2e81d1892e71ab4c3c60ab722a05d97c2419dd2cc666349773a1'
REVISION='controlled_native_first_portrait_two_toggles_v1'
NATIVE_SPANS=((0x423860,593),(0x4608F0,13),(0x460900,13),(0x4609D0,52),(0x418700,25))
NATIVE_CALLS={0x4238D4:0x460D80,0x4238DE:0x460900,0x423932:0x4608F0,
              0x42395F:0x423420,0x42396B:0x418700,0x423975:0x4609D0,
              0x4609DB:0x4608F0,0x4609F7:0x460900}
LIMITS=[
    'Two controlled first-portrait calls follow direct native army selection; ordinary map dispatch and manual input are not proved.',
    'Mouse/button writes and native call injection are disclosed. No selected index, squad, visibility, flag or predicate result is forced.',
    'The controlled button release is applied before native release polling; zero query results are observed, not overwritten.',
    'The secondary map query runs after release, so its zero return proves no subsequent movement in this call, not held-button exclusion by itself.',
    'Three stopped E0 dumps do not prove pixels, final primary composition, host cleanup, endurance or promotion.',
    'This new baseline/toggle protocol requires its own complete validator; old selection stop markers are not fabricated or reused as final readiness.',
]


def sha(data):return hashlib.sha256(data).hexdigest()


def verify_sources():
    if sha(Path(base.__file__).read_bytes())!=BASE_SHA256:
        raise ValueError('frozen selection-v3 producer differs')
    return base.verify_sources()|{'tools/framed_army_selection_probe.py':BASE_SHA256}


def _guard(condition,body):
    return '.if ('+condition+') { '+body+' } .else { .echo PTGL_REJECT native_contract; q }'


def build_portrait_probe(original,candidate,save,*,capture_dir,minimap_viewport=True):
    """Return the whole deterministic main probe and three supplemental files.

    No file or process is created. A separate host must write exact immutable
    bytes, enforce a deadline, stop only on PTGL_HOST_READY and prove cleanup.
    """
    sources=verify_sources()
    prior=base.build_selection_probe(original,candidate,save,capture_dir=capture_dir,minimap_viewport=minimap_viewport)
    directory=prior['capture_dir'];read=lambda va,n:base._read(candidate,va,n)
    returns={f'{va:08x}':base._call_return(candidate,va,target) for va,target in NATIVE_CALLS.items()}
    old=read(0x423984,5)
    if old[0]!=0xE8:raise ValueError('bound secondary map CALL opcode differs')
    map_target=0x423989+struct.unpack('<i',old[1:])[0]
    for va,expected in ((0x423860,'5283ec2c'),(0x423952,'8034b5786f520001'),
                        (0x423A99,'c3'),(0x42397A,'bf01000000'),(0x423989,'85c0'),(0x4609D0,'535156')):
        if read(va,len(bytes.fromhex(expected)))!=bytes.fromhex(expected):raise ValueError(f'native portrait boundary differs at{va:08x}')
    p=base._printf
    same='(@$tid == @$t2) & (poi(005202e4) == @$t1) & (poi(005199d8) == 0040ad40) & (poi(00526990) == 0) & (poi(005202ec) == 0)'
    own=same+' & (poi(00511b58) == 3) & (poi(00514194) == 3) & (poi(00526994) == 1) & (poi(00526fa0) == @$t1+0n149349)'
    physical='(wo(poi(005202e0)) == 0n1024) & (wo(poi(005202e0)+2) == 0n768) & (poi(poi(005202e0)+b8) == 0050ee24) & (poi(poi(005202e0)+4) >= 00010000) & (poi(poi(005202e0)+4) <= fff40000)'
    other_flags=' & '.join(f'(poi({0x526F78+4*i:08x}) == 0)' for i in range(1,10))
    flags=lambda value:f'(poi(00526f78) == {value}) & '+other_flags
    after_flags=flags('(2-@$t10)');before_flags=flags('(@$t10-1)')
    toggle='((@$t10 == 1) | (@$t10 == 2))'
    def observation(kind):
        message='PTGL_OBS kind='+kind+' toggle=%d phase=%d tid=%x eip=%p esp=%p caller=%p eax=%x ecx=%x edx=%x esi=%x edi=%x selected=%d prior=%d lower=%d unit=%p mouse_raw=(%x,%x) shift=%x buttons=%x accumulator=%x flags=('+','.join(['%x']*10)+') draws=(%d,%d,%d)'
        args=['@$t10','@$t0','@$tid','@eip','@esp','poi(@esp)','@eax','@ecx','@edx','@esi','@edi','poi(00511b58)','poi(00514194)','poi(00526994)','poi(00526fa0)','poi(00544cfc)','poi(00544d00)','by(0054512c)','poi(00544d04)','by(005451c0)']
        args.extend(f'poi({0x526F78+4*i:08x})' for i in range(10));args.extend(['@$t5','@$t6','@$t7'])
        return p(message,*args)
    def body(phase,kind,extra='gc'):
        return f'r @$t0=0n{phase}; '+observation(kind)+(('; '+extra) if extra else '')
    records={}
    def add(number,va,previous,next_phase,kind,condition,extra='gc',flags_guard=None):
        records[number]=(va,_guard(own+' & '+toggle+f' & (@$t0 == 0n{previous}) & '+(flags_guard or after_flags)+' & '+condition,
                                  body(next_phase,kind,extra)))
    add(100,0x423861,20,21,'post-push','(@esp == @$t3-8) & (poi(@esp+4) == 00406fa1)',flags_guard=before_flags)
    add(101,0x4238CA,21,22,'portrait-hit','(@esp == @$t3-0n68) & (@esi == 0) & (@edi == 0) & (wo(poi(00526fa0)+6) == 0n16) & (poi(00544cfc) == (0n54 << by(0054512c))) & (poi(00544d00) == (0n719 << by(0054512c)))',flags_guard=before_flags)
    add(102,0x4238E3,22,23,'right-return','(@esp == @$t3-0n68) & (@eax == 0) & (@esi == 0)',flags_guard=before_flags)
    add(103,0x423937,23,24,'left-return','(@esp == @$t3-0n68) & (@eax == 1) & (@esi == 0)',flags_guard=before_flags)
    add(104,0x423952,24,25,'xor-before','(@esp == @$t3-0n68) & (@esi == 0) & (@eax == 0n16) & (wo(poi(00526fa0)+6) == 0n16)',flags_guard=before_flags)
    add(105,0x42395A,25,26,'xor-after','(@esp == @$t3-0n68) & (@esi == 0)')
    complete='(@$t5 == 2) & (@$t6 == 2) & (@$t7 == 1)'
    add(106,0x423964,26,27,'native-draw-return','(@esp == @$t3-0n68) & (@$t5 == 1) & (@$t6 == 1) & (@$t7 == 0)')
    add(107,0x418700,27,28,'map-entry','(@esp == @$t3-0n72) & (poi(@esp) == 00423970) & (@eax == 1) & (@edx == 0)')
    release=observation('release-before')+'; eb 005451c0 00; ed 00544d04 0; '+observation('release-after')+'; gc'
    add(108,0x423970,28,29,'map-return','(@esp == @$t3-0n68) & '+complete+' & (poi(00544d04) == 1) & (by(005451c0) == 0x80)',extra=release)
    add(109,0x4609D0,29,30,'release-entry','(@esp == @$t3-0n72) & (poi(@esp) == 0042397a) & (@eax == 00544cd8) & (@edx == 0) & (poi(00544d04) == 0) & (by(005451c0) == 0)')
    add(110,0x4609E0,30,31,'release-left-return','(@esp == @$t3-0n84) & (@eax == 0) & (poi(00544d04) == 0)')
    add(111,0x4609FC,31,32,'release-right-return','(@esp == @$t3-0n84) & (@eax == 0) & (poi(00544d04) == 0)')
    add(112,0x42397A,32,33,'release-return','(@esp == @$t3-0n68) & (@eax == 0) & (poi(00544d04) == 0)')
    add(113,0x423989,33,34,'secondary-map-return','(@esp == @$t3-0n68) & (@eax == 0) & (@esi == 0) & (@edi == 1) & (poi(00544d04) == 0)')
    add(114,0x423A99,34,35,'portrait-return','(@esp == @$t3-4) & (poi(@esp) == 00406fa1) & (@eax == 1) & '+complete)
    for number,va in ((115,0x423991),(116,0x423A59)):
        records[number]=(va,observation('forbidden-movement')+'; .echo PTGL_REJECT movement_route; q')
    native_return=prior['native_call_returns']['native_draw'];compose_return=prior['native_call_returns']['composition_draw']
    extra_commands={}
    start=lambda n: f'r @$t10=0n{n}; r @$t0=0n20; r @$t5=0; r @$t6=0; r @$t7=0; '+_guard(own+' & '+physical+' & '+before_flags+' & (@esp == @$t3)',
        'ed 00544cfc (0n54 << by(0054512c)); ed 00544d00 (0n719 << by(0054512c)); eb 005451c0 80; ed 00544d04 1; '+observation('begin')+
        '; r esp=@esp-4; ed @esp 00406fa1; r eip=00423860; gc')
    for index in range(3):
        path=f'{directory}/portrait-checkpoint-{index}.cdb'
        name='portrait-before' if index==0 else f'portrait-after-{index}'
        check=own+' & '+physical+' & (@esp == @$t3) & '+(flags('0') if index==0 else after_flags)
        if index==0:
            prefix='; '.join('bd '+str(i) for i in range(81,90))+'; '+'; '.join('be '+str(i) for i in records)+'; r @$t10=0; '
        else:prefix=''
        action=p(f'PTGL_SURFACE checkpoint={index} tid=%x eip=%p esp=%p surface=%p base=%p width=%d height=%d vtable=%p',
            '@$tid','@eip','@esp','poi(005202e0)','poi(poi(005202e0)+4)','wo(poi(005202e0))','wo(poi(005202e0)+2)','poi(poi(005202e0)+b8)')
        action+=f'; .writemem {directory}/{name}.header.raw poi(005202e0) L0n188; .writemem {directory}/{name}.raw poi(poi(005202e0)+4) L0n786432; '
        if index<2:action+=start(index+1)
        else:
            action+=observation('ready')+'; .echo PTGL_HOST_READY'
        text=prefix+_guard(check,action)+'\n'
        extra_commands[path]=text.replace(r'\"','"').replace(r'\\n',r'\n')
    quiet=lambda path:'$$>a<\\"'+path+'\\";'
    modifications={}
    compiled=prior['compiled_probe'].replace('SHSEL_','PTGL_BASE_')
    old_records={}
    for number in (80,90,91,92):
        matches=re.findall(r'^bp'+str(number)+r' ([0-9a-f]{8}) "(.*)"$',compiled,re.M)
        if len(matches)!=1:raise ValueError('frozen baseline observer grammar differs')
        old_records[number]=(int(matches[0][0],16),matches[0][1])
    baseline_stop=old_records[80][1]
    if baseline_stop.count('.echo PTGL_BASE_HOST_READY')!=1:raise ValueError('frozen baseline stop differs')
    baseline_stop=baseline_stop.replace('.echo PTGL_BASE_HOST_READY',quiet(f'{directory}/portrait-checkpoint-0.cdb'))
    stop_body='.if (@$t10 == 1) { '+quiet(f'{directory}/portrait-checkpoint-1.cdb')+' } .elsif (@$t10 == 2) { '+quiet(f'{directory}/portrait-checkpoint-2.cdb')+' } .else { .echo PTGL_REJECT toggle; q }'
    modifications[80]='.if (@$t0 < 0n20) { '+baseline_stop+' } .else { '+_guard(own+' & '+physical+' & '+after_flags+' & '+toggle+' & (@$t0 == 0n35) & (@esp == @$t3) & '+complete,stop_body)+' }'
    # 423860 body is64 below its entry; its423420 CALL adds4, that
    # routine saves76, and the preserving suffix hook adds40: S-188.
    # The unchanged full-map composition call is240 below418700 entry.
    draw_guard=own+' & '+after_flags+' & '+toggle+' & (@$t5 == @$t6) & '+f'(((@$t0 == 0n26) & (@$t5 == 0) & (@esp == @$t3-0n188) & (poi(@esp) == {native_return:08x})) | ((@$t0 == 0n28) & (@$t5 == 1) & (@esp == @$t3-0n312) & (poi(@esp) == {compose_return:08x})))'
    new_draw=_guard(draw_guard,'r @$t5=@$t5+1; r @$t8=@esp; r @$t9=poi(@esp); '+observation('draw-entry')+'; gc')
    modifications[90]='.if (@$t0 < 0n20) { '+old_records[90][1]+' } .else { '+new_draw+' }'
    for number,phase,kind,return_va in ((91,26,'draw-native-return',native_return),(92,28,'draw-composition-return',compose_return)):
        guard=own+' & '+after_flags+' & '+toggle+f' & (@$t0 == 0n{phase}) & (@$t9 == {return_va:08x}) & (@esp == @$t8+4) & (@eax == 1) & (@$t5 == @$t6+1)'
        body='r @$t6=@$t6+1; '+('r @$t7=@$t7+1; ' if number==92 else '')+observation(kind)+'; gc'
        modifications[number]='.if (@$t0 < 0n20) { '+old_records[number][1]+' } .else { '+_guard(guard,body)+' }'
    for number,command in modifications.items():
        compiled,count=re.subn(r'^bp'+str(number)+r' [0-9a-f]{8} ".*"$',lambda _:f'bp{number} {old_records[number][0]:08x} "{command}"',compiled,flags=re.M)
        if count!=1:raise ValueError('baseline observer replacement is not unique')
    checked={va+i:value for va,size in NATIVE_SPANS for i,value in enumerate(read(va,size))}
    conditions=[f'(by({va:08x}) != 0x{value:02x})' for va,value in sorted(checked.items())]
    bytechecks='\n'.join('.if ('+' | '.join(conditions[i:i+48])+') { .echo PTGL_REJECT loaded_bytes; q }' for i in range(0,len(conditions),48))+'\n.echo PTGL_BYTES_PASS\n'
    first=re.search(r'(?m)^bp[0-9]+ ',compiled)
    if first is None:raise ValueError('baseline has no native breakpoint declaration')
    compiled=compiled[:first.start()]+bytechecks+compiled[first.start():]
    if not compiled.endswith('g\n'):raise ValueError('baseline final resume grammar differs')
    startup='\n'.join(f'bp{number} {va:08x} "{command}"\nbd {number}' for number,(va,command) in records.items())+'\n'
    compiled=compiled[:-2]+startup+'g\n'
    all_commands=compiled+'\n'+'\n'.join(extra_commands.values())
    if max(map(len,all_commands.splitlines()))>=4096:raise ValueError('debugger line exceeds4096 transport limit')
    if all_commands.count('PTGL_HOST_READY')!=1 or 'PTGL_BASE_HOST_READY' in all_commands:
        raise ValueError('only the final portrait host readiness is permitted')
    verify_sources()
    return dict(schema='clash95_framed_army_portrait_probe_v1',revision=REVISION,stage=prior['stage'],resolution='1024x768',
        width=1024,height=768,original_sha256=prior['original_sha256'],candidate_sha256=prior['candidate_sha256'],save_sha256=prior['save_sha256'],
        capture_dir=directory,minimap_viewport=minimap_viewport,unit=3,slot=0,unit_xy=[16,19],unit_squad_types=[16,16,1,1,1,1,1,1],
        controlled_scroll=[10,17],controlled_mouse=[54,719],flag_vectors=[[0]*10,[1]+[0]*9,[0]*10],
        compiled_probe=compiled,probe_sha256=sha(compiled.encode('ascii')),initial_extra=prior['initial_extra'],initial_extra_sha256=prior['initial_extra_sha256'],
        supplemental_commands=extra_commands,supplemental_sha256={path:sha(text.encode('ascii')) for path,text in extra_commands.items()},
        source_sha256=prior['source_sha256']|sources,base_compiled_probe_sha256=prior['probe_sha256'],
        baseline_observer_vas=prior['observer_vas'],baseline_native_call_returns=prior['native_call_returns'],
        portrait_observer_vas={str(n):va for n,(va,_) in records.items()},portrait_native_call_returns=returns,
        guarded_secondary_map_target=map_target,loaded_native_spans=[dict(va=va,bytes=size,sha256=sha(read(va,size))) for va,size in NATIVE_SPANS],
        stack_offsets_from_sentinel=dict(portrait_entry=-4,portrait_body=-68,native_draw_helper=-188,
            map_entry=-72,composition_draw_helper=-312,release_entry=-72,release_query_return=-84,portrait_ret=-4),
        controlled_input=True,controlled_release=True,native_predicate_forced=False,selected_value_forced=False,flag_value_forced=False,
        runtime_executed=False,manual_input_proof=False,promotion_ready=False,limits=LIMITS)
