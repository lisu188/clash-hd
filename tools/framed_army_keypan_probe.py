#!/usr/bin/env python3
"""Pure source-bound preparation of one controlled native right-key pan.

Copies frozen selection-v3 under KPAN_BASE, then calls 407D20 with only the
right-arrow scan byte pressed. The actual time gate, native camera store,
full redraw and true return are observed. A second actual key query proves
release. This module neither executes anything nor writes output files.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

import framed_army_selection_probe as base

ROOT = base.ROOT
BASE_SHA256 = 'e5476178b80c29cf35ac2c64f8f89cb29a34596f8b3d1aa971ae456d0bbfc2e8'
REVISION = 'controlled_native_right_key_pan_v1'
UNIT_OFFSET = 149349
KEYBOARD = 0x5451CC
RIGHT_KEY = 0x545299
INITIAL_AP = (26, 22, 16, 16, 16, 16, 16, 16)
NATIVE_SPANS = ((0x407D20, 0x302), (0x461570, 16), (0x460900, 13),
                (0x418700, 25), (0x40B126, 5), (0x4207B0, 65))
NATIVE_CALLS = {0x407D43:0x4207B0, 0x407D62:0x461570,
    0x407D74:0x461570, 0x407DB9:0x461570, 0x407DE3:0x4207B0,
    0x407DF7:0x418700, 0x407E07:0x461570, 0x407E4C:0x461570,
    0x407E9A:0x461570, 0x407ECF:0x461570, 0x407F04:0x461570,
    0x407F3C:0x56442A, 0x407F9D:0x460900, 0x40B126:0x407D20}
LIMITS = [
    'The frozen native selection setup controls its initial camera and mouse. The subsequent key-pan phase never writes camera, unit, AP, queue, selection or flags.',
    'One direct 407D20 call uses a controlled keyboard-state byte, not OS key delivery or ordinary full-loop input dispatch.',
    'All256 keyboard bytes must already be zero; only545299 is written80 then00. No keyboard clear, timestamp write or native predicate/result override is allowed.',
    'The actual unsigned timing predicate must pass; an ineligible sample fails closed without retry or forced time.',
    'Exactly one native X store10 to11, unchanged Y17, a complete418700/composition draw and both native true returns are required.',
    'Before/after stopped E0, header and725-byte unit dumps require independent trace, state, pixel and owned-host validation. Preparation is no runtime, visual, manual or promotion proof.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    if sha(Path(base.__file__).read_bytes()) != BASE_SHA256:
        raise ValueError('frozen selection-v3 producer differs')
    return base.verify_sources() | {'tools/framed_army_selection_probe.py': BASE_SHA256}


def _guard(condition, body):
    # t1 is the already validated selection-baseline GD, even when the live
    # owner/global identity fails. Reading its saved bounded camera fields
    # does not follow a newly supplied or rejected pointer.
    context = base._printf('KPAN_REJECT_CONTEXT phase=%d tid=%x eip=%p esp=%p camera=(%d,%d) keys=(%x,%x,%x,%x,%x)',
        '@$t0','@$tid','@eip','@esp','poi(@$t1+0n140008)','poi(@$t1+0n140012)',
        'by(00545204)','by(00545297)','by(00545299)','by(00545294)','by(0054529c)')
    return '.if (' + condition + ') { ' + body + ' } .else { '+context+'; .echo KPAN_REJECT native_contract; q }'


def build_keypan_probe(original, candidate, save, *, capture_dir, minimap_viewport=True):
    """Return deterministic main probe and two stopped snapshot command files."""
    sources = verify_sources()
    prior = base.build_selection_probe(original, candidate, save,
        capture_dir=capture_dir, minimap_viewport=minimap_viewport)
    directory = prior['capture_dir']
    read = lambda va, n: base._read(candidate, va, n)
    returns = {f'{va:08x}': base._call_return(candidate, va, target)
               for va, target in NATIVE_CALLS.items()}
    for va, expected in ((0x407D20,'535152565755'), (0x407D48,'39d0'),
        (0x407DDD,'8990e8220200'), (0x407F4B,'c3'),
        (0x461570,'f680cc515400800f95c025ff000000c3')):
        if read(va,len(bytes.fromhex(expected))) != bytes.fromhex(expected):
            raise ValueError(f'native key-pan boundary differs at{va:08x}')
    if save[16+147171] != 8:
        raise ValueError('native save scroll speed differs')
    p = base._printf
    unit = '(@$t1+0n149349)'
    own = ('(@$tid == @$t2) & (poi(005202e4) == @$t1) & (poi(005199d8) == 0040ad40)'
           ' & (poi(00526990) == 0) & (poi(005202ec) == 0) & (poi(00511b58) == 3)'
           ' & (poi(00514194) == 3) & (poi(00526994) == 1) & (poi(00526fa0) == @$t1+0n149349)'
           ' & (by(@$t1+0n149353) == 0)')
    own += ' & ' + ' & '.join(f'(poi({0x526F78+4*i:08x}) == 0)' for i in range(10))
    physical = ('(wo(poi(005202e0)) == 0n1024) & (wo(poi(005202e0)+2) == 0n768)'
                ' & (poi(poi(005202e0)+b8) == 0050ee24)'
                ' & (poi(poi(005202e0)+4) >= 00010000) & (poi(poi(005202e0)+4) <= fff40000)')
    idle = (f'(wo({unit}) == 0n16) & (wo({unit}+2) == 0n19) & (poi({unit}+0n316) == 0)'
            ' & (poi(00544d04) == 0) & (by(005451c0) == 0) & (poi(00545140) == 0)'
            ' & (by(@$t1+0n147171) == 8)')
    idle += ' & ' + ' & '.join(f'(by(@$t1+0n{UNIT_OFFSET+14+31*i}) == 0n{v})' for i,v in enumerate(INITIAL_AP))
    def camera(x):
        return f'(poi(@$t1+0n140008) == 0n{x}) & (poi(@$t1+0n140012) == 0n17)'
    preserved = ' & '.join(f'((@{reg} & 0x00000000ffffffff) == (@$t{n} & 0x00000000ffffffff))'
        for n,reg in enumerate(('ebx','ecx','edx','esi','edi','ebp'),14))
    def obs(kind):
        message = ('KPAN_OBS kind='+kind+' phase=%d tid=%x eip=%p esp=%p caller=%p'
            ' eax=%x ebx=%x ecx=%x edx=%x esi=%x edi=%x ebp=%x'
            ' selected=%d prior=%d lower=%d unit=%p xy=(%d,%d) camera=(%d,%d)'
            ' keys=(%x,%x,%x,%x,%x) time=(%x,%x,%d) stores=%d draws=(%d,%d,%d)')
        args = ['@$t0','@$tid','@eip','@esp','poi(@esp)','@eax','@ebx','@ecx','@edx','@esi','@edi','@ebp',
            'poi(00511b58)','poi(00514194)','poi(00526994)',unit,'wo('+unit+')','wo('+unit+'+2)',
            'poi(@$t1+0n140008)','poi(@$t1+0n140012)',
            'by(00545204)','by(00545297)','by(00545299)','by(00545294)','by(0054529c)',
            'poi(005202a0)','@edx','by(@$t1+0n147171)','@$t10','@$t5','@$t6','@$t7']
        return p(message,*args)
    records = {}
    def add(number, va, previous, next_phase, kind, condition, extra='gc'):
        records[number] = (va,_guard(own+f' & (@$t0 == 0n{previous}) & '+condition,
            f'r @$t0=0n{next_phase}; '+obs(kind)+('; '+extra if extra else '')))
    body = '(@esp == @$t3-0n28)'
    pressed = '(by(00545299) == 0x80)'
    released = '(by(00545299) == 0)'
    pair = '(@$t5 == 1) & (@$t6 == 1) & (@$t7 == 1) & (@$t10 == 1)'
    add(100,0x407D21,20,21,'post-push','(@esp == @$t3-8) & (poi(@esp+4) == 00406fa1) & ((poi(@esp) & 0x00000000ffffffff) == (@$t14 & 0x00000000ffffffff)) & '+camera(10)+' & '+pressed)
    # The diagnostic precedes the timing guard, retaining an ineligible sample.
    add(101,0x407D48,21,22,'time-return',body+' & '+camera(10)+' & '+pressed+
        ' & ((@eax & 0x00000000ffffffff) > (@edx & 0x00000000ffffffff))'
        ' & ((@edx & 0x00000000ffffffff) == ((poi(005202a0)+8) & 0x00000000ffffffff))')
    records[101] = (records[101][0],obs('time-sample')+'; '+records[101][1])
    for n,va,phase,kind,result in ((102,0x407D67,22,'alt-return',0),
        (103,0x407D79,23,'left-return',0),(104,0x407DBE,24,'right-return',1)):
        add(n,va,phase,phase+1,kind,body+' & '+camera(10)+' & '+pressed+f' & (@eax == {result})')
    add(105,0x407DDD,25,26,'store-before',body+' & '+camera(10)+' & '+pressed+
        ' & (@eax == @$t1) & (@edx == 0n11) & (@ebp == 0n10) & (@$t10 == 0)')
    add(106,0x407DE3,26,27,'store-after',body+' & '+camera(11)+' & '+pressed+
        ' & (@eax == @$t1) & (@edx == 0n11) & (@ebp == 0n10) & (@$t10 == 0)',
        'r @$t10=1; '+obs('release-before')+'; eb 00545299 00; '+obs('release-after')+'; gc')
    add(107,0x407DF7,27,28,'redraw-call',body+' & '+camera(11)+' & '+released+' & (@eax == 1) & (@ecx == 1) & (@$t10 == 1)')
    add(108,0x418700,28,29,'redraw-entry','(@esp == @$t3-0n32) & (poi(@esp) == 00407dfc) & (@eax == 1) & '+camera(11)+' & '+released)
    add(109,0x407DFC,29,30,'redraw-return',body+' & '+camera(11)+' & '+released+' & '+pair+' & (@ecx == 1)')
    for n,va,phase,kind in ((110,0x407E0C,30,'up-return'),(111,0x407E51,31,'down-return'),
        (112,0x407E9F,32,'m-return'),(113,0x407ED4,33,'f1-return'),(114,0x407F09,34,'f2-return'),
        (115,0x407F41,35,'minimap-return'),(116,0x407FA2,36,'right-mouse-return')):
        add(n,va,phase,phase+1,kind,body+' & '+camera(11)+' & '+released+' & '+pair+' & (@eax == 0)')
    add(117,0x407F4B,37,38,'pan-ret','(@esp == @$t3-4) & (poi(@esp) == 00406fa1) & '+camera(11)+' & '+released+' & '+pair+' & '+preserved+' & (@eax == 0)')
    # Disabled until pan's true return, because this RET serves every key query.
    add(118,0x46157F,39,40,'released-query-ret','(@esp == @$t3-4) & (poi(@esp) == 00406fa1) & '+camera(11)+' & '+released+' & '+pair+' & '+preserved+' & (@eax == 0)')
    compiled = prior['compiled_probe'].replace('SHSEL_','KPAN_BASE_')
    old = {}
    for n in (80,90,91,92):
        matches = re.findall(r'^bp'+str(n)+r' ([0-9a-f]{8}) "(.*)"$',compiled,re.M)
        if len(matches)!=1:raise ValueError('baseline observer grammar differs')
        old[n] = (int(matches[0][0],16),matches[0][1])
    extras = {}
    quiet = lambda path:'$$>a<\\"'+path+'\\";'
    save_gprs = '; '.join(f'r @$t{n}=@{reg}' for n,reg in enumerate(('ebx','ecx','edx','esi','edi','ebp'),14))
    for index,name in enumerate(('keypan-before','keypan-after')):
        path = f'{directory}/keypan-checkpoint-{index}.cdb'
        lines = [_guard(own+' & (@esp == @$t3) & (@eip == 00406fa1) & '+camera(10+index)+' & '+idle,
            p(f'KPAN_CHECK checkpoint={index} kind=owner-idle pass=1'))]
        lines.append(_guard(physical,p(f'KPAN_CHECK checkpoint={index} kind=physical pass=1')))
        # Four independent bounded guards cover exactly256bytes without long
        # CDB lines. No writes normalize a failed keyboard baseline.
        for block in range(4):
            condition = ' & '.join(f'(poi({KEYBOARD+4*i:08x}) == 0)' for i in range(block*16,(block+1)*16))
            lines.append(_guard(condition,p(f'KPAN_KEYS checkpoint={index} block={block} zero=1')))
        if index == 0:
            lines.append('; '.join('bd '+str(i) for i in range(81,90))+'; '+'; '.join('be '+str(i) for i in range(100,118)))
        else:
            lines.append(_guard('(@$t0 == 0n40) & '+pair+' & '+preserved+' & (@eax == 0)',
                p('KPAN_CHECK checkpoint=1 kind=completed pass=1')))
        action = p(f'KPAN_SURFACE checkpoint={index} tid=%x eip=%p esp=%p surface=%p base=%p width=%d height=%d vtable=%p',
            '@$tid','@eip','@esp','poi(005202e0)','poi(poi(005202e0)+4)','wo(poi(005202e0))','wo(poi(005202e0)+2)','poi(poi(005202e0)+b8)')
        action += f'; .writemem {directory}/{name}.header.raw poi(005202e0) L0n188; .writemem {directory}/{name}.raw poi(poi(005202e0)+4) L0n786432; .writemem {directory}/{name}.unit.raw @$t1+0n149349 L0n725; .writemem {directory}/{name}.keyboard.raw 005451cc L0n256; '
        if index == 0:
            action += ('r @$t0=0n20; r @$t5=0; r @$t6=0; r @$t7=0; r @$t10=0; '+save_gprs+'; '+obs('keydown-before')+
                '; eb 00545299 80; '+obs('begin')+'; r esp=@esp-4; ed @esp 00406fa1; r eip=00407d20; gc')
        else:
            action += obs('ready')+'; .echo KPAN_HOST_READY'
        lines.append(action)
        extras[path] = ('\n'.join(lines)+'\n').replace(r'\"','"').replace(r'\\n',r'\n')
    baseline_stop = old[80][1]
    if baseline_stop.count('.echo KPAN_BASE_HOST_READY') != 1:raise ValueError('baseline stop differs')
    baseline_stop = baseline_stop.replace('.echo KPAN_BASE_HOST_READY',quiet(f'{directory}/keypan-checkpoint-0.cdb'))
    stopguard = own+' & (@esp == @$t3) & '+camera(11)+' & '+released+' & '+pair+' & '+preserved+' & (@eax == 0) & ((@$t0 == 0n38) | (@$t0 == 0n40))'
    query = (obs('pan-return')+'; be 118; r @$t0=0n39; r eax=0n205; '+p('KPAN_QUERY_CALL tid=%x eip=%p esp=%p eax=%x','@$tid','@eip','@esp','@eax')+
             '; r esp=@esp-4; ed @esp 00406fa1; r eip=00461570; gc')
    stopped = _guard(stopguard,'.if (@$t0 == 0n38) { '+query+' } .else { '+
        obs('released-query-return')+'; '+quiet(f'{directory}/keypan-checkpoint-1.cdb')+' }')
    modifications = {80:'.if (@$t0 < 0n20) { '+baseline_stop+' } .else { '+stopped+' }'}
    composition_return = prior['native_call_returns']['composition_draw']
    drawguard = own+' & (@$t0 == 0n29) & '+camera(11)+' & '+released
    drawbody = _guard(drawguard+f' & (@esp == @$t3-0n272) & (poi(@esp) == {composition_return:08x}) & (@$t5 == 0) & (@$t6 == 0) & (@$t7 == 0)',
        'r @$t5=1; r @$t8=@esp; r @$t9=poi(@esp); '+obs('draw-entry')+'; gc')
    modifications[90] = '.if (@$t0 < 0n20) { '+old[90][1]+' } .else { '+drawbody+' }'
    modifications[91] = '.if (@$t0 < 0n20) { '+old[91][1]+' } .else { .echo KPAN_REJECT unexpected_native_draw; q }'
    drawreturn = _guard(drawguard+f' & (@esp == @$t3-0n268) & (@esp == @$t8+4) & (@$t9 == {composition_return:08x}) & (@eax == 1) & (@$t5 == 1) & (@$t6 == 0) & (@$t7 == 0)',
        'r @$t6=1; r @$t7=1; '+obs('draw-composition-return')+'; gc')
    modifications[92] = '.if (@$t0 < 0n20) { '+old[92][1]+' } .else { '+drawreturn+' }'
    for n,command in modifications.items():
        compiled,count = re.subn(r'^bp'+str(n)+r' [0-9a-f]{8} ".*"$',lambda _:f'bp{n} {old[n][0]:08x} "{command}"',compiled,flags=re.M)
        if count != 1:raise ValueError('baseline replacement not unique')
    checked = {va+i:value for va,size in NATIVE_SPANS for i,value in enumerate(read(va,size))}
    bytechecks = [f'(by({va:08x}) != 0x{value:02x})' for va,value in sorted(checked.items())]
    checks = '\n'.join('.if ('+' | '.join(bytechecks[i:i+48])+') { .echo KPAN_REJECT loaded_bytes; q }' for i in range(0,len(bytechecks),48))+'\n.echo KPAN_BYTES_PASS\n'
    checks += f'.echo KPAN_CONTRACT revision={REVISION} candidate_sha256={prior["candidate_sha256"]} save_sha256={prior["save_sha256"]} camera=(10,17)-(11,17) key=205 calls=1\n'
    first = re.search(r'(?m)^bp[0-9]+ ',compiled)
    if first is None or not compiled.endswith('g\n'):raise ValueError('baseline transport differs')
    compiled = compiled[:first.start()]+checks+compiled[first.start():]
    compiled = compiled[:-2]+'\n'.join(f'bp{n} {va:08x} "{command}"\nbd {n}' for n,(va,command) in records.items())+'\ng\n'
    all_text = compiled+'\n'+'\n'.join(extras.values())
    if max(map(len,all_text.splitlines())) >= 4096:raise ValueError('debugger line exceeds4096 transport limit')
    if all_text.count('KPAN_HOST_READY') != 1 or 'KPAN_BASE_HOST_READY' in all_text:raise ValueError('only final key-pan host readiness allowed')
    verify_sources()
    return dict(schema='clash95_framed_army_keypan_probe_v1',revision=REVISION,stage=prior['stage'],resolution='1024x768',
        width=1024,height=768,original_sha256=prior['original_sha256'],candidate_sha256=prior['candidate_sha256'],save_sha256=prior['save_sha256'],
        capture_dir=directory,minimap_viewport=minimap_viewport,unit=3,unit_xy=[16,19],camera_before=[10,17],camera_after=[11,17],
        expected_ap=list(INITIAL_AP),keyboard_va=KEYBOARD,keyboard_bytes=256,right_key_va=RIGHT_KEY,right_scan_code=205,
        compiled_probe=compiled,probe_sha256=sha(compiled.encode('ascii')),initial_extra=prior['initial_extra'],initial_extra_sha256=prior['initial_extra_sha256'],
        supplemental_commands=extras,supplemental_sha256={path:sha(text.encode('ascii')) for path,text in extras.items()},
        source_sha256=prior['source_sha256']|sources,base_compiled_probe_sha256=prior['probe_sha256'],
        baseline_observer_vas=prior['observer_vas'],baseline_native_call_returns=prior['native_call_returns'],
        keypan_observer_vas={str(n):va for n,(va,_) in records.items()},keypan_native_call_returns=returns,
        loaded_native_spans=[dict(va=va,bytes=size,sha256=sha(read(va,size))) for va,size in NATIVE_SPANS],
        stack_offsets_from_sentinel=dict(pan_entry=-4,post_push=-8,pan_body=-28,redraw_entry=-32,
            compose_entry=-272,compose_return=-268,pan_ret=-4,released_query_entry=-4,released_query_ret=-4),
        controlled_input=True,controlled_release=True,native_predicate_forced=False,camera_value_forced=False,
        unit_value_forced=False,runtime_executed=False,manual_input_proof=False,promotion_ready=False,limits=LIMITS)
