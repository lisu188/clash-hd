#!/usr/bin/env python3
"""Execute emitted primary adapters with the real inherited ownership x86.

Only synthetic memory is executed. Native callees are independent ABI and
pixel-copy recorders; no game, debugger, wrapper, or runtime capture is started.
The full-publication integration cases additionally execute the exact inherited
4E9920 instructions; only their final native partial-copy leaf is modeled.
The full-blit fallback retains the inherited mirror behavior, including on a
sticky fault; rejection forbids the added physical-source primary publication.
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
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import framed_modal_canvas as modal
from src.patcher import framed_modal_primary as primary
from src.patcher import pe_extension as pe
from src.patcher import partial_tile_clip as clip
import build_framed_modal_slots_candidate as builder
import test_framed_modal_canvas as canvas

CODE = canvas.BASE + 0xB000
HD = canvas.BASE + 0xC000
REMOVE = canvas.BASE + 0xC400
DRAW = canvas.BASE + 0xC800
RECT = canvas.BASE + 0xCC00
PARTIAL = canvas.BASE + 0xD000
CONTINUATION = canvas.BASE + 0xD400
SPRITE = canvas.BASE + 0xD600
CURSOR = canvas.BASE + 0xD1000
PRIMARY_PIXELS = canvas.BASE + 0x300000
OBS = canvas.RECORD + 0x200
EVENTS = canvas.RECORD + 0x600
DESCRIPTORS = canvas.BASE + 0xD2000
BACKING = canvas.BASE + 0xD6000

INVOKE = r'''
 const int U=B+0x300000,C=B+0xD1000,O=R+0x200,E=R+0x600;
 const int L=B+0xD2028,J=B+0xD3000,Z=B+0xD5000,A=B+0xD5100,T=B+0xD6000;
 static byte[] ReadBytes(int p,int n){byte[] v=new byte[n];Marshal.Copy((IntPtr)p,v,0,n);return v;}
 static bool SameBytes(int p,byte[] b){for(int i=0;i<b.Length;i++)if(Marshal.ReadByte((IntPtr)p,i)!=b[i])return false;return true;}
 static Dictionary<string,object> PrimaryCall(string name,int entry,Dictionary<string,object> c,int width,int height){
  Fill(O,0x600,0);Fill(U-16,width*height+32,0xD7);Fill(U,width*height,0x5D);
  int visible=Get(c,"cursor",0);W(C+0x38,visible);
  int descriptor=Get(c,"cursor_descriptor",L),first=Get(c,"cursor_first",2),last=Get(c,"cursor_last",2),frame=Get(c,"cursor_frame",0);
  Fill(descriptor,40,0);W(descriptor,first);W(descriptor+4,last);W(descriptor+8,Get(c,"cursor_mode",0));
  W(descriptor+12,4);W(descriptor+16,4);W(descriptor+32,frame);W(C+0x3C,descriptor);
  Fill(J,0x1020,0);W(J+(first+frame)*4,Z);W(J+0x1004,Get(c,"cursor_count",3));W(C+0x40,J);W(Z,4|(4<<16));
  Fill(A,188+16,0xD7);W(A,64|(64<<16));W(A+4,T);W(A+0xB8,V);W(C+8,A);
  Fill(T-16,4096+32,0xD7);Fill(T,4096,0x5D);
  string bad=c.ContainsKey("cursor_bad")?(string)c["cursor_bad"]:"";
  if(bad=="descriptor")W(C+0x3C,descriptor+1);
  else if(bad=="prefix")W(descriptor,3);
  else if(bad=="zero_width")W(descriptor+12,0);
  else if(bad=="large_height")W(descriptor+16,65);
  else if(bad=="frame")W(descriptor+32,last-first+1);
  else if(bad=="negative_frame")W(descriptor+32,-1);
  else if(bad=="resource_null")W(C+0x40,0);
  else if(bad=="resource_wrap")W(C+0x40,unchecked((int)0xFFFFF800));
  else if(bad=="resource_high")W(C+0x40,unchecked((int)0x80010000));
  else if(bad=="count_zero")W(J+0x1004,0);
  else if(bad=="count_short")W(J+0x1004,2);
  else if(bad=="count_large")W(J+0x1004,1025);
  else if(bad=="sprite_null")W(J+8,0);
  else if(bad=="sprite_wrap")W(J+8,unchecked((int)0xFFFFFFFE));
  else if(bad=="sprite_high")W(J+8,unchecked((int)0x80010000));
  else if(bad=="sprite_zero")W(Z,4<<16);
  else if(bad=="sprite_large")W(Z,5|(4<<16));
  else if(bad=="backing_null")W(C+8,0);
  else if(bad=="backing_high")W(C+8,unchecked((int)0x80010000));
  else if(bad=="backing_size")W(A,63|(64<<16));
  else if(bad=="backing_vtable")W(A+0xB8,V+4);
  else if(bad=="pixels_null")W(A+4,0);
  else if(bad=="pixels_wrap")W(A+4,unchecked((int)0xFFFFF800));
  else if(bad=="pixels_high")W(A+4,unchecked((int)0x80010000));
  else if(bad=="pixels_native")W(A+4,P);
  else if(bad=="pixels_physical")W(A+4,F);
  else if(bad=="pixels_resource")W(A+4,J);
  else if(bad=="pixels_header")W(A+4,A);
  else if(bad=="pixels_sprite")W(A+4,Z);
  else if(bad!="")throw new Exception("unknown cursor mutation");
  for(int y=0;y<4;y++)for(int x=0;x<4;x++){
   if(visible==1)Marshal.WriteByte((IntPtr)U,(19+y)*width+17+x,0xE9);
  }
  int[] args;int[] regs={Get(c,"source",Read(S+8)),0x11223344,0x22334455,0x33445566,0,0x44556677,0x55667788,0x66778899};
  if(name=="primary_full")args=new int[0];
  else if(name=="primary_placeholder"){
   args=new int[]{-1,-2,-3,-4,0x11112222,0x22223333,0x33334444};
   regs[0]=Get(c,"source",D);regs[2]=0x12345678;regs[6]=Get(c,"vtable",Q);
  }else if(name.StartsWith("primary_rect")){
   args=new int[]{Get(c,"bottom",408)};regs[0]=Get(c,"source",C);
   regs[1]=Get(c,"right",422);regs[2]=Get(c,"left",220);regs[3]=Get(c,"top",289);
  }else{
   args=new int[]{Get(c,"right",422),Get(c,"bottom",408),Get(c,"dest_x",220),Get(c,"dest_y",289)};
   regs[1]=Get(c,"top",289);regs[2]=Get(c,"destination",D);regs[3]=Get(c,"left",220);
  }
  byte[] oldPhysical=ReadBytes(F,width*height),oldPrimary=ReadBytes(U,width*height),native=ReadBytes(P,307200);
  byte[] cursorState=ReadBytes(C,0x80),descriptorBytes=ReadBytes(descriptor,40),resourceBytes=ReadBytes(J,0x1010),spriteBytes=ReadBytes(Z,4),backingHeader=ReadBytes(A,188);
  int[] state=new int[32];for(int i=0;i<32;i++)state[i]=Read(S+i*4);
  var b=new List<byte>();b.Add(0x9c);b.Add(0x60);b.Add(0x89);b.Add(0x25);Imm(b,R+0x90);
  b.Add(0x68);Imm(b,0x24681357);b.Add(0x68);Imm(b,0x13572468);
  for(int i=args.Length-1;i>=0;i--){b.Add(0x68);Imm(b,args[i]);}
  for(int i=0;i<8;i++)if(i!=4){b.Add((byte)(0xb8+i));Imm(b,regs[i]);}
  b.Add(0x68);Imm(b,0xED7);b.Add(0x9d);b.Add(0xe8);Imm(b,entry-(B+0xA000+b.Count+4));
  for(int i=0;i<8;i++){b.Add(0x89);b.Add((byte)(5+(i<<3)));Imm(b,R+0xA0+i*4);}
  b.Add(0x9c);b.Add(0x58);Abs(b,0xa3,R+0xC0);
  b.Add(0x58);Abs(b,0xa3,R+0xC4);b.Add(0x58);Abs(b,0xa3,R+0xC8);
  b.Add(0x61);b.Add(0x9d);b.Add(0x31);b.Add(0xc0);b.Add(0xc3);
  Bytes(B+0xA000,b.ToArray());((Entry)Marshal.GetDelegateForFunctionPointer((IntPtr)(B+0xA000),typeof(Entry)))();
  int ox=(width-640)/2,oy=(height-480)/2;
  bool published=Read(O+0x100)==H,translated=name=="primary_panel"&&Read(O+32+8)!=args[2];
  bool physicalOracle=true,primaryOracle=true,sourceIntact=true,stateIntact=true;int physicalChanges=0,primaryChanges=0;
  for(int y=0;y<height;y++)for(int x=0;x<width;x++){
   int index=y*width+x;byte expected=oldPhysical[index];
   if(name=="primary_full"&&(Read(S+48)>state[12]||(published&&regs[0]==N))){
    expected=(x>=ox&&x<ox+640&&y>=oy&&y<oy+480)?native[(y-oy)*640+x-ox]:(byte)0;
   }else if(translated&&x>=220+ox&&x<=args[0]+ox&&y>=289+oy&&y<=args[1]+oy)expected=native[(y-oy)*640+x-ox];
   byte actual=Marshal.ReadByte((IntPtr)F,index);if(actual!=expected)physicalOracle=false;if(actual!=oldPhysical[index])physicalChanges++;
   byte expectedPrimary=published?expected:oldPrimary[index];
   if(published&&visible==1&&x>=17&&x<21&&y>=19&&y<23)expectedPrimary=0xE9;
   byte actualPrimary=Marshal.ReadByte((IntPtr)U,index);if(actualPrimary!=expectedPrimary)primaryOracle=false;if(actualPrimary!=oldPrimary[index])primaryChanges++;
  }
  for(int i=0;i<native.Length;i++)if(Marshal.ReadByte((IntPtr)P,i)!=native[i])sourceIntact=false;
  for(int i=0;i<state.Length;i++)if(i!=7&&i!=9&&i!=12&&Read(S+i*4)!=state[i])stateIntact=false;
  int[] seen=new int[7+args.Length];for(int i=0;i<7;i++)seen[i]=Read(O+i*4);for(int i=0;i<args.Length;i++)seen[7+i]=Read(O+32+i*4);
  int count=Read(E);var order=new List<int>();for(int i=0;i<count;i++)order.Add(Read(E+4+i*4));
  int[] returned=new int[7];for(int i=0,j=0;i<8;i++)if(i!=4)returned[j++]=Read(R+0xA0+i*4);
  bool backing=true;for(int y=0;y<64;y++)for(int x=0;x<64;x++){
   byte expected=published&&visible==1&&x<4&&y<4?Marshal.ReadByte((IntPtr)F,(19+y)*width+17+x):(byte)0x5D;
   if(Marshal.ReadByte((IntPtr)T,y*64+x)!=expected)backing=false;
  }
  return new Dictionary<string,object>{{"call",name},{"args",args},{"input",regs},{"seen",seen},{"returned",returned},
   {"esp",Read(R+0xB0)==Read(R+0x90)-8},{"stack_canaries",Read(R+0xC4)==0x13572468&&Read(R+0xC8)==0x24681357},
   {"flags",Read(R+0xC0)&0xCD5},{"incoming_flags",Read(O+28)&0xCD5},{"hd_flags",Read(O+0x120)&0xCD5},
   {"published",published},{"hd_source",Read(O+0x100)},{"translated",translated},{"order",order},
   {"hd_copy",new int[]{Read(O+0x1C0),Read(O+0x1C4),Read(O+0x1C8),Read(O+0x1CC),Read(O+0x1D0),Read(O+0x1D4),Read(O+0x1D8),Read(O+0x1DC)}},
   {"physical_oracle",physicalOracle},{"primary_oracle",primaryOracle},{"physical_changes",physicalChanges},{"primary_changes",primaryChanges},
   {"source_intact",sourceIntact},{"state_unchanged_except_mirror_fault",stateIntact},{"cursor_backing",backing},{"cursor_visible",Read(C+0x38)},
   {"cursor_context_intact",SameBytes(C,cursorState)&&SameBytes(descriptor,descriptorBytes)&&SameBytes(J,resourceBytes)&&SameBytes(Z,spriteBytes)&&SameBytes(A,backingHeader)},
   {"remove_arg",Read(O+0x140)},{"draw_arg",Read(O+0x144)},
   {"fault",Read(S+36)},{"mirrors",Read(S+48)},{"alloc_calls",Read(R)},{"free_calls",Read(R+4)},
   {"canaries",IsFill(P-16,16,0xD7)&&IsFill(P+307200,16,0xD7)&&IsFill(F-16,16,0xD7)&&IsFill(F+width*height,16,0xD7)&&IsFill(U-16,16,0xD7)&&IsFill(U+width*height,16,0xD7)&&IsFill(T-16,16,0xD7)&&IsFill(T+4096,16,0xD7)&&IsFill(A+188,16,0xD7)&&IsFill(S+128,16,0xD7)}};
 }
'''
CSHARP = canvas.CSHARP.replace(' static int Main()', INVOKE + '\n static int Main()')
CSHARP = CSHARP.replace('int arg=name==', '''if(name.StartsWith("primary_")){steps.Add(PrimaryCall(name,I(entries[name]),c,width,height));continue;}
    int arg=name==''')
CSHARP = CSHARP.replace('else if(kv.Key=="root_esp")', 'else if(kv.Key=="fault")W(S+36,I(kv.Value));else if(kv.Key=="root_esp")')


def payload(original, owner, bundle, cases):
    data = canvas.payload(original, owner, cases)
    native_map = {primary.HD_BLIT: HD, primary.CURSOR_REMOVE: REMOVE,
                  primary.CURSOR_DRAW: DRAW, primary.CURSOR_RECT: RECT,
                  primary.PLACEHOLDER + 10: CONTINUATION, 0x4024E0: PARTIAL,
                  modal.PRIMARY: canvas.PRIMARY, modal.PRIMARY_VTABLE: canvas.PRIMVT,
                  modal.MEMORY_VTABLE: canvas.MEMVT,
                  primary.CURSOR_STATE: CURSOR, primary.CURSOR_VISIBLE: CURSOR + 0x38}
    code = bytearray(bundle.code)
    for r in bundle.relocations:
        if bundle.base_va <= r.target < bundle.base_va + len(bundle.code):
            value = CODE + r.target - bundle.base_va
        elif bundle.modal_state_va <= r.target < bundle.modal_state_va + 128:
            value = canvas.STATE + r.target - bundle.modal_state_va
        elif r.target in owner.entries.values():
            value = canvas.BASE + r.target - owner.base_va
        elif primary.CURSOR_STATE <= r.target < primary.CURSOR_STATE + 0x80:
            value = CURSOR + r.target - primary.CURSOR_STATE
        elif r.target in primary.CURSOR_DESCRIPTORS:
            value = DESCRIPTORS + r.target - primary.CURSOR_DESCRIPTORS[0]
        elif r.target == primary.CURSOR_STARTUP_DESCRIPTOR:
            value = DESCRIPTORS + 0x800
        else:
            value = native_map[r.target]
        if r.kind == 'rel32': value -= CODE + r.offset + 4
        struct.pack_into('<I', code, r.offset, value & 0xffffffff)
    data['stubs'][str(CODE)] = code.hex()
    # Both inherited and new paths reach this same original ABI recorder.
    old_hd = canvas.STUBS[primary.HD_BLIT]
    data['stubs'][str(old_hd)] = (b'\xe9' + canvas.u32(HD - old_hd - 5)).hex()

    def event(a, number):
        a.emit('8b0d'); a.u32(EVENTS)
        a.emit('c7048d'); a.u32(EVENTS + 4); a.u32(number)
        a.emit('ff05'); a.u32(EVENTS)

    def record(a, nargs):
        for reg, pos in ((0,0),(1,4),(2,8),(3,12),(5,16),(6,20),(7,24)):
            a.emit('89' + bytes([5 + reg*8]).hex()); a.u32(OBS + pos)
        a.emit('9c8f05'); a.u32(OBS + 28)
        a.emit('50')
        for index in range(nargs):
            a.emit('8b4424' + bytes([8+index*4]).hex() + 'a3'); a.u32(OBS + 32 + index*4)
        a.emit('58')

    def clobber(a, stack):
        # Model the native leaf's observable return, not adapter internals.
        for reg, value in ((0,0x1234AABB),(1,0x2234AABB),(2,0x3234AABB),(3,0x4234AABB)):
            a.emit(bytes([0xB8+reg]).hex()); a.u32(value)
        a.emit('68020200009d')
        a.emit('c2' + struct.pack('<H',stack).hex() if stack else 'c3')

    # Old HD helper preserves GPRs, returns its own flags, and sees the actual
    # source header. Only its physical-source case performs the full-HD copy;
    # other sources are delegation recorders, not a model of legacy rendering.
    a = clip._Assembler(HD)
    a.emit('a3'); a.u32(OBS + 0x100)
    a.emit('9c8f05'); a.u32(OBS + 0x120)
    a.emit('9c60'); event(a, 2)
    a.emit('3d'); a.u32(canvas.PHYSICAL); a.branch('0f85','done')
    a.emit('8b7004bf'); a.u32(PRIMARY_PIXELS)
    a.emit('b9'); a.u32(bundle.width*bundle.height); a.emit('fcf3a4')
    a.label('done'); a.emit('619d68020200009dc3')
    data['stubs'][str(HD)] = a.finish().hex()

    # Independent 4x4 cursor backing model. Deliberately clobber every saved
    # register/flag: the adapter must protect both incoming and HD-return ABI.
    for location, number, is_draw in ((REMOVE,1,False),(DRAW,3,True)):
        a = clip._Assembler(location)
        a.emit('a3'); a.u32(OBS + (0x144 if is_draw else 0x140))
        event(a,number)
        for y in range(4):
            for x in range(4):
                target=PRIMARY_PIXELS+(19+y)*bundle.width+17+x
                if is_draw:
                    a.emit('a0');a.u32(target);a.emit('a2');a.u32(BACKING+y*64+x)
                    a.emit('c605');a.u32(target);a.emit('e9')
                else:
                    a.emit('a0');a.u32(BACKING+y*64+x);a.emit('a2');a.u32(target)
        a.emit('c705'); a.u32(CURSOR+0x38); a.u32(int(is_draw))
        for reg in (5,6,7): a.emit(bytes([0xB8+reg]).hex()); a.u32(0x77770000+reg)
        clobber(a,0)
        data['stubs'][str(location)] = a.finish().hex()

    for location,nargs,number in ((RECT,1,4),(PARTIAL,4,5),(SPRITE,7,6)):
        a=clip._Assembler(location);record(a,nargs)
        a.emit('9c60');event(a,number);a.emit('619d');clobber(a,nargs*4)
        data['stubs'][str(location)] = a.finish().hex()
    # Execute the actual displaced continuation CALL [ESI+34]. The appended
    # RET stands in for the enclosing function; its seven args must be gone.
    continuation=modal._read(original,primary.PLACEHOLDER+10,3)
    assert continuation==bytes.fromhex('ff5634')
    data['stubs'][str(CONTINUATION)] = (continuation+b'\xc3').hex()
    # The continuation adds its own return address. Retain seven operands by
    # temporarily removing the fixture's enclosing return before original CALL.
    data['stubs'][str(CONTINUATION)] = (
        b'\x8f\x05'+canvas.u32(OBS+0x180)+continuation+
        b'\xff\x35'+canvas.u32(OBS+0x180)+b'\xc3').hex()
    data['stubs'][str(canvas.PRIMVT+0x34)] = canvas.u32(SPRITE).hex()
    data['stubs'][str(canvas.PRIMVT+0x100+0x34)] = canvas.u32(SPRITE).hex()
    for name,entry in (('primary_full','full_blit'),('primary_placeholder','placeholder'),
                       ('primary_rect0','cursor_rect'),('primary_rect1','cursor_rect'),('primary_panel','panel_copy')):
        data['entries'][name]=CODE+bundle.entries[entry]-bundle.base_va
    # Execute each actual patched CALL shape with a native one-operand stack,
    # rather than aliasing both call-site tests straight to the shared entry.
    for index,site in enumerate(primary.CURSOR_RECTS):
        hook=next(h for h in bundle.hook_sites if h.va==site)
        target=CODE+hook.relocations[0].target-bundle.base_va
        location=canvas.BASE+0xDA00+index*0x40
        stub=b'\x8f\x05'+canvas.u32(OBS+0x184)
        self_call=bytes([hook.new[0]])+canvas.u32(target-(location+len(stub)+5))
        assert self_call[0]==0xE8 and len(hook.new)==5
        stub+=self_call+b'\xff\x35'+canvas.u32(OBS+0x184)+b'\xc3'
        data['stubs'][str(location)]=stub.hex()
        data['entries'][f'primary_rect{index}']=location
    return data


def with_inherited_hd_blitter(data, candidate, width, height):
    """Map authenticated predecessor instructions, then record/copy their ABI.

    The 800x600 historical cave uses PUSH imm8 for both center offsets. Every
    other profile uses two PUSH imm32 instructions. Keep those real branch
    lengths, source-size comparisons and native-source equality checks intact.
    Only absolute fixture addresses and the native leaf CALL are relocated.
    """
    u32 = canvas.u32
    def center_push(value):
        return b'\x6a' + bytes([value]) if (width, height) == (800, 600) else b'\x68' + u32(value)
    centered = center_push((height - 480) // 2) + center_push((width - 640) // 2)
    expected = (bytes.fromhex('6089c6bddf010000bf7f02000066813e') + struct.pack('<H', width)
        + bytes.fromhex('751266817e02') + struct.pack('<H', height)
        + bytes.fromhex('750abd') + u32(height - 1) + b'\xbf' + u32(width - 1)
        + bytes.fromhex('31c931db3b35e002520075') + bytes([len(centered) + 9])
        + bytes.fromhex('66813e800275') + bytes([len(centered) + 2])
        + centered + bytes.fromhex('eb02515155bac0d451005789f0'))
    expected += b'\xe8' + struct.pack('<i', 0x4024E0 - primary.HD_BLIT - len(expected) - 5) + bytes.fromhex('61c3')
    actual = modal._read(candidate, primary.HD_BLIT, len(expected))
    if actual != expected:
        raise AssertionError('inherited HD blit differs from its independent instruction contract')

    # Observation prefix is transparent to the entire original instruction
    # stream, including its incoming flags and all general-purpose registers.
    prefix = clip._Assembler(HD)
    prefix.emit('a3'); prefix.u32(OBS + 0x100)
    prefix.emit('9c8f05'); prefix.u32(OBS + 0x120)
    prefix.emit('9c608b0d'); prefix.u32(EVENTS)
    prefix.emit('c7048d'); prefix.u32(EVENTS + 4); prefix.u32(2)
    prefix.emit('ff05'); prefix.u32(EVENTS)
    prefix.emit('619d')
    prefix_bytes = prefix.finish()
    wrapper = bytearray(actual)
    map_operand = wrapper.index(b'\x3b\x35' + u32(modal.MAP)) + 2
    primary_operand = wrapper.index(b'\xba' + u32(modal.PRIMARY)) + 1
    struct.pack_into('<I', wrapper, map_operand, canvas.GLOBAL)
    struct.pack_into('<I', wrapper, primary_operand, canvas.PRIMARY)
    call = len(wrapper) - 7
    if wrapper[call] != 0xE8 or wrapper[-2:] != b'\x61\xc3':
        raise AssertionError('inherited HD tail CALL/POPAD/RET differs')
    struct.pack_into('<i', wrapper, call + 1, PARTIAL - HD - len(prefix_bytes) - call - 5)
    data['stubs'][str(HD)] = (prefix_bytes + wrapper).hex()

    # Independent inclusive native partial-copy model. It receives the source
    # header in EAX, primary in EDX, source left/top in EBX/ECX, and four stack
    # operands: right, bottom, destination x, destination y. Read its source
    # stride from the header; do not manufacture a full-copy success marker.
    a = clip._Assembler(PARTIAL)
    for reg, offset in ((0, 0), (2, 4), (3, 8), (1, 12)):
        a.emit('89' + bytes([5 + reg * 8]).hex()); a.u32(OBS + 0x1C0 + offset)
    a.emit('9c60')
    for source, offset in ((40, 16), (44, 20), (48, 24), (52, 28)):
        a.emit('8b4424' + bytes([source]).hex() + 'a3'); a.u32(OBS + 0x1C0 + offset)
    a.emit('8b44241c0fb7288b7004')  # source header, stride, pixels
    a.emit('8b54242c2b54241842')  # inclusive rows
    a.emit('8b5c24282b5c241043')  # inclusive columns
    a.emit('8b4424180fafc50344241001c6')
    a.emit('8b44243469c0'); a.u32(width)
    a.emit('034424308db8'); a.u32(PRIMARY_PIXELS)
    a.emit('fc'); a.label('row'); a.emit('89d9f3a489e829d801c6')
    a.emit('81c7'); a.u32(width); a.emit('29df4a'); a.branch('0f85', 'row')
    a.emit('619d')
    for reg, value in ((0, 0x1357AABB), (1, 0x2357AABB), (2, 0x3357AABB), (3, 0x4357AABB)):
        a.emit(bytes([0xB8 + reg]).hex()); a.u32(value)
    a.emit('68020200009dc21000')  # observable native clobbers and RET 16
    data['stubs'][str(PARTIAL)] = a.finish().hex()
    return data


def owner_from_verified_slots(candidate, context, width, height):
    """Extract actual inherited x86 after this fixture's exact slots rebuild.

    The production primary emitter independently reconstructs this same slots
    image before this helper is used. Nothing caches or mocks either rebuild.
    Mapping its already authenticated owner section avoids three additional
    framed reconstructions per profile solely to re-emit the same helper.
    This fixture helper is not an admission API for caller-supplied manifests.
    """
    meta = context['base_candidate']['predecessor']['base_candidate']
    code = modal._read(candidate, meta['code_va'], meta['code_bytes'])
    if hashlib.sha256(code).hexdigest() != meta['code_sha256']:
        raise AssertionError('inherited modal code hash differs')
    if meta['resolution'] != f'{width}x{height}' or meta['modal_state_offsets'] != modal.STATE:
        raise AssertionError('inherited modal geometry or state layout differs')
    if not meta['modal_entry_vas'] or any(type(va) is not int or not meta['code_va'] <= va < meta['code_va'] + len(code)
                                        for va in meta['modal_entry_vas'].values()):
        raise AssertionError('inherited modal entry lies outside authenticated code')
    owner = modal.ModalCanvasBundle(
        meta['code_va'], code, dict(meta['modal_entry_vas']),
        tuple(clip.Relocation(**row) for row in meta['relocations']), width, height,
        state_va=meta['state_va'], state_size=meta['modal_state_size'],
        state_offsets=dict(meta['modal_state_offsets']), observer_vas=dict(meta['modal_observer_vas']),
        candidate_sha256=meta['base_candidate_sha256'], source_contract=dict(meta['modal_canvas_contract']))
    clip.absolute_relocation_offsets(owner)
    return owner


NATIVE_FIXTURE_AVAILABLE = os.name == 'nt' and canvas.CSC.is_file() and Path('C:/Clash/clash95.exe').is_file()
NATIVE_FIXTURE_REASON = 'user-owned original and Windows x86 fixture compiler required'


class PrimaryFixture:
    """Shared fixture machinery only; it declares no discoverable test cases."""
    @classmethod
    def setUpClass(cls):
        cls.original=Path('C:/Clash/clash95.exe').read_bytes();cls.cache={}
        cls.temp=tempfile.TemporaryDirectory(prefix='clash-modal-primary-fixture-')
        source=Path(cls.temp.name)/'Fixture.cs';source.write_text(CSHARP)
        cls.exe=Path(cls.temp.name)/'Fixture.exe'
        result=subprocess.run([str(canvas.CSC),'/nologo','/platform:x86','/r:System.Web.Extensions.dll',
            '/out:'+str(cls.exe),str(source)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise AssertionError(result.stdout+result.stderr)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    @classmethod
    def bundles(cls,w=1024,h=768):
        if (w,h) not in cls.cache:
            candidate,context,probe=builder.build_candidate(cls.original,f'{w}x{h}')
            bundle=primary.emit_modal_primary(cls.original,candidate,base_va=0x400000+pe.inspect_pe(candidate).image_size,width=w,height=h)
            owner=owner_from_verified_slots(candidate,context,w,h)
            cls.cache[w,h]=(candidate,context,probe,owner,bundle)
        return cls.cache[w,h]

    def run_cases(self,cases,w=1024,h=768,*,actual_hd=False):
        candidate,_,_,owner,bundle=self.bundles(w,h)
        data=payload(self.original,owner,bundle,cases)
        if actual_hd:data=with_inherited_hd_blitter(data,candidate,w,h)
        r=subprocess.run([str(self.exe)],input=json.dumps(data),
                         capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=45)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        rows=json.loads(r.stdout)
        for row in rows:
            for s in row:
                self.assertTrue(s['esp'],s);self.assertTrue(s['canaries'],s)
                if 'call' not in s:continue
                for key in ('stack_canaries','physical_oracle','primary_oracle','source_intact',
                            'state_unchanged_except_mirror_fault','cursor_backing','cursor_context_intact'):
                    self.assertTrue(s[key],s)
                self.assertEqual(s['flags'],0,s)
                if s['call']=='primary_full':
                    self.assertEqual(s['returned'],[v for i,v in enumerate(s['input']) if i!=4],s)
                    self.assertEqual(s['hd_flags'],canvas.FLAGS&canvas.MASK,s)
                else:
                    self.assertEqual(s['incoming_flags'],canvas.FLAGS&canvas.MASK,s)
                    self.assertEqual(s['returned'][:4],[0x1234AABB,0x2234AABB,0x3234AABB,0x4234AABB],s)
                    self.assertEqual(s['returned'][4:],[s['input'][i] for i in (5,6,7)],s)
        return rows

    def check_inherited_hd_profile(self,w,h):
        rows=self.run_cases([dict(cursor=cursor,steps=['try_enter','paint','primary_full'])
                             for cursor in (0,1)],w,h,actual_hd=True)
        for row in rows:
            s=row[-1]
            self.assertTrue(s['published'])
            self.assertEqual(s['hd_copy'],[canvas.PHYSICAL,canvas.PRIMARY,0,0,w-1,h-1,0,0])
            self.assertEqual(s['order'],[1,2,3] if s['cursor_visible'] else [2])
            self.assertGreater(s['primary_changes'],w*h//2)
            self.assertEqual((s['mirrors'],s['alloc_calls'],s['free_calls']),(1,2,0))


@unittest.skipUnless(NATIVE_FIXTURE_AVAILABLE,NATIVE_FIXTURE_REASON)
class PrimaryTests(PrimaryFixture,unittest.TestCase):
    def test_actual_inherited_hd_blitter_copies_every_pixel_at_regression_resolutions(self):
        # The remaining three profiles have their own bounded fixture module;
        # do not repeat their expensive exact reconstruction in this suite.
        for w,h in ((1024,768),(1920,1080),(802,602)):
            with self.subTest(resolution=f'{w}x{h}'):
                self.check_inherited_hd_profile(w,h)

    def test_full_publication_clears_all_margins_preserves_original_arguments_and_return_flags(self):
        for w,h in ((1024,768),(1920,1080),(802,602)):
            s=self.run_cases([dict(steps=['try_enter','paint','primary_full'])],w,h)[0][-1]
            self.assertTrue(s['published']);self.assertEqual(s['hd_source'],canvas.PHYSICAL)
            self.assertEqual(s['order'],[2]);self.assertGreater(s['primary_changes'],w*h//2)
            self.assertEqual((s['mirrors'],s['alloc_calls'],s['free_calls']),(1,2,0))
            self.assertEqual((s['remove_arg'],s['draw_arg']),(0,0))

    def test_active_cursor_remove_copy_draw_order_recaptures_new_backing(self):
        for w,h in ((1024,768),(1920,1080)):
            s=self.run_cases([dict(cursor=1,steps=['try_enter','paint','primary_full'])],w,h)[0][-1]
            self.assertTrue(s['published']);self.assertEqual(s['order'],[1,2,3])
            self.assertEqual((s['remove_arg'],s['draw_arg'],s['cursor_visible']),(CURSOR,CURSOR,1))
            self.assertEqual(s['mirrors'],1)

    def test_all_static_and_startup_cursor_prefixes_and_animation_endpoints(self):
        b=self.bundles()[-1];cases=[]
        self.assertEqual(primary.CURSOR_DESCRIPTORS,tuple(0x519678+40*i for i in range(18)))
        prefixes={va:struct.unpack('<3I',modal._read(self.original,va,12)) for va in primary.CURSOR_DESCRIPTORS}
        prefixes[0x545158]=(0,0,0)  # independently known zero-initialized BSS descriptor
        self.assertEqual(b.source_contract['cursor_descriptor_prefixes'],
                         {f'{va:08x}':list(prefix) for va,prefix in prefixes.items()})
        for va,prefix in prefixes.items():
            descriptor=DESCRIPTORS+(0x800 if va==primary.CURSOR_STARTUP_DESCRIPTOR else va-primary.CURSOR_DESCRIPTORS[0])
            first,last,mode=prefix
            for frame in sorted({0,last-first}):
                cases.append(dict(cursor=1,cursor_descriptor=descriptor,cursor_first=first,cursor_last=last,
                    cursor_mode=mode,cursor_frame=frame,cursor_count=last+1,
                    steps=['try_enter','paint','primary_full']))
        for row in self.run_cases(cases):
            s=row[-1];self.assertTrue(s['published']);self.assertEqual(s['order'],[1,2,3]);self.assertEqual(s['mirrors'],1)
        animated=next(c for c in cases if c['cursor_last']>c['cursor_first'])
        bad=dict(animated,cursor_bad='frame')
        s=self.run_cases([bad])[0][-1]
        self.assertFalse(s['published']);self.assertEqual(s['order'],[2])

    def test_unrelated_full_source_does_not_latch_an_ownership_fault(self):
        s=self.run_cases([dict(source=canvas.PHYSICAL,steps=['try_enter','paint',dict(tid=124),'primary_full'])])[0][-1]
        self.assertEqual((s['hd_source'],s['fault'],s['mirrors']),(canvas.PHYSICAL,0,0))
        self.assertEqual(s['order'],[2]);self.assertEqual((s['remove_arg'],s['draw_arg']),(0,0))

    def test_invalid_cursor_metadata_rejects_new_callbacks_and_physical_source_publication(self):
        mutations=('descriptor','prefix','zero_width','large_height','frame','negative_frame',
                   'resource_null','resource_wrap','resource_high','count_zero','count_short','count_large',
                   'sprite_null','sprite_wrap','sprite_high','sprite_zero','sprite_large','backing_null','backing_high',
                   'backing_size','backing_vtable','pixels_null','pixels_wrap','pixels_high','pixels_native',
                   'pixels_physical','pixels_resource','pixels_header','pixels_sprite')
        for row in self.run_cases([dict(cursor=1,cursor_bad=m,steps=['try_enter','paint','primary_full']) for m in mutations]):
            s=row[-1];self.assertFalse(s['published']);self.assertEqual(s['hd_source'],canvas.NATIVE)
            self.assertEqual(s['order'],[2]);self.assertEqual((s['remove_arg'],s['draw_arg']),(0,0))
            self.assertEqual(s['primary_changes'],0)

    def test_hidden_cursor_does_not_dereference_its_unusable_context(self):
        s=self.run_cases([dict(cursor=0,cursor_bad='resource_wrap',steps=['try_enter','paint','primary_full'])])[0][-1]
        self.assertTrue(s['published']);self.assertEqual(s['order'],[2])

    def test_full_fallback_preserves_inherited_path_without_new_publication_or_cursor_calls(self):
        cases=[dict(steps=['primary_full']),dict(source=canvas.PHYSICAL,steps=['try_enter','paint','primary_full']),
               dict(cursor=2,steps=['try_enter','paint','primary_full']),
               dict(cursor=1,steps=['try_enter','paint',dict(fault=5),'primary_full']),
               dict(steps=['try_enter','paint',dict(tid=124),'primary_full'])]
        rows=self.run_cases(cases)
        for row in rows:
            s=row[-1]
            # A caller that already supplied PHYSICAL is inherited delegation;
            # received source remains unchanged. It is not a newly chosen one.
            self.assertEqual(s['hd_source'],s['input'][0]);self.assertEqual(s['order'],[2])
            self.assertEqual((s['remove_arg'],s['draw_arg']),(0,0))
        self.assertEqual(rows[3][-1]['fault'],5)
        self.assertEqual(rows[3][-1]['mirrors'],1)  # inherited behavior is preserved

    def test_placeholder_replays_movs_translates_only_xy_and_preserves_seven_arguments(self):
        for w,h in ((1024,768),(1920,1080),(802,602)):
            s=self.run_cases([dict(steps=['try_enter','paint','primary_placeholder'])],w,h)[0][-1]
            expected=[canvas.PRIMARY,289+(h-480)//2,0x12345678,220+(w-640)//2,
                      0x44556677,canvas.PRIMVT,0x66778899]+s['args']
            self.assertEqual(s['seen'],expected);self.assertEqual(s['order'],[6])
            self.assertEqual((s['physical_changes'],s['primary_changes']),(0,0))

    def test_placeholder_wrong_context_and_sticky_fault_replay_native_coordinates(self):
        cases=[dict(steps=['primary_placeholder']),dict(source=canvas.NATIVE,steps=['try_enter','primary_placeholder']),
               dict(vtable=canvas.PRIMVT+0x100,steps=['try_enter','primary_placeholder']),
               dict(steps=['try_enter',dict(fault=5),'primary_placeholder']),
               dict(steps=['try_enter',dict(tid=124),'primary_placeholder'])]
        for row in self.run_cases(cases):
            s=row[-1];self.assertEqual((s['seen'][1],s['seen'][3]),(289,220))
            self.assertEqual(s['seen'][7:],s['args']);self.assertEqual(s['physical_changes'],0)

    def test_both_cursor_rect_call_sites_translate_physical_bounds_and_ret4(self):
        for w,h in ((1024,768),(1920,1080),(802,602)):
            for name in ('primary_rect0','primary_rect1'):
                s=self.run_cases([dict(right=639,bottom=479,steps=['try_enter',name])],w,h)[0][-1]
                self.assertEqual(s['seen'],[CURSOR,639+(w-640)//2,220+(w-640)//2,
                    289+(h-480)//2,0x44556677,0x55667788,0x66778899,479+(h-480)//2])
                self.assertEqual(s['order'],[4]);self.assertEqual(s['physical_changes'],0)

    def test_cursor_rect_rejects_signed_highword_bounds_wrong_owner_and_wrong_state(self):
        changes=[dict(left=219),dict(top=288),dict(right=219),dict(right=640),dict(right=-1),
                 dict(right=0x10000+422),dict(bottom=288),dict(bottom=480),dict(bottom=-1),dict(source=CURSOR+4)]
        cases=[dict(c,steps=['try_enter','primary_rect0']) for c in changes]
        cases += [dict(steps=['primary_rect0']),dict(steps=['try_enter',dict(fault=5),'primary_rect1']),
                  dict(steps=['try_enter',dict(tid=124),'primary_rect1'])]
        for row in self.run_cases(cases):
            s=row[-1];self.assertEqual(s['seen'][:4],s['input'][:4]);self.assertEqual(s['seen'][7:],s['args'])
            self.assertEqual((s['physical_changes'],s['primary_changes']),(0,0))

    def test_selected_panel_inclusive_dirty_rectangle_exact_copy_and_ret16(self):
        for w,h in ((1024,768),(1920,1080),(802,602)):
            for right,bottom in ((220,289),(422,408),(639,479)):
                s=self.run_cases([dict(right=right,bottom=bottom,steps=['try_enter','paint','primary_panel'])],w,h)[0][-1]
                self.assertTrue(s['translated']);self.assertEqual(s['order'],[5])
                self.assertEqual(s['seen'],[canvas.NATIVE,289,canvas.PRIMARY,220,0x44556677,0x55667788,0x66778899,
                    right,bottom,220+(w-640)//2,289+(h-480)//2])
                self.assertGreater(s['physical_changes'],0);self.assertEqual(s['primary_changes'],0)

    def test_selected_panel_invalid_arguments_delegate_without_copy_or_translation(self):
        changes=[dict(source=0),dict(destination=0),dict(left=219),dict(top=288),dict(dest_x=221),dict(dest_y=290),
                 dict(right=219),dict(right=640),dict(right=-1),dict(right=0x10000+422),
                 dict(bottom=288),dict(bottom=480),dict(bottom=-1)]
        for row in self.run_cases([dict(c,steps=['try_enter','paint','primary_panel']) for c in changes]):
            s=row[-1];self.assertFalse(s['translated']);self.assertEqual(s['physical_changes'],0)
            self.assertEqual(s['seen'][:4],s['input'][:4]);self.assertEqual(s['seen'][7:],s['args'])

    def test_selected_panel_bad_pointer_alias_thread_header_fault_and_inactive_never_copy(self):
        mutations=[dict(fault=5),dict(tid=124),dict(native_width=800),dict(map_pointer=canvas.PHYSICAL),
                   dict(native_pixels=canvas.PIXELS+4),dict(physical_pixels=canvas.PHYSPIX+4),dict(native_com=1),
                   dict(native_pixels=canvas.PHYSPIX,owned_native_pixels=canvas.PHYSPIX),
                   dict(physical_pixels=canvas.PIXELS,entered_physical_pixels=canvas.PIXELS),
                   dict(native_pixels=0xFFFF0000,owned_native_pixels=0xFFFF0000)]
        cases=[dict(steps=['try_enter','paint',m,'primary_panel']) for m in mutations]
        cases += [dict(steps=['primary_panel']),dict(allocation_failure=1,steps=['try_enter','primary_panel']),
                  dict(steps=['try_enter','paint','try_leave','primary_panel'])]
        for row in self.run_cases(cases):
            s=row[-1];self.assertFalse(s['translated']);self.assertEqual(s['physical_changes'],0)
            self.assertEqual(s['seen'][7:],s['args'])

    def test_exact_hooks_old_bytes_full_source_identity_and_new_claims_remain_uninstalled(self):
        candidate,context,probe,owner,b=self.bundles()
        self.assertFalse(b.installation_ready);self.assertEqual(len(b.hook_sites),5)
        self.assertEqual(b.candidate_sha256,hashlib.sha256(candidate).hexdigest())
        self.assertEqual(b.modal_entry_vas,owner.entries)
        for hook in b.hook_sites:
            self.assertEqual(candidate[hook.offset:hook.offset+len(hook.old)],hook.old)
            self.assertEqual(len(hook.new),len(hook.old));self.assertEqual(len(hook.relocations),1)
            self.assertEqual(hook.va+5+struct.unpack_from('<i',hook.new,1)[0],hook.relocations[0].target)
            self.assertFalse(clip._original_highlow_fields(self.original,hook.va,len(hook.old)))
        for key in ('runtime_executed','primary_composition_proven','manual_input_proof','promotion_ready'):
            self.assertFalse(b.source_contract[key])
        self.assertEqual(b.source_contract['new_state_bytes'],0)
        self.assertEqual({h.va for h in b.hook_sites},{primary.FULL_BLIT,primary.PLACEHOLDER,primary.PANEL_COPY,*primary.CURSOR_RECTS})
        clip.absolute_relocation_offsets(b)

    def test_fixture_owner_extraction_rejects_changed_code_entries_geometry_and_relocations(self):
        candidate,context,_,_,_=self.bundles()
        meta=context['base_candidate']['predecessor']['base_candidate']
        changed=bytearray(candidate)
        changed[pe.inspect_pe(candidate).file_offset(meta['code_va']-0x400000,1)]^=1
        with self.assertRaisesRegex(AssertionError,'code hash'):
            owner_from_verified_slots(bytes(changed),context,1024,768)
        for field,value in (('modal_entry_vas',{'is_active':meta['code_va']-1}),
                            ('resolution','800x600'),
                            ('relocations',[dict(meta['relocations'][0],offset=meta['code_bytes'])])):
            changed_context=json.loads(json.dumps(context))
            changed_context['base_candidate']['predecessor']['base_candidate'][field]=value
            with self.assertRaises((AssertionError,ValueError)):
                owner_from_verified_slots(candidate,changed_context,1024,768)

    def test_reject_unknown_candidate_original_allocation_native_span_and_displaced_bytes(self):
        candidate,context,probe,_,b=self.bundles();kw=dict(base_va=b.base_va,width=1024,height=768)
        for original,value,args in ((self.original[:-1],candidate,kw),(self.original,candidate[:-1],kw),
                                    (self.original,candidate,dict(kw,base_va=b.base_va-4096))):
            with self.assertRaises(ValueError):primary.emit_modal_primary(original,value,**args)
        for va in (primary.PLACEHOLDER,primary.CURSOR_REMOVE,primary.FULL_BLIT):
            bad=bytearray(candidate);bad[pe.inspect_pe(candidate).file_offset(va-0x400000,1)]^=1;bad=bytes(bad)
            with patch.object(builder,'build_candidate',return_value=(bad,context,probe)):
                with self.assertRaises(ValueError):primary.emit_modal_primary(self.original,bad,**kw)
        bad=bytearray(candidate);coff=struct.unpack_from('<I',bad,0x3C)[0]+22
        struct.pack_into('<H',bad,coff,struct.unpack_from('<H',bad,coff)[0]|0x20)
        with patch.object(builder,'build_candidate',return_value=(bytes(bad),context,probe)):
            with self.assertRaises(ValueError):primary.emit_modal_primary(self.original,bytes(bad),**kw)


if __name__=='__main__':unittest.main()
