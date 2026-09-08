"""Pure synthetic snapshot fixtures; no process, debugger, DLL load or game run.

The synthetic PE's hash is substituted only inside this fixture's patch scope.
Production remains restricted to the reviewed proxy binary/private palette ABI.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import framed_primary_surface as primary


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(data, offset, value):
    struct.pack_into('<I', data, offset, value)


def synthetic_proxy():
    """Actual PE32 bytes with canonical read-only COM tables and HIGHLOWs."""
    data=bytearray(0xA00)
    data[:2]=b'MZ';put(data,0x3C,0x80);data[0x80:0x84]=b'PE\0\0'
    struct.pack_into('<HH',data,0x84,0x14C,3)
    struct.pack_into('<HH',data,0x94,224,0x2102)
    opt=0x98
    struct.pack_into('<H',data,opt,0x10B)
    put(data,opt+28,0x10000000);put(data,opt+32,0x1000);put(data,opt+36,0x200)
    put(data,opt+56,0x4000);put(data,opt+60,0x200);put(data,opt+92,16)
    sections=[(b'.text',0x200,0x1000,0x200,0x200,0x60000020),
              (b'.rdata',0x400,0x2000,0x400,0x400,0x40000040),
              (b'.reloc',0x200,0x3000,0x200,0x800,0x42000040)]
    for i,(name,vs,rva,rs,ro,flags) in enumerate(sections):
        p=opt+224+i*40;data[p:p+len(name)]=name
        struct.pack_into('<4I',data,p+8,vs,rva,rs,ro);put(data,p+36,flags)
    data[0x200]=0xC3  # Inert canonical executable address; never executed.
    offsets=list(range(0,36*4,4))+list(range(0x100,0x100+7*4,4))
    for offset in offsets:put(data,0x400+offset,0x10001000)
    entries=[0x3000+offset for offset in offsets]
    if len(entries)%2:entries.append(0)
    length=8+2*len(entries)
    struct.pack_into('<II',data,0x800,0x2000,length)
    struct.pack_into('<'+'H'*len(entries),data,0x808,*entries)
    put(data,opt+96+5*8,0x3000);put(data,opt+96+5*8+4,length)
    return bytes(data)


def write_word(read,offset,value):
    data=bytearray(read.data);put(data,offset,value)
    return replace(read,data=bytes(data))


def fixture(width=800,height=600,base=0x10000000):
    image=synthetic_proxy();digest=sha(image)
    backend=0x20000000;surface=0x20001000;palette=0x20002000;pointer=0x22000000
    p=bytearray(primary.PRIMARY_BYTES)
    struct.pack_into('<HH',p,0,width,height)
    put(p,0xB8,primary.PRIMARY_VTABLE);put(p,0xBC,backend);put(p,0xD4,8)
    b=bytearray(primary.BACKEND_BYTES)
    for offset,value in {0x38:108,0x3C:0x180F,0x40:height,0x44:width,0x48:width,
                         0x5C:pointer,0x80:32,0x84:0x60,0x8C:8,0xA0:0x200,0xA4:surface}.items():
        put(b,offset,value)
    table=struct.pack('<36I',*([base+0x1000]*36))
    pal_table=struct.pack('<7I',*([base+0x1000]*7))
    pal=struct.pack('<III',base+0x2100,1,0)+bytes(range(256))*4
    state=primary.Snapshot(primary.Read(primary.PRIMARY,bytes(p)),primary.Read(backend,bytes(b)),
        primary.Read(surface,struct.pack('<I',base+0x2000)),primary.Read(base+0x2000,table),
        primary.Read(palette,pal),primary.Read(base+0x2100,pal_table))
    identity=dict(run_id='synthetic-offline',process_id=101,process_start='2026-09-06T00:00:00Z',
        candidate_sha256='a'*64,proxy_sha256=digest,thread_id=102,trace_sha256='b'*64,
        capture_boundary='fixture-paused-only',ready_line=100,last_primary_lock_line=80,current_palette_line=50)
    fields={k:identity[k] for k in ('run_id','process_id','process_start','candidate_sha256',
                                   'proxy_sha256','thread_id','trace_sha256','capture_boundary')}
    lock=dict(fields,schema='clash95_full_primary_lock_v1',line=80,call_line=79,
        call_eip=0x47386F,return_eip=0x473872,call_esp=0x30000,return_esp=0x30014,
        hresult=0,rect_is_null=True,flags=1,event_handle=0,backend=backend,surface=surface,
        descriptor=backend+0x38,pixels=pointer,width=width,height=height,pitch=width,
        descriptor_sha256=sha(b[0x38:0xA4]))
    pal_obs=dict(fields,schema='clash95_current_primary_palette_v1',line=50,surface=surface,
        palette=palette,entries_address=palette+12,entries_sha256=sha(pal[12:]),entry_count=256)
    return dict(before=state,after=state,pixels=primary.Read(pointer,bytes(width*height)),width=width,height=height,
        proxy_image=image,expected_proxy_sha256=digest,proxy_base=base,
        regions=[primary.Region(0x51D000,0x1000,0x1000,4),primary.Region(backend,0x10000,0x1000,4),
                 primary.Region(pointer,width*height,0x1000,4),primary.Region(base,0x4000,0x1000,0x20)],
        identity=identity,lock_observation=lock,palette_observation=pal_obs)


def replace_read(packet,name,value):
    packet['before']=replace(packet['before'],**{name:value})
    packet['after']=packet['before']


class PrimarySurfaceTests(unittest.TestCase):
    def evaluate(self,packet):
        with patch.multiple(primary,SUPPORTED_PROXY_SHA256=sha(synthetic_proxy()),
                            SURFACE_VTABLE_RVA=0x2000,PALETTE_VTABLE_RVA=0x2100):
            return primary.validate_snapshot(**packet)

    def rejects(self,packet):
        with self.assertRaises(primary.PrimarySnapshotError):self.evaluate(packet)

    def test_all_resolutions_and_rebased_module_tables(self):
        for width,height in [(640,480),(800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602)]:
            for base in (0x10000000,0x30000000):
                with self.subTest(size=(width,height),base=base):
                    packet=fixture(width,height,base);report=self.evaluate(packet)
                    self.assertTrue(report['cached_primary_snapshot_valid'])
                    self.assertEqual(report['pixel_sha256'],sha(bytes(width*height)))
                    self.assertEqual(report['bytes'],width*height)
                    for key in ('source_authenticated','runtime_passed','visual_passed','manual_input_proof','promotion_ready'):
                        self.assertIs(report[key],False)

    def test_read_plan_has_no_process_operations_and_pins_private_abi(self):
        plan=primary.primary_read_plan(1024,768)
        self.assertFalse(plan['runtime_ready']);self.assertTrue(plan['read_only'])
        self.assertEqual(plan['supported_proxy_sha256'],primary.SUPPORTED_PROXY_SHA256)
        self.assertEqual(plan['reads'][0],dict(name='primary',address=0x51D4C0,bytes=220))
        self.assertEqual(plan['lock_abi']['stack_argument_bytes'],20)
        self.assertEqual(len(plan['repeat_after_pixels']),6)
        with self.assertRaises(primary.PrimarySnapshotError):primary.validate_snapshot(**fixture())

    def test_all_identity_reads_are_exact_and_stable(self):
        for name in primary.Snapshot.__dataclass_fields__:
            for mutation in ('short','missing','address','changed_after'):
                with self.subTest(name=name,mutation=mutation):
                    p=fixture();read=getattr(p['before'],name)
                    if mutation=='short':replace_read(p,name,replace(read,data=read.data[:-1]))
                    elif mutation=='missing':replace_read(p,name,None)
                    elif mutation=='address':replace_read(p,name,replace(read,address=0))
                    else:p['after']=replace(p['after'],**{name:replace(read,data=bytes([read.data[0]^1])+read.data[1:])})
                    self.rejects(p)

    def test_surface_primary_and_indexed_format_contract(self):
        changes=[('primary',0xB8,0x50EE24),('primary',0xD4,16),('primary',0xBC,0),
                 ('backend',0x38,0),('backend',0x3C,0x100F),('backend',0x40,480),
                 ('backend',0x44,640),('backend',0x48,801),('backend',0x48,0xFFFFFFFF),
                 ('backend',0x80,0),('backend',0x84,0x40),('backend',0x88,1),
                 ('backend',0x8C,32),('backend',0x90,0xFF),('backend',0xA0,0x204),
                 ('backend',0xA0,0),('backend',0xA4,0)]
        for name,offset,value in changes:
            with self.subTest(name=name,offset=offset,value=value):
                p=fixture();replace_read(p,name,write_word(getattr(p['before'],name),offset,value));self.rejects(p)

    def test_pixel_bounds_counts_and_aliases(self):
        for kind in ('short','zero','overflow','header','module','wrong_address'):
            with self.subTest(kind=kind):
                p=fixture();pointer=p['pixels'].address
                if kind=='short':p['pixels']=replace(p['pixels'],data=p['pixels'].data[:-1])
                else:
                    pointer={'zero':0,'overflow':0xFFFFF000,'header':primary.PRIMARY,
                             'module':p['proxy_base'],'wrong_address':pointer+4}[kind]
                    p['pixels']=replace(p['pixels'],address=pointer)
                    if kind!='wrong_address':replace_read(p,'backend',write_word(p['before'].backend,0x5C,pointer))
                self.rejects(p)

    def test_complete_readable_regions_required(self):
        for kind in ('guard','noaccess','reserve','gap','overlap','badtype','zero'):
            with self.subTest(kind=kind):
                p=fixture();r=p['regions'][2]
                if kind=='guard':p['regions'][2]=replace(r,protect=0x104)
                elif kind=='noaccess':p['regions'][2]=replace(r,protect=1)
                elif kind=='reserve':p['regions'][2]=replace(r,state=0x2000)
                elif kind=='gap':p['regions'][2]=replace(r,size=r.size-1)
                elif kind=='overlap':p['regions'].append(replace(r,address=r.address+10))
                elif kind=='badtype':p['regions'][2]=replace(r,address='wrong')
                else:p['regions'][2]=replace(r,size=0)
                self.rejects(p)
        p=fixture();r=p['regions'].pop(2);mid=r.size//2
        p['regions'] += [replace(r,size=mid),replace(r,address=r.address+mid,size=r.size-mid)]
        self.assertTrue(self.evaluate(p)['cached_primary_snapshot_valid'])

    def test_vtables_are_pinned_file_bytes_and_executable_targets(self):
        for name in ('surface_vtable','palette_vtable'):
            p=fixture();replace_read(p,name,write_word(getattr(p['before'],name),0,p['proxy_base']+0x2000));self.rejects(p)
        p=fixture();p['proxy_image']=p['proxy_image'][:-1]+b'X';self.rejects(p)
        p=fixture(base=0x30000000)
        replace_read(p,'surface_vtable',primary.Read(p['before'].surface_vtable.address,struct.pack('<36I',*([0x10001000]*36))))
        self.rejects(p)
        # Even a caller-authenticated synthetic DLL is rejected when its table points to data.
        p=fixture();image=bytearray(p['proxy_image']);put(image,0x400,0x10002000)
        digest=sha(image);p['proxy_image']=bytes(image);p['expected_proxy_sha256']=digest
        p['identity']['proxy_sha256']=digest;p['lock_observation']['proxy_sha256']=digest;p['palette_observation']['proxy_sha256']=digest
        replace_read(p,'surface_vtable',write_word(p['before'].surface_vtable,0,0x10002000))
        with patch.multiple(primary,SUPPORTED_PROXY_SHA256=digest,SURFACE_VTABLE_RVA=0x2000,PALETTE_VTABLE_RVA=0x2100):
            with self.assertRaisesRegex(primary.PrimarySnapshotError,'executable'):
                primary.validate_snapshot(**p)

    def test_missing_failed_partial_or_unpaired_lock(self):
        changes={'schema':'wrong','return_eip':0x473870,'call_eip':0x47386E,'hresult':1,
                 'rect_is_null':False,'line':79,'call_line':80,'call_esp':0,'return_esp':0x30010,
                 'flags':2,'event_handle':1,'backend':0,'surface':0,'descriptor':0,
                 'pixels':0,'width':640,'height':480,'pitch':640,'descriptor_sha256':'0'*64}
        for key,value in changes.items():
            with self.subTest(field=key):
                p=fixture();p['lock_observation'][key]=value;self.rejects(p)
        p=fixture();p['lock_observation']={};self.rejects(p)

    def test_observations_bind_same_capture_and_current_lines(self):
        for target in ('lock_observation','palette_observation'):
            for key in ('run_id','process_id','process_start','candidate_sha256','proxy_sha256','thread_id','trace_sha256','capture_boundary'):
                with self.subTest(target=target,key=key):
                    p=fixture();p[target][key]='different';self.rejects(p)
            p=fixture();p[target]['line']=101;self.rejects(p)
        for key in ('ready_line','last_primary_lock_line','current_palette_line'):
            p=fixture();p['identity'][key]=None;self.rejects(p)

    def test_palette_must_be_live_current_attached_and_exact(self):
        for key,value in {'schema':'wrong','surface':0,'line':49,'palette':0,'entries_address':0,
                          'entries_sha256':'0'*64,'entry_count':255}.items():
            with self.subTest(key=key):
                p=fixture();p['palette_observation'][key]=value;self.rejects(p)
        p=fixture();replace_read(p,'palette',write_word(p['before'].palette,4,0));self.rejects(p)
        p=fixture();pal=p['before'].palette
        replace_read(p,'palette',replace(pal,data=pal.data[:-1]+bytes([pal.data[-1]^1])));self.rejects(p)

    def test_dimension_rejections(self):
        for width,height in ((639,480),(640,479),(801,600),(800,601),(8194,600),(800,8194),(True,600)):
            with self.subTest(size=(width,height)):
                p=fixture();p['width']=width;p['height']=height;self.rejects(p)

    def test_native_lock_bytes_when_original_available(self):
        path=Path('C:/Clash/clash95.exe')
        if not path.is_file():self.skipTest('user-owned original unavailable')
        data=path.read_bytes()
        self.assertEqual(sha(data),'500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae')
        # Native code VA -> file offset differs by C00 in this authenticated section.
        start=0x47385D-0x400000-0xC00
        self.assertEqual(data[start:start+21],bytes.fromhex('8b86a4000000c746386c0000006a008b1850ff5364'))
        post=bytes.fromhex('89c33dc2017688740889d85f5e5a595bc3')
        self.assertEqual(data[start+21:start+21+len(post)],post)

    def test_reviewed_proxy_tables_and_rtti_when_dll_available(self):
        path=Path('C:/ClashTests/hd-completion/framed-minimap-v1-1024x768-20260906-031649/candidate/ddraw.dll')
        if not path.is_file():self.skipTest('reviewed local proxy build unavailable')
        image=path.read_bytes()
        self.assertEqual(sha(image),primary.SUPPORTED_PROXY_SHA256)
        source=Path(__file__).resolve().parents[1]/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp'
        self.assertEqual(sha(source.read_bytes()),primary.SUPPORTED_PROXY_SOURCE_SHA256)
        for base in (0x10000000,0x30000000):
            proxy=primary._Proxy(image,primary.SUPPORTED_PROXY_SHA256,base)
            for rva,size,name in ((primary.SURFACE_VTABLE_RVA,144,b'.?AVFakeSurface@'),
                                  (primary.PALETTE_VTABLE_RVA,28,b'.?AVFakePalette@')):
                with self.subTest(base=base,name=name):
                    raw=bytearray(proxy.raw(rva,size))
                    for site in proxy.fixups:
                        if rva<=site<rva+size:
                            pos=site-rva;put(raw,pos,(primary._u32(raw,pos)+base-proxy.preferred)&0xFFFFFFFF)
                    proxy.vtable(primary.Read(base+rva,bytes(raw)))
                    locator=primary._u32(proxy.raw(rva-4,4),0)-proxy.preferred
                    descriptor=primary._u32(proxy.raw(locator,20),12)-proxy.preferred
                    self.assertTrue(proxy.raw(descriptor+8,len(name)).startswith(name))


if __name__=='__main__':
    unittest.main(verbosity=2)
