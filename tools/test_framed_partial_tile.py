#!/usr/bin/env python3
"""Execute the optional framed clipping/composition integration offline.

Uses the source-canonical framed recipe only in memory. Native drawing calls
are ABI recorders; the emitted frame helper itself executes against synthetic
FRAME descriptors. No game, debugger, input, images or candidate files occur.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_recipe
from src.patcher import four_sided_frame
from src.patcher.framed_viewport import FramedViewport
import test_partial_tile_clip as runner
import test_four_sided_frame_x86 as frame_fixture

# Literal independent acceptance table: physical W/H, full counts, ceiling
# counts, inclusive terrain end. Native640 is outside the candidate builder.
PROFILES = ((800,600,11,8,12,9,767,583), (1024,768,15,11,15,12,991,751),
            (1280,720,19,10,19,11,1247,703), (1280,960,19,14,19,15,1247,943),
            (1920,1080,29,16,29,17,1887,1063), (802,602,11,8,12,9,769,585))
GLOBALS = dict(runner.GLOBALS,frame_sprites_global=frame_fixture.FRAME_GLOBAL)


def pixels(rect):
    l,t,r,b=rect
    return {(x,y) for y in range(t,b+1) for x in range(l,r+1)} if l<=r and t<=b else set()


def intersection(a,b):
    return max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])


def tile_with_virtual_primitives(w,h,delta):
    """Synthetic tile calls the actual installed vtable, not adapter labels.

    This checks the wiring through all four changed primitive slots. It is not
    execution of the game's complete tile routine or a native rendering claim.
    """
    b=bytearray.fromhex('9c60')+runner.recorder(4,0,delta=delta)[:-3]
    for slot,top,right,left,bottom in ((5,16,w+9,-10,16),(6,20,w-1,0,h-30),
                                      (7,-10,w+9,-10,h+9),(13,0,0,0,0)):
        b+=b'\xa1'+struct.pack('<I',runner.GLOBAL+delta)+bytes.fromhex('8bb8b8000000')
        if slot==13:
            for value in (0,0,1,-1,-1,-1,-1):b+=b'\x68'+struct.pack('<I',value&0xffffffff)
            values=((0xbb,0),(0xb9,0),(0xba,runner.SPRITE+delta))
        else:
            for value in (0x17,bottom):b+=b'\x68'+struct.pack('<I',value&0xffffffff)
            values=((0xbb,top),(0xb9,right),(0xba,left))
        for opcode,value in values:b+=bytes([opcode])+struct.pack('<I',value&0xffffffff)
        b+=bytes((0xff,0x57,slot*4))
    return bytes(b+bytes.fromhex('619db868245713c3'))


@unittest.skipUnless(runner.ORIGINAL.is_file(),'requires known original for byte authentication')
class FramedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.original=runner.ORIGINAL.read_bytes()

    def test_literal_edge_counts_endpoints_and_clipped_world_tails(self):
        for w,h,tx,ty,cx,cy,right,bottom in PROFILES:
            layout=FramedViewport(w,h)
            for sx,sy in ((0,0),(60-tx,60-ty)):
                cells=clip.edge_cells(width=w,height=h,map_width=60,map_height=60,
                                      scroll_x=sx,scroll_y=sy,layout=layout)
                expected=[(col,row) for row in range(cy) for col in range(cx) if col>=tx or row>=ty]
                self.assertEqual([(c.column,c.row) for c in cells],expected)
                self.assertEqual(len(cells),cx*cy-tx*ty)
                for c,(col,row) in zip(cells,expected):
                    self.assertEqual(c.rect,(32+64*col,16+64*row,min(right,95+64*col),min(bottom,79+64*row)))
                    self.assertEqual(c.operation,'draw_clipped_tile' if sx+col<60 and sy+row<60 else 'clear_outside_world')
                    self.assertTrue(32<=c.rect[0]<=c.rect[2]<=right and 16<=c.rect[1]<=c.rect[3]<=bottom)

    def test_clip_end_and_layout_mismatch_fail_closed(self):
        image=framed_recipe.canonical_candidate(self.original,800,600).image
        for end in ((31,583),(767,15),(800,583),(767,600),(-1,10),(True,583),(767,583.0),(767,),()):
            with self.assertRaises((ValueError,TypeError)):
                clip.emit_adapters(self.original,base_va=runner.BASE,width=800,height=600,
                                   clip_origin=(32,16),clip_end=end)
        for layout in (FramedViewport(802,602),object(),(800,600)):
            for fn in (clip.emit_edge_dispatch,clip.emit_map_composition):
                with self.assertRaises(ValueError):fn(self.original,image,base_va=runner.BASE,width=800,height=600,layout=layout)
            with self.assertRaises(ValueError):
                clip.edge_cells(width=800,height=600,map_width=60,map_height=60,scroll_x=0,scroll_y=0,layout=layout)


@unittest.skipUnless(os.name=='nt' and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     'requires local x86 compiler and authenticated original')
class FramedIntegrationX86Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='clash-framed-partial-fixture-');cls.addClassCleanup(cls.temp.cleanup)
        root=Path(cls.temp.name);cls.exe=root/'fixture.exe';source=root/'fixture.cs'
        # Reuse authentic width-low/height-high FRAME descriptor setup, including
        # encoding0, nonzero stream pointers and rejection mutations. Only native
        # sprite primitives are recorded; draw_frame is never replaced by a stub.
        text=frame_fixture.fixture_source()
        text=frame_fixture.replace_once(text,' static int B,Surface,Sprite,Global,Record,Output,GameData;',
              ' [DllImport("kernel32")] static extern uint SetErrorMode(uint mode);\n'
              ' static int B,Surface,Sprite,Global,Record,Output,GameData;')
        text=frame_fixture.replace_once(text,'   if(IntPtr.Size!=4)throw new Exception("Fixture must execute as x86");',
              '   SetErrorMode(3);\n   if(IntPtr.Size!=4)throw new Exception("Fixture must execute as x86");')
        source.write_text(text,encoding='utf-8')
        result=subprocess.run([str(runner.CSC),'/nologo','/platform:x86','/optimize+',
                               '/r:System.Web.Extensions.dll',f'/out:{cls.exe}',str(source)],
                              capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise AssertionError(result.stdout+result.stderr)
        cls.original=runner.ORIGINAL.read_bytes();cls.cache={}

    def bundle(self,w,h,mode):
        key=w,h,mode
        if key not in self.cache:
            layout=FramedViewport(w,h)
            canonical=framed_recipe.canonical_candidate(self.original,w,h)
            if mode=='adapters':
                b=clip.emit_adapters(self.original,base_va=runner.BASE,width=w,height=h,
                                     clip_origin=(32,16),clip_end=(w-33,h-17))
            else:
                fn=clip.emit_map_composition if mode=='composition' else clip.emit_edge_dispatch
                b=fn(self.original,canonical.image,base_va=runner.BASE,width=w,height=h,layout=layout)
            self.assertFalse(b.installation_ready);self.assertFalse(canonical.installation_ready)
            self.cache[key]=(b,canonical.image)
        return self.cache[key]

    def execute(self,w,h,cases,mode='composition',delta=0,tile_primitives=False):
        bundle,candidate=self.bundle(w,h,mode);code=bytearray(bundle.code)
        self.assertLess(len(code),0x6000,'code overlaps synthetic native recorders')
        for r in bundle.relocations:
            if r.kind=='abs32':struct.pack_into('<I',code,r.offset,GLOBALS.get(r.purpose,r.target)+delta)
            else:
                self.assertIn(r.purpose,runner.STUBS,'new native transfer requires independent ABI recorder')
                struct.pack_into('<i',code,r.offset,runner.STUBS[r.purpose]-runner.BASE-r.offset-4)
        payload=dict(code=code.hex(),width=w,height=h,base=runner.BASE+delta,image_delta=delta,
                     stubs={str(runner.STUBS[n]+delta):runner.recorder(i,runner.ARGC[n],delta=delta,
                            cleanup=0 if n in ('turn_text_format','turn_text_draw') else None).hex()
                            for i,n in enumerate(runner.STUBS,1)},cases=[])
        if tile_primitives:
            payload['stubs'][str(runner.STUBS['tile']+delta)]=tile_with_virtual_primitives(w,h,delta).hex()
        off=clip.file_offset(candidate,clip.COMMAND_DESCRIPTORS,322)
        desc=bytearray(candidate[off:off+322])
        for i in range(6):
            self.assertEqual(struct.unpack_from('<ii',desc,53*i),(w-224+64*(i%3),h-80+32*(i//3)))
            struct.pack_into('<I',desc,53*i+12,GLOBALS['command_sprites']+delta)
            struct.pack_into('<I',desc,53*i+28,0x4191f0+delta)
        payload['descriptor_bytes']=desc.hex()
        for case in cases:
            row=dict(case,args=case.get('args',[]),entry=bundle.entries[case['name']]+delta)
            row['regs']=list(case.get('regs',[0,0,0,0]))
            # Only addresses supplied to low-level primitives require rebasing;
            # map tile/rectangle coordinates remain ordinary integers.
            if mode=='adapters':
                row['regs'][0]+=delta
                if row['name']=='sprite':row['regs'][3]+=delta
            if case.get('initial_vtable')=='clipped':row['initial_vtable']=bundle.entries['clipped_vtable']+delta
            payload['cases'].append(row)
        proc=subprocess.run([str(self.exe)],input=json.dumps(payload),capture_output=True,text=True,
                            timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        reports=json.loads(proc.stdout);self.assertEqual(len(reports),len(cases))
        for case,sent,report in zip(cases,payload['cases'],reports):
            state=report['state'];self.assertEqual(state[1:4],[case.get('esi',0x11223344),0x55667788,0x99aabbcc])
            self.assertEqual(state[4],state[5],'exact caller stack must survive')
            # Low-level primitive adapters pass clipped working registers to
            # the native callee; the higher-level cell/composition ABI promises
            # preservation of those registers as well as the nonvolatiles.
            if mode!='adapters':self.assertEqual(state[6:9],[v&0xffffffff for v in sent['regs'][1:]])
            self.assertEqual(report['render'],case.get('initial_render',0x12345000))
            expected_vtable=0x50ee74 if case.get('bad')=='vtable' else sent.get('initial_vtable',clip.MEMORY_VTABLE+delta)
            self.assertEqual(report['vtable'],expected_vtable)
        return reports

    def test_all_primitive_clips_exclude_four_borders(self):
        for w,h,_,_,_,_,right,bottom in PROFILES:
            bounds=(32,16,right,bottom)
            rects=[(-10,-10,w+9,h+9),(31,16,32,16),(right,16,right+1,16),
                   (32,bottom,32,bottom+1),(0,0,31,h-1),(right+1,0,w-1,h-1),
                   (0,0,w-1,15),(0,bottom+1,w-1,h-1),(40,20,45,25)]
            cases=[]
            for name in ('fill','outline','line','sprite'):
                for l,t,r,b in rects:
                    if name=='line':b=t
                    cases.append(dict(name=name,rect=(l,t,r,b),
                                      regs=[runner.SURFACE,0,0,runner.SPRITE] if name=='sprite' else [runner.SURFACE,t,r,l],
                                      args=[l,t,r,b,1,0,0] if name=='sprite' else [b,0x101]))
            reports=self.execute(w,h,cases,mode='adapters')
            for case,report in zip(cases,reports):
                expected=pixels(intersection(case['rect'],bounds));observed=set()
                if case['name']=='outline':
                    l,t,r,b=case['rect'];expected={p for p in expected if p[0] in (l,r) or p[1] in (t,b)}
                for row in report['records']:
                    rect=tuple(runner.signed(x) for x in (row[5:9] if row[0]==3 else [row[4],row[2],row[3],row[5]]))
                    self.assertEqual(intersection(rect,bounds),rect)
                    observed |= pixels(rect)
                self.assertEqual(observed,expected,(w,h,case))

    def test_partial_and_full_cells_clear_world_tails_without_border_writes(self):
        for w,h,tx,ty,cx,cy,right,bottom in PROFILES:
            partial=[(col,row) for row in range(cy) for col in range(cx) if col>=tx or row>=ty]
            selected=[(0,0),(tx-1,ty-1),partial[0],partial[-1]]
            cases=[dict(name='cell',regs=[col,row,0,0],esi=present,scroll_x=sx,scroll_y=sy)
                   for col,row in selected for sx,sy in ((0,0),(60-tx,60-ty)) for present in (0,1)]
            reports=self.execute(w,h,cases,mode='edge')
            bundle,_=self.bundle(w,h,'edge')
            for c,r in zip(cases,reports):
                col,row=c['regs'][:2];wx,wy=c['scroll_x']+col,c['scroll_y']+row
                clear=wx>=60 or wy>=60;rect=(32+col*64,16+row*64,min(right,95+col*64),min(bottom,79+row*64))
                self.assertEqual(r['state'][0],2 if clear else 1)
                rows=r['records'];self.assertEqual([x[0] for x in rows],([2,14] if clear else [4])+([5,6,7] if c['esi'] else []))
                self.assertEqual(rows[0][12:14],[bundle.entries['clipped_vtable'],runner.SURFACE])
                if clear:self.assertEqual(rows[0][1:7],[runner.SURFACE,rect[1],rect[2],rect[0],rect[3],1])
                else:
                    # Native tile inputs are EAX=X, EBX=world pointer, EDX=Y;
                    # ECX is an incidental working register, not a fourth arg.
                    self.assertEqual(rows[0][1:3],[rect[0],runner.GAME_DATA+1400*wx+14*wy])
                    self.assertEqual(rows[0][4],rect[1])
                if c['esi']:
                    copy=next(x for x in rows if x[0]==6)
                    self.assertEqual(copy[1:9],[runner.SURFACE,rect[0],rect[1],0,rect[2],rect[3],rect[0],rect[1]])
            # Incremental world coordinates reach a genuine complete cell and
            # the final visible partial cell; neither uses legacy W/H counts.
            inc=[dict(name='cell_incremental_composed',regs=[10+col,0,0,17+row]) for col,row in ((tx-1,ty-1),partial[-1])]
            for r in self.execute(w,h,inc):self.assertEqual(r['state'][0],1)

    def test_full_order_executes_real_frame_helper_then_commands_before_present(self):
        for w,h,tx,ty,cx,cy,right,bottom in PROFILES:
            edge_count=cx*cy-tx*ty;plan=four_sided_frame.frame_draw_plan(FramedViewport(w,h))
            cases=[dict(name='edge_full_composed',regs=[present,0,0,0],scroll_x=0,scroll_y=0,cursor=0)
                   for present in (0,1)]
            for c,r in zip(cases,self.execute(w,h,cases)):
                self.assertEqual(r['state'][0],1)
                rows=r['records'];kinds=[x[0] for x in rows]
                self.assertEqual(kinds,[4]*edge_count+[3]*len(plan)+[8]+([5,6] if c['regs'][0] else []))
                frame_rows=rows[edge_count:edge_count+len(plan)]
                for row,draw in zip(frame_rows,plan):
                    self.assertEqual(row[1:5],[runner.SURFACE,draw.x&0xffffffff,draw.y&0xffffffff,runner.SPRITE+0x100+0x100*draw.sprite])
                    self.assertEqual(row[5:12],[*draw.clip.as_tuple(),1,0,0])
                    self.assertEqual(row[12:14],[clip.MEMORY_VTABLE,runner.SURFACE])
                self.assertEqual(frame_rows[-1][4],runner.SPRITE+0x600,'footer5 must be last and separate')
                panel=rows[edge_count+len(plan)];self.assertEqual(panel[1],runner.DESCRIPTORS);self.assertEqual(panel[4],0)
                if c['regs'][0]:self.assertEqual(rows[-1][1:9],[runner.SURFACE,0,0,0,w-1,h-1,0,0])
                else:self.assertFalse(any(row[0] in (5,6,7) for row in rows),'offscreen frame composition reached primary')

    def test_frame_rejection_prevents_panel_and_presentation(self):
        cases=[dict(name='edge_full_composed',regs=[1,0,0,0],**bad)
               for bad in ({'null_table':1},{'bad_encoding':0},{'zero_stream':5},{'wrong_width':3})]
        for r in self.execute(800,600,cases):
            self.assertEqual(r['state'][0],0)
            self.assertEqual([x[0] for x in r['records']],[4]*20,'a failed real frame helper cannot imply completed composition')

    def test_framed_command_and_ai_docks_stay_within_terrain(self):
        for w,h,_,_,_,_,right,bottom in PROFILES:
            cases=[dict(name='compose_panel',regs=[0,0,0,0],interactive=interactive,turn_number=1)
                   for interactive in (1,0)]
            command,ai=self.execute(w,h,cases)
            self.assertEqual([x[0] for x in command['records']],[8]);self.assertEqual(command['state'][0],1)
            rows=ai['records'];self.assertEqual([x[0] for x in rows],[9,3,9,3,10,11,12,13])
            sprites=[x for x in rows if x[0]==3]
            self.assertEqual([x[2:4] for x in sprites],[[w-224,h-80],[w-72,h-76]])
            self.assertTrue(all(x[5:9]==[32,16,right,bottom] for x in sprites))
            self.assertEqual(rows[5][5:9],[w-224,w-32,h-44,3])
            self.assertEqual(rows[-1][5:9],[w-219,h-75,0x4ec7c5,7])
            self.assertEqual(ai['state'][0],1);self.assertFalse(any(x[0] in (5,6,7) for x in rows))

    def test_full_physical_present_excludes_only_primary_tooltip_and_rebases(self):
        for delta in (0,0x02000000):
            w,h=800,600;tooltip=(240,586,553,599)
            cases=[dict(name='present_map_rect',regs=list(rect),tooltip=1,cursor=0)
                   for rect in ((0,0,799,599),(0,0,31,599),(768,0,799,599),(0,584,799,599),(240,586,553,599))]
            for c,r in zip(cases,self.execute(w,h,cases,delta=delta)):
                self.assertEqual(r['state'][0],1);observed=set()
                rows=r['records'];self.assertEqual(len(rows)%2,0)
                for dirty,copy in zip(rows[::2],rows[1::2]):
                    self.assertEqual((dirty[0],copy[0]),(5,6));self.assertEqual(copy[1],runner.SURFACE+delta)
                    rect=(copy[2],copy[3],copy[5],copy[6]);part=pixels(rect)
                    self.assertFalse(part&observed);self.assertFalse(part&pixels(tooltip));observed|=part
                self.assertEqual(observed,pixels(c['regs'])-pixels(tooltip))
            # Rebasing the integrated real frame body must retain all absolute
            # descriptor/global and native transfer fields, not only presenters.
            r=self.execute(w,h,[dict(name='edge_full_composed',regs=[0,0,0,0],scroll_x=0,scroll_y=0)],delta=delta)[0]
            self.assertEqual(r['state'][0],1)
            self.assertTrue(any(x[0]==3 and x[4]==runner.SPRITE+0x600+delta for x in r['records']))
            self.assertFalse(any(x[0] in (5,6,7) for x in r['records']))

    def test_scoped_cell_preserves_existing_clipped_vtable_and_rejects_wrong_owner(self):
        cases=[dict(name='cell_composed',regs=[2,2,0,0],esi=0,initial_vtable='clipped',initial_render=0),
               dict(name='cell_composed',regs=[2,2,0,0],esi=1,render_hook=0x4617a0),
               dict(name='cell_composed',regs=[11,8,0,0],esi=0,scroll_x=49,scroll_y=52)]
        a,b,c=self.execute(800,600,cases)
        self.assertEqual(a['state'][0],1);self.assertEqual([r[0] for r in a['records']],[4,8])
        self.assertEqual(b['state'][0],0);self.assertEqual(b['records'],[])
        self.assertEqual(c['state'][0],2);self.assertEqual([r[0] for r in c['records']],[2,14,8])

    def test_native_tile_dispatch_uses_each_framed_virtual_primitive(self):
        for delta in (0,0x02000000):
            w,h=802,602;right,bottom=769,585
            r=self.execute(w,h,[dict(name='cell',regs=[2,2,0,0],esi=0)],mode='edge',
                           delta=delta,tile_primitives=True)[0]
            self.assertEqual(r['state'][0],1)
            rows=r['records'];self.assertEqual([x[0] for x in rows],[4,1,1,1,2,3])
            for row in rows[1:]:
                rect=tuple(row[5:9]) if row[0]==3 else (row[4],row[2],row[3],row[5])
                self.assertEqual(intersection(rect,(32,16,right,bottom)),rect)
            self.assertEqual(rows[-2][2:6],[16,right,32,bottom])
            self.assertEqual(rows[-1][5:9],[32,16,right,bottom])


if __name__=='__main__':unittest.main()
