"""Read-only cursor decoding and native-input opt-in boundaries."""
from contextlib import redirect_stderr
import io
import struct
import sys
import unittest
from unittest.mock import patch
import runner_menu_input as tool


class CursorFeedbackTests(unittest.TestCase):
    def test_native_coordinates_decode_without_animation_or_image_inference(self):
        for width,height in ((802,602),(1024,768),(3840,2160)):
            for point in ((0,0),(320,365),(width-1,height-1)):
                for shift in range(5):
                    raw=struct.pack('<ii',point[0]<<shift,point[1]<<shift)
                    self.assertEqual(tool.decode_cursor(raw,bytes([shift]),(width,height)),point)

    def test_invalid_or_incomplete_coordinate_reads_fail_closed(self):
        for raw,shift in ((b'bad',b'\0'),(bytes(8),b''),(bytes(8),b'\x05'),
                          (struct.pack('<ii',-1,0),b'\0'),(struct.pack('<ii',1024,0),b'\0')):
            with self.subTest(raw=raw,shift=shift),self.assertRaises(ValueError):
                tool.decode_cursor(raw,shift,(1024,768))

    def test_owned_foreground_pairs_are_unique_and_never_self_attached(self):
        self.assertEqual(tool.attach_pairs(1,2,3),[(1,2),(1,3)])
        self.assertEqual(tool.attach_pairs(1,2,2),[(1,2)])
        self.assertEqual(tool.attach_pairs(1,1,2),[(1,2)])
        self.assertEqual(tool.attach_pairs(1,0,1),[])

    def test_feedback_flag_does_not_bypass_approval_or_disposable_runner_boundary(self):
        for flags in (['--engine-coordinate-feedback'],['--engine-coordinate-feedback','--approval-text','test','--owner-creation','1']):
            with patch.object(sys,'argv',['test',*flags]),patch.object(tool.owned,'win32',side_effect=AssertionError('no native access')),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:
                tool.main()
            self.assertEqual(error.exception.code,2)


if __name__=='__main__':unittest.main(verbosity=2)
