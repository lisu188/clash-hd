#!/usr/bin/env python3
"""Prepare native whole-army preview/confirmation on exact Complete-HD bytes.

The versioned Complete-HD selection protocol is copied under WMOV_BASE. The
frozen movement-v3 observers are preserved at all six supported resolutions.
Complete candidate reconstruction and startup provenance remain mandatory. A diagnostic
then calls the real world click handler twice, observes its pathfinder and
animation/occupancy commits, and stops after its true return. Only disclosed
mouse/button and native call-stack controls are written; no movement result,
unit, path, action point, selection or portrait flag is forced. No runtime is
executed and no output file is written by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import complete_hd_army_selection_probe as base

ROOT = base.ROOT
PARENT_SOURCE_SHA256 = 'ba7f2db5998cad455909b13c60aba1b1b80a31740a092422dc2ff7c014c6a5da'
REVISION = 'complete_hd_controlled_native_whole_army_outward_move_v1'
UNIT_OFFSET = 149349
INITIAL_AP = (26, 22, 16, 16, 16, 16, 16, 16)
PATH_WORDS = (0x000A1312, 0x00051311)
NATIVE_SPANS = ((0x4084A0, 0x1820), (0x410330, 0xE30), (0x411F60, 0xA0),
                (0x413910, 0x750), (0x4147A0, 0xD60), (0x4608F0, 29),
                (0x4609D0, 52), (0x418700, 25), (0x4605D0,0x250),
                (0x460A50,0x92), (0x47BFD0,0x180),
                (0x512568 + 88 + 29, 9), (0x512568 + 16*88 + 29, 9))
NATIVE_CALLS = {0x408568:0x4608F0, 0x40858F:0x40F0C0,
                0x40872E:0x460900, 0x4087DC:0x4608F0,
                0x4099DE:0x4082C0, 0x409A6C:0x4147A0,
                0x409BC5:0x411F60, 0x409C0E:0x410330,
                0x409C13:0x406980, 0x409CA6:0x4609D0,
                0x409CB0:0x418700, 0x4108DF:0x410170,
                0x4105E8:0x423B90, 0x4105F2:0x418700,
                0x410605:0x40A490, 0x410AF7:0x42B770,
                0x4609DB:0x4608F0, 0x4609F7:0x460900,
                0x414B3F:0x4605D0,0x410DAE:0x4605D0,0x410C91:0x4605D0,
                0x460A5C:0x47BFD0}
LIMITS = [
    'Controlled direct world-handler calls follow native selection; ordinary dispatch and manual input are not proved.',
    'Only mouse/button and injected native call-stack controls are written. No unit, path, AP, visibility, selection, flags or predicate result is forced.',
    'Exactly one outward move16,19 to18,19 is requested. Native desert cost5 gives expected total10; no return trip or AP refill is attempted.',
    'A queue becoming empty or AP being charged is insufficient: both native occupancy/XY commits and the final native redraw, ExecuteQueuedPath return and world-handler return are required.',
    'Native pathfinding, cursor changes and animation can refresh raw mouse/button state. Three bounded DD_Pump call/return observations are retained; they do not establish complete input-backend tracing or unchanged input between native calls. Only the two explicitly recorded release controls write button state. No input-query or HRESULT result is overridden.',
    'The pathfinder initially searches the source/target bounding rectangle, here the unique row19 corridor; unexpected queue count, cells or cumulative costs fail before confirmation.',
    'The three stopped E0 and unit dumps require independent full-protocol, state, pixel and host-ownership validation. No runtime, visual, manual or promotion result is asserted by preparation.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    parent = 'tools/framed_army_movement_probe.py'
    if sha((ROOT / parent).read_bytes()) != PARENT_SOURCE_SHA256:
        raise ValueError('frozen movement-v3 producer differs')
    return base.verify_sources() | {parent: PARENT_SOURCE_SHA256,
        'tools/complete_hd_army_movement_probe.py': sha(Path(__file__).read_bytes())}


def _guard(condition, body):
    context = base._printf('WMOV_REJECT_CONTEXT phase=%d tid=%x eip=%p esp=%p shift=%x raw=(%x,%x)',
        '@$t0','@$tid','@eip','@esp','by(0054512c)','poi(00544cfc)','poi(00544d00)')
    return '.if (' + condition + ') { ' + body + ' } .else { '+context+'; .echo WMOV_REJECT native_contract; q }'


def build_movement_probe(original, candidate, save, *, capture_dir, candidate_manifest, resolution):
    """Return one deterministic main probe and three exact quiet-command files."""
    sources = verify_sources()
    prior = base.build_selection_probe(original, candidate, save,
        capture_dir=capture_dir, candidate_manifest=candidate_manifest, resolution=resolution)
    width, height = prior['width'], prior['height']
    surface_size = width * height
    surface_maximum = 0x100000000 - surface_size
    directory = prior['capture_dir']
    read = lambda va, n: base._read(candidate, va, n)
    returns = {f'{va:08x}': base._call_return(candidate, va, target)
               for va, target in NATIVE_CALLS.items()}
    # Native metadata has road at+29; terrain profile2 (desert) is+30+2.
    for unit_type in (1, 16):
        if read(0x512568 + 88*unit_type + 32, 1) != b'\x05':
            raise ValueError('native desert movement cost differs')
    for va, expected in ((0x4084A0,'53515256575583ec58'),(0x409CBE,'c3'),
        (0x409C21,'c3'),(0x410615,'c3'),(0x410330,'53515655'),
        (0x410747,'8d04bd00000000'),(0x410AF3,'66895f02'),
        (0x409AB3,'f3a5'),(0x4147A0,'565581ecfc000000')):
        if read(va,len(bytes.fromhex(expected))) != bytes.fromhex(expected):
            raise ValueError(f'native movement boundary differs at{va:08x}')
    data = save[16:]
    for x, terrain in ((17,13),(18,15)):
        if (int.from_bytes(data[556374+200*x+38:556374+200*x+40],'little') != 0xFFFF
            or int.from_bytes(data[1400*x+14*19:1400*x+14*19+2],'little') != terrain
            or int.from_bytes(data[1400*x+14*19+4:1400*x+14*19+6],'little') != 0xFFFF
            or not (data[140081+x*13+(19>>3)] & (1<<(19&7)))
            or data[576374+100*x+19] != 0):
            raise ValueError('save destination corridor differs')
    p = base._printf
    unit = '(@$t1+0n149349)'
    own = ('(@$tid == @$t2) & (poi(005202e4) == @$t1) & (poi(005199d8) == 0040ad40)'
           ' & (poi(00526990) == 0) & (poi(005202ec) == 0) & (poi(00511b58) == 3)'
           ' & (poi(00514194) == 3) & (poi(00526994) == 1) & (poi(00526fa0) == @$t1+0n149349)'
           ' & (by(@$t1+0n149353) == 0)')
    own += ' & ' + ' & '.join(f'(poi({0x526F78+4*i:08x}) == 0)' for i in range(10))
    physical = (f'(wo(poi(005202e0)) == 0n{width}) & (wo(poi(005202e0)+2) == 0n{height})'
                ' & (poi(poi(005202e0)+b8) == 0050ee24)'
                f' & (poi(poi(005202e0)+4) >= 00010000) & (poi(poi(005202e0)+4) <= {surface_maximum:08x})')
    mouse = ('(poi(00544cfc) == (0n576 << by(0054512c)))'
             ' & (poi(00544d00) == (0n176 << by(0054512c)))'
             ' & (by(0054512c) <= 0n21)')
    def ap(cost):
        return ' & '.join(f'(by(@$t1+0n{UNIT_OFFSET+14+31*i}) == 0n{v}-{cost})'
                          for i,v in enumerate(INITIAL_AP))
    def xy(x):
        return f'(wo({unit}) == {x}) & (wo({unit}+2) == 0n19)'
    queue = f'(poi({unit}+0n316) == 2) & (poi({unit}+0n320) == 000a1312) & (poi({unit}+0n324) == 00051311)'
    idle = xy('0n16') + ' & ' + ap('0')
    settled = (xy('0n18') + ' & ' + ap('0n10') + f' & (poi({unit}+0n316) == 0)'
               ' & (wo(@$t1+0n559612) == 0xffff) & (wo(@$t1+0n559812) == 0xffff)'
               ' & (wo(@$t1+0n560012) == 3) & (poi(00523f70) == 0) & (poi(00523f74) == 0)'
               ' & ((poi(00512360) & 0x00000000ffffffff) == 0xffffffff)')
    # Occupancy is column-major: GD+556374+200*X+2*Y.
    def obs(kind):
        message = ('WMOV_OBS kind='+kind+' click=%d phase=%d tid=%x eip=%p esp=%p caller=%p'
            ' eax=%x ebx=%x ecx=%x edx=%x esi=%x edi=%x ebp=%x selected=%d prior=%d lower=%d unit=%p'
            ' xy=(%d,%d) path=(%d,%x,%x) ap=('+','.join(['%d']*8)+')'
            ' occupancy=(%x,%x,%x) buttons=%x accumulator=%x steps=%d draws=(%d,%d,%d)')
        args = ['@$t10','@$t0','@$tid','@eip','@esp','poi(@esp)','@eax','@ebx','@ecx','@edx','@esi','@edi','@ebp',
                'poi(00511b58)','poi(00514194)','poi(00526994)',unit,'wo('+unit+')','wo('+unit+'+2)',
                'poi('+unit+'+0n316)','poi('+unit+'+0n320)','poi('+unit+'+0n324)']
        args += [f'by(@$t1+0n{UNIT_OFFSET+14+31*i})' for i in range(8)]
        args += ['wo(@$t1+0n559612)','wo(@$t1+0n559812)','wo(@$t1+0n560012)',
                 'poi(00544d04)','by(005451c0)','@$t11','@$t5','@$t6','@$t7']
        return p(message,*args)
    records = {}
    def add(number,va,previous,next_phase,kind,condition,extra='gc'):
        records[number]=(va,_guard(own+f' & (@$t0 == 0n{previous}) & '+condition,
            f'r @$t0=0n{next_phase}; '+obs(kind)+('; '+extra if extra else '')))
    # Shared native input gates occur once on each of the two direct calls.
    for number,va,delta,kind,condition in (
        (100,0x4084A1,0,'post-push','(@esp == @$t3-8) & (poi(@esp+4) == 00406fa1)'),
        (101,0x4084AE,1,'framed-admission-return','(@esp == @$t3-0n116) & (@eax == 0)'),
        (102,0x40856D,2,'left-sample-return','(@esp == @$t3-0n116) & (@eax == 1)'),
        (103,0x408594,3,'fog-return','(@esp == @$t3-0n116) & ((@eax & 0x00000000ffffffff) == 0xffffffff)'),
        (104,0x408733,4,'right-return','(@esp == @$t3-0n116) & (@eax == 0)'),
        (105,0x4087E1,5,'left-return','(@esp == @$t3-0n116) & (@eax == 1)'),
        (106,0x4099E3,6,'empty-target-return','(@esp == @$t3-0n116) & (@eax == 0) & (@ebp == 0n18) & (poi(@esp+54) == 0n19)')):
        records[number]=(va,_guard(own+' & '+mouse+' & '+idle+
            f' & (((@$t10 == 1) & (@$t0 == 0n{20+delta})) | ((@$t10 == 2) & (@$t0 == 0n{40+delta}))) & '+condition,
            'r @$t0=@$t0+1; '+obs(kind)+'; gc'))
    add(107,0x409A6C,27,28,'track-call','(@$t10 == 1) & (@esp == @$t3-0n120) & (poi(@esp) == 0n19) & (@eax == 3) & (@edx == 0n16) & (@ecx == 0n18) & (@ebx == 0n19)')
    add(108,0x4147A0,28,29,'track-entry','(@esp == @$t3-0n124) & (poi(@esp) == 00409a71) & (poi(@esp+4) == 0n19) & (@eax == 3) & (@edx == 0n16) & (@ecx == 0n18) & (@ebx == 0n19)')
    result='(@eax >= 00010000) & (@eax <= fffffe00) & (poi(@eax) == 2) & (poi(@eax+4) == 000a1312) & (poi(@eax+8) == 00051311)'
    # A pointer guard is nested because MASM bitwise predicates evaluate eagerly.
    records[109]=(0x409A71,_guard(own+' & (@$t0 == 0n29) & (@esp == @$t3-0n116) & (@eax >= 00010000) & (@eax <= fffffe00) & (@$t12 >= 1) & (@$t13 == 0)',
        _guard(result+' & '+idle, 'r @$t4=@eax; r @$t0=0n30; '+obs('track-return')+'; gc')))
    add(110,0x409AB5,30,31,'track-copied','(@esp == @$t3-0n116) & '+queue+' & '+idle)
    release=lambda kind:obs(kind+'-release-before')+'; eb 005451c0 00; ed 00544d04 0; '+obs(kind+'-release-after')+'; gc'
    # The native pathfinder's DD_Pump refreshes the input backend. Its actual
    # PollInputAndClampCursor writes exactly the two button bits, not a held
    # diagnostic input invariant. Retain those observations, then release at
    # the already-authenticated wait boundary; no next click gate is bypassed.
    add(111,0x409CA6,31,32,'preview-wait-call','(@esp == @$t3-0n116) & '+queue+' & '+idle+' & (poi(00544d04) <= 3) & (@$t13 == 0)',release('preview'))
    add(112,0x4609D0,32,33,'release-entry','(@esp == @$t3-0n120) & (poi(@esp) == 00409cab) & (@eax == 00544cd8) & (@edx == 0) & (poi(00544d04) == 0)')
    add(113,0x4609E0,33,34,'release-left-return','(@esp == @$t3-0n132) & (@eax == 0)')
    add(114,0x4609FC,34,35,'release-right-return','(@esp == @$t3-0n132) & (@eax == 0)')
    add(115,0x409CAB,35,36,'release-return','(@esp == @$t3-0n116) & (@eax == 0)')
    paired='(@$t5 == @$t6) & (@$t7 >= 1)'
    add(116,0x409CB5,36,37,'preview-redraw-return','(@esp == @$t3-0n116) & '+queue+' & '+idle+' & '+paired)
    preserved=' & '.join(f'((@{reg} & 0x00000000ffffffff) == (@$t{n} & 0x00000000ffffffff))' for n,reg in enumerate(('ebx','ecx','edx','esi','edi','ebp'),14))
    add(117,0x409CBE,37,38,'preview-ret','(@esp == @$t3-4) & (poi(@esp) == 00406fa1) & '+preserved)
    add(118,0x409BC5,47,48,'affordability-call','(@$t10 == 2) & (@esp == @$t3-0n116) & (@eax == 3) & '+queue+' & '+idle)
    add(119,0x409BCA,48,49,'affordability-return','(@esp == @$t3-0n116) & (@eax == 1)')
    add(120,0x409C0E,49,50,'execute-call','(@esp == @$t3-0n116) & (@eax == 3) & (@edx == 1) & '+queue+' & '+idle+' & (poi(00544d04) == 1) & (by(005451c0) == 0x80)',release('execute'))
    add(121,0x410330,50,51,'execute-entry','(@esp == @$t3-0n120) & (poi(@esp) == 00409c13) & (@eax == 3) & (@edx == 1) & (poi(00544d04) == 0)')
    add(122,0x4108DF,51,52,'spend-call','(@esp == @$t3-0n328) & (@eax == @$t1+0n149349) & (@edx == 5) & (@$t11 < 2) & '+xy('(0n16+@$t11)')+' & '+ap('(5*@$t11)'),
        'r @$t11=@$t11+1; gc')
    add(123,0x4108E4,52,53,'spend-return','(@esp == @$t3-0n328) & (@$t11 >= 1) & (@$t11 <= 2) & '+ap('(5*@$t11)'))
    add(124,0x410747,53,54,'path-decrement','(@esp == @$t3-0n328) & '+f'(poi({unit}+0n316) == 2-@$t11)')
    add(125,0x410AF7,54,51,'xy-occupancy-commit','(@esp == @$t3-0n328) & (@edi == @$t1+0n149349) & '+xy('(0n16+@$t11)')+' & '+ap('(5*@$t11)')+
        ' & (wo(@$t1+0n556374+0n200*(0n16+@$t11)+0n38) == 3) & (wo(@$t1+0n556374+0n200*(0n15+@$t11)+0n38) == 0xffff)')
    add(126,0x4105F7,51,55,'execute-redraw-return','(@esp == @$t3-0n328) & (@$t11 == 2) & '+settled+' & '+paired)
    add(127,0x410615,55,56,'execute-ret','(@esp == @$t3-0n120) & (poi(@esp) == 00409c13) & '+settled)
    add(128,0x409C13,56,57,'execute-return','(@esp == @$t3-0n116) & '+settled)
    add(129,0x409C18,57,58,'updater-return','(@esp == @$t3-0n116) & '+settled+' & '+paired)
    add(130,0x409C21,58,59,'world-ret','(@esp == @$t3-4) & (poi(@esp) == 00406fa1) & '+settled+' & '+preserved)
    # Wrong route is an explicit failure; no split, alternate execute or retry.
    for n,va in ((131,0x423050),(132,0x409C81)):
        records[n]=(va,obs('forbidden-route')+'; .echo WMOV_REJECT unexpected_route; q')
    def pump(kind):
        return p('WMOV_PUMP kind='+kind+' count=%d phase=%d tid=%x eip=%p esp=%p eax=%x edx=%x raw=(%x,%x) shift=%x buttons=%x accumulator=%x secondary=%x',
            '@$t12','@$t0','@$tid','@eip','@esp','@eax','@edx','poi(00544cfc)','poi(00544d00)',
            'by(0054512c)','poi(00544d04)','by(005451c0)','by(005451c8)')
    pump_sites=((133,0x414B3F,134,0x414B44,'pathfinder',29,388,1),
                (135,0x410DAE,136,0x410DB3,'animation',54,328,2),
                (137,0x410C91,138,0x410C96,'delay',51,328,3))
    for call_n,call_va,return_n,return_va,kind,phase,depth,identity in pump_sites:
        state=(idle+f' & (poi({unit}+0n316) == 0)' if kind=='pathfinder' else
               xy('(0n16+@$t11'+('-1)' if kind=='animation' else ')'))+' & '+ap('(5*@$t11)')+
               f' & (poi({unit}+0n316) == 2-@$t11) & (@$t11 >= 1) & (@$t11 <= 2)')
        context=own+f' & (@$t0 == 0n{phase}) & (@esp == @$t3-0n{depth}) & '+state
        call_context=context+' & (@eax == 00544cd8) & (@edx == 0) & (@$t13 == 0) & (@$t12 < 0n1024) & (poi(00545138) >= 00400000) & (poi(00545138) <= 7fffffe8)'
        records[call_n]=(call_va,_guard(call_context,
            _guard('(poi(poi(00545138)+14) == 00460a50)',
                f'r @$t4=poi(00545138); r @$t12=@$t12+1; r @$t13={identity}; '+pump(kind+'-call')+'; gc')))
        records[return_n]=(return_va,_guard(context+f' & (@$t13 == {identity}) & (@$t12 >= 1) & (@$t12 <= 0n1024) & (poi(00545138) == @$t4) & (poi(00544d04) <= 3)',
            'r @$t13=0; '+pump(kind+'-return')+'; gc'))
    compiled=prior['compiled_probe'].replace('SHSEL_','WMOV_BASE_')
    old={}
    for n in (80,90,91,92):
        matches=re.findall(r'^bp'+str(n)+r' ([0-9a-f]{8}) "(.*)"$',compiled,re.M)
        if len(matches)!=1:raise ValueError('baseline observer grammar differs')
        old[n]=(int(matches[0][0],16),matches[0][1])
    extras={}
    quiet=lambda path:'$$>a<\\"'+path+'\\";'
    def start(click):
        phase=20 if click==1 else 40
        save_gprs='; '.join(f'r @$t{n}=@{reg}' for n,reg in enumerate(('ebx','ecx','edx','esi','edi','ebp'),14))
        measured_mouse=p('WMOV_MOUSE click=%d tid=%x eip=%p esp=%p raw=(%x,%x) shift=%x',
            '@$t10','@$tid','@eip','@esp','poi(00544cfc)','poi(00544d00)','by(0054512c)')
        return (f'r @$t10=0n{click}; r @$t0=0n{phase}; r @$t5=0; r @$t6=0; r @$t7=0; r @$t11=0; r @$t12=0; r @$t13=0; '+save_gprs+
                '; ed 00544cfc (0n576 << by(0054512c)); ed 00544d00 (0n176 << by(0054512c)); eb 005451c0 80; ed 00544d04 1; '+measured_mouse+'; '+obs('begin')+
                '; r esp=@esp-4; ed @esp 00406fa1; r eip=004084a0; gc')
    for index,name in enumerate(('movement-before','movement-preview','movement-after')):
        path=f'{directory}/movement-checkpoint-{index}.cdb'
        condition=own+' & '+physical+' & (@esp == @$t3) & (poi(@$t1+0n140008) == 0n10) & (poi(@$t1+0n140012) == 0n17)'
        # Native SAR r32,CL consumes a fixed-point raw coordinate. This fixed
        # target576 fits a positive signed DWORD through shift21 inclusive;
        # shift22 overflows. Reject before coordinate writes, not after them.
        condition+=' & (by(0054512c) <= 0n21)'
        if index:condition+=' & (@$t13 == 0)'
        condition+=' & '+(settled if index==2 else idle)
        condition+=' & '+(queue if index==1 else f'(poi({unit}+0n316) == 0)')
        action=p(f'WMOV_SURFACE checkpoint={index} tid=%x eip=%p esp=%p surface=%p base=%p width=%d height=%d vtable=%p',
            '@$tid','@eip','@esp','poi(005202e0)','poi(poi(005202e0)+4)','wo(poi(005202e0))','wo(poi(005202e0)+2)','poi(poi(005202e0)+b8)')
        action+=f'; .writemem {directory}/{name}.header.raw poi(005202e0) L0n188; .writemem {directory}/{name}.raw poi(poi(005202e0)+4) L0n{surface_size}; .writemem {directory}/{name}.unit.raw @$t1+0n149349 L0n725; '
        if index<2:action+=start(index+1)
        else:action+=obs('ready')+'; .echo WMOV_HOST_READY'
        prefix=''
        if index==0:prefix='; '.join('bd '+str(i) for i in range(81,90))+'; '+'; '.join('be '+str(i) for i in records)+'; '
        extras[path]=(prefix+_guard(condition,action)+'\n').replace(r'\"','"').replace(r'\\n',r'\n')
    baseline_stop=old[80][1]
    if baseline_stop.count('.echo WMOV_BASE_HOST_READY')!=1:raise ValueError('baseline stop differs')
    baseline_stop=baseline_stop.replace('.echo WMOV_BASE_HOST_READY',quiet(f'{directory}/movement-checkpoint-0.cdb'))
    stopped='.if (@$t10 == 1) { '+quiet(f'{directory}/movement-checkpoint-1.cdb')+' } .else { '+quiet(f'{directory}/movement-checkpoint-2.cdb')+' }'
    modifications={80:'.if (@$t0 < 0n20) { '+baseline_stop+' } .else { '+_guard(own+' & (@esp == @$t3) & '+paired+
        ' & (((@$t10 == 1) & (@$t0 == 0n38)) | ((@$t10 == 2) & (@$t0 == 0n59)))',stopped)+' }'}
    native_return=prior['native_call_returns']['native_draw'];composition_return=prior['native_call_returns']['composition_draw']
    active='((@$t10 == 1) | (@$t10 == 2)) & (@$t0 >= 0n20) & (@$t0 <= 0n59)'
    draw_guard=(own+' & '+active+' & (@$t5 == @$t6) & (@$t5 < 0n512) & (@esp >= @$t3-0n4096) & (@esp < @$t3)'
                f' & ((poi(@esp) == {native_return:08x}) | (poi(@esp) == {composition_return:08x}))')
    drawbody=_guard(draw_guard,'r @$t5=@$t5+1; r @$t8=@esp; r @$t9=poi(@esp); '+obs('draw-entry')+'; gc')
    modifications[90]='.if (@$t0 < 0n20) { '+old[90][1]+' } .else { '+drawbody+' }'
    for n,kind,ret in ((91,'draw-native-return',native_return),(92,'draw-composition-return',composition_return)):
        condition=own+' & '+active+f' & (@$t9 == {ret:08x}) & (@esp == @$t8+4) & (@eax == 1) & (@$t5 == @$t6+1)'
        body='r @$t6=@$t6+1; '+('r @$t7=@$t7+1; ' if n==92 else '')+obs(kind)+'; gc'
        modifications[n]='.if (@$t0 < 0n20) { '+old[n][1]+' } .else { '+_guard(condition,body)+' }'
    for n,command in modifications.items():
        compiled,count=re.subn(r'^bp'+str(n)+r' [0-9a-f]{8} ".*"$',lambda _:f'bp{n} {old[n][0]:08x} "{command}"',compiled,flags=re.M)
        if count!=1:raise ValueError('baseline replacement not unique')
    checked={va+i:value for va,size in NATIVE_SPANS for i,value in enumerate(read(va,size))}
    conditions=[f'(by({va:08x}) != 0x{value:02x})' for va,value in sorted(checked.items())]
    checks='\n'.join('.if ('+' | '.join(conditions[i:i+48])+') { .echo WMOV_REJECT loaded_bytes; q }' for i in range(0,len(conditions),48))+'\n.echo WMOV_BYTES_PASS\n'
    checks+=f'.echo WMOV_CONTRACT revision={REVISION} candidate_sha256={prior["candidate_sha256"]} save_sha256={prior["save_sha256"]} source=(16,19) target=(18,19) clicks=2\n'
    first=re.search(r'(?m)^bp[0-9]+ ',compiled)
    if first is None or not compiled.endswith('g\n'):raise ValueError('baseline transport differs')
    compiled=compiled[:first.start()]+checks+compiled[first.start():]
    compiled=compiled[:-2]+'\n'.join(f'bp{n} {va:08x} "{command}"\nbd {n}' for n,(va,command) in records.items())+'\ng\n'
    all_text=compiled+'\n'+'\n'.join(extras.values())
    if max(map(len,all_text.splitlines()))>=4096:raise ValueError('debugger line exceeds4096 transport limit')
    if all_text.count('WMOV_HOST_READY')!=1 or 'WMOV_BASE_HOST_READY' in all_text:raise ValueError('only final movement host readiness allowed')
    if sources != verify_sources():
        raise ValueError('army movement sources changed during preparation')
    return dict(schema='clash95_complete_hd_army_movement_probe_v1',revision=REVISION,stage=prior['stage'],resolution=resolution,
        width=width,height=height,original_sha256=prior['original_sha256'],candidate_sha256=prior['candidate_sha256'],save_sha256=prior['save_sha256'],
        capture_dir=directory,minimap_viewport=True,unit=3,source_xy=[16,19],destination_xy=[18,19],
        controlled_scroll=[10,17],controlled_mouse=[576,176],mouse_shift_max=21,
        expected_initial_ap=list(INITIAL_AP),expected_final_ap=[v-10 for v in INITIAL_AP],
        expected_path_count=2,expected_path_words=list(PATH_WORDS),compiled_probe=compiled,probe_sha256=sha(compiled.encode('ascii')),
        initial_extra=prior['initial_extra'],initial_extra_sha256=prior['initial_extra_sha256'],
        supplemental_commands=extras,supplemental_sha256={path:sha(text.encode('ascii')) for path,text in extras.items()},
        source_sha256=prior['source_sha256']|sources,base_compiled_probe_sha256=prior['probe_sha256'],
        candidate_manifest_canonical_sha256=prior['candidate_manifest_canonical_sha256'],
        candidate_recipe=prior['candidate_recipe'], inherited_stage=prior['inherited_stage'],
        inherited_revision=prior['inherited_revision'], startup_recipe=prior['startup_recipe'],
        parent_source_sha256=PARENT_SOURCE_SHA256, capture_class='e0_software_diagnostic',
        baseline_observer_vas=prior['observer_vas'],baseline_native_call_returns=prior['native_call_returns'],
        movement_observer_vas={str(n):va for n,(va,_) in records.items()},movement_native_call_returns=returns,
        pump_observers=[dict(kind=kind,call=call_va,returned=return_va,phase=phase,stack_depth=depth,pending_identity=identity)
            for _,call_va,_,return_va,kind,phase,depth,identity in pump_sites],max_pump_calls_per_click=1024,
        loaded_native_spans=[dict(va=va,bytes=size,sha256=sha(read(va,size))) for va,size in NATIVE_SPANS],
        stack_offsets_from_sentinel=dict(world_entry=-4,world_body=-116,path_entry=-124,execute_entry=-120,execute_body=-328,
            preview_release_entry=-120,preview_release_query_return=-132,world_ret=-4),
        controlled_input=True,controlled_release=True,native_predicate_forced=False,selected_value_forced=False,
        flag_value_forced=False,movement_state_forced=False,runtime_executed=False,manual_input_proof=False,promotion_ready=False,limits=LIMITS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', required=True, type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--candidate-manifest', required=True, type=Path)
    parser.add_argument('--resolution', required=True, choices=base.builder.RESOLUTIONS)
    parser.add_argument('--save', required=True, type=Path)
    parser.add_argument('--capture-dir', required=True)
    args = parser.parse_args()
    packet = build_movement_probe(args.original.read_bytes(), args.candidate.read_bytes(),
        args.save.read_bytes(), capture_dir=args.capture_dir,
        candidate_manifest=base.read_manifest(args.candidate_manifest), resolution=args.resolution)
    print(json.dumps(packet, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
