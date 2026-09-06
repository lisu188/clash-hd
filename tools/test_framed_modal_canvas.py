#!/usr/bin/env python3
"""Execute only emitted canvas x86 in synthetic memory; no game or debugger.

Allocator, primary-blit and game-body calls are ABI recorders. The actual
authenticated base constructor/member constructor and scalar destructor/member
destructor execute from cloned original instructions with explicit fixups.
All synthetic compiler outputs remain in a temporary directory.
"""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.patcher import framed_modal_canvas as modal
from src.patcher import partial_tile_clip as clip
import build_framed_candidate as builder

BASE=0x20000000
STATE=BASE+0x20000
GLOBAL=BASE+0x10000
NATIVE=BASE+0x30000
PIXELS=BASE+0x40000
PHYSICAL=BASE+0xD0000
PRIMARY=BASE+0xD0200
BACKEND=BASE+0xD0400
MEMVT=BASE+0xD0600
PRIMVT=BASE+0xD0800
PHYSPIX=BASE+0x100000
RECORD=BASE+0xF0000
GLOBALS={modal.MAP:GLOBAL,modal.RENDER:GLOBAL+4,modal.HOOK_OWNER:GLOBAL+8,
         clip.LOWER_ROW_OWNER_GLOBAL:GLOBAL+12,clip.POST_TILE_CALLBACK_GLOBAL:GLOBAL+16,
         modal.THREAD_IAT:GLOBAL+20}
STUBS={va:BASE+0x8000+index*0x100 for index,va in enumerate((
    modal.ALLOC,modal.FREE,modal.BASE_CTOR,0x473250,modal.DTOR,0x4732E0,
    0x461C70,0x47312B,0x47314C,0x40AD40,0x4E9920,0x422185,0x422025,
    0x51B6D6,0x51BC26,0x435B90))}
THREAD=BASE+0x9800
CSC=Path(r'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe')
FLAGS=0xED7
MASK=0xCD5


