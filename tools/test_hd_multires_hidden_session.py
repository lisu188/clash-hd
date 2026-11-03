"""Hidden-session source/policy tests and separately opted-in native job check."""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import io
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import hd_multires_hidden_session as session
import hd_multires_win32 as native

NATIVE = False


class PolicyTests(unittest.TestCase):
    def test_fixed_ladder_durations_and_pending_plans_are_not_a_free_duration_override(self):
        self.assertEqual(session.ROUTES["menu-idle"], (120,))
        self.assertEqual(session.ROUTES["map-idle"], (120, 600, 7200))
        self.assertEqual(session.ROUTES["map-pan"], (600, 1800, 7200))
        with self.assertRaisesRegex(ValueError, "fixed short-ladder"):
            session.plan(Path("missing.json"), duration=1)
        with self.assertRaisesRegex(ValueError, "fixed short-ladder"):
            session.plan(Path("missing.json"), route="map-pan", duration=120)
        with self.assertRaisesRegex(ValueError, "either initial smoke"):
            session.plan(Path("missing.json"), smoke_only=True, acquire_only=True)
        for option in ("smoke_only", "acquire_only"):
            with self.assertRaisesRegex(ValueError, "observation-only menu route"):
                session.plan(Path("missing.json"), route="map-idle", **{option: True})
        with patch.object(session, "stage_assets", side_effect=AssertionError("must not copy")), \
                patch.object(session, "HiddenJob", side_effect=AssertionError("must not create process")):
            with self.assertRaisesRegex(ValueError, "not implemented"):
                session.execute({"pending": ["collector is not implemented"]}, {}, {}, {}, [],
                    output_root=Path("unused"), asset_root=Path("unused"))

    def test_map_commands_disclose_every_forced_step_after_the_exact_canonical_probe(self):
        prefix = b"CANONICAL_PROBE_BYTES\r\n"
        template = (session.ROOT / session.SOAK_TEMPLATE).read_bytes()
        metadata = {"probe_contract": {"required_chunks": 47}}
        idle = session.map_command_script(prefix, {"resolution": "1920x1080"}, metadata, route="map-idle",
                                          duration=120, soak_template=template)
        self.assertTrue(idle.startswith(prefix))
        text = idle[len(prefix):].decode("ascii")
        lines = text.split("\r\n")
        # Image and base gates run before any breakpoint or forced write.
        self.assertEqual(lines[1], ".if ((@$t19 == 0) | (@$t18 != 0n47)) { .echo HDSESSION_INITIAL_REJECT; q }")
        self.assertEqual(lines[2], ".if (@$t19 != 0x400000) { .echo HDSESSION_BASE_REJECT; q }")
        first_write = min(index for index, line in enumerate(lines) if line.startswith(("bp ", "ed ", "eb ")))
        self.assertGreater(first_write, 3)
        self.assertIn("HDSESSION_FORCED_ROUTE map_entry=cdb_forced_menu_load_route start_animations="
                      "cdb_fast_forward_sleeps acquisition=cdb_forced_bypass pan=none load_slot=0", text)
        self.assertNotIn("r @$t18 = 0", text)
        self.assertNotIn("r @$t19 = 0", text)
        # Centered 640x480 menu point at 1920x1080 and the native load-list point, in <<6 units.
        self.assertIn("ed 00544cfc 0000d700; ed 00544d00 00007280;", text)
        self.assertEqual(text.count("ed 00544cfc 00005000; ed 00544d00 00002980;"), 2)
        for site in ("00401DDA", "0047BD66", "0047BDAE", "0044789a", "00419B80", "00419C51", "00447780",
                     "00448A68", "00448AE3", "00444490", "0040B660", "0040B0C3", "00406FA1", "00407D20"):
            self.assertEqual(text.count(f"bp {site} "), 1, site)
        self.assertIn("route_ticks=%d pan=%d", text)
        self.assertIn("ed 00400040 0", text)
        self.assertEqual(lines[-2:], ["g", ""])
        # The legacy base template's 800x600 dump gate (bp 00406FA0) is not composed.
        self.assertFalse([line for line in lines if line.startswith("bp 00406FA0")])
        self.assertNotIn("SURFDUMP_INVALID", text)
        self.assertNotIn("2048", text)
        self.assertNotRegex(text, r"__[A-Z0-9_]+__")
        for forbidden in ("SendInput", "PostMessage", ".writemem"):
            self.assertNotIn(forbidden, text)
        pan = session.map_command_script(prefix, {"resolution": "3840x2160"}, metadata, route="map-pan",
                                         duration=600, soak_template=template).decode("ascii")
        self.assertIn("pan=cdb_forced_native_arrow_key", pan)
        self.assertIn("ed 00544cfc 0001c700; ed 00544d00 0000f980;", pan)  # (220+1600, 158+840) << 6
        self.assertIn("0n38400", pan)  # 600 s at 64 ticks per second
        self.assertIn("0n640", pan)    # 10 s pan interval
        for kwargs, message in ((dict(route="menu-idle", duration=120), "fixed short-ladder"),
                                (dict(route="map-idle", duration=60), "fixed short-ladder")):
            with self.assertRaisesRegex(ValueError, message):
                session.map_command_script(prefix, {"resolution": "1920x1080"}, metadata, soak_template=template, **kwargs)
        with self.assertRaisesRegex(ValueError, "640x480"):
            session.map_command_script(prefix, {"resolution": "320x200"}, metadata, route="map-idle", duration=120,
                                       soak_template=template)
        with self.assertRaisesRegex(ValueError, "standalone g"):
            session.map_command_script(prefix, {"resolution": "1920x1080"}, metadata, route="map-idle", duration=120,
                                       soak_template=template + b"\r\ng\r\n")
        with self.assertRaisesRegex(ValueError, "chunk inventory"):
            session.map_command_script(prefix, {"resolution": "1920x1080"}, {"probe_contract": {"required_chunks": 0}},
                                       route="map-idle", duration=120, soak_template=template)
        # The observation-only menu route is unchanged by the map collector.
        menu = session.command_script(prefix, {}, metadata).decode("ascii")
        self.assertNotIn("HDSESSION_FORCE", menu)

    def test_map_ready_binds_one_entry_and_the_selected_canvas_to_the_adopted_process(self):
        identity, target = {"resolution": "1920x1080"}, {"pid": 0xabc, "base": 0x400000}
        game = ("HDSESSION_PLAYGAME pid=abc gd=0a000000 map=(72,72) scroll=(10,17) "
                "surface=00520000 size=(1920,1080)\n")
        start = "SOAK_ROUTE_START route_ticks=7680 pan=0 player=0 tick=100 gd=0a000000 scroll=(10,17)\n"
        ready = "SOAK_SURFDUMP_READY redraw_seq=0 surface=00520000 size=(1920,1080) base=20000000 bytes=2073600\n"
        actual = session.map_ready(game + start + ready, identity, target)
        self.assertFalse(actual["failures"])
        self.assertEqual(actual["surface"]["pixels"], 0x20000000)
        self.assertEqual(actual["playgame"]["map"], (72, 72))
        self.assertIsNone(session.map_ready(game, identity, target)["surface"])
        for bad in (game.replace("pid=abc", "pid=ddd") + start + ready,
                    game + start + ready.replace("size=(1920,1080)", "size=(1920,1088)"),
                    game + start + ready.replace("bytes=2073600", "bytes=2073599"),
                    game + start + ready.replace("base=20000000", "base=00000000"),
                    game + game + start + ready, start + ready,
                    game + start + ready + "HDSESSION_AV\n", game + "HDSESSION_PLAYGAME_NO_GAME_DATA\n",
                    game + start + ready + "SOAK_PAN_UNSAFE base=(1,1) max=(0,0) reason=no_inward_direction\n",
                    game + start + ready + "SOAK_ROUTE_END route_ticks=7680 pan=0 hits=x\n"):
            with self.subTest(bad=bad[-60:]):
                self.assertTrue(session.map_ready(bad, identity, target)["failures"])
        self.assertTrue(session.map_ready(game + start + ready, identity, None)["failures"])

    def test_log_tail_returns_only_complete_new_lines(self):
        with tempfile.TemporaryDirectory(prefix="clash-log-tail-") as directory:
            path = Path(directory) / "cdb.log"
            path.write_bytes(b"old line\r\nSOAK_HEART")
            tail = session._LogTail(path, len(b"old line\r\n"))
            self.assertEqual(tail.lines(), [])
            with path.open("ab") as stream:
                stream.write(b"BEAT hits=1\r\n  SOAK_ROUTE_END x \r\npartial")
            self.assertEqual(tail.lines(), ["SOAK_HEARTBEAT hits=1", "SOAK_ROUTE_END x"])
            self.assertEqual(tail.lines(), [])
            with patch.object(session, "MAX_LOG", 4):
                with self.assertRaisesRegex(ValueError, "retained output budget"):
                    tail.lines()

    def run_steady_state(self, route, duration, rows, *, end_at, extra=(), alive=True):
        """Drive the sampler with a fake clock; rows after the start arrive once the clock passes end_at."""
        clock = [1000.0]
        start = ["SOAK_ROUTE_START route_ticks=%d pan=%d player=0 tick=100 gd=0a000000 scroll=(10,17)"
                 % (duration * 64, route == "map-pan"),
                 "SOAK_SURFDUMP_READY redraw_seq=0 surface=00520000 size=(4,2) base=20000000 bytes=8"]

        class Tail:
            def __init__(self):
                self.sent = False

            def lines(self):
                if self.sent or clock[0] - 1000.0 < end_at:
                    return list(extra) if not self.sent and extra else []
                self.sent = True
                return list(rows)

        class Native:
            def alive(self, _handle):
                return alive

            def read(self, _handle, address, count):
                return struct.pack("<HHI", 4, 2, 0x20000000) if address == 0x520000 else bytes(range(count))

            def telemetry(self, _handle):
                return {"private_bytes": 1}

        report = {"frames": [], "samples": []}
        ready = {"playgame": {"pid": 1}, "surface": dict(descriptor=0x520000, width=4, height=2, pixels=0x20000000,
                                                           bytes=8)}
        with tempfile.TemporaryDirectory(prefix="clash-map-steady-") as directory:
            run = Path(directory)
            (run / "cdb.log").write_text("\n".join(start + list(rows)) + "\n", encoding="ascii")
            with contextlib.redirect_stdout(io.StringIO()), patch.object(session.time, "monotonic", lambda: clock[0]), \
                    patch.object(session.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)), \
                    patch.object(session.qualification, "_reserve"):
                try:
                    session._map_steady_state(Native(), 1, 2, run / "cdb.log", Tail(), [], run, report,
                                              {"route": route, "duration_sec": duration}, ready)
                except (ValueError, TimeoutError) as error:
                    return report, str(error)
        return report, None

    def test_map_sampler_requires_its_end_marker_ticks_host_clock_and_route_shape(self):
        end = "SOAK_ROUTE_END route_ticks=7680 pan=0 hits=3137 tickdelta=7681 player=0 scroll=(10,17)"
        beat = "SOAK_HEARTBEAT hits=2048 tickdelta=5030 player=0 scroll=(10,17)"
        report, error = self.run_steady_state("map-idle", 120, [beat, end], end_at=119.5)
        self.assertIsNone(error)
        self.assertTrue(report["map_route_completed"])
        self.assertEqual(report["soak_route"]["heartbeats"], 1)
        self.assertGreaterEqual(len(report["frames"]), 3)  # start, 60 s, final
        self.assertTrue(all(frame["coherent_snapshot_verified"] is False for frame in report["frames"]))
        self.assertGreater(len(report["samples"]), 100)
        cases = (
            ([beat, end.replace("tickdelta=7681", "tickdelta=7000")], 119.5, "does not cover the fixed route"),
            ([beat, end], 110.0, "host clock does not corroborate"),
            ([end], 119.5, "no structured SOAK_HEARTBEAT"),
            ([beat, "SOAK_PAN_SET phase=0 x=11 y=17 hits=2100 tickdelta=5100 delta=(1,0)", end.replace("(10,17)", "(11,17)")],
             119.5, "idle map route recorded forced pan rows"),
            ([beat], 0.0, "end was not observed"),
        )
        for rows, end_at, message in cases:
            with self.subTest(message=message):
                report, error = self.run_steady_state("map-idle", 120, rows, end_at=end_at)
                self.assertIn(message, error or "")
                self.assertNotIn("map_route_completed", report)
        _, error = self.run_steady_state("map-idle", 120, [beat, end], end_at=119.5, extra=["HDSESSION_AV"])
        self.assertIn("runtime failure: HDSESSION_AV", error)
        _, error = self.run_steady_state("map-idle", 120, [beat, end], end_at=119.5, alive=False)
        self.assertIn("exited before the soak route end", error)
        plan = "SOAK_PAN_PLAN base=(10,17) delta=(1,1) max=(88,91) safe=1"
        steps, x, y, hits = [], 10, 17, 2000
        for index in range(58):
            phase = index % 4
            x, y = (11, 17) if phase == 0 else (11, 18) if phase == 1 else (10, 18) if phase == 2 else (10, 17)
            hits += 50
            steps.append(f"SOAK_PAN_SET phase={phase} x={x} y={y} hits={hits} tickdelta={640 * (index + 1)} delta=(1,1)")
        pan_end = f"SOAK_ROUTE_END route_ticks=38400 pan=1 hits={hits + 100} tickdelta=38401 player=0 scroll=({x},{y})"
        pan_beat = "SOAK_HEARTBEAT hits=2048 tickdelta=600 player=0 scroll=(10,17)"
        report, error = self.run_steady_state("map-pan", 600, [plan, pan_beat, *steps, pan_end], end_at=599.5)
        self.assertIsNone(error, report.get("soak_route"))
        self.assertEqual(report["soak_route"]["pan_events"], 58)
        _, error = self.run_steady_state("map-pan", 600, [plan, pan_beat, *steps[:30], pan_end.replace(f"scroll=({x},{y})", "scroll=(11,18)")],
                                         end_at=599.5)
        self.assertIn("scheduled native arrow-key steps", error)

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
            for name in (*session.ASSET_FILES, "DATA/GFX3.RES", "DATA/lower.res", "DATA/main.wav", "DATA/LOUD.WAV",
                         "AVI/intro.avi", "AVI/UPPER.AVI", "GFX/CACHE/cell.s32", "GFX/CACHE/CELL2.S32",
                         "save/2.dat", "save/2.fac", "save/3.DAT", "save/3.Fac", "DATA/output/copied.res",
                         "DATA/Backup/OLD.RES", "DATA/stale.RES.bak", "DATA/ImageMagick/tool.exe", "reverse/dump.res", "ddraw.dll"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
            actual = {row["path"] for row in session.asset_inventory(root)}
            # Names match case-insensitively on every host, as on Windows.
            self.assertTrue({"DATA/GFX3.RES", "DATA/lower.res", "DATA/main.wav", "DATA/LOUD.WAV", "AVI/intro.avi",
                             "AVI/UPPER.AVI", "GFX/CACHE/cell.s32", "GFX/CACHE/CELL2.S32", "save/2.dat",
                             "save/2.fac", "save/3.DAT", "save/3.Fac"} <= actual)
            self.assertFalse(actual & {"DATA/output/copied.res", "DATA/Backup/OLD.RES", "DATA/stale.RES.bak",
                                       "DATA/ImageMagick/tool.exe", "reverse/dump.res", "ddraw.dll"})

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
