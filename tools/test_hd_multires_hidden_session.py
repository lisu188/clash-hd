"""Hidden-session source/policy tests and separately opted-in native job check."""
from __future__ import annotations

import argparse
import ctypes
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import hd_multires_hidden_session as session
import hd_multires_win32 as native

NATIVE = False


class PolicyTests(unittest.TestCase):
    def test_fixed_ladder_durations_and_map_pending_are_not_a_free_duration_override(self):
        self.assertEqual(session.ROUTES["menu-idle"], (120,))
        self.assertEqual(session.ROUTES["map-idle"], (120, 600, 7200))
        self.assertEqual(session.ROUTES["map-pan"], (600, 1800, 7200))
        with self.assertRaisesRegex(ValueError, "fixed short-ladder"):
            session.plan(Path("missing.json"), duration=1)
        with self.assertRaisesRegex(ValueError, "either initial smoke"):
            session.plan(Path("missing.json"), smoke_only=True, acquire_only=True)
        with patch.object(session, "stage_assets", side_effect=AssertionError("must not copy")), \
                patch.object(session, "HiddenJob", side_effect=AssertionError("must not create process")):
            with self.assertRaisesRegex(ValueError, "not implemented"):
                session.execute({"pending": ["map collector is not implemented"]}, {}, {}, {}, [],
                    output_root=Path("unused"), asset_root=Path("unused"))

    def test_commands_use_exact_canonical_probe_then_observation_only_rebased_one_shots(self):
        prefix = b"CANONICAL_PROBE_BYTES\r\n"
        script = session.command_script(prefix, {}, {"probe_contract": {"required_chunks": 47}})
        self.assertTrue(script.startswith(prefix))
        suffix = script[len(prefix):].decode()
        self.assertIn("@$t18 != 0n47", suffix)
        self.assertIn("bp /1 @$t19+0x47d61", suffix)
        self.assertIn("bp /1 @$t19+0x7bd6f", suffix)
        self.assertIn("bp /1 @$t19+0x7bdb7", suffix)
        self.assertNotIn("bp /1 @$t19+0x7bd66", suffix)
        self.assertNotIn("bp /1 @$t19+0x7bdae", suffix)
        self.assertIn("@eax", suffix)
        self.assertNotIn("2048", suffix)
        self.assertNotIn("800", suffix)
        for forbidden in ("r eip", "r eax", "r esp", "ed ", "eb ", "SendInput", "PostMessage"):
            self.assertNotIn(forbidden, suffix)
        smoke = session.command_script(prefix, {}, {"probe_contract": {"required_chunks": 47}}, smoke_only=True)
        self.assertNotIn(b"HDSESSION_MENU_READY", smoke)
        self.assertIn(b".sleep 0n300000", smoke)  # Host binds retained target before terminating its own job.
        acquisition = session.command_script(prefix, {}, {"probe_contract": {"required_chunks": 47}}, acquire_only=True)
        self.assertIn(b'.if ((@eax & 0x80000000) != 0)', acquisition)
        self.assertNotIn(b'r eax', acquisition)
        self.assertNotIn(b'r eip', acquisition)

    def test_markers_cannot_be_forged_by_echoed_commands_duplicates_or_wrong_geometry(self):
        identity, metadata = {"resolution": "3840x2160"}, {"probe_contract": {"acceptance_marker": "EXACT_CANONICAL_PASS"}}
        self.assertFalse(session.parse_observations('.echo EXACT_CANONICAL_PASS\n', identity, metadata)["initial_image_bytes_verified"])
        self.assertFalse(session.parse_observations('EXACT_CANONICAL_PASS\nEXACT_CANONICAL_PASS\n', identity, metadata)["initial_image_bytes_verified"])
        log = 'EXACT_CANONICAL_PASS\nHDSESSION_TARGET pid=abc base=00400000\n'
        menu = 'HDSESSION_MENU_READY pid=abc surface=0051d4c0 width=3840 height=2160 pixels=20000000\n'
        actual = session.parse_observations(log + menu, identity, metadata)
        self.assertFalse(actual["failures"])
        self.assertEqual(actual["menu"]["width"], 3840)
        for bad in (menu.replace('3840', '2048'), menu.replace('pid=abc', 'pid=ddd'), menu + menu):
            self.assertTrue(session.parse_observations(log + bad, identity, metadata)["failures"])
        self.assertTrue(session.parse_observations(log + 'HDSESSION_APP_REQUEST_QUIT\n', identity, metadata)["failures"])

    def test_acquisition_returns_bind_real_postcall_pcs_and_preserve_failed_hresult(self):
        identity, metadata = {"resolution": "1920x1080"}, {"probe_contract": {"acceptance_marker": "EXACT_CANONICAL_PASS"}}
        target = 'EXACT_CANONICAL_PASS\nHDSESSION_TARGET pid=abc base=00400000\n'
        mouse = ('HDSESSION_ACQUIRE_BEGIN_mouse\n'
            'HDSESSION_ACQUIRE kind=mouse pid=abc pc=0047bd6f hr=0x80070005 hwnd=00012345 device=03000000\n'
            'HDSESSION_ACQUIRE_END_mouse\n')
        keyboard = ('HDSESSION_ACQUIRE_BEGIN_keyboard\n'
            'HDSESSION_ACQUIRE kind=keyboard pid=abc pc=0047bdb7 hr=0x00000000 hwnd=00012345 device=03000100\n'
            'HDSESSION_ACQUIRE_END_keyboard\n')
        actual = session.parse_observations(target + mouse + keyboard, identity, metadata)
        self.assertFalse(actual["failures"])
        self.assertEqual(actual["acquisition_returns"][0]["hresult"], 0x80070005)
        self.assertTrue(actual["acquisition_returns"][0]["failed_hresult"])
        self.assertFalse(actual["acquisition_returns"][1]["failed_hresult"])
        for bad in (mouse.replace('0047bd6f', '0047bd66'), mouse.replace('pid=abc', 'pid=ddd'), mouse + mouse):
            self.assertTrue(session.parse_observations(target + bad, identity, metadata)["failures"])
        incomplete = mouse.removesuffix('HDSESSION_ACQUIRE_END_mouse\n')
        self.assertFalse(session.parse_observations(target + incomplete, identity, metadata)["acquisition_returns"])
        split = mouse.replace('pid=abc', 'pid=*** WARNING: Unable to verify checksum for clash95.exe\nabc')
        self.assertFalse(session.parse_observations(target + split, identity, metadata)["acquisition_returns"])

    def test_fixed_asset_selection_excludes_tools_output_reverse_and_wrappers(self):
        with tempfile.TemporaryDirectory(prefix="clash-runtime-inventory-") as directory:
            root = Path(directory)
            for name in (*session.ASSET_FILES, "DATA/GFX3.RES", "DATA/main.wav", "AVI/intro.avi", "GFX/CACHE/cell.s32",
                         "save/2.dat", "save/2.fac", "DATA/output/copied.res", "DATA/ImageMagick/tool.exe", "reverse/dump.res", "ddraw.dll"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
            actual = {row["path"] for row in session.asset_inventory(root)}
            self.assertTrue({"DATA/GFX3.RES", "save/2.dat", "AVI/intro.avi"} <= actual)
            self.assertFalse(actual & {"DATA/output/copied.res", "DATA/ImageMagick/tool.exe", "reverse/dump.res", "ddraw.dll"})

    def test_actual_launched_artifacts_are_rehashed_not_trusted_from_the_bundle(self):
        with tempfile.TemporaryDirectory(prefix="clash-launch-binding-") as directory:
            path = Path(directory) / "candidate.exe"
            path.write_bytes(b"original staged bytes")
            refs = {"candidate": dict(path=str(path), sha256=session._sha(path.read_bytes()))}
            self.assertTrue(session.verify_launch_artifacts(refs))
            path.write_bytes(b"changed staged bytes")
            with self.assertRaisesRegex(ValueError, "launched artifact changed"):
                session.verify_launch_artifacts(refs)

    def test_mutable_staged_files_cannot_be_hardlinks_to_live_state(self):
        import json
        with tempfile.TemporaryDirectory(prefix="clash-stage-links-") as directory:
            root = Path(directory)
            staged = root / "staged"
            staged.mkdir(); (staged / "save").mkdir()
            live = root / "live.cfg"
            live.write_bytes(b"owned synthetic live state")
            os.link(live, staged / "CLASH.CFG")
            rows = [dict(path="CLASH.CFG", bytes=live.stat().st_size)]
            manifest = dict(schema="hd_multires_isolated_assets_v1", source=str(session.GAME),
                files=[rows[0] | {"sha256": session._sha(live.read_bytes())}])
            (staged / "asset-stage.json").write_text(json.dumps(manifest))
            with patch.object(session, "_external", return_value=staged):
                with self.assertRaisesRegex(ValueError, "non-linked file"):
                    session.stage_assets(staged, rows)
            self.assertEqual(live.read_bytes(), b"owned synthetic live state")

    def test_unlisted_save_created_after_staging_cannot_redirect_live_state(self):
        import json
        with tempfile.TemporaryDirectory(prefix="clash-stage-new-save-") as directory:
            root = Path(directory)
            staged = root / "staged"
            staged.mkdir(); (staged / "save").mkdir()
            live = root / "live.dat"
            live.write_bytes(b"owned synthetic live state")
            os.link(live, staged / "save" / "new-unlisted.dat")
            manifest = dict(schema="hd_multires_isolated_assets_v1", source=str(session.GAME), files=[])
            (staged / "asset-stage.json").write_text(json.dumps(manifest))
            with patch.object(session, "_external", return_value=staged):
                with self.assertRaisesRegex(ValueError, "non-linked file"):
                    session.stage_assets(staged, [])
            self.assertEqual(live.read_bytes(), b"owned synthetic live state")


class FakeKernel:
    def __init__(self, fail_assign=False):
        self.fail_assign, self.assigned, self.resumed, self.terminated = fail_assign, False, False, False
        self.path = ""
    def CreateJobObjectW(self, *args): return 10
    def SetInformationJobObject(self, *args): return True
    def QueryInformationJobObject(self, job, kind, value, *args):
        if kind == 9: value._obj.basic.flags = 0x2000
        else: value._obj.active = 0
        return True
    def CreateProcessW(self, image, *args):
        self.path = image
        info = args[-1]._obj
        info.process, info.thread, info.pid, info.tid = 30, 31, 1001, 1002
        return True
    def AssignProcessToJobObject(self, *args):
        self.assigned = not self.fail_assign
        return self.assigned
    def QueryFullProcessImageNameW(self, handle, flags, output, length):
        output.value = self.path
        return True
    def GetProcessTimes(self, handle, *times):
        times[0]._obj.dwLowDateTime = 123
        return True
    def IsProcessInJob(self, process, job, answer):
        answer._obj.value = self.assigned
        return True
    def ResumeThread(self, handle):
        if not self.assigned: raise AssertionError("resumed before job membership")
        self.resumed = True
        return 1
    def TerminateProcess(self, *args): self.terminated = True; return True
    def TerminateJobObject(self, *args): return True
    def WaitForSingleObject(self, *args): return 0
    def CloseHandle(self, *args): return True


class FakeUser:
    def CreateDesktopW(self, *args): return 20
    def CloseDesktop(self, *args): return True


class OwnershipTests(unittest.TestCase):
    def test_suspended_process_is_identified_and_assigned_before_first_resume(self):
        kernel = FakeKernel()
        with patch.object(native, "_api", return_value=(kernel, FakeUser(), object())):
            job = native.HiddenJob().open()
            _, identity = job.spawn(Path("python.exe").resolve(), [], Path.cwd(), {"CLASH_PROXY_PRESENT": "0"})
            self.assertTrue(kernel.resumed)
            self.assertTrue(identity["task_job_member"])
            self.assertLess(job.events.index("process_membership_and_generation_verified"), job.events.index("process_resumed"))
            self.assertTrue(job.close()["cleanup_verified"])

    def test_failed_assignment_never_resumes_and_stops_only_the_just_created_process(self):
        kernel = FakeKernel(fail_assign=True)
        with patch.object(native, "_api", return_value=(kernel, FakeUser(), object())):
            job = native.HiddenJob().open()
            with self.assertRaises(OSError):
                job.spawn(Path("python.exe").resolve(), [], Path.cwd(), {})
            self.assertFalse(kernel.resumed)
            self.assertTrue(kernel.terminated)
            self.assertTrue(job.close()["cleanup_verified"])

    def test_empty_job_cannot_hide_failed_cleanup_of_an_unassigned_process(self):
        kernel = FakeKernel(fail_assign=True)
        kernel.TerminateProcess = lambda *args: False
        kernel.WaitForSingleObject = lambda *args: 258
        with patch.object(native, "_api", return_value=(kernel, FakeUser(), object())):
            job = native.HiddenJob().open()
            with self.assertRaises(OSError):
                job.spawn(Path("python.exe").resolve(), [], Path.cwd(), {})
            cleanup = job.close()
            self.assertTrue(cleanup["task_job_drained"])
            self.assertFalse(cleanup["cleanup_verified"])
            self.assertTrue(any("unsignaled" in error for error in cleanup["errors"]))


class NativeOwnershipTests(unittest.TestCase):
    def test_hidden_synthetic_cmd_has_verified_job_generation_and_cleanup(self):
        if not NATIVE or os.name != "nt":
            self.skipTest("explicit --native owns this small Windows process")
        job = native.HiddenJob().open()
        try:
            handle, identity = job.spawn(Path(os.environ["SystemRoot"]) / "System32/cmd.exe",
                ["/d", "/c", "exit", "0"], Path(os.environ["SystemRoot"]), dict(os.environ, CLASH_PROXY_PRESENT="0"))
            self.assertTrue(identity["task_job_member"])
            self.assertGreater(identity["creation_filetime"], 0)
        finally:
            cleanup = job.close()
        self.assertTrue(cleanup["cleanup_verified"], cleanup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", action="store_true")
    args, rest = parser.parse_known_args()
    NATIVE = args.native
    unittest.main(argv=[sys.argv[0], *rest])
