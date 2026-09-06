#!/usr/bin/env python3
"""Pure frame geometry/pixel fixtures; no extracted assets or runtime."""
from __future__ import annotations

from dataclasses import replace
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frame_surface_audit as audit
from hd_layout_asset_composition import Sprite
from src.patcher.framed_viewport import FramedViewport

RESOURCE = Path('C:/Clash/DATA/GFX3.RES')
RESOLUTIONS = ((640,480),(800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602))


def synthetic_frame():
    base=tuple((x*13+y*7)%253+2 if x<32 or x>=608 or y<16 or y>=464 else None
               for y in range(480) for x in range(640))
    footer=Sprite(324,15,tuple(100+i%100 for i in range(4860)))
    return audit.NativeFrame(base,footer,'synthetic','synthetic',0,0)


def surface(frame,layout):
    raw=bytearray([1])*(layout.width*layout.height)
    for (x,y),value in audit.expected_frame_pixels(frame,layout).items():
        raw[y*layout.width+x]=value
    return raw


class FramePixelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame=synthetic_frame()

    def test_native_identity_and_separate_footer(self):
        layout=FramedViewport(640,480)
        pixels=audit.expected_frame_pixels(self.frame,layout,include_footer=False)
        original={(x,y):v for y in range(480) for x in range(640)
                  if (v:=self.frame.base_pixels[y*640+x]) is not None}
        self.assertEqual(pixels,original)
        composite=audit.expected_frame_pixels(self.frame,layout)
        for y in range(15):
            for x in range(324):
                self.assertEqual(composite[155+x,465+y],self.frame.footer.pixels[y*324+x])
        self.assertEqual(len(pixels),49152)
        self.assertEqual(len(composite),49152)
        self.assertEqual(self.frame.footer_native_origin,(155,465))

    def test_all_four_corners_survive_at_every_profile(self):
        for w,h in RESOLUTIONS:
            layout=FramedViewport(w,h)
            for dx,dy,sx,sy in ((0,0,0,0),(w-32,0,608,0),(0,h-16,0,464),(w-32,h-16,608,464)):
                for y in range(16):
                    for x in range(32):
                        self.assertEqual(audit.native_source_xy(dx+x,dy+y,layout),(sx+x,sy+y))
            self.assertIsNone(audit.native_source_xy(32,16,layout))
            self.assertIsNone(audit.native_source_xy(w-33,h-17,layout))

    def test_repeat_bands_and_clipped_tail_against_native_row_sequences(self):
        for w,h in RESOLUTIONS:
            layout=FramedViewport(w,h)
            expected_x=(list(range(32,608))*((w-64+575)//576))[:w-64]
            expected_y=(list(range(16,464))*((h-32+447)//448))[:h-32]
            self.assertEqual([audit.native_source_xy(x,0,layout)[0] for x in range(32,w-32)],expected_x)
            self.assertEqual([audit.native_source_xy(w-1,y,layout)[1] for y in range(16,h-16)],expected_y)
            self.assertEqual(audit.footer_origin(layout),(155+(w-640)//2,h-15))

    def test_complete_pixel_pass_and_single_pixel_failures_are_exact(self):
        for w,h in RESOLUTIONS:
            layout=FramedViewport(w,h);raw=surface(self.frame,layout)
            result=audit.audit_surface(bytes(raw),layout,self.frame)
            self.assertTrue(result['passed'])
            self.assertEqual(result['checked_border_pixels']+4860,2*w*16+2*(h-32)*32)
            for x,y in ((0,0),(w-1,0),(0,h-1),(w-1,h-1),(w//2,0),(w-1,h//2),(0,h//2),(40,h-1)):
                original=raw[y*w+x];raw[y*w+x]=(original+1)%256
                failed=audit.audit_surface(bytes(raw),layout,self.frame)
                self.assertFalse(failed['structural_border_exact'],(w,h,x,y))
                self.assertFalse(failed['passed'])
                raw[y*w+x]=original

    def test_footer_overlay_uncertainty_does_not_mask_frame_or_become_pass(self):
        layout=FramedViewport(800,600);raw=surface(self.frame,layout)
        ax,ay=audit.footer_origin(layout)
        raw[(ay+2)*800+ax+5]^=1 # A possible tooltip glyph; no claim it is actual text.
        result=audit.audit_surface(bytes(raw),layout,self.frame)
        self.assertTrue(result['structural_border_exact'])
        self.assertFalse(result['passed'])
        self.assertEqual(result['footer']['status'],'unverified_background_or_active_tooltip_text')
        self.assertEqual(result['footer']['exact_matches'],4859)
        with self.assertRaises(TypeError):
            audit.audit_surface(bytes(raw),layout,self.frame,ignore_footer=True)

    def test_full_frame_cannot_pass_with_only_top_left_and_action_bar(self):
        layout=FramedViewport(1024,768);raw=surface(self.frame,layout)
        for y in range(16,752):raw[y*1024+992:(y+1)*1024]=bytes(32)
        for y in range(752,768):raw[y*1024+32:y*1024+992]=bytes(960)
        result=audit.audit_surface(bytes(raw),layout,self.frame)
        self.assertFalse(result['passed'])
        self.assertFalse(result['structural_border_exact'])
        self.assertGreater(next(r for r in result['bands'] if r['name']=='right')['mismatches'],0)
        self.assertGreater(next(r for r in result['bands'] if r['name']=='bottom')['mismatches'],0)

    def test_invalid_identity_dimensions_shape_and_size_fail_closed(self):
        with self.assertRaises(ValueError):audit.load_native_frame(b'not a resource')
        for wh in ((639,480),(640,479),(801,600),(800,601),(True,480),(8194,480)):
            with self.assertRaises(ValueError):FramedViewport(*wh)
        layout=FramedViewport(800,600)
        for n in (0,479999,480001):
            with self.assertRaises(ValueError):audit.audit_surface(bytes(n),layout,self.frame)
        for malformed in (replace(self.frame,base_pixels=()),replace(self.frame,footer=Sprite(1,1,(0,))),
                          replace(self.frame,footer=Sprite(324,15,(None,)*4860))):
            with self.assertRaises(ValueError):audit.expected_frame_pixels(malformed,layout)
        for xy in ((-1,0),(800,0),(0,600)):
            with self.assertRaises(ValueError):audit.native_source_xy(*xy,layout)

    def test_summary_byte_counts_cannot_contradict_exact_pixels(self):
        # Virtual artifacts exercise the summary adapter without producing
        # images or bypassing the real pixel oracle. Binding itself has its
        # dedicated reconstruction tests in the action-bar fixture.
        layout=FramedViewport(800,600);raw=bytes(surface(self.frame,layout))
        path=Path(__file__).resolve().parent/'virtual-frame-run'/'summary.json'
        raw_path=path.with_name('surface.raw');png_path=path.with_name('surface.png')
        summary=dict(Surface=dict(Width=800,Height=600,Bytes=len(raw)),RawBytes=len(raw),
                     Resolution='800x600',RawPath=str(raw_path),PngPath=str(png_path),
                     Stage='fixture-validation',CandidateSha256='a'*64,Passed=False)
        current=copy.deepcopy(summary)
        def read_bytes(p):
            return {path:json.dumps(current).encode(),raw_path:raw,png_path:b'virtual PNG'}[p]
        with patch.object(Path,'read_bytes',autospec=True,side_effect=read_bytes), \
             patch.object(audit,'bind_screenshot',return_value={'fixture_binding':True}) as binding:
            result=audit.audit_summary(path,self.frame)
            self.assertTrue(result['passed'])
            self.assertFalse(result['existing_surface_gate_passed'])
            self.assertEqual(result['candidate_sha256'],'a'*64)
            for key in ('RawBytes','Bytes'):
                for bad in (479999,480001,None,True,480000.0,'480000'):
                    current=copy.deepcopy(summary)
                    (current if key=='RawBytes' else current['Surface'])[key]=bad
                    binding.reset_mock()
                    with self.assertRaisesRegex(ValueError,'raw size differs'):
                        audit.audit_summary(path,self.frame)
                    binding.assert_not_called()


@unittest.skipUnless(RESOURCE.is_file(),'optional user-owned GFX3.RES is unavailable')
class NativeAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resource=RESOURCE.read_bytes()
        cls.frame=audit.load_native_frame(cls.resource)

    def test_exact_native_source_and_opaque_border_partition(self):
        self.assertEqual(self.frame.resource_sha256,audit.RESOURCE_SHA256)
        self.assertEqual(self.frame.member_sha256,audit.MEMBER_SHA256)
        self.assertEqual((self.frame.member_offset,self.frame.member_length),(1884879,89593))
        self.assertEqual(sum(v is not None for v in self.frame.base_pixels),49152)
        before=self.resource
        native=surface(self.frame,FramedViewport(640,480))
        self.assertTrue(audit.audit_surface(bytes(native),FramedViewport(640,480),self.frame)['passed'])
        self.assertEqual(RESOURCE.read_bytes(),before)
        changed=bytearray(before);changed[1884879+4096]^=1
        with self.assertRaisesRegex(ValueError,'identity'):audit.load_native_frame(bytes(changed))

    def test_footer_not_incorporated_into_repeatable_base(self):
        differences=sum(self.frame.base_pixels[(465+y)*640+155+x]!=self.frame.footer.pixels[y*324+x]
                        for y in range(15) for x in range(324))
        self.assertGreater(differences,100)
        layout=FramedViewport(1920,1080)
        base=audit.expected_frame_pixels(self.frame,layout,include_footer=False)
        composed=audit.expected_frame_pixels(self.frame,layout)
        ax,ay=audit.footer_origin(layout)
        self.assertTrue(all(ax<=x<ax+324 and ay<=y<ay+15 for (x,y),v in base.items() if v!=composed[x,y]))


if __name__=='__main__':
    unittest.main()
