"""Synthetic pixel and retained-cursor regression checks; no game is launched."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_modal_primary_surface_audit as fixtures
import modal_primary_surface_audit as audit
import modal_primary_capture as capture


class CursorRegressionTests(unittest.TestCase):
    def test_half_open_edges_corners_gaps_and_one_pixel_overlaps(self):
        for width, height in ((1024, 768), (1920, 1080), (802, 602)):
            left, top = (width - 640) // 2 + 220, (height - 480) // 2 + 289
            right, bottom = left + 203, top + 120
            cases = (
                (left - 4, top + 20, False), (right, top + 20, False),
                (left + 20, top - 4, False), (left + 20, bottom, False),
                (left - 4, top - 4, False), (right, top - 4, False),
                (left - 4, bottom, False), (right, bottom, False),
                (left - 5, top + 20, False), (right + 1, top + 20, False),
                (left + 20, top - 5, False), (left + 20, bottom + 1, False),
                (left - 3, top + 20, True), (right - 1, top + 20, True),
                (left + 20, top - 3, True), (left + 20, bottom - 1, True),
            )
            for active in (0, 1):
                for x, y, overlap in cases:
                    with self.subTest(resolution=(width, height), active=active, position=(x, y)):
                        samples, route = fixtures.pixel_fixture(width, height, active, (x, y))
                        result = audit.audit_pixels(samples, width, height, route)
                        self.assertTrue(result['passed'], result['failures'])
                        self.assertIs(result['cursor']['rectangle_intersection'], overlap)
                        self.assertIs(result['cursor']['removed_before_placeholder'], bool(active and overlap))

    def test_decoded_sprite_index_survives_all_nine_paired_artifact_ranges(self):
        tiny = fixtures.assets.Sprite(3, 3, (1, None, 2, 3, 4, 5, None, 6, None))
        placeholder = fixtures.assets.Sprite(203, 120, (31,) * (203 * 120))
        oracle = {'mouse': fixtures.s32([tiny]), 'barracks': fixtures.s32([tiny] * 25 + [placeholder])}
        addresses = dict(state=audit.patcher.CURSOR_STATE, descriptor=audit.patcher.CURSOR_STARTUP_DESCRIPTOR,
                        resource=0x28010000, sprite_header=0x28020000, backing_header=0x28030000,
                        backing_pixels=0x28040000, barracks_pointer=0x532144,
                        barracks_resource=0x28050000, placeholder_sprite_header=0x28060000)
        data = {name: bytearray(size) for name, size in audit.CURSOR_READS.items()}
        for offset, value in ((0, 25), (4, 20), (8, addresses['backing_header']), (48, 25), (52, 20),
                              (60, addresses['descriptor']), (64, addresses['resource'])):
            fixtures.put(data['state'], offset, value)
        fixtures.put(data['descriptor'], 12, 4)
        fixtures.put(data['descriptor'], 16, 4)
        fixtures.put(data['resource'], 0, addresses['sprite_header'])
        struct.pack_into('<H', data['resource'], 0x1004, 1)
        data['sprite_header'][:] = audit.sprite_header(oracle['mouse'], 0)[0]
        struct.pack_into('<HH', data['backing_header'], 0, 64, 64)
        fixtures.put(data['backing_header'], 4, addresses['backing_pixels'])
        fixtures.put(data['backing_header'], 184, 0x50EE24)
        fixtures.put(data['barracks_pointer'], 0, addresses['barracks_resource'])
        fixtures.put(data['barracks_resource'], 100, addresses['placeholder_sprite_header'])
        struct.pack_into('<H', data['barracks_resource'], 0x1004, 26)
        data['placeholder_sprite_header'][:] = audit.sprite_header(oracle['barracks'], 25)[0]
        checkpoint = dict(canvas=dict(native=0x30000000, physical=0x31000000,
                                     native_pixels=0x32000000, physical_pixels=0x34000000),
                          values=dict(width=1024, height=768, pixels=0x36000000), core_values={'cursor': 0})
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            receipt = {'reads': {}, 'regions': [dict(address=addresses[name], size=len(raw), state=0x1000, protect=4)
                                               for name, raw in data.items()]}
            for phase in ('before', 'after'):
                receipt['reads'][phase] = {}
                for name, raw in data.items():
                    filename = 'barracks-pointer' if name == 'barracks_pointer' else name
                    receipt['reads'][phase][name] = fixtures.file_receipt(
                        folder / f'cursor-{phase}-{filename}.raw', bytes(raw), addresses[name])
            reader = capture.Artifacts()
            bound = audit.bind_cursor(receipt, folder, reader, oracle, b'', checkpoint)
            reader.unchanged()
            self.assertEqual(len(bound['reads']), 9)
            self.assertEqual(bound['index'], 0)
            self.assertEqual(bound['sprite'], tiny)
            samples, route = fixtures.pixel_fixture()
            for rows in samples.values():
                for row in rows:
                    row['cursor']['index'] = bound['index']
            result = audit.audit_pixels(samples, 1024, 768, route)
            self.assertTrue(result['passed'], result['failures'])
            self.assertEqual(result['cursor']['source_sprite_index'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