CSHARP=r'''
using System; using System.Collections; using System.Collections.Generic;
using System.Runtime.InteropServices; using System.Web.Script.Serialization;
class Fixture {
 [DllImport("kernel32")] static extern IntPtr VirtualAlloc(IntPtr p,UIntPtr n,uint t,uint f);
 [DllImport("kernel32")] static extern bool VirtualFree(IntPtr p,UIntPtr n,uint t);
 [DllImport("kernel32")] static extern uint SetErrorMode(uint mode);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Entry();
 const int B=0x20000000,G=B+0x10000,S=B+0x20000,N=B+0x30000,P=B+0x40000;
 const int H=B+0xD0000,D=B+0xD0200,K=B+0xD0400,V=B+0xD0600,Q=B+0xD0800;
 const int R=B+0xF0000,F=B+0x100000;
 static int I(object x){return unchecked((int)Convert.ToInt64(x));}
 static int Get(Dictionary<string,object>d,string k,int v){return d.ContainsKey(k)?I(d[k]):v;}
 static int Read(int a){return Marshal.ReadInt32((IntPtr)a);}
 static void W(int a,int v){Marshal.WriteInt32((IntPtr)a,v);}
 static void Bytes(int a,byte[]b){Marshal.Copy(b,0,(IntPtr)a,b.Length);}
 static byte[] Hex(string x){byte[] b=new byte[x.Length/2];for(int i=0;i<b.Length;i++)b[i]=Convert.ToByte(x.Substring(2*i,2),16);return b;}
 static void Imm(List<byte>b,int v){b.AddRange(BitConverter.GetBytes(v));}
 static void Abs(List<byte>b,byte op,int p){b.Add(op);Imm(b,p);}
 static void Fill(int a,int n,byte v){byte[] b=new byte[n];for(int i=0;i<n;i++)b[i]=v;Bytes(a,b);}
 static bool IsFill(int a,int n,byte v){for(int i=0;i<n;i++)if(Marshal.ReadByte((IntPtr)a,i)!=v)return false;return true;}
 static Dictionary<string,object> Invoke(int entry,int arg){
  var b=new List<byte>();b.Add(0x9c);b.Add(0x60);
  b.Add(0x89);b.Add(0x25);Imm(b,R+0x90);
  int[] seed={arg,0x11223344,0x22334455,0x33445566,0,0x44556677,0x55667788,0x66778899};
  for(int i=0;i<8;i++)if(i!=4){b.Add((byte)(0xb8+i));Imm(b,seed[i]);}
  b.Add(0x68);Imm(b,0xED7);b.Add(0x9d);b.Add(0xe8);Imm(b,entry-(B+0xA000+b.Count+4));
  for(int i=0;i<8;i++){b.Add(0x89);b.Add((byte)(5+(i<<3)));Imm(b,R+0xA0+i*4);}
  b.Add(0x9c);b.Add(0x58);Abs(b,0xa3,R+0xC0);b.Add(0x61);b.Add(0x9d);b.Add(0x31);b.Add(0xc0);b.Add(0xc3);
  Bytes(B+0xA000,b.ToArray());((Entry)Marshal.GetDelegateForFunctionPointer((IntPtr)(B+0xA000),typeof(Entry)))();
  bool regs=true;for(int i=1;i<8;i++)if(i!=4 && Read(R+0xA0+i*4)!=seed[i])regs=false;
  return new Dictionary<string,object>{{"eax",Read(R+0xA0)},{"gprs",regs},{"esp",Read(R+0xB0)==Read(R+0x90)},
   {"flags",Read(R+0xC0)&0xCD5},{"phase",Read(S)},{"native",Read(S+8)},{"physical",Read(S+4)},
   {"enter",Read(S+24)},{"mirror",Read(S+28)},{"leave",Read(S+32)},{"fault",Read(S+36)},
   {"allocations",Read(S+40)},{"frees",Read(S+44)},{"mirrors",Read(S+48)},
   {"alloc_calls",Read(R)},{"free_calls",Read(R+4)},{"draw_calls",Read(R+16)},
   {"map_calls",Read(R+20)},{"old_blits",Read(R+24)},{"old_center",Read(R+28)},
   {"poll_calls",Read(R+32)},{"map_restored",Read(R+36)},{"global_map",Read(G)},{"global_render",Read(G+4)},
   {"pending_header",Read(S+52)},{"pending_pixels",Read(S+56)},
   {"header_zero_com",Read(N+0xAC)==0},{"header_vtable",Read(N+0xB8)}};
 }
 static int Main(){IntPtr mem=IntPtr.Zero;try {
  SetErrorMode(0x8007);
  if(IntPtr.Size!=4)throw new Exception("x86 required");
  var js=new JavaScriptSerializer();js.MaxJsonLength=16000000;
  var input=js.Deserialize<Dictionary<string,object>>(Console.In.ReadToEnd());
  mem=VirtualAlloc((IntPtr)B,(UIntPtr)0x500000,0x3000,0x40);if(mem!=(IntPtr)B)throw new Exception("reservation");
  Bytes(B,Hex((string)input["code"]));var stubs=(Dictionary<string,object>)input["stubs"];
  foreach(var kv in stubs)Bytes(int.Parse(kv.Key),Hex((string)kv.Value));
  var entries=(Dictionary<string,object>)input["entries"];var all=new List<object>();int width=I(input["width"]),height=I(input["height"]);
  foreach(Dictionary<string,object> c in (IEnumerable)input["cases"]){
   Fill(S,128,0);Fill(S+128,16,0xD7);Fill(R,256,0);Fill(N,188,0xB9);Fill(P-16,307232,0xD7);Fill(F-16,width*height+32,0xD7);Fill(F,width*height,0xB9);
   W(G,H);W(G+4,Get(c,"render_primary",0)!=0?D:H);W(G+8,Get(c,"owner",I(input["map_stub"])));W(G+12,Get(c,"lower",0));W(G+16,Get(c,"post",0));W(G+20,I(input["thread_stub"]));
   W(G+24,Get(c,"tid",123));W(R+8,Get(c,"allocation_failure",0));
   W(H,Get(c,"surface_width",width)|(Get(c,"surface_height",height)<<16));W(H+4,F);W(H+0xB8,V);
   W(D,width|(height<<16));W(D+0xB8,Get(c,"primary_vtable",Q));W(D+0xD4,Get(c,"depth",8));W(D+0xBC,K);W(K+0xA4,Get(c,"backend",K+0x100));
   var steps=new List<object>();bool painted=false;
   foreach(object item in (IEnumerable)c["steps"]){
    string name=item as string;
    if(name==null){var m=(Dictionary<string,object>)item;foreach(var kv in m){
     if(kv.Key=="tid")W(G+24,I(kv.Value));else if(kv.Key=="native_width")W(N,I(kv.Value)|(480<<16));
     else if(kv.Key=="map_pointer")W(G,I(kv.Value));else if(kv.Key=="phase")W(S,I(kv.Value));
     else if(kv.Key=="root_esp")W(S+16,I(kv.Value));
     else if(kv.Key=="native_pixels")W(N+4,I(kv.Value));else if(kv.Key=="physical_pixels")W(H+4,I(kv.Value));
     else if(kv.Key=="owned_native_pixels")W(S+60,I(kv.Value));else if(kv.Key=="entered_physical_pixels")W(S+64,I(kv.Value));
     else if(kv.Key=="native_com")W(N+0xAC,I(kv.Value));
     else throw new Exception("unknown mutation");}continue;}
    if(name=="paint"){byte[] p=new byte[307200];for(int y=0;y<480;y++)for(int x=0;x<640;x++)p[y*640+x]=(byte)((x*13+y*7)%251);Bytes(P,p);painted=true;continue;}
    int arg=name=="try_enter"?0x30001000:name=="try_leave"?Get(c,"leave_esp",0x30000FC4):name=="full_blit"?Read(S+8):0x12345678;
    var result=Invoke(I(entries[name]),arg);
    bool canaries=IsFill(P-16,16,0xD7)&&IsFill(P+307200,16,0xD7)&&IsFill(F-16,16,0xD7)&&IsFill(F+width*height,16,0xD7)&&IsFill(S+128,16,0xD7);
    result["canaries"]=canaries;
    if((name=="mirror"||name=="full_blit"||name=="overview_draw")&&Read(S+28)==1){
     bool ok=true;int ox=(width-640)/2,oy=(height-480)/2;
     for(int y=0;y<height;y++)for(int x=0;x<width;x++){
      byte expected=0;if(x>=ox&&x<ox+640&&y>=oy&&y<oy+480&&painted)expected=(byte)(((x-ox)*13+(y-oy)*7)%251);
      if(Marshal.ReadByte((IntPtr)F,y*width+x)!=expected)ok=false;
     }result["pixel_oracle"]=ok;
    }
    if(painted){bool intact=true;for(int y=0;y<480;y++)for(int x=0;x<640;x++)if(Marshal.ReadByte((IntPtr)P,y*640+x)!=(byte)((x*13+y*7)%251))intact=false;result["source_intact"]=intact;}
    steps.Add(result);
   }all.Add(steps);
  }Console.WriteLine(js.Serialize(all));return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}finally{if(mem!=IntPtr.Zero)VirtualFree(mem,UIntPtr.Zero,0x8000);}}
}
'''


