"""Portable source-transform checks; no compilation, target or debugger launch."""
from __future__ import annotations

import unittest
import re

import ordinary_map_pause_host as host
import real_exe_smoke


class PauseHostSourceTests(unittest.TestCase):
    def test_only_declared_source_changes_are_applied(self):
        original = real_exe_smoke.HARNESS
        rendered = host.render_source(original)
        self.assertIs(original, real_exe_smoke.HARNESS)
        for old, new in reversed(host.SOURCE_REPLACEMENTS):
            self.assertEqual(rendered.count(new), 1)
            rendered = rendered.replace(new, old, 1)
        self.assertEqual(rendered, original)

    def test_each_missing_anchor_fails_closed(self):
        for old, _new in host.SOURCE_REPLACEMENTS:
            with self.subTest(anchor=old), self.assertRaisesRegex(ValueError, 'anchor'):
                host.render_source(real_exe_smoke.HARNESS.replace(old, '', 1))

    def test_each_duplicated_anchor_fails_closed(self):
        for old, _new in host.SOURCE_REPLACEMENTS:
            with self.subTest(anchor=old), self.assertRaisesRegex(ValueError, 'anchor'):
                host.render_source(real_exe_smoke.HARNESS + old)

    def test_second_application_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'already contains'):
            host.render_source(host.render_source(real_exe_smoke.HARNESS))

    def test_non_source_input_is_rejected(self):
        for value in (None, b'code', 42):
            with self.subTest(value=value), self.assertRaises(TypeError):
                host.render_source(value)

    def test_unrelated_source_text_is_preserved(self):
        original = real_exe_smoke.HARNESS + '\n// independent harness annotation\n'
        self.assertTrue(host.render_source(original).endswith('// independent harness annotation\n'))

    def test_legacy_invocation_keeps_control_disabled(self):
        rendered = host.render_source(real_exe_smoke.HARNESS)
        self.assertIn('if (argc!=5 && argc!=6) return 2;', rendered)
        self.assertIn('PauseLeaseController leases(s,argc==6?argv[5]:nullptr,base);', rendered)
        constructor = host.CONTROLLER_SOURCE.split('PauseLeaseController(Session &owner,', 1)[1]
        self.assertLess(constructor.index('if (!control_directory) return;'),
                        constructor.index('enabled=true;'))
        self.assertIn('if (!enabled || ready_published || !entered) return;', rendered)
        self.assertIn('if (!enabled || !ready_published) return;', rendered)

    def test_entry_readiness_and_loop_service_are_at_owned_boundaries(self):
        rendered = host.render_source(real_exe_smoke.HARNESS)
        main = rendered.split('int main(int argc,char **argv) {', 1)[1]
        self.assertLess(main.index('REAL_LOADED'), main.index('PauseLeaseController leases'))
        self.assertIn('leases.service();\n            HRESULT hr=s.control->WaitForEvent(0,1000);', main)
        self.assertIn('"continue actual code");\n                leases.publish_ready(entered);', main)
        self.assertEqual(main.count('leases.publish_ready('), 1)
        self.assertLess(main.index('entered=true;'), main.index('leases.publish_ready(entered);'))

    def test_ack_payload_is_encoded_written_and_flushed_once_before_shared_replace(self):
        ack=host.CONTROLLER_SOURCE.split('    void ack(',1)[1].split('    void publish_ready(',1)[0]
        self.assertEqual(set(re.findall(r'\\"([a-z_0-9]+)\\":',ack)),set(
            'schema session_id request_seq status lease_id pid primary_tid creation_filetime image_base deadline_tick_ms paused'.split()))
        for operation in ('sprintf_s(', 'WriteFile(', 'FlushFileBuffers(', 'replace_ack('):
            self.assertEqual(ack.count(operation),1)
        self.assertLess(ack.index('FlushFileBuffers('),ack.index('temporary.close();'))
        self.assertLess(ack.index('temporary.close();'),ack.index('replace_ack('))
        self.assertIn('replace_ack("ack.json",json,static_cast<DWORD>(count),last_sequence,deadline,publication_bound)',ack)
        self.assertNotIn('for (',ack)
        self.assertNotIn('MoveFileExA(',ack)

    def test_retry_is_only_for_actual_atomic_replace_access_or_sharing_denial(self):
        helper=host.CONTROLLER_SOURCE.split('    void replace_ack(',1)[1].split('    void ack(',1)[0]
        self.assertEqual(helper.count('MoveFileExA('),1)
        self.assertIn('MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH',helper)
        error=helper.split('DWORD error=GetLastError();',1)[1]
        self.assertLess(error.index('error!=ERROR_ACCESS_DENIED && error!=ERROR_SHARING_VIOLATION'),
                        error.index('++attempt;'))
        self.assertLess(error.index('throw std::runtime_error'),error.index('REAL_ACK_REPLACE_RETRY'))
        self.assertIn('name,sequence,attempt,error,bound); fflush(stdout);',error)
        for forbidden in ('catch(', 'catch (', 'WriteFile(', 'FlushFileBuffers(', 'sprintf_s(', 'SetLastError('):
            self.assertNotIn(forbidden,helper)

    def test_publication_deadline_is_fixed_capped_and_only_uses_applicable_bounds(self):
        helper=host.CONTROLLER_SOURCE.split('    void replace_ack(',1)[1].split('    void ack(',1)[0]
        setup,loop=helper.split('for (;;) {',1)
        self.assertIn('now>~static_cast<ULONGLONG>(0)-1000',setup)
        self.assertIn('ULONGLONG bound=now+1000;',setup)
        self.assertIn('if (until && until<bound) bound=until;',setup)
        self.assertIn('if (publication_bound && publication_bound<bound) bound=publication_bound;',setup)
        self.assertNotRegex(loop,r'\bbound\s*=')
        self.assertNotIn('transition_deadline',helper)
        self.assertNotIn('held_deadline',helper)
        self.assertGreaterEqual(loop.count('replace_deadline(name,started,bound,attempt);'),4)
        self.assertLess(loop.index('replace_deadline('),loop.index('MoveFileExA('))
        self.assertIn('if (now>=bound)',loop)
        self.assertIn('bound-now<10?bound-now:10',loop)
        deadline=host.CONTROLLER_SOURCE.split('    static void replace_deadline(',1)[1].split('    static BY_HANDLE_FILE_INFORMATION',1)[0]
        self.assertIn('if (now>=bound)',deadline)
        self.assertIn('REAL_ACK_REPLACE_EXPIRED',deadline)
        self.assertIn('fflush(stdout);',deadline)
        self.assertIn('throw std::runtime_error',deadline)

    def test_each_attempt_rechecks_owner_token_paths_and_exact_pinned_payload(self):
        helper=host.CONTROLLER_SOURCE.split('    void replace_ack(',1)[1].split('    void ack(',1)[0]
        loop=helper.split('for (;;) {',1)[1]
        before_move=loop.split('if (MoveFileExA(',1)[0]
        for requirement in ('verify_owner(); verify_token();', 'absent_or_regular(destination,false);',
                            'absent_or_regular(temporary,false);', 'FILE_SHARE_READ|FILE_SHARE_DELETE',
                            'FILE_FLAG_OPEN_REPARSE_POINT', 'verify_ack_bytes(checked.value,expected,size)'):
            self.assertIn(requirement,before_move)
        self.assertNotIn('FILE_SHARE_WRITE',helper)
        verify=host.CONTROLLER_SOURCE.split('    static BY_HANDLE_FILE_INFORMATION verify_ack_bytes(',1)[1].split('    void replace_ack(',1)[0]
        for requirement in ('GetFileType(file)!=FILE_TYPE_DISK', 'GetFileInformationByHandle(file,&info)',
                            'FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT', 'info.nFileSizeHigh',
                            'info.nFileSizeLow!=size', 'got!=size', 'memcmp(bytes.data(),expected,size)'):
            self.assertIn(requirement,verify)
        self.assertIn('throw std::runtime_error',verify)
        self.assertNotIn('catch',verify)

    def test_published_payload_and_file_identity_are_verified_before_success(self):
        helper=host.CONTROLLER_SOURCE.split('    void replace_ack(',1)[1].split('    void ack(',1)[0]
        success=helper.split('if (MoveFileExA(',1)[1].split('DWORD error=GetLastError();',1)[0]
        for requirement in ('verify_owner(); verify_token();', 'absent_or_regular(destination,false);',
                            'verify_ack_bytes(published.value,expected,size)',
                            'info.dwVolumeSerialNumber!=final_info.dwVolumeSerialNumber',
                            'info.nFileIndexHigh!=final_info.nFileIndexHigh',
                            'info.nFileIndexLow!=final_info.nFileIndexLow'):
            self.assertIn(requirement,success)
        self.assertLess(success.index('published file identity changed'),success.index('return;'))
        self.assertLess(success.index('replace_deadline('),success.index('return;'))
        self.assertNotIn('checked.close()',success)

    def test_resumed_payload_retains_zero_deadline_but_publication_uses_current_lease_bound(self):
        source=host.CONTROLLER_SOURCE
        self.assertIn('ack("ready","",0,false);',source)
        self.assertIn('ack("paused",initial.lease,deadline,true);',source)
        self.assertIn('accept(next); ack("resumed",initial.lease,0,false,deadline); return;',source)
        self.assertIn('ULONGLONG deadline=GetTickCount64()+20000;',source)


if __name__ == '__main__':
    unittest.main()
