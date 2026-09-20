import struct
import unittest
import launcher_display_mode as tool


def data(width, height, depth=32, frequency=60):
    value=bytearray(220);struct.pack_into('<H',value,68,220)
    struct.pack_into('<5I',value,168,depth,width,height,0,frequency)
    return bytes(value)


class FakeModes:
    def __init__(self, available=(), test_result=0, apply_result=0):
        self.original=data(1024,768);self.current=self.original;self.available=available
        self.test_result=test_result;self.apply_result=apply_result;self.calls=[]
    def read(self,index):
        return self.current if index==-1 else self.available[index] if index<len(self.available) else None
    def apply(self,value,flags):
        self.calls.append((value,flags))
        if flags==2:return self.test_result
        if value==self.original:self.current=value;return 0
        if self.apply_result==0:self.current=value
        return self.apply_result


class DisplayTests(unittest.TestCase):
    def test_exact_win32_fields_and_smallest_containing_mode(self):
        modes=[tool.mode_values(data(*size)) for size in ((3840,2160),(1920,1080),(2560,1440),(3440,1440))]
        self.assertEqual(tool.select_mode(modes,1920,1080),1)
        self.assertEqual(tool.select_mode(modes,3440,1440),3)
        self.assertEqual(tool.select_mode(modes,3840,2160),0)
        self.assertIsNone(tool.select_mode(modes[:0],1280,720))
        for width,height in ((True,600),(800,599),(3841,2160)):
            with self.assertRaises(ValueError):tool.select_mode(modes,width,height)
        for raw in (bytes(219),bytes(220),data(800,600)+b'x'):
            with self.assertRaises(ValueError):tool.mode_values(raw)

    def test_no_change_when_original_mode_already_fits(self):
        api=FakeModes()
        with tool.temporary_display(800,600,api=api) as report:
            self.assertTrue(report['adequate']);self.assertFalse(report['changed'])
        self.assertTrue(report['restored']);self.assertEqual(api.calls,[])

    def test_selected_mode_is_tested_then_applied_and_restored_without_registry(self):
        api=FakeModes([data(3840,2160),data(1920,1080)])
        with tool.temporary_display(1920,1080,api=api) as report:
            self.assertTrue(report['adequate']);self.assertEqual(tool.mode_values(api.current)['width'],1920)
        self.assertTrue(report['restored']);self.assertEqual(api.current,api.original)
        self.assertEqual([flags for _,flags in api.calls],[2,0,0])
        self.assertFalse(report['registry_modified'])

    def test_unavailable_or_failed_modes_never_claim_suitable_display(self):
        for api in (FakeModes(),FakeModes([data(3840,2160)],test_result=-2),FakeModes([data(3840,2160)],apply_result=-1)):
            with tool.temporary_display(1920,1080,api=api) as report:
                self.assertFalse(report['adequate']);self.assertFalse(report['changed'])
            self.assertTrue(report['restored'])

    def test_original_restored_even_when_game_observation_raises(self):
        api=FakeModes([data(1920,1080)])
        with self.assertRaisesRegex(RuntimeError,'game'):
            with tool.temporary_display(1920,1080,api=api) as report:
                raise RuntimeError('game observation failure')
        self.assertTrue(report['restored']);self.assertEqual(api.current,api.original)


if __name__=='__main__':unittest.main(verbosity=2)
