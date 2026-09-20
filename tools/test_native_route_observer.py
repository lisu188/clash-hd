"""Nonexecuting native route observer contract checks."""
import unittest
import native_route_observer as observer
import real_exe_smoke as runtime

class NativeRouteTests(unittest.TestCase):
    def test_native_instrumentation_is_read_only_and_insertion_is_exact(self):
        result=observer.instrument(runtime.HARNESS)
        self.assertIn('ROUTE_ARMED after_initialization=1',result)
        self.assertIn('owner!=s.owned_pid || tid!=s.primary_tid',result)
        self.assertIn('seconds>180',result)
        for text in ('WriteVirtual(','.call ','SetThreadContext('):self.assertNotIn(text,result)
        with self.assertRaises(ValueError):observer.instrument(result)

    def test_callbacks_require_exact_order_thread_and_site(self):
        lines=[f'ROUTE_NATIVE event={name} ip={address:08x} tid=25 raw_x=416 raw_y=329 game_data=01111000'
               for name,address in observer.SITES.items()]
        self.assertEqual(len(observer.parse('\n'.join(lines))),3)
        for changed in (lines[::-1],lines+[lines[0]],lines[:1]+[lines[1].replace('tid=25','tid=26')],
                        [lines[0].replace('00447700','00447701')],[' prefix '+lines[0]]):
            with self.subTest(lines=changed),self.assertRaises(ValueError):observer.parse('\n'.join(changed))

if __name__=='__main__':unittest.main(verbosity=2)
