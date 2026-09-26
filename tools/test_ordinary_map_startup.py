"""Portable startup-source contracts; no game, debugger, compiler or writes."""
import unittest

import ordinary_map_startup as startup
import ordinary_map_pause_host as pause
import real_exe_smoke as smoke


class StartupSourceTests(unittest.TestCase):
    def test_dimensions_and_slot_zero_controls_are_explicit(self):
        for width,height,x,y in ((640,480,220,158),(1024,768,412,302),(3840,2160,1820,998)):
            with self.subTest(size=(width,height)):
                text=startup.render_source(smoke.HARNESS,width,height)
                self.assertIn(f'main_x={x},main_y={y}',text)
                self.assertIn('point(320,166)',text)
                self.assertNotIn('__SITE_ROWS__',text)
                self.assertIn('reg("eax")!=0||s.word(selected_slot)!=0',text)

    def test_invalid_dimensions_and_source_types_fail(self):
        for width,height in ((True,768),(1024,False),(639,480),(640,479),(4098,768),(1024,2162),(801,600),(800,601)):
            with self.subTest(size=(width,height)),self.assertRaises(ValueError):
                startup.render_source(smoke.HARNESS,width,height)
        for source in (None,b'code',1):
            with self.assertRaises(TypeError):startup.render_source(source,1024,768)

    def test_each_missing_duplicate_or_reapplied_anchor_fails(self):
        for anchor in (startup.SNAPSHOT_ANCHOR,startup.LOADED_ANCHOR,startup.EVENT_ANCHOR):
            for source in (smoke.HARNESS.replace(anchor,'',1),smoke.HARNESS+anchor):
                with self.subTest(anchor=anchor),self.assertRaises(ValueError):
                    startup.render_source(source,1024,768)
        with self.assertRaises(ValueError):
            startup.render_source(startup.render_source(smoke.HARNESS,1024,768),1024,768)

    def test_pause_transform_composes_and_keeps_native_entry_handling(self):
        text=startup.render_source(smoke.HARNESS,1024,768)
        for old,_ in pause.SOURCE_REPLACEMENTS:self.assertEqual(text.count(old),1)
        combined=pause.render_source(text)
        self.assertLess(combined.index('startup.on_event(type,proc,thread,ip)'),combined.index('if (ip==entry && !entered)'))
        self.assertLess(combined.index('REAL_LOADED pid='),combined.index('StartupController startup(s,disk,base);'))
        self.assertIn('PauseLeaseController leases(s,argc==6?argv[5]:nullptr,base);',combined)
        self.assertTrue(startup.render_source(smoke.HARNESS+'// retained note\n',1024,768).endswith('// retained note\n'))

    def test_control_inventory_excludes_gameplay_and_only_retires_owned_breakpoints(self):
        self.assertEqual(set(startup.NATIVE_ANCHORS),set(startup.SITE_NAMES))
        self.assertEqual(len(startup.NATIVE_ANCHORS),15)
        for site in (0x408030,0x4084a0,0x40b0a0,0x40b233,0x406fa0,0x4608f0):
            self.assertNotIn(site,startup.NATIVE_ANCHORS)
        text=startup.CONTROLLER_SOURCE
        self.assertIn('RemoveBreakpoint(removed)',text)
        self.assertNotIn('s.command(',text)
        self.assertNotIn('Execute(',text)
        self.assertIn('write(primary_button,0,1);write(buttons,0)',text)
        self.assertIn('retired=true;',text)
        self.assertIn('if(retired || type!=DEBUG_EVENT_BREAKPOINT)return false;',text)
        self.assertIn('OWNED_STARTUP_RETIRED_SITE',text)
        self.assertIn('remaining=0 slot=0 load_seen=1 load_returned=1',text)

    def test_removed_breakpoints_are_never_released_or_reused(self):
        source=startup.CONTROLLER_SOURCE
        self.assertNotIn('->Release(',source)
        cleanup=source.split('void cleanup() noexcept {',1)[1].split('    ULONG reg(',1)[0]
        retirement=source.split('    void retire() {',1)[1].split('    bool on_event(',1)[0]
        for body in (cleanup,retirement):
            self.assertLess(body.index('site.bp=nullptr;'),body.index('RemoveBreakpoint(removed)'))
            self.assertNotIn('removed->',body)
        self.assertIn('check(s.control->RemoveBreakpoint(removed)',retirement)

    def test_bootstrap_writes_require_matching_native_route_and_identity(self):
        text=startup.CONTROLLER_SOURCE
        for requirement in ('SetMatchThreadId(engine_primary)', 'GetProcessIdOfThread(s.primary_thread)!=s.owned_pid',
                            'process!=engine_process||thread!=engine_primary', 'ip!=owned->address',
                            'GetTickCount64()>=deadline', '++total_hits>50000',
                            'disk_read(disk,site.address,expected.size())!=expected',
                            's.read(site.address,static_cast<ULONG>(expected.size()))!=expected',
                            's.word(reg("esp"))!=0x419c60', 's.word(reg("esp"))!=0x448b74',
                            'reg("esp")!=load_sp+4', 's.word(reg("esp"))!=0x448b79',
                            'startup unexpected widget or notice click'):
            self.assertIn(requirement,text)
        self.assertLess(text.index('Check every source/disk/loaded anchor'),text.index('AddBreakpoint('))
        self.assertIn('address==raw_x||address==raw_y||address==buttons||address==menu_choice||address==menu_exit',text)
        self.assertIn('size==1 && address==primary_button',text)
        self.assertIn('startup memory allowlist',text)
        self.assertNotIn('write(selected_slot',text)
        self.assertNotIn('write(load_accept',text)

    def test_unknown_original_cannot_supply_byte_contracts(self):
        for value in (None,bytearray(100),b'',b'MZ'+bytes(5000)):
            with self.assertRaises(ValueError):startup.verify_original_anchors(value)


if __name__=='__main__':unittest.main(verbosity=2)
