"""Executable offline pixel/provenance fixtures; synthetic files are not evidence."""
import copy
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

import modal_primary_surface_audit as tool
import modal_primary_capture as capture
import hd_layout_asset_composition as assets


def put(data,offset,value):struct.pack_into('<I',data,offset,value)


def pixel_fixture(width=1024,height=768,active=1,position='clear'):
    """Independent slice compositor implementing the documented native order."""
    ox,oy=(width-640)//2,(height-480)//2
    yy,xx=np.indices((480,640));n0=((xx*7+yy*13)%251+1).astype(np.uint8);n1=n0.copy()
    for row,y in enumerate((75,206)):
        for col,x in enumerate((126,197,268,339,410,481)):
            n1[y:y+65,x:x+33]=(33+row*80+col*7)
    cursor=assets.Sprite(3,3,(None,245,None,246,247,248,None,249,None))
    placeholder=assets.Sprite(203,120,tuple((i*5+32)%251+1 for i in range(203*120)))
    coords={'clear':(25,20),'slot':(ox+130,oy+80),'placeholder':(ox+250,oy+300)}
    x,y=position if isinstance(position,tuple) else coords[position];dw=dh=4
    state=bytearray(68);put(state,0,x);put(state,4,y);put(state,8,0x28030000)
    put(state,48,x);put(state,52,y);put(state,60,0x5196a0);put(state,64,0x28010000)
    descriptor=bytearray(40)
    for off,value in ((0,2),(4,2),(12,dw),(16,dh)):put(descriptor,off,value)
    backing=np.full((64,64),151,dtype=np.uint8)
    def centered(n):
        a=np.zeros((height,width),dtype=np.uint8);a[oy:oy+480,ox:ox+640]=n;return a
    def paint(a,s,px,py):
        for i,value in enumerate(s.pixels):
            if value is not None:a[py+i//s.width,px+i%s.width]=value
    def row(n,p,flag,b):
        s=state.copy();put(s,56,flag)
        c=dict(state=bytes(s),descriptor=bytes(descriptor),resource=b'unchanged synthetic cursor resource',sprite=cursor,index=2,
            x=x,y=y,old_x=x,old_y=y,width=dw,height=dh,visible=flag,backing=b.tobytes(),
            barracks_address=0x28050000,placeholder_address=0x28060000)
        return dict(native=n.tobytes(),physical=centered(n).tobytes(),primary=p.tobytes(),cursor=c,placeholder=placeholder)
    p=centered(n0);first=row(n0,p,0,backing)
    if active:
        backing[:dh,:dw]=p[y:y+dh,x:x+dw];paint(p,cursor,x,y)
    for sy in (75,206):
        for sx in (126,197,268,339,410,481):p[oy+sy:oy+sy+65,ox+sx:ox+sx+33]=n1[sy:sy+65,sx:sx+33]
    intersects=(max(x,ox+220)<min(x+dw,ox+423) and max(y,oy+289)<min(y+dh,oy+409))
    visible=int(active and not intersects)
    if active and intersects:p[y:y+dh,x:x+dw]=backing[:dh,:dw]
    before=row(n1,p,visible,backing)
    paint(p,placeholder,ox+220,oy+289);after=row(n1,p,visible,backing)
    if not visible:
        backing[:dh,:dw]=p[y:y+dh,x:x+dw];paint(p,cursor,x,y)
    final=row(n1,p,1,backing)
    samples={n:[r] for n,r in zip(capture.CHECKPOINTS,(first,before,after,final))}
    samples['final-ready']=[copy.deepcopy(final) for _ in range(3)]
    route=dict(full_publish_routes=[dict(route='barracks',complete=True,cursor_initial=active)],
        cursor_rectangle={'values':dict(cursor=active,x=ox+220,y=oy+289,right=ox+423,bottom=oy+409)},
        placeholder={'values':dict(x=ox+220,y=oy+289,width=203,height=120,sprite=0x28060000,resource=0x28050000)})
    return samples,route


def s32(sprites):
    table=bytearray(4096);body=bytearray()
    for index,sprite in enumerate(sprites):
        put(table,index*4,4096+len(body));body+=struct.pack('<5H',sprite.width,sprite.height,0,0,0)
        for y in range(sprite.height):
            row=list(sprite.pixels[y*sprite.width:(y+1)*sprite.width]);i=0
            while i<len(row):
                transparent=row[i] is None;j=i+1
                while j<len(row) and j-i<127 and (row[j] is None)==transparent:j+=1
                body.append((0x80 if transparent else 0)+(j-i))
                if not transparent:body.extend(row[i:j])
                i=j
    return bytes(table+body)


def llrs(tree,trailing=0):
    data=bytearray(b'llrs\x01\0\0\0'+struct.pack('<II',len(tree)+1,0))
    def directory(node,root=False):
        padding=0 if root else trailing
        start=len(data);data.extend(struct.pack('<I',len(node))+bytes((len(node)+1)*26+padding))
        # Inactive native slots may contain arbitrary stale name bytes.
        data[start+4+len(node)*26:start+4+len(node)*26+14]=b'\xff'*14
        length=4+(len(node)+1)*26+padding
        for i,(name,value) in enumerate(node.items()):
            if type(value) is dict:flags=2;offset,size=directory(value)
            else:flags=1;offset=len(data);size=len(value);data.extend(value)
            pos=start+4+i*26;encoded=name.encode();data[pos:pos+len(encoded)]=encoded
            struct.pack_into('<III',data,pos+14,flags,offset,size)
        return start,length
    directory(tree,root=True);return bytes(data)


def file_receipt(path,data,address=None):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    result=dict(path=str(path),sha256=tool.sha(data),bytes=len(data))
    if address is not None:result['address']=address
    return result


class PixelTests(unittest.TestCase):
    def test_all_draw_boundaries_both_cursor_branches_and_three_resolutions(self):
        for w,h in ((1024,768),(1920,1080),(802,602)):
            for active in (0,1):
                for position in ('clear','slot','placeholder'):
                    samples,route=pixel_fixture(w,h,active,position)
                    report=tool.audit_pixels(samples,w,h,route)
                    with self.subTest(resolution=(w,h),active=active,position=position):self.assertTrue(report['passed'],report['failures'])
                    self.assertEqual(report['placeholder_call']['compared_pixels'],w*h)
                    self.assertEqual(len(report['native_slot_delta']['slots']),12)

    def test_every_checkpoint_and_final_triplet_member_is_compared(self):
        samples,route=pixel_fixture()
        for name,rows in samples.items():
            for index in range(len(rows)):
                for kind in ('primary','physical','native'):
                    bad=copy.deepcopy(samples);raw=bytearray(bad[name][index][kind]);raw[4]^=1;bad[name][index][kind]=bytes(raw)
                    with self.subTest(name=name,index=index,kind=kind):
                        self.assertFalse(tool.audit_pixels(bad,1024,768,route)['passed'])

    def test_later_opaque_overlay_cannot_hide_a_bad_before_call(self):
        samples,route=pixel_fixture(position='placeholder');bad=copy.deepcopy(samples)
        raw=bytearray(bad['placeholder-before'][0]['primary']);raw[(144+300)*1024+192+250]^=1
        bad['placeholder-before'][0]['primary']=bytes(raw)
        report=tool.audit_pixels(bad,1024,768,route)
        self.assertFalse(report['passed'])
        self.assertIn('placeholder-before/draw_order_complete_primary pixel mismatch',report['failures'])

    def test_full_backing_outside_current_sprite_must_remain_exact(self):
        samples,route=pixel_fixture()
        for name in capture.CHECKPOINTS[1:]:
            bad=copy.deepcopy(samples);b=bytearray(bad[name][0]['cursor']['backing']);b[-1]^=1;bad[name][0]['cursor']['backing']=bytes(b)
            with self.subTest(checkpoint=name),self.assertRaisesRegex(ValueError,'backing'):
                tool.audit_pixels(bad,1024,768,route)

    def test_unknown_cursor_motion_missing_capture_truncation_and_wrong_source_fail(self):
        samples,route=pixel_fixture()
        bad=copy.deepcopy(samples);del bad['placeholder-before']
        with self.assertRaises(ValueError):tool.audit_pixels(bad,1024,768,route)
        bad=copy.deepcopy(samples);bad['final-ready'][1]['primary']=b''
        with self.assertRaises(ValueError):tool.audit_pixels(bad,1024,768,route)
        bad=copy.deepcopy(samples);state=bytearray(bad['placeholder-before'][0]['cursor']['state']);state[48]^=1
        bad['placeholder-before'][0]['cursor']['state']=bytes(state)
        with self.assertRaisesRegex(ValueError,'position'):tool.audit_pixels(bad,1024,768,route)
        bad=copy.deepcopy(samples);bad['placeholder-after'][0]['placeholder']=assets.Sprite(203,120,(7,)*(203*120))
        self.assertFalse(tool.audit_pixels(bad,1024,768,route)['passed'])

    def test_unconditional_final_present_is_required_for_inactive_entry(self):
        samples,route=pixel_fixture(active=0);bad=copy.deepcopy(samples);bad['final-ready'][0]['cursor']['visible']=0
        with self.assertRaisesRegex(ValueError,'visible flag'):tool.audit_pixels(bad,1024,768,route)

    def test_native_changes_outside_authenticated_slots_and_blank_slots_fail(self):
        samples,route=pixel_fixture()
        bad=copy.deepcopy(samples)
        for name in capture.CHECKPOINTS[1:]:
            for row in bad[name]:
                raw=bytearray(row['native']);raw[100]^=1;row['native']=bytes(raw)
                raw=bytearray(row['physical']);raw[144*1024+192+100]^=1;row['physical']=bytes(raw)
        result=tool.audit_pixels(bad,1024,768,route)
        self.assertFalse(result['passed']);self.assertEqual(result['native_slot_delta']['unexpected_pixels'],1)
        bad=copy.deepcopy(samples);raw=bytearray(bad['placeholder-before'][0]['native'])
        for y in range(75,139):raw[y*640+126:y*640+158]=bytes(32)
        bad['placeholder-before'][0]['native']=bytes(raw)
        self.assertFalse(tool.audit_pixels(bad,1024,768,route)['passed'])


class AssetAndBindingTests(unittest.TestCase):
    def test_native_directory_floor_keeps_trailing_bytes_outside_readable_slots(self):
        payload=b'bounded source payload'
        resource=llrs({'GFX':{'CASTLE.CHR':{'DW_12.S32':payload}}},trailing=22)
        self.assertEqual(tool.resource_member(resource,('GFX','CASTLE.CHR','DW_12.S32')),payload)
        # Truncation and a false active count remain errors; padding is never
        # parsed as an additional active slot or substituted for a real member.
        with self.assertRaises(ValueError):tool.resource_member(resource[:-1],('GFX','CASTLE.CHR','DW_12.S32'))
        malformed=bytearray(resource);put(malformed,16,2)
        with self.assertRaises(ValueError):tool.resource_member(bytes(malformed),('GFX','CASTLE.CHR','DW_12.S32'))

    @unittest.skipUnless(Path('C:/Clash/DATA/maximum.res').is_file() and Path('C:/Clash/DATA/minimum.res').is_file(),
                         'exact user-owned minimum/maximum resources required')
    def test_actual_native_resources_and_nondivisible_directory_extents(self):
        reader=capture.Artifacts();oracle=tool.source_assets(Path('C:/Clash'),reader)
        self.assertEqual(oracle['receipts']['barracks_member_sha256'],tool.BARRACKS_MEMBER_SHA256)
        self.assertEqual((oracle['placeholder'].width,oracle['placeholder'].height),(203,120))
        for index in (0,2,4,6,8):
            sprite=assets.decode_sprite(oracle['barracks'],index)
            self.assertEqual((sprite.width,sprite.height),(96,51))
        reader.unchanged()

    def test_real_llrs_walker_and_source_sprites_with_drift_rejection(self):
        tiny=assets.Sprite(3,2,(1,None,2,3,4,None));mouse=s32([tiny]*3)
        placeholder=assets.Sprite(203,120,(31,)*(203*120));bar=s32([tiny]*25+[placeholder])
        minimum=llrs({'GFX':{'MOUSE.S32':mouse}});maximum=llrs({'GFX':{'CASTLE.CHR':{'DW_12.S32':bar}}})
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'DATA').mkdir();(root/'DATA/minimum.res').write_bytes(minimum);(root/'DATA/maximum.res').write_bytes(maximum)
            with patch.object(assets,'RESOURCE_SHA256',tool.sha(minimum)),patch.object(tool,'MAXIMUM_SHA256',tool.sha(maximum)), \
                 patch.object(tool,'BARRACKS_MEMBER_SHA256',tool.sha(bar)):
                reader=capture.Artifacts();result=tool.source_assets(root,reader)
                self.assertEqual(result['placeholder'],placeholder);self.assertEqual(assets.decode_sprite(result['mouse'],2),tiny)
                (root/'DATA/maximum.res').write_bytes(maximum+b'x')
                with self.assertRaises(ValueError):reader.unchanged()
                with self.assertRaises(ValueError):tool.source_assets(root,capture.Artifacts())
        with self.assertRaises(ValueError):tool.resource_member(minimum,('GFX','MISSING.S32'))
        with self.assertRaises(ValueError):tool.resource_member(minimum[:30],('GFX','MOUSE.S32'))

    def test_normalized_regions_allow_adjacent_different_flags_but_reject_overlap(self):
        a=dict(address=0x10000,size=4096,state=0x1000,protect=4)
        b=dict(address=0x11000,size=4096,state=0x1000,protect=2)
        result=tool.region_set([a,b],[a,b]);self.assertEqual(len(result),2)
        same=dict(b,protect=4);merged=dict(a,size=8192)
        self.assertEqual(len(tool.region_set([merged],[a,same])),1)
        overlap=dict(a,address=0x10800,size=0x1000)
        union=dict(a,size=0x1800)
        self.assertEqual(len(tool.region_set([union],[a,overlap,a])),1)
        with self.assertRaisesRegex(ValueError,'overlapping VQ state/protection differs'):
            tool.region_set([union],[a,dict(overlap,protect=2)])
        with self.assertRaisesRegex(ValueError,'normalized VQ union'):
            tool.region_set([merged],[a,b])
        for bad in ([a,dict(b,address=0x10800)],[dict(a,protect=0x104)],[dict(a,state=True)]):
            with self.assertRaises(ValueError):tool.region_set(bad,bad)

    def test_paired_auxiliary_paths_exact_extents_and_live_regions(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);receipt=dict(reads={},regions=[dict(address=0x10000,size=8192,state=0x1000,protect=4)])
            for phase in ('before','after'):
                receipt['reads'][phase]={'state':file_receipt(root/f'cursor-{phase}-state.raw',b'abcd',0x10000)}
            r=tool.paired_reads(receipt,root,'cursor',capture.Artifacts(),{'state':4});self.assertEqual(r['state']['data'],b'abcd')
            for change in ({'bytes':3},{'address':0x12000},{'path':receipt['reads']['before']['state']['path']},{'bytes':True}):
                bad=copy.deepcopy(receipt);bad['reads']['after']['state'].update(change)
                with self.assertRaises(ValueError):tool.paired_reads(bad,root,'cursor',capture.Artifacts(),{'state':4})
            bad=copy.deepcopy(receipt);bad['reads']['after']['state']=file_receipt(root/'cursor-after-state.raw',b'abce',0x10000)
            with self.assertRaisesRegex(ValueError,'changed'):tool.paired_reads(bad,root,'cursor',capture.Artifacts(),{'state':4})

    def test_exact_boolean_and_retained_cleanup_identity_rules(self):
        plan=dict(candidate_sha256='a'*64,cdb='C:/fixture/cdb.exe',candidate_path='C:/fixture/game.exe')
        debugger=dict(process_id=40,creation_filetime=100,creation_utc='2026-09-13T00:00:00Z',handle_retained=True,path=plan['cdb'])
        owner=dict(process_id=41,parent_process_id=40,creation_filetime=101,creation_utc='2026-09-13T00:00:01Z',
                   handle_retained=True,path=plan['candidate_path'],candidate_sha256='a'*64)
        receipt=dict(cdb=debugger,candidates=[owner],cleanup=dict(desktop_closed=True,
            cdb=dict(absent=True,handle_closed=True,input_closed=True,identity=debugger),
            candidates=[dict(absent=True,handle_closed=True,identity=owner)]))
        self.assertEqual(tool.owned_cleanup(receipt,plan),owner)
        for key,value in (('process_id',True),('parent_process_id',40.0),('creation_filetime',99),('handle_retained',1)):
            bad=copy.deepcopy(receipt);bad['candidates'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):tool.owned_cleanup(bad,plan)
        bad=copy.deepcopy(receipt);bad['cleanup']['cdb']['input_closed']=1
        with self.assertRaises(ValueError):tool.owned_cleanup(bad,plan)
        with self.assertRaises(ValueError):tool.same_json({'parent_environment_modified':0},{'parent_environment_modified':False},'environment')

    def test_png_uses_exact_current_palette_and_rejects_raw_or_metadata_drift(self):
        width,height=640,480;raw=bytes(range(256))*1200
        palette=bytes(v for i in range(256) for v in (i,255-i,(i*7)%256,0))
        rgb=np.frombuffer(palette,dtype=np.uint8).reshape(256,4)[:,:3][np.frombuffer(raw,dtype=np.uint8).reshape(height,width)]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);png=root/'primary.png';Image.fromarray(rgb).save(png)
            meta=dict(raw_path=str(root/'primary.raw'),palette_path=str(root/'palette.bin'),png_path=str(png),log_path=str(root/'prefix.log'),
                width=width,height=height,pitch=width,raw_bytes=len(raw),used_bytes=len(raw),palette_mode='directdraw-palette',
                raw_sha256=tool.sha(raw),used_sha256=tool.sha(raw),png_sha256=tool.sha(png.read_bytes()))
            args=dict(reader=capture.Artifacts(),raw_path=root/'primary.raw',palette_path=root/'palette.bin',png_path=png,
                log_path=root/'prefix.log',width=width,height=height)
            self.assertEqual(tool.validate_png(meta,raw,palette,**args)['sha256'],meta['png_sha256'])
            for change in ({'width':True},{'raw_sha256':'0'*64},{'palette_mode':'diagnostic'},{'raw_path':str(root/'foreign.raw')}):
                with self.assertRaises(ValueError):tool.validate_png(dict(meta,**change),raw,palette,**args)
            altered=bytes([1])+palette[1:]
            with self.assertRaisesRegex(ValueError,'PNG pixels differ'):tool.validate_png(meta,raw,altered,**args)

    def test_empty_attached_palette_requires_explicit_exact_grayscale_preview(self):
        width,height=640,480;raw=bytes(range(256))*1200
        # Nonzero PALETTEENTRY flags do not supply colors.
        palette=bytes(v for i in range(256) for v in (0,0,0,i))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);png=root/'primary.png'
            indices=np.frombuffer(raw,dtype=np.uint8).reshape(height,width)
            Image.fromarray(np.repeat(indices[:,:,None],3,axis=2)).save(png)
            meta=dict(raw_path=str(root/'primary.raw'),palette_path=str(root/'palette.bin'),png_path=str(png),log_path=str(root/'prefix.log'),
                width=width,height=height,pitch=width,raw_bytes=len(raw),used_bytes=len(raw),palette_mode='grayscale-index-empty-palette',
                raw_sha256=tool.sha(raw),used_sha256=tool.sha(raw),png_sha256=tool.sha(png.read_bytes()))
            args=dict(reader=capture.Artifacts(),raw_path=root/'primary.raw',palette_path=root/'palette.bin',png_path=png,
                log_path=root/'prefix.log',width=width,height=height)
            result=tool.validate_png(meta,raw,palette,**args)
            self.assertEqual(result['palette_mode'],'grayscale-index-empty-palette')
            self.assertEqual(result['scope'],'grayscale_index_preview_empty_attached_palette')
            with self.assertRaisesRegex(ValueError,'palette mode'):
                tool.validate_png(dict(meta,palette_mode='directdraw-palette'),raw,palette,**args)
            colored=bytes([1])+palette[1:]
            with self.assertRaisesRegex(ValueError,'palette mode'):tool.validate_png(meta,raw,colored,**args)
            wrong=indices.copy();wrong[0,0]^=1;Image.fromarray(np.repeat(wrong[:,:,None],3,axis=2)).save(png)
            meta['png_sha256']=tool.sha(png.read_bytes());args['reader']=capture.Artifacts()
            with self.assertRaisesRegex(ValueError,'PNG pixels differ'):tool.validate_png(meta,raw,palette,**args)

    def test_missing_or_excessive_summary_fails_without_claims(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'summary.json'
            self.assertFalse(tool.evaluate(path)['passed'])
            summary=dict(schema='clash95_modal_primary_capture_v1',passed=True,executed=True,failures=[],
                plan={'out_dir':folder},manual_input_proof=True,visible_composition_proof=False,promotion_ready=False)
            path.write_text(json.dumps(summary));result=tool.evaluate(path)
            self.assertFalse(result['passed']);self.assertIn('excessive host claim',result['failures'][0])
            for key in ('source_authenticated','primary_composition_proven','owned_cleanup_verified','manual_input_proof','promotion_ready'):
                self.assertIs(result[key],False)


if __name__=='__main__':unittest.main()
