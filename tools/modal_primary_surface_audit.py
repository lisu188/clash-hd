#!/usr/bin/env python3
"""Offline, source-bound audit of the four owned-modal-primary checkpoints.

All comparisons use original retained indexed pixels. The native canvas is a
measured oracle for native artwork, while the two primary-only sprites come
from the authenticated user-owned assets. Nothing runs or modifies the game.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import io
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image

import modal_primary_capture as capture
import hd_layout_asset_composition as assets
from src.patcher import framed_modal_primary as patcher

need, sha, integer, path_value = capture.need, capture.sha, capture.integer, capture.path_value
ROOT = capture.ROOT
MAXIMUM_SHA256 = '44f545780f11081cd0d45421eb8b7ed985221ef776319573bbfd89ff6431ccf2'
BARRACKS_MEMBER_SHA256 = '00215de437943ec7ec009324fa534a865d2be89d0dcc0b79d59ef0b78f8b9776'
SOURCE_PATHS = {'host_path':'scripts/cdb/run_modal_primary_capture.ps1',
    'producer':'tools/modal_primary_capture.py', 'trace':'tools/modal_primary_capture.py',
    'primary_source':'tools/modal_slots_primary_surface.py', 'converter':'tools/cdb_surface_dump_to_png.py',
    'proxy_source':'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp'}
CURSOR_READS = {'state':68, 'descriptor':40, 'resource':0x1010, 'sprite_header':10,
    'backing_header':188, 'backing_pixels':4096, 'barracks_pointer':4,
    'barracks_resource':0x1010, 'placeholder_sprite_header':10}
LIMITS = [
    'Only the controlled first barracks placeholder route and these four paused boundaries are covered.',
    'Native artwork and slot contents are measured from the same owned native canvas, not independently decoded building artwork.',
    'Cursor and placeholder output pixels are compared to source S32 sprites; captured live headers do not prove encoded heap payload ownership or allocation lifetime.',
    'The supported pixel oracle requires wholly on-screen cursor backing bounds and stable descriptor/position across this short route.',
    'Current attached proxy palettes reconstruct diagnostic PNGs; visible-wrapper composition and ordinary mouse input remain unproved.',
    'No selected-panel branch, other building, native modal exit, destructor/free path, soak, release, or stable promotion is established.',
    'Ordinary map frame/action-bar claims do not apply to this centered modal screen.',
]


def u32(data, offset=0): return struct.unpack_from('<I',data,offset)[0]
def i32(data, offset=0): return struct.unpack_from('<i',data,offset)[0]


def same_json(actual, expected, label):
    # Canonical JSON retains the distinction between booleans and integers.
    need(capture.canonical(actual)==capture.canonical(expected),label+' differs')


def timestamp(value):
    need(type(value) is str,'timestamp must be a string')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    need(result.tzinfo is not None,'timestamp must include its timezone')
    return result


def resource_member(data, components):
    """Strict native LLRS path traversal, skipping inactive names before decoding."""
    need(len(data)>=20 and data[:8]==b'llrs\x01\0\0\0','unsupported LLRS header')
    slots,skip=struct.unpack_from('<II',data,8);offset=16+skip;length=4+26*slots
    for part_index,component in enumerate(components):
        need(0<slots<=10000 and offset>=16 and offset+length<=len(data) and 4+26*slots<=length,'LLRS directory bounds differ')
        count=u32(data,offset);active=0;found=[]
        for index in range(slots):
            pos=offset+4+index*26;flags,start,size=struct.unpack_from('<III',data,pos+14)
            if not flags:continue
            active+=1
            need(flags in (1,2) and start>=16 and size>0 and start+size<=len(data),'invalid active LLRS entry')
            name=data[pos:pos+14].split(b'\0',1)[0].decode('ascii')
            if name==component:found.append((flags,start,size))
        need(active==count and len(found)==1,'LLRS path is missing or ambiguous: '+component)
        flags,offset,length=found[0]
        if part_index<len(components)-1:
            # Native 00478770 truncates (declared_bytes-4)/26. Real maximum.res
            # directories include 22 trailing bytes outside the readable slots.
            need(flags==2 and length>=30,'LLRS child is not a valid directory')
            slots=(length-4)//26
        else:need(flags==1,'LLRS leaf is not a file')
    return data[offset:offset+length]


def source_assets(resource_root, reader):
    root=path_value(resource_root)
    minimum=reader.read(root/'DATA/minimum.res',expected=assets.RESOURCE_SHA256)
    maximum=reader.read(root/'DATA/maximum.res',expected=MAXIMUM_SHA256)
    mouse=resource_member(minimum,('GFX','MOUSE.S32'))
    barracks=resource_member(maximum,('GFX','CASTLE.CHR','DW_12.S32'))
    need(sha(barracks)==BARRACKS_MEMBER_SHA256,'barracks source member differs')
    placeholder=assets.decode_sprite(barracks,25)
    need((placeholder.width,placeholder.height)==(203,120) and None not in placeholder.pixels,
         'source placeholder must be the exact opaque native 203x120 sprite')
    return dict(mouse=mouse,barracks=barracks,placeholder=placeholder,
        receipts=dict(minimum_sha256=sha(minimum),maximum_sha256=sha(maximum),mouse_member_sha256=sha(mouse),
                      barracks_member_sha256=sha(barracks),placeholder_index=25,placeholder_size=[203,120]))


def sprite_header(member,index):
    # Decode first so the entire source member/index is structurally checked.
    sprite=assets.decode_sprite(member,index);offset=u32(member,index*4)
    return member[offset:offset+10],sprite


def region_set(rows, observations=None):
    need(type(rows) is list and rows,'actual readable-region receipts required')
    normalized=[]
    for row in rows:
        need(set(row)=={'address','size','state','protect'},'region fields differ')
        start=integer(row['address'],'region address',1);size=integer(row['size'],'region size',1)
        need(start+size<=1<<32 and type(row['state']) is int and row['state']==0x1000
             and type(row['protect']) is int and row['protect'] in (2,4,8,0x20,0x40,0x80),'region is not bounded readable committed memory')
        normalized.append(dict(row))
    normalized.sort(key=lambda r:(r['address'],r['size']))
    need(all(a['address']+a['size']<=b['address'] for a,b in zip(normalized,normalized[1:])),'overlapping normalized region claims')
    if observations is not None:
        need(type(observations) is list and observations,'raw VirtualQueryEx receipts required')
        combined=[]
        for row in sorted(observations,key=lambda r:(r['address'],r['size'])):
            region_set([row])
            adjacent=bool(combined and row['address']==combined[-1]['address']+combined[-1]['size'])
            overlapping=bool(combined and row['address']<combined[-1]['address']+combined[-1]['size'])
            same=bool(combined and (row['state'],row['protect'])==(combined[-1]['state'],combined[-1]['protect']))
            if overlapping or (adjacent and same):
                previous=combined[-1]
                need((row['state'],row['protect'])==(previous['state'],previous['protect']), 'overlapping VQ state/protection differs')
                previous['size']=max(previous['address']+previous['size'],row['address']+row['size'])-previous['address']
            else:combined.append(dict(row))
        same_json(normalized,combined,'normalized VQ union')
    return [capture.reader.Region(**row) for row in normalized]


def paired_reads(receipt,folder,prefix,reader,extents):
    need(set(receipt['reads'])=={'before','after'},prefix+' requires exactly paired phases')
    regions=region_set(receipt['regions'],receipt.get('region_observations')) if 'regions' in receipt else None
    result={}
    for phase in ('before','after'):
        rows=receipt['reads'][phase];need(set(rows)==set(extents),prefix+' read set differs')
        current={}
        for name,size in extents.items():
            record=rows[name]
            filename='barracks-pointer' if prefix=='cursor' and name=='barracks_pointer' else name
            data=reader.artifact(record,path=folder/f'{prefix}-{phase}-{filename}.raw',size=size)
            address=integer(record['address'],prefix+' read address',0x10000,0x7ffe0000-size)
            if regions is not None:capture.reader._read(capture.reader.Read(address,data),address,size,name,regions)
            current[name]=dict(address=address,data=data)
        if result:need(current==result,prefix+' changed across paused reads')
        result=current
    return result


def bind_cursor(receipt,folder,reader,oracle,original,cp):
    reads=paired_reads(receipt,folder,'cursor',reader,CURSOR_READS)
    state=reads['state']['data'];desc=reads['descriptor']['data'];resource=reads['resource']['data']
    need(reads['state']['address']==patcher.CURSOR_STATE and reads['descriptor']['address']==u32(state,60)
         and reads['resource']['address']==u32(state,64),'cursor descriptor/resource pointer chain differs')
    dptr=reads['descriptor']['address']
    if dptr==patcher.CURSOR_STARTUP_DESCRIPTOR:prefix=bytes(12)
    else:
        need(dptr in patcher.CURSOR_DESCRIPTORS,'unsupported native cursor descriptor address')
        prefix=capture.route.producer._read(original,dptr,12)[1]
    need(desc[:12]==prefix,'native descriptor immutable prefix differs')
    first,last,mode=struct.unpack_from('<III',desc);frame=u32(desc,32);dw,dh=u32(desc,12),u32(desc,16)
    need(first<=last<1024 and 0<=frame<=last-first and 1<=dw<=64 and 1<=dh<=64,'cursor animation/descriptor bounds differ')
    index=first+frame;count=struct.unpack_from('<H',resource,0x1004)[0]
    need(index<count<=1024 and reads['sprite_header']['address']==u32(resource,index*4),'live cursor sprite index/pointer differs')
    header,sprite=sprite_header(oracle['mouse'],index)
    need(reads['sprite_header']['data']==header and sprite.width<=dw and sprite.height<=dh,'live cursor header differs from source sprite')
    backing=reads['backing_header']['data']
    need(reads['backing_header']['address']==u32(state,8) and struct.unpack_from('<HH',backing)==(64,64)
         and u32(backing,184)==0x50ee24 and reads['backing_pixels']['address']==u32(backing,4),'native cursor backing pointer/layout differs')
    barracks=reads['barracks_resource']['data'];bptr=reads['barracks_pointer']
    need(bptr['address']==0x532144 and reads['barracks_resource']['address']==u32(bptr['data'])
         and 25<struct.unpack_from('<H',barracks,0x1004)[0]<=1024
         and reads['placeholder_sprite_header']['address']==u32(barracks,100),'live barracks resource pointer/index differs')
    need(reads['placeholder_sprite_header']['data']==sprite_header(oracle['barracks'],25)[0], 'live placeholder header differs from source sprite25')
    ranges=[(name,r['address'],r['address']+len(r['data'])) for name,r in reads.items()]
    for range_index,(name,start,end) in enumerate(ranges):
        for other,begin,finish in ranges[range_index+1:]:need(end<=begin or finish<=start,'cursor metadata/backing aliases: '+name+'/'+other)
        canvas=cp['canvas'];w,h=cp['values']['width'],cp['values']['height']
        for pointer,size in ((canvas['native'],188),(canvas['physical'],188),(canvas['native_pixels'],640*480),
                             (canvas['physical_pixels'],w*h),(cp['values']['pixels'],w*h)):
            need(end<=pointer or pointer+size<=start,'cursor metadata/backing aliases an owned surface')
    flag=u32(state,56);need(flag in (0,1) and flag==cp['core_values']['cursor'],'observed cursor flag differs from native checkpoint')
    result=dict(reads=reads,state=state,descriptor=desc,resource=resource,sprite=sprite,index=index,
        x=i32(state,48),y=i32(state,52),old_x=i32(state),old_y=i32(state,4),width=dw,height=dh,visible=flag,
        backing=reads['backing_pixels']['data'],barracks_address=reads['barracks_resource']['address'],
        placeholder_address=reads['placeholder_sprite_header']['address'])
    return result


def image_bytes(data,width,height):
    need(type(width) is int and type(height) is int and width>=640 and height>=480,'invalid image dimensions')
    need(type(data) is bytes and len(data)==width*height,'pixel allocation has wrong exact byte count')
    return np.frombuffer(data,dtype=np.uint8).reshape(height,width)


def compare(actual,expected):
    need(actual.shape==expected.shape,'pixel oracle dimensions differ')
    ys,xs=np.nonzero(actual!=expected)
    return dict(passed=len(xs)==0,compared_pixels=int(actual.size),mismatches=int(len(xs)),
                mismatch_bounds=None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1])


def centered(native,width,height):
    result=np.zeros((height,width),dtype=np.uint8);x,y=(width-640)//2,(height-480)//2
    result[y:y+480,x:x+640]=image_bytes(native,640,480);return result


def draw_sprite(image,sprite,x,y):
    need(0<=x and 0<=y and x+sprite.width<=image.shape[1] and y+sprite.height<=image.shape[0], 'source sprite is outside supported on-screen bounds')
    for yy in range(sprite.height):
        for xx in range(sprite.width):
            value=sprite.pixels[yy*sprite.width+xx]
            if value is not None:image[y+yy,x+xx]=value


def cursor_draw(image,cursor,backing):
    x,y,w,h=(cursor[k] for k in ('x','y','width','height'))
    need(0<=x and 0<=y and x+w<=image.shape[1] and y+h<=image.shape[0], 'cursor backing is outside supported on-screen bounds')
    result=np.frombuffer(backing,dtype=np.uint8).reshape(64,64).copy()
    result[:h,:w]=image[y:y+h,x:x+w]
    draw_sprite(image,cursor['sprite'],x,y)
    return result.tobytes()


def cursor_remove(image,cursor,backing):
    x,y,w,h=cursor['old_x'],cursor['old_y'],cursor['width'],cursor['height']
    need(0<=x and 0<=y and x+w<=image.shape[1] and y+h<=image.shape[0], 'old cursor backing is outside supported on-screen bounds')
    image[y:y+h,x:x+w]=np.frombuffer(backing,dtype=np.uint8).reshape(64,64)[:h,:w]


def audit_pixels(samples,width,height,route):
    """Reconstruct each actual draw boundary, without excluded rectangles."""
    need(set(samples)==set(capture.CHECKPOINTS),'all four measured pixel checkpoints required')
    first,before,after,final=(samples[n][0] for n in capture.CHECKPOINTS)
    c0,c1,c2,c3=(r['cursor'] for r in (first,before,after,final))
    result=dict(passed=False,checkpoints=[],native_slot_delta=None,placeholder_call=None,failures=[])
    def check(label,actual,expected):
        row=dict(check=label,**compare(actual,expected));result['checkpoints'].append(row)
        if not row['passed']:result['failures'].append(label+' pixel mismatch')
    ox,oy=(width-640)//2,(height-480)//2
    for name,rows in samples.items():
        for number,row in enumerate(rows,1):
            check(name+f'/{number}/physical_center_and_margins',image_bytes(row['physical'],width,height),centered(row['native'],width,height))
    p0=image_bytes(first['primary'],width,height)
    check('full-published/complete_primary_equals_physical',p0,image_bytes(first['physical'],width,height))
    need(c0['visible']==0,'full publish must be captured before native cursor redraw')
    # This bounded initial route has no input polling. Require unchanged
    # descriptor/position; never infer a moved or animated cursor sprite.
    for cursor in (c1,c2,c3):
        need(cursor['descriptor']==c0['descriptor'] and cursor['resource']==c0['resource']
             and cursor['state'][8:56]==c0['state'][8:56] and cursor['state'][60:]==c0['state'][60:],
             'cursor descriptor, desired position or pointer state changed across checkpoints')
        need(cursor['barracks_address']==c0['barracks_address'] and cursor['placeholder_address']==c0['placeholder_address'],
             'placeholder resource identity changed across checkpoints')
    group=[g for g in route['full_publish_routes'] if g['route']=='barracks']
    need(len(group)==1 and group[0]['complete'] is True,'complete native barracks publication route required')
    active=group[0]['cursor_initial'];need(type(active) is int and active in (0,1),'native cursor entry flag required')
    expected=p0.copy();backing=c0['backing']
    if active:backing=cursor_draw(expected,c0,backing)
    # All subsequent native canvas writes must be exactly within the twelve
    # source-bound inclusive dirty rectangles. Their actual later bytes are
    # copied in the same order as the native slot callbacks.
    n0=image_bytes(first['native'],640,480);n1=image_bytes(before['native'],640,480)
    allowed=np.zeros(n0.shape,dtype=bool);slots=[]
    for y in (75,206):
        for x in (126,197,268,339,410,481):
            allowed[y:y+65,x:x+33]=True
            expected[oy+y:oy+y+65,ox+x:ox+x+33]=n1[y:y+65,x:x+33]
            slots.append(dict(x=x,y=y,width=33,height=65,nonzero_pixels=int(np.count_nonzero(n1[y:y+64,x:x+32]))))
    result['native_slot_delta']=dict(unexpected_pixels=int(np.count_nonzero((n0!=n1)&~allowed)),slots=slots)
    if result['native_slot_delta']['unexpected_pixels']:result['failures'].append('native canvas changed outside twelve authenticated dirty slots')
    if any(row['nonzero_pixels']==0 for row in slots):result['failures'].append('one or more native slot interiors are blank')
    rect=route['cursor_rectangle']['values']
    need(rect['cursor']==active,'cursor changed before native placeholder rectangle call')
    intersects=(c0['x']+c0['width']>rect['x'] and rect['right']>c0['x']
                and c0['y']+c0['height']>rect['y'] and rect['bottom']>c0['y'])
    removed=bool(active and intersects)
    need(c1['visible']==int(active and not removed),'native cursor rectangle removal flag differs')
    if active:need((c1['old_x'],c1['old_y'])==(c0['x'],c0['y']),'native redraw did not retain desired cursor position')
    if removed:cursor_remove(expected,c1,backing)
    need(c1['backing']==backing,'native post-publication cursor backing differs from exact source pixels')
    check('placeholder-before/draw_order_complete_primary',image_bytes(before['primary'],width,height),expected)
    need(c2['state']==c1['state'] and c2['backing']==c1['backing'],'placeholder sprite call changed native cursor state/backing')
    check('placeholder-call/native_unchanged',image_bytes(after['native'],640,480),n1)
    check('placeholder-call/physical_unchanged',image_bytes(after['physical'],width,height),image_bytes(before['physical'],width,height))
    p=route['placeholder']['values'];need((p['x'],p['y'],p['width'],p['height'])==(ox+220,oy+289,203,120)
        and p['sprite']==c2['placeholder_address'] and p['resource']==c2['barracks_address'],'source-bound placeholder placement/pointers differ')
    # Compare this call independently against its actual before image too;
    # an earlier failure cannot be canceled by later overlay coverage.
    actual_delta=image_bytes(before['primary'],width,height).copy()
    draw_sprite(actual_delta,after['placeholder'],p['x'],p['y'])
    result['placeholder_call']=compare(image_bytes(after['primary'],width,height),actual_delta)
    if not result['placeholder_call']['passed']:result['failures'].append('native placeholder before/after call pixels differ')
    draw_sprite(expected,after['placeholder'],p['x'],p['y'])
    check('placeholder-after/draw_order_complete_primary',image_bytes(after['primary'],width,height),expected)
    # The inner placeholder renderer re-presents when entered visible, and
    # barracks also unconditionally calls native Present at 433E72. Thus a
    # previously hidden cursor becomes visible at final-ready as well.
    need(c3['visible']==1,'final native cursor visible flag differs')
    need((c3['old_x'],c3['old_y'])==(c3['x'],c3['y']),'final native cursor backing position differs')
    if c2['visible']==0:backing=cursor_draw(expected,c3,backing)
    need(c3['backing']==backing,'final native cursor backing differs from exact post-placeholder pixels')
    for number,row in enumerate(samples['final-ready'],1):
        check(f'final-ready/{number}/native_unchanged',image_bytes(row['native'],640,480),n1)
        check(f'final-ready/{number}/draw_order_complete_primary',image_bytes(row['primary'],width,height),expected)
    result['cursor']=dict(initial_visible=active,rectangle_intersection=intersects,removed_before_placeholder=removed,
        source_sprite_index=c0['index'],draw_order='full publish; cursor redraw if entered visible; twelve native dirty slot blits; intersecting cursor removal; source placeholder; native cursor re-present')
    result['passed']=not result['failures'];return result


def owned_cleanup(receipt,plan):
    identities=[receipt['cdb'],*receipt['candidates']];need(len(identities)==2,'one debugger and one owned candidate required')
    debugger,owner=identities
    for row in identities:
        integer(row['process_id'],'process id',1);integer(row['creation_filetime'],'creation filetime',1,(1<<63)-1)
        need(row.get('handle_retained') is True,'original process handle must be retained')
        timestamp(row['creation_utc'])
    integer(owner['parent_process_id'],'parent process id',1)
    need(owner['process_id']!=debugger['process_id'] and owner['parent_process_id']==debugger['process_id']
         and owner['creation_filetime']>=debugger['creation_filetime'] and owner['candidate_sha256']==plan['candidate_sha256']
         and path_value(debugger['path'])==path_value(plan['cdb']) and path_value(owner['path'])==path_value(plan['candidate_path']),
         'retained parent/process/path/candidate identity differs')
    cleanup=receipt['cleanup'];need(cleanup.get('desktop_closed') is True and len(cleanup['candidates'])==1,'owned desktop/candidate cleanup incomplete')
    for row,identity in zip((cleanup['cdb'],cleanup['candidates'][0]),identities):
        need(row.get('absent') is True and row.get('handle_closed') is True,'owned process absence/handle cleanup incomplete')
        same_json(row['identity'],identity,'cleanup process identity')
    need(cleanup['cdb'].get('input_closed') is True,'private debugger input handle not closed')
    return owner


def bind_canvas(row,folder,cp,packet,reader,owner,plan):
    v=cp['canvas'];w,h=plan['width'],plan['height']
    need(row.get('paused') is True and row.get('capture')=='owned_physical_mirror','paused owned physical canvas required')
    same_json(row['game_identity'],owner,'canvas process identity')
    for key,val in dict(pixel_reads=1,physical_header_reads=2,native_header_reads=2,state_reads=2,e0_reads=2,width=w,height=h,pitch=w).items():
        need(type(row.get(key)) is int and row[key]==val,'physical capture '+key+' differs')
    n=row['native']
    for key,val in dict(width=640,height=480,pitch=640,pixel_reads=1).items():need(type(n.get(key)) is int and n[key]==val,'native capture '+key+' differs')
    need((row['state_va'],row['physical'],row['physical_pixels'],n['surface'],n['base'])==
         (packet['canvas_state_va'],v['physical'],v['physical_pixels'],v['native'],v['native_pixels']),'canvas address identity differs')
    raw=reader.artifact(row,path=folder/'surface.raw',size=w*h)
    native=reader.artifact(n,path=folder/'native-surface.raw',size=640*480)
    reads=paired_reads(row,folder,'surface',reader,dict(state=128,e0=4,physical_header=188,native_header=188))
    addresses=dict(state=packet['canvas_state_va'],e0=0x5202e0,physical_header=v['physical'],native_header=v['native'])
    for name,address in addresses.items():need(reads[name]['address']==address,'canvas '+name+' read address differs')
    expected=dict(phase=1,physical=v['physical'],native=v['native'],root_esp=v['root_esp'],owner_tid=v['tid'],enter_status=1,
        mirror_status=1,leave_status=0,fault=0,allocations=1,frees=0,mirrors=v['mirrors'],pending_header=0,pending_pixels=0,
        native_pixels=v['native_pixels'],physical_pixels=v['physical_pixels'])
    state=reads['state']['data'];need(all(u32(state,packet['canvas_state_offsets'][key])==val for key,val in expected.items()),'captured canvas ownership differs from actual checkpoint')
    need(u32(reads['e0']['data'])==v['native'],'E0 no longer owns native canvas')
    for key,dims,pointer in (('native_header',(640,480),v['native_pixels']),('physical_header',(w,h),v['physical_pixels'])):
        header=reads[key]['data']
        need(struct.unpack_from('<HH',header)==dims and u32(header,4)==pointer and u32(header,184)==0x50ee24,'canvas dimensions/pixel pointer/vtable differs')
    need(u32(reads['native_header']['data'],172)==0,'native memory canvas unexpectedly owns COM')
    same_json(n['header'],row['reads']['before']['native_header'],'native header alias')
    need(timestamp(row['started_at'])<=timestamp(row['captured_at']),'canvas capture time order differs')
    return raw,native,reads


def bound_capture_report(log,packet,full,checkpoint):
    """Recheck prefix semantics only after exact full packet/probe authentication."""
    text=log.decode('utf-8-sig');base=copy.deepcopy(packet);base.pop('primary_capture')
    sequence=capture.route.evaluate_sequence(text,base,checkpoint=checkpoint)
    slots=capture.route.evaluate_slots(text,base,sequence,checkpoint=checkpoint)
    primary=capture.route.evaluate_primary_route(text,base,sequence,checkpoint=checkpoint)
    for label,part in (('native route',sequence),('slots',slots),('primary route',primary)):
        verdict='sequence_passed' if label=='native route' else 'passed'
        need(part.get(verdict) is True and part.get('failures')==[],checkpoint+' '+label+' failed: '+str(part.get('failures')))
    core=dict(primary_route_sequence=primary,modal_sequence=sequence)
    observed=capture.evaluate_primary_sequence(text,packet,core,checkpoint)
    cp=observed['checkpoints'][-1];cp['core_values']=primary['checkpoints'][-1]['values']
    return dict(passed=True,candidate_sha256=full['candidate_sha256'],source=dict(log_raw_sha256=sha(log)),
                capture_checkpoint=cp,primary_route_sequence=primary,primary_sequence=observed,modal_sequence=sequence,slot_trace=slots)


def bind_triplet(receipt,*,reader=None):
    """Authenticate actual host receipts and then audit every measured boundary."""
    reader=reader or capture.Artifacts()
    need(receipt.get('schema')=='clash95_modal_primary_triplet_v1','wrong primary triplet receipt schema')
    need(receipt.get('failures')==[],'host already reported a capture failure')
    need(receipt.get('manual_input_proof') is False and receipt.get('promotion_ready') is False,'excessive triplet evidence claim')
    plan=receipt['plan'];need(plan.get('schema')=='clash95_modal_primary_capture_plan_v1','wrong primary plan schema')
    root=path_value(plan['out_dir']);need(plan['run_id']==root.name,'planned run identity differs')
    same_json(plan['child_environment'],dict(CLASH_PROXY_PRESENT='0',parent_environment_modified=False),'child-only environment')
    for key in ('manual_input_proof','visible_composition_proof','promotion_ready'):need(plan.get(key) is False,'excessive plan claim: '+key)
    for role,relative in SOURCE_PATHS.items():
        need(path_value(plan[role])==path_value(ROOT/relative),'noncanonical source role '+role)
    roles={'original':'original_sha256','input_candidate':'candidate_sha256','candidate_path':'candidate_sha256',
        'candidate_manifest':'candidate_manifest_sha256','proxy_input':'proxy_sha256','proxy_path':'proxy_sha256',
        'proxy_manifest':'proxy_manifest_sha256','python':'python_sha256','cdb':'cdb_sha256',
        **{role:('host_sha256' if role=='host_path' else role+'_sha256') for role in SOURCE_PATHS}}
    files={role:reader.read(plan[role],expected=plan[digest]) for role,digest in roles.items()}
    packet=json.loads(reader.artifact(receipt['packet'],path=root/'packet.json'))
    for sources in (packet['capture_source_hashes'],packet['primary_capture']['source_hashes']):
        for relative,digest in sources.items():reader.read(ROOT/relative,expected=digest)
    sidecar=path_value(plan['candidate_manifest'])
    need(sidecar.name.endswith('.candidate.json'),'canonical candidate sidecar suffix required')
    stem=sidecar.name.removesuffix('.candidate.json')
    reader.read(sidecar.with_name(stem+'.exe'),expected=plan['candidate_sha256'])
    reader.read(sidecar.with_name(stem+'.cdb'))
    probe=reader.artifact(receipt['probe'],path=root/'modal-primary-barracks.cdb')
    scripts={name:reader.read(path) for name,path in packet['primary_capture']['ready_files'].items()}
    log=reader.artifact(receipt['final_log'],path=root/'cdb.log')
    full=capture.evaluate_trace(log,original=files['original'],candidate=files['candidate_path'],packet=packet,
        generated_probe=probe,ready_scripts=scripts,checkpoint='final-ready')
    for key in ('stage','resolution','castle_index','availability','minimap_viewport','candidate_sha256','original_sha256',
                'canvas_state_va','canvas_state_offsets','stop_va','checkpoints'):
        same_json(plan[key],packet[key],'plan/packet '+key)
    need(plan['route']==packet['route']['name']=='barracks' and plan['probe_sha256']==sha(probe),'plan route/probe differs')
    width,height=map(int,packet['resolution'].split('x'))
    need(type(plan['width']) is int and type(plan['height']) is int and (plan['width'],plan['height'])==(width,height),'plan dimensions differ')
    same_json(packet['candidate_manifest'],dict(path=str(path_value(plan['candidate_manifest'])),sha256=plan['candidate_manifest_sha256']),'candidate sidecar binding')
    need(path_value(plan['proxy_manifest'])==path_value(packet['primary_capture']['proxy_manifest']['path'])
         and sha(files['proxy_manifest'])==packet['primary_capture']['proxy_manifest']['sha256'],'proxy manifest binding differs')
    proxy_manifest=json.loads(files['proxy_manifest'])
    need(path_value(proxy_manifest['output'])==path_value(plan['proxy_input']),'proxy manifest output role differs')
    reader.read(proxy_manifest['source'],expected=plan['proxy_source_sha256'])
    for name,path in packet['primary_capture']['ready_files'].items():
        need(path_value(path)==root/('primary-'+name+'.cdb'),'checkpoint script path differs')
        reader.artifact(plan['primary_ready_scripts'][name],path=path,size=len(scripts[name]))
    need(receipt['final_log'].get('capture_prefix_preserved') is True,'host did not retain its validated final prefix')
    owner=owned_cleanup(receipt,plan);oracle=source_assets(plan['work_dir'],reader)
    checkpoints=receipt['checkpoints'];need(type(checkpoints) is list and len(checkpoints)==4,'four exact checkpoints required')
    samples={};diagnostics=[];previous=b'';previous_time=None
    for index,(name,checkpoint) in enumerate(zip(capture.CHECKPOINTS,checkpoints)):
        need(checkpoint['name']==name and type(checkpoint['index']) is int and checkpoint['index']==index,'checkpoint identity/order differs')
        folder=root/'checkpoints'/name
        prefix=reader.artifact(checkpoint['prefix'],path=folder/'capture-prefix.log')
        need(log.startswith(prefix) and prefix.startswith(previous) and len(prefix)>len(previous),'checkpoint log prefix not strictly nested in final log')
        previous=prefix
        retained=json.loads(reader.artifact(checkpoint['trace'],path=folder/'trace.json'))
        current=bound_capture_report(prefix,packet,full,name);cp=current['capture_checkpoint']
        need(retained.get('passed') is True and retained['source']['log_raw_sha256']==sha(prefix)
             and retained['source']['generated_probe_sha256']==sha(probe),'retained checkpoint trace binding differs')
        projected=copy.deepcopy(cp);projected.pop('core_values')
        same_json(retained['capture_checkpoint'],projected,'retained checkpoint observation')
        need(len(checkpoint['snapshots'])==(3 if index==3 else 1),'wrong matched sample count')
        phase=[];stable=[]
        for number,row in enumerate(checkpoint['snapshots'],1):
            sample_folder=folder/f'capture-{number}';physical,native,headers=bind_canvas(row,sample_folder,cp,packet,reader,owner,plan)
            sample=row['primary'];same_json(sample['game_identity'],owner,'primary owned identity')
            need(sample.get('schema')=='clash95_modal_primary_snapshot_receipt_v1' and sample.get('paused') is True
                 and sample.get('run_id')==plan['run_id'] and sample.get('manual_input_proof') is False and sample.get('promotion_ready') is False,
                 'primary receipt scope/run differs')
            need(path_value(sample['proxy_module']['path'])==path_value(plan['proxy_path']),'loaded proxy path differs')
            paired_reads(sample,sample_folder,'primary',reader,dict(primary=220,backend=176,surface_full=32,palette=1036,
                proxy_header=512,proxy_getpalette=len(capture.GET_PALETTE_BYTES),surface=4,surface_vtable=144,palette_vtable=28))
            primary=reader.artifact(sample['pixels'],path=sample_folder/'primary.raw',size=width*height)
            palette=reader.artifact(sample['palette_entries'],path=sample_folder/'primary-palette.bin',size=1024)
            observation=capture.audit_snapshot(sample,proxy_image=files['proxy_path'],trace=current,artifacts=reader)
            need(observation['cached_primary_snapshot_valid'] is True,'cached primary read was rejected')
            cursor=bind_cursor(row['cursor'],sample_folder,reader,oracle,files['original'],cp)
            need(timestamp(row['started_at'])<=timestamp(sample['started_at'])<=timestamp(sample['captured_at']), 'matched primary/canvas capture time order differs')
            if previous_time:need(previous_time<=timestamp(row['started_at']),'checkpoint/sample capture order differs')
            previous_time=timestamp(sample['captured_at'])
            value=dict(native=native,physical=physical,primary=primary,palette=palette,cursor=cursor,placeholder=oracle['placeholder'])
            phase.append(value)
            primary_headers=tuple((name,record['address'],reader.artifact(record)) for name,record in sorted(sample['reads']['before'].items()))
            stable.append((native,physical,primary,palette,headers,cursor['reads'],primary_headers))
            diagnostics.append(dict(checkpoint=name,index=number,cached_primary=observation,
                physical_sha256=sha(physical),native_sha256=sha(native),primary_sha256=sha(primary),palette_sha256=sha(palette)))
        # Absolute per-sample paths differ; compare actual bytes/addresses.
        normalized=stable
        need(all(value==normalized[0] for value in normalized),'three matched final captures differ')
        samples[name]=phase
        if index<3:
            resume=checkpoint['resume'];need(checkpoint.get('resumed') is True and resume.get('written') is True
                and resume.get('command')=='g' and type(resume.get('bytes')) is int and resume['bytes']==3
                and resume.get('command_sha256')==sha(b'g\r\n') and resume.get('prefix_sha256')==sha(prefix)
                and resume.get('input_method')=='private_debugger_stdin' and resume.get('checkpoint')==name
                and type(resume.get('index')) is int and resume['index']==index,'exact private debugger continuation receipt differs')
            same_json(resume['debugger_identity'],receipt['cdb'],'resume debugger identity')
            need(timestamp(resume['sent_at'])>=previous_time,'debugger resumed before retained sample completed')
            previous_time=timestamp(resume['sent_at'])
        else:need(checkpoint['resume'] is None and checkpoint.get('resumed') is False,'final paused boundary must not resume')
    same_json(receipt['snapshots'],checkpoints[-1]['snapshots'],'top final snapshot alias')
    same_json(receipt['capture_prefix'],checkpoints[-1]['prefix'],'top final prefix alias')
    need(receipt.get('clean_stable_pair') is True,'host final stable triplet not affirmative')
    pixels=audit_pixels(samples,width,height,full['primary_route_sequence'])
    reader.unchanged()
    return dict(cached_primary_snapshot_valid=True,three_matched_captures=True,source_authenticated=True,
        owned_cleanup_verified=True,primary_composition_proven=pixels['passed'],pixel_audit=pixels,samples=diagnostics,
        candidate_sha256=packet['candidate_sha256'],stage=packet['stage'],resolution=packet['resolution'],
        proof_class='hidden_controlled_barracks_four_draw_boundaries',source_assets=oracle['receipts'],
        final_trace_source=full['source'],artifacts=reader.receipts(),visible_composition_proof=False,
        manual_input_proof=False,native_modal_exit_proven=False,selected_panel_proven=False,promotion_ready=False,limits=LIMITS)


def palette_rendering(palette):
    need(type(palette) is bytes and len(palette)==1024,'exact captured palette required')
    colors=np.frombuffer(palette,dtype=np.uint8).reshape(256,4)[:,:3]
    if not np.any(colors):
        return ('grayscale-index-empty-palette',
                np.repeat(np.arange(256,dtype=np.uint8)[:,None],3,axis=1),
                'grayscale_index_preview_empty_attached_palette')
    return 'directdraw-palette',colors,'matched_current_attached_proxy_palette'


def validate_png(metadata,raw,palette,*,reader,raw_path,palette_path,png_path,log_path,width,height):
    for key,path in (('raw_path',raw_path),('palette_path',palette_path),('png_path',png_path),('log_path',log_path)):
        need(path_value(metadata[key])==path_value(path),'PNG '+key+' differs')
    for key,value in dict(width=width,height=height,pitch=width,raw_bytes=len(raw),used_bytes=len(raw)).items():
        need(type(metadata[key]) is int and metadata[key]==value,'PNG '+key+' differs')
    mode,colors,scope=palette_rendering(palette)
    need(metadata['palette_mode']==mode and metadata['raw_sha256']==metadata['used_sha256']==sha(raw),'PNG raw/palette mode differs')
    png=reader.read(png_path,expected=metadata['png_sha256'])
    rgb=np.array(Image.open(io.BytesIO(png)).convert('RGB'))
    expected=colors[image_bytes(raw,width,height)]
    need(rgb.shape==expected.shape and np.array_equal(rgb,expected),'PNG pixels differ from actual raw and attached palette')
    return dict(path=str(path_value(png_path)),sha256=sha(png),raw_sha256=sha(raw),palette_sha256=sha(palette),width=width,height=height,
                palette_mode=mode,scope=scope)


def evaluate(summary_path):
    reader=capture.Artifacts();result=dict(schema='clash95_modal_primary_surface_audit_v1',passed=False,failures=[],
        source_authenticated=False,primary_composition_proven=False,owned_cleanup_verified=False,
        manual_input_proof=False,visible_composition_proof=False,selected_panel_proven=False,promotion_ready=False,limits=LIMITS)
    try:
        path=path_value(summary_path);summary=reader.json(path);plan=summary['plan'];root=path_value(plan['out_dir'])
        need(path==root/'summary.json' and summary.get('schema')=='clash95_modal_primary_capture_v1','canonical summary/schema required')
        need(summary.get('passed') is True and summary.get('executed') is True and summary.get('failures')==[],'host summary is not successful')
        for key in ('manual_input_proof','visible_composition_proof','promotion_ready'):need(summary.get(key) is False,'excessive host claim: '+key)
        triplet=json.loads(reader.artifact(summary['primary_triplet'],path=root/'primary-triplet.json'))
        for key in ('plan','checkpoints','snapshots','clean_stable_pair','cdb','candidates','cleanup','packet','probe','capture_prefix','final_log'):
            same_json(triplet[key],summary[key],'summary/triplet '+key)
        audit=bind_triplet(triplet,reader=reader);result['capture_audit']=audit
        need(audit['primary_composition_proven'] is True,'source-bound primary draw-order pixel audit failed')
        same_json(summary['snapshot'],summary['snapshots'][0],'first snapshot alias')
        for key in ('original_sha256','input_candidate_sha256','candidate_sha256','proxy_sha256'):
            expected=plan['candidate_sha256'] if key=='input_candidate_sha256' else plan[key]
            need(summary['postrun_identity'][key]==expected,'post-run '+key+' differs')
        final=summary['final_trace'];need(final.get('passed') is True and final['source']==audit['final_trace_source'],'retained final trace differs from fresh full binding')
        screenshots=[];w,h=plan['width'],plan['height'];logpath=summary['capture_prefix']['path']
        raw=reader.read(summary['snapshot']['path']);palrec=summary['snapshots'][0]['primary']['palette_entries'];palette=reader.artifact(palrec)
        same_json(reader.json(root/'surface.png.json'),summary['png'],'root PNG metadata')
        screenshots.append(validate_png(summary['png'],raw,palette,reader=reader,raw_path=summary['snapshot']['path'],
            palette_path=palrec['path'],png_path=root/'surface.png',log_path=logpath,width=w,height=h))
        same_json(summary['primary_pngs'],[s['primary_png'] for s in summary['snapshots']],'final primary PNG aliases')
        for checkpoint in summary['checkpoints']:
            for snapshot in checkpoint['snapshots']:
                folder=path_value(snapshot['path']).parent;p=snapshot['primary']
                for kind,rawrec,dims in (('primary',p['pixels'],(w,h)),('physical',snapshot,(w,h)),('native',snapshot['native'],(640,480))):
                    row=snapshot[kind+'_png'];meta=reader.json(folder/(kind+'-png.json'))
                    mode,_,scope=palette_rendering(reader.artifact(p['palette_entries']))
                    need(path_value(row['metadata_path'])==folder/(kind+'-png.json')
                         and sha(reader.read(row['metadata_path']))==row['metadata_sha256']
                         and path_value(row['path'])==folder/(kind+'.png') and row['sha256']==meta['png_sha256']
                         and row['raw_sha256']==rawrec['sha256'] and row['palette_sha256']==p['palette_entries']['sha256']
                         and row['checkpoint']==checkpoint['name'] and row['capture_method']=='hidden_cached_primary_and_owned_surfaces'
                         and row['palette_mode']==mode and row['color_scope']==scope
                         and row['palette_colors_available'] is (mode=='directdraw-palette'),
                         'checkpoint PNG receipt binding differs')
                    need(type(row['width']) is int and type(row['height']) is int and (row['width'],row['height'])==dims,'PNG receipt dimensions differ')
                    screenshots.append(validate_png(meta,reader.artifact(rawrec),reader.artifact(p['palette_entries']),reader=reader,
                        raw_path=rawrec['path'],palette_path=p['palette_entries']['path'],png_path=folder/(kind+'.png'),
                        log_path=checkpoint['prefix']['path'],width=dims[0],height=dims[1]))
        reader.unchanged();result.update(passed=True,source_authenticated=True,primary_composition_proven=True,
            owned_cleanup_verified=True,screenshots=screenshots,stage=audit['stage'],resolution=audit['resolution'],candidate_sha256=audit['candidate_sha256'])
    except (OSError,UnicodeError,ValueError,TypeError,KeyError,IndexError,AttributeError,struct.error) as error:
        result['failures'].append(str(error))
        result.update(passed=False,source_authenticated=False,primary_composition_proven=False,owned_cleanup_verified=False)
    result['artifacts']=reader.receipts();return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--summary',type=Path,required=True)
    args=parser.parse_args(argv);result=evaluate(args.summary);print(json.dumps(result,indent=2));return 0 if result['passed'] else 2


if __name__=='__main__':raise SystemExit(main())