def u32(x):return struct.pack('<I',x&0xffffffff)


def payload(original,bundle,cases):
    def mapped(value):
        if bundle.base_va<=value<bundle.base_va+len(bundle.code):return BASE+value-bundle.base_va
        if bundle.state_va<=value<bundle.state_va+4096:return STATE+value-bundle.state_va
        if modal.PRIMARY<=value<modal.PRIMARY+0x200:return PRIMARY+value-modal.PRIMARY
        if value==modal.MEMORY_VTABLE:return MEMVT
        if value==modal.PRIMARY_VTABLE:return PRIMVT
        if value in GLOBALS:return GLOBALS[value]
        if value==0x422020:return BASE+bundle.entries['overview_draw']-bundle.base_va
        if value==bundle.source_contract['old_action_wrapper_va']+6:return STUBS[0x51BC26]
        if value in STUBS:return STUBS[value]
        # Other base/member vtable constants are never dereferenced; preserve
        # their image-relative identity under a synthetic image rebase.
        if 0x400000<=value<0x600000:return BASE+0xE0000+(value&0xffff)
        raise AssertionError(hex(value))
    code=bytearray(bundle.code)
    for r in bundle.relocations:
        value=mapped(r.target)
        if r.kind=='rel32':value-=BASE+r.offset+4
        struct.pack_into('<I',code,r.offset,value&0xffffffff)
    stubs={}
    def recorder(field,body=b''):
        return b'\x9c\x60\xff\x05'+u32(RECORD+field)+body+b'\x61\x9d\xc3'
    # Handwritten independent allocation recorder, including exact sizes and
    # each failure. It preserves all non-EAX registers and flags like473FF0.
    a=clip._Assembler(STUBS[modal.ALLOC]);a.emit('9c60ff05');a.u32(RECORD)
    a.emit('8b0d');a.u32(RECORD);a.emit('3b0d');a.u32(RECORD+8);a.branch('0f84','zero')
    a.emit('3dbc000000');a.branch('0f84','header');a.emit('3d00b00400');a.branch('0f85','zero')
    a.emit('b8');a.u32(PIXELS);a.branch('e9','return');a.label('header');a.emit('b8');a.u32(NATIVE)
    a.branch('e9','return');a.label('zero');a.emit('31c0');a.label('return');a.emit('8944241c619dc3');stubs[STUBS[modal.ALLOC]]=a.finish()
    stubs[STUBS[modal.FREE]]=recorder(4)
    stubs[STUBS[0x461C70]]=b'\xe9'+u32(STUBS[modal.FREE]-STUBS[0x461C70]-5)
    def clone(va,size,calls):
        data=bytearray(modal._read(original,va,size))
        for field in clip._original_highlow_fields(original,va,size):
            offset=field;old=struct.unpack_from('<I',data,offset)[0];struct.pack_into('<I',data,offset,mapped(old))
        for off in calls:
            assert data[off]==0xe8
            target=va+off+5+struct.unpack_from('<i',data,off+1)[0]
            struct.pack_into('<I',data,off+1,(mapped(target)-STUBS[va]-off-5)&0xffffffff)
        stubs[STUBS[va]]=data
    clone(modal.BASE_CTOR,0x25,[0x12]);clone(0x473250,0x50,[])
    clone(modal.DTOR,0x5E,[0x1D,0x2C,0x43,0x48,0x54]);clone(0x4732E0,0x33,[])
    stubs[STUBS[0x47312B]]=b'\xcc';stubs[STUBS[0x47314C]]=b'\xcc'
    stubs[THREAD]=b'\xa1'+u32(GLOBAL+24)+b'\xc3'
    # Native overview body recorder receives the five actual replayed PUSHes.
    stubs[STUBS[0x422025]]=recorder(16)[:-1]+bytes.fromhex('5f5e5a595bc3')
    stubs[STUBS[0x435B90]]=recorder(32)
    stubs[STUBS[0x4E9920]]=recorder(24)
    for va in (0x51B6D6,0x51BC26):stubs[STUBS[va]]=b'\x61'+recorder(28)
    # Simulate only the original remaining root prologue and common exit call,
    # not the game: exact root S-60 reaches the emitted leave CALL adapter.
    target=BASE+bundle.entries['leave_before_map']-bundle.base_va
    body=bytes.fromhex('5583ec20e8')+u32(target-STUBS[0x422185]-9)+bytes.fromhex('83c4205d5f5e5a595bc3')
    stubs[STUBS[0x422185]]=body
    body=b'\xa1'+u32(GLOBAL)+b'\x3d'+u32(PHYSICAL)+b'\x0f\x94\xc0\x0f\xb6\xc0\xa3'+u32(RECORD+36)
    stubs[STUBS[0x40AD40]]=recorder(20,body)
    return dict(code=bytes(code).hex(),stubs={str(k):bytes(v).hex() for k,v in stubs.items()},
        entries={k:BASE+v-bundle.base_va for k,v in bundle.entries.items()},width=bundle.width,height=bundle.height,
        map_stub=STUBS[0x40AD40],thread_stub=THREAD,cases=cases)


class CanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=Path('C:/Clash/clash95.exe').read_bytes();cls.cache={}
        cls.temp=tempfile.TemporaryDirectory(prefix='clash-modal-canvas-fixture-')
        cls.source=Path(cls.temp.name)/'Fixture.cs';cls.source.write_text(CSHARP)
        cls.exe=Path(cls.temp.name)/'Fixture.exe'
        r=subprocess.run([str(CSC),'/nologo','/platform:x86','/r:System.Web.Extensions.dll','/out:'+str(cls.exe),str(cls.source)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode:raise AssertionError(r.stdout+r.stderr)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    @classmethod
    def bundle(cls,w=1024,h=768):
        if (w,h) not in cls.cache:
            c=builder.build_candidate(cls.original,f'{w}x{h}',minimap_viewport=True)[0]
            cls.cache[w,h]=(c,modal.emit_modal_canvas(cls.original,c,base_va=0x580000,state_va=0x5A0000,width=w,height=h))
        return cls.cache[w,h][1]
    def run_cases(self,cases,w=1024,h=768):
        data=payload(self.original,self.bundle(w,h),cases)
        r=subprocess.run([str(self.exe)],input=json.dumps(data),capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        rows=json.loads(r.stdout)
        for case in rows:
            for step in case:
                self.assertTrue(step['gprs'],step);self.assertTrue(step['esp'],step)
                self.assertTrue(step['canaries'],step)
                self.assertTrue(step.get('source_intact',True),step)
        return rows
    def test_allocation_constructor_destruction_and_exact_gpr_flags(self):
        for primary in (0,1):
            row=self.run_cases([dict(render_primary=primary,steps=['try_enter','paint','mirror','try_leave'])])[0]
            for step in row:self.assertEqual(step['flags'],FLAGS&MASK)
            self.assertEqual([s['eax'] for s in row],[1,1,1])
            self.assertEqual(row[0]['global_map'],NATIVE);self.assertEqual(row[0]['header_vtable'],MEMVT)
            self.assertTrue(row[0]['header_zero_com']);self.assertTrue(row[1]['pixel_oracle'])
            self.assertEqual((row[-1]['phase'],row[-1]['global_map'],row[-1]['free_calls']),(0,PHYSICAL,2))
            self.assertEqual(row[-1]['global_render'],PRIMARY if primary else PHYSICAL)
    def test_both_allocation_failures_leave_no_partial_install(self):
        rows=self.run_cases([dict(allocation_failure=n,steps=['try_enter']) for n in (1,2)])
        for n,row in enumerate(rows,1):
            s=row[0];self.assertEqual((s['eax'],s['phase'],s['global_map'],s['global_render']),(0,0,PHYSICAL,PHYSICAL))
            self.assertEqual((s['alloc_calls'],s['free_calls']),(n,n-1));self.assertEqual(s['pending_header'],0);self.assertEqual(s['pending_pixels'],0)
    def test_wrong_context_primary_and_native640_fallback(self):
        bad=[dict(surface_width=640,surface_height=480),dict(owner=1),dict(lower=1),dict(post=1),dict(primary_vtable=1),dict(depth=16),dict(backend=0),dict(tid=0)]
        rows=self.run_cases([dict(c,steps=['try_enter']) for c in bad])
        for row in rows:self.assertEqual((row[0]['eax'],row[0]['alloc_calls'],row[0]['global_map']),(0,0,PHYSICAL))
    def test_bad_owner_thread_stack_or_header_does_not_free(self):
        cases=[dict(steps=['try_enter',{'tid':124},'try_leave']),dict(leave_esp=0x30000FC0,steps=['try_enter','try_leave']),dict(steps=['try_enter',{'native_width':800},'try_leave'])]
        for row in self.run_cases(cases):
            self.assertEqual((row[-1]['eax'],row[-1]['free_calls'],row[-1]['phase'],row[-1]['fault']),(0,0,1,3))
    def test_source_stride_physical_clear_and_clipped_fractional_sizes(self):
        for w,h in ((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602)):
            row=self.run_cases([dict(steps=['try_enter','paint','mirror','full_blit','try_leave'])],w,h)[0]
            self.assertTrue(row[1]['pixel_oracle']);self.assertTrue(row[2]['pixel_oracle'])
            self.assertEqual(row[2]['old_blits'],1)
    def test_pixel_pointer_changes_aliases_and_offsets_never_copy_or_free(self):
        changes=[dict(native_pixels=PIXELS+4),dict(physical_pixels=PHYSPIX+4),
                 dict(native_pixels=PHYSPIX),dict(physical_pixels=PIXELS),
                 dict(native_pixels=PHYSPIX,owned_native_pixels=PHYSPIX),
                 dict(physical_pixels=PIXELS,entered_physical_pixels=PIXELS),
                 dict(native_pixels=0xFFFF0000,owned_native_pixels=0xFFFF0000),
                 dict(native_com=1)]
        rows=self.run_cases([dict(steps=['try_enter',c,'mirror','try_leave']) for c in changes])
        for row in rows:
            self.assertEqual((row[1]['eax'],row[1]['mirrors'],row[1]['fault']),(0,0,2))
            self.assertEqual((row[2]['eax'],row[2]['free_calls'],row[2]['phase'],row[2]['fault']),(0,0,1,3))
    def test_unknown_reentry_is_latched_without_a_second_allocation(self):
        row=self.run_cases([dict(steps=['try_enter','try_enter','try_leave'])])[0]
        self.assertEqual((row[1]['eax'],row[1]['alloc_calls'],row[1]['phase'],row[1]['fault']),(0,2,1,5))
        self.assertEqual(row[-1]['fault'],5)
    def test_nested_work_reuses_canvas_and_old_wrappers_do_not_center(self):
        row=self.run_cases([dict(steps=['try_enter','paint','overview_wrapper','action_wrapper','overview_draw','mirror','try_leave'])])[0]
        self.assertEqual(row[-1]['alloc_calls'],2);self.assertEqual(row[-1]['free_calls'],2)
        self.assertEqual(row[-1]['old_center'],0);self.assertEqual(row[-1]['poll_calls'],1)
        self.assertEqual(row[-1]['draw_calls'],2);self.assertTrue(row[-2]['pixel_oracle'])
    def test_inactive_paths_keep_original_work_and_center_continuations(self):
        row=self.run_cases([dict(steps=['overview_wrapper','action_wrapper','overview_draw','full_blit'])])[0]
        self.assertEqual(row[-1]['old_center'],2);self.assertEqual(row[-1]['draw_calls'],2)
        self.assertEqual(row[-1]['poll_calls'],1);self.assertEqual(row[-1]['alloc_calls'],0)
    def test_replayed_root_and_cleanup_precede_actual_map_call(self):
        row=self.run_cases([dict(steps=['root_entry'])])[0][0]
        self.assertEqual((row['alloc_calls'],row['free_calls'],row['map_calls'],row['map_restored']),(2,2,1,1))
        self.assertEqual((row['phase'],row['enter'],row['leave'],row['fault']),(0,1,1,0))
    def test_candidate_state_and_hook_relocation_contract(self):
        b=self.bundle();c=self.cache[1024,768][0]
        self.assertFalse(b.installation_ready);self.assertEqual(b.state_size,128);self.assertEqual(len(b.hook_sites),6)
        self.assertEqual(b.candidate_sha256,hashlib.sha256(c).hexdigest())
        for h in b.hook_sites:
            self.assertEqual(c[h.offset:h.offset+len(h.old)],h.old)
            self.assertEqual(len(h.new),len(h.old));self.assertEqual(len(h.relocations),1)
            self.assertEqual(h.va+5+struct.unpack_from('<i',h.new,1)[0],h.relocations[0].target)
            self.assertFalse(clip._original_highlow_fields(self.original,h.va,len(h.old)))
        clip.absolute_relocation_offsets(b)
        for bad in (c[:-1]+bytes([c[-1]^1]),self.original):
            with self.assertRaises(ValueError):modal.emit_modal_canvas(self.original,bad,base_va=0x580000,state_va=0x5A0000,width=1024,height=768)
        with self.assertRaises(ValueError):modal.emit_modal_canvas(self.original,c,base_va=0x580000,state_va=0x580004,width=1024,height=768)


if __name__=='__main__':unittest.main()
