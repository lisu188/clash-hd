"""Independent literal placement/count fixtures, with synthetic buffers only."""
from pathlib import Path
import hashlib
import unittest

import framed_modal_mirror_audit as audit

# Literal independent geometry, including both axes of the fractional802 case.
POSITIONS={(800,600):(80,60),(1024,768):(192,144),(1280,720):(320,120),
           (1280,960):(320,240),(1920,1080):(640,300),(802,602):(81,61)}


def fixture(width,height,source=None):
    if source is None:source=bytes((x*13+y*7)%251 for y in range(480) for x in range(640))
    left,top=POSITIONS[width,height]
    target=bytearray(width*height)
    for y in range(480):
        start=(top+y)*width+left
        target[start:start+640]=source[y*640:(y+1)*640]
    return source,bytes(target)


class MirrorTests(unittest.TestCase):
    def test_all_six_exact_copies_with_independent_literal_geometry(self):
        for (w,h),(x,y) in POSITIONS.items():
            with self.subTest(resolution=(w,h)):
                native,physical=fixture(w,h)
                r=audit.audit_mirror(native,physical,width=w,height=h,stage=audit.STAGE)
                self.assertTrue(r['passed']);self.assertTrue(r['input_valid'])
                self.assertEqual(r['native_rect_in_physical'],[x,y,x+639,y+479])
                self.assertEqual(r['counts']['native_pixels_matched'],307200)
                self.assertEqual(r['counts']['margin_pixels_zero'],w*h-307200)
                self.assertEqual(r['counts']['total_mismatches'],0)
                self.assertEqual(r['native_sha256'],hashlib.sha256(native).hexdigest())
                self.assertEqual(r['physical_sha256'],hashlib.sha256(physical).hexdigest())
                self.assertTrue(r['native_content_bearing']);self.assertEqual(r['mismatch_coordinates'],[])
                for key in ('visual_proof','controls_proof','manual_input_proof','promotion_ready','runtime_binding_verified'):
                    self.assertFalse(r[key])

    def test_exact_counts_cover_both_native_corners_and_all_four_margins(self):
        w,h=1024,768;native,original=fixture(w,h);physical=bytearray(original)
        inside=((192,144),(831,623));outside=((0,0),(1023,0),(0,767),(1023,767))
        for x,y in inside:physical[y*w+x]^=255
        for x,y in outside:physical[y*w+x]=17
        r=audit.audit_mirror(native,bytes(physical),width=w,height=h,stage=audit.STAGE)
        self.assertFalse(r['passed']);self.assertTrue(r['input_valid'])
        self.assertEqual(r['counts']['native_copy_mismatches'],2)
        self.assertEqual(r['counts']['margin_nonzero_pixels'],4)
        self.assertEqual(r['counts']['total_mismatches'],6)
        self.assertEqual({(x['x'],x['y']) for x in r['mismatch_coordinates']},set(inside+outside))
        self.assertEqual(native,fixture(w,h)[0]);self.assertEqual(original,fixture(w,h)[1])

    def test_coordinate_limit_never_truncates_exact_comparison_counts(self):
        native=bytes(307200);physical=bytes([1])*(800*600)
        for limit in (0,1,16,64):
            r=audit.audit_mirror(native,physical,width=800,height=600,stage=audit.STAGE,coordinate_limit=limit)
            self.assertEqual(r['counts']['native_copy_mismatches'],307200)
            self.assertEqual(r['counts']['margin_nonzero_pixels'],172800)
            self.assertEqual(r['counts']['total_mismatches'],480000)
            self.assertEqual(len(r['mismatch_coordinates']),limit)

    def test_all_zero_relation_pass_is_separate_from_content_and_visual_proof(self):
        for value in (0,7):
            native,physical=fixture(800,600,bytes([value])*307200)
            r=audit.audit_mirror(native,physical,width=800,height=600,stage=audit.STAGE)
            self.assertTrue(r['mirror_relation_passed'])
            self.assertFalse(r['native_content_bearing']);self.assertFalse(r['visual_proof'])
            self.assertEqual(r['native_content']['all_zero'],value==0)
            self.assertFalse(r['native_content']['has_variation'])

    def test_packed_wrong_pitch_or_shifted_rectangle_is_not_a_match(self):
        native,physical=fixture(1024,768)
        wrong=bytearray(1024*768);wrong[:len(native)]=native
        for bad in (bytes(wrong),physical[1:]+b'\0'):
            r=audit.audit_mirror(native,bad,width=1024,height=768,stage=audit.STAGE)
            self.assertFalse(r['passed']);self.assertGreater(r['counts']['native_copy_mismatches'],0)
            self.assertGreater(r['counts']['margin_nonzero_pixels'],0)

    def test_invalid_geometry_stage_lengths_types_and_limits_fail_with_unknown_counts(self):
        native,physical=fixture(800,600)
        changes=[dict(width=640,height=480),dict(width=1024,height=600),dict(width=True),
                 dict(stage=audit.STAGE.replace('-modalcanvas','')),dict(stage=None),
                 dict(coordinate_limit=-1),dict(coordinate_limit=65),dict(coordinate_limit=True)]
        for change in changes:
            r=audit.audit_mirror(native,physical,**(dict(width=800,height=600,stage=audit.STAGE)|change))
            self.assertFalse(r['passed']);self.assertFalse(r['input_valid']);self.assertIsNone(r['counts'])
        for a,b in ((native[:-1],physical),(native+b'\0',physical),(native,physical[:-1]),
                    (native,physical+b'\0'),(bytearray(native),physical),(native,None)):
            r=audit.audit_mirror(a,b,width=800,height=600,stage=audit.STAGE)
            self.assertFalse(r['passed']);self.assertIsNone(r['counts'])

    def test_independent_stage_literal_matches_current_builder_without_importing_emitter_in_oracle(self):
        import build_framed_modal_candidate as builder
        self.assertEqual(audit.STAGE,builder.STAGE)
        source=Path(audit.__file__).read_text(encoding='utf-8')
        self.assertNotIn('import framed_modal_canvas',source)
        self.assertNotIn('import build_framed',source)


if __name__=='__main__':unittest.main()
