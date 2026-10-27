"""Source/synthetic approval and owned-window tests; never a visible launch."""
from __future__ import annotations

import contextlib
import ctypes as C
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import hd_multires_visible_session as visible
import hd_multires_visible_win32 as window_api
import hd_multires_win32 as native
from test_hd_multires_hidden_session import FakeKernel, FakeUser


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
        self.plan = dict(plan_sha256="a" * 64, scope=list(visible.SCOPE))
        # In-memory synthetic approval fixture; never written as user evidence.
        self.record = dict(schema=visible.APPROVAL, approved=True, plan_sha256="a" * 64,
            scope=list(visible.SCOPE), user_response="synthetic-test-only", approval_question="fixture?",
            thread_id="synthetic-test", recorded_at_utc=self.now.isoformat())

    def test_approval_binds_exact_digest_scope_real_response_and_fresh_time(self):
        self.assertTrue(visible.verify_approval(self.record, self.plan, now=self.now))
        for changed in (dict(approved=False), dict(plan_sha256="b" * 64),
                dict(scope=self.plan["scope"] + ["capture_owned_window"]), dict(user_response=""), dict(thread_id=""),
                dict(recorded_at_utc=(self.now - timedelta(hours=13)).isoformat()),
                dict(recorded_at_utc=(self.now + timedelta(seconds=1)).isoformat()),
                dict(recorded_at_utc="2026-10-27T12:00:00")):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                visible.verify_approval(self.record | changed, self.plan, now=self.now)

    def test_invalid_approval_stops_before_files_reconstruction_or_native_operations(self):
        with tempfile.TemporaryDirectory(prefix="clash-visible-approval-") as directory:
            root = Path(directory)
            approval = root / "not-approved.json"
            approval.write_text(json.dumps(self.record | {"approved": False}))
            with patch.object(visible, "reconstruct", side_effect=AssertionError("must not reconstruct")), \
                    patch.object(visible, "DefaultDesktopJob", side_effect=AssertionError("must not launch")), \
                    self.assertRaisesRegex(ValueError, "real-user approval"):
                visible.execute(self.plan, approval)
            self.assertEqual(list(root.iterdir()), [approval])

    def test_dry_plan_and_missing_approval_cli_never_open_windows(self):
        with patch.object(visible.hidden.qualification, "read_json", return_value=self.plan), \
                patch.object(visible, "reconstruct", return_value=(self.plan, {}, {}, {})), \
                patch.object(visible, "DefaultDesktopJob", side_effect=AssertionError("no launch")), \
                patch.object(visible, "OwnedWindow", side_effect=AssertionError("no window API")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(visible.main(["--plan", "synthetic-plan.json"]), 0)
            self.assertEqual(visible.main(["--plan", "synthetic-plan.json", "--execute"]), 1)

    def test_saved_plan_cannot_change_duration_or_asset_hash_after_approval(self):
        saved = dict(bundle="bundle.json", proxy=dict(path="proxy.dll"), asset_root="assets",
            session_dir="new-session", capture_owned_window=False, maximum_session_sec=300)
        with patch.object(visible, "prepare", return_value=(saved, {}, {}, {})):
            self.assertEqual(visible.reconstruct(saved)[0], saved)
            with self.assertRaisesRegex(ValueError, "differs from fresh"):
                visible.reconstruct(saved | {"maximum_session_sec": 301})


class PlanAndSourceTests(unittest.TestCase):
    def test_script_keeps_exact_probe_and_only_observes_real_returns(self):
        prefix = b"CANONICAL_PRIVATE_IMAGE_PROBE\r\n"
        raw = visible.command_script(prefix, {}, {"probe_contract": {"required_chunks": 123}})
        suffix = raw[len(prefix):].decode()
        self.assertTrue(raw.startswith(prefix))
        self.assertIn("bp /1 @$t19+0x61ace", suffix)
        self.assertIn(".sleep 0n3000; gc", suffix)
        self.assertIn("HDSESSION_WINDOW_BEGIN", suffix)
        self.assertIn("HDSESSION_WINDOW_END", suffix)
        self.assertIn("bp /1 @$t19+0x7bd6f", suffix)
        self.assertIn("bp /1 @$t19+0x7bdb7", suffix)
        self.assertLess(suffix.index("HDSESSION_CONTEXT_WARMUP"), suffix.index("HDSESSION_ACQUIRE_BEGIN_mouse"))
        for forbidden in ("r eax=", "r eip=", "ed ", "eb ", "SendInput", "PostMessage", "SetCursorPos"):
            self.assertNotIn(forbidden, suffix)

    def test_read_only_asset_preflight_cannot_create_a_missing_stage(self):
        with tempfile.TemporaryDirectory(prefix="clash-visible-missing-") as directory:
            root = Path(directory) / "missing"
            with patch.object(visible.hidden, "_external", return_value=root):
                with self.assertRaisesRegex(ValueError, "previously isolated"):
                    visible._stage_snapshot(root, [])
            self.assertFalse(root.exists())

    def test_approved_asset_snapshot_rejects_mutation_and_new_linked_saves(self):
        with tempfile.TemporaryDirectory(prefix="clash-visible-assets-") as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir(); (assets / "save").mkdir()
            bundle, manifest, proxy_manifest = root / "bundle.json", assets / "asset-stage.json", root / "proxy.json"
            for path in (bundle, manifest, proxy_manifest): path.write_bytes(b"synthetic manifest")
            state = assets / "CLASH.CFG"
            state.write_bytes(b"private mutable state")
            plan = dict(bundle=str(bundle), bundle_sha256=visible.hidden._file_sha(bundle),
                source_hashes={}, producer_source_hashes={}, asset_root=str(assets),
                proxy=dict(build_manifest_path=str(proxy_manifest), build_manifest_sha256=visible.hidden._file_sha(proxy_manifest)),
                asset_snapshot=dict(manifest_sha256=visible.hidden._file_sha(manifest),
                    files=[dict(path="CLASH.CFG", sha256=visible.hidden._file_sha(state))]))
            self.assertTrue(visible.verify_plan_files(plan, before_launch=True))
            state.write_bytes(b"state changed after approval")
            with self.assertRaisesRegex(ValueError, "asset changed"):
                visible.verify_plan_files(plan, before_launch=True)
            self.assertTrue(visible.verify_plan_files(plan, before_launch=False))
            live = root / "synthetic-live.dat"
            live.write_bytes(b"live fixture")
            os.link(live, assets / "save" / "unlisted.dat")
            with self.assertRaisesRegex(ValueError, "save inventory changed"):
                visible.verify_plan_files(plan, before_launch=True)
            with self.assertRaisesRegex(ValueError, "non-linked file"):
                visible.verify_plan_files(plan, before_launch=False)

    def test_default_desktop_still_assigns_verified_job_before_first_resume(self):
        kernel = FakeKernel()
        user = FakeUser()
        user.CreateDesktopW = lambda *args: (_ for _ in ()).throw(AssertionError("must not create hidden desktop"))
        with patch.object(native, "_api", return_value=(kernel, user, object())):
            job = window_api.DefaultDesktopJob().open()
            self.assertEqual(job.desktop_name, "winsta0\\default")
            self.assertEqual(job.show_window, 1)
            _, identity = job.spawn(Path("synthetic-python.exe").resolve(), [], Path.cwd(), {})
            self.assertTrue(identity["task_job_member"])
            self.assertLess(job.events.index("process_membership_and_generation_verified"), job.events.index("process_resumed"))
            self.assertTrue(job.close()["cleanup_verified"])

    def test_independent_deadline_targets_only_retained_job_and_disarms_before_close(self):
        calls = []
        job = SimpleNamespace(job=44, kernel=SimpleNamespace(TerminateJobObject=lambda handle, code: calls.append((handle, code)) or True))
        deadline = visible.NativeDeadline(job, 300)
        deadline._expire()
        self.assertTrue(deadline.stop()["deadline_reached"])
        self.assertEqual(calls, [(44, 0x4844)])
        deadline._expire()
        self.assertEqual(len(calls), 1)


class WindowOwnershipTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows DLL signature binding only; no window operation")
    def test_windows_signatures_bind_without_performing_any_window_action(self):
        item = window_api.OwnedWindow(lambda: (_ for _ in ()).throw(ValueError("no approved retained process")))
        with self.assertRaisesRegex(ValueError, "no approved"):
            item.verify(123, 456)

    def make_window(self, pid=123):
        calls = []
        item = object.__new__(window_api.OwnedWindow)
        item.retained_process_guard = lambda: calls.append("retained_process_verified")
        def owner(hwnd, result): result._obj.value = pid; return 1
        item.user = SimpleNamespace(IsWindow=lambda hwnd: True, GetWindowThreadProcessId=owner,
            ShowWindow=lambda *args: calls.append("show"), SetForegroundWindow=lambda *args: calls.append("foreground") or True,
            GetForegroundWindow=lambda: 99)
        return item, calls

    def test_foreign_window_and_dead_retained_process_cannot_be_activated(self):
        item, calls = self.make_window(pid=456)
        with self.assertRaisesRegex(ValueError, "ownership differs"):
            item.activate(99, 123)
        self.assertNotIn("show", calls)
        item, calls = self.make_window()
        item.retained_process_guard = lambda: (_ for _ in ()).throw(ValueError("retained process is dead"))
        with self.assertRaisesRegex(ValueError, "dead"):
            item.activate(99, 123)
        self.assertNotIn("foreground", calls)

    def test_owned_activation_rechecks_identity_and_injects_no_input(self):
        item, calls = self.make_window()
        actual = item.activate(99, 123)
        self.assertTrue(actual["foreground_verified"])
        self.assertFalse(actual["input_injected"])
        self.assertGreaterEqual(calls.count("retained_process_verified"), 4)

    def test_capture_reads_only_owned_window_dc_and_releases_all_gdi_objects(self):
        item, calls = self.make_window()
        def rectangle(hwnd, result):
            result._obj.right, result._obj.bottom = 2, 2
            return True
        def pixels(dc, bitmap, start, rows, target, info, mode):
            C.memmove(target, bytes(range(16)), 16)
            return 2
        item.user.GetWindowRect = rectangle
        item.user.GetWindowDC = lambda hwnd: calls.append(("window_dc", hwnd)) or 11
        item.user.ReleaseDC = lambda hwnd, dc: calls.append(("release_dc", hwnd, dc)) or 1
        item.user.PrintWindow = lambda hwnd, dc, flags: calls.append(("print", hwnd, dc)) or True
        item.gdi = SimpleNamespace(CreateCompatibleDC=lambda source: 12, CreateCompatibleBitmap=lambda *args: 13,
            SelectObject=lambda *args: 14, GetDIBits=pixels,
            DeleteObject=lambda bitmap: calls.append(("delete_bitmap", bitmap)) or True,
            DeleteDC=lambda dc: calls.append(("delete_dc", dc)) or True)
        raw, metadata = item.capture(99, 123)
        self.assertEqual(raw[:2], b"BM")
        self.assertEqual(struct.unpack_from("<I", raw, 2)[0], len(raw))
        self.assertEqual(raw[54:], bytes(range(16)))
        self.assertEqual((metadata["width"], metadata["height"]), (2, 2))
        self.assertIn(("window_dc", 99), calls)
        self.assertIn(("release_dc", 99, 11), calls)
        self.assertIn(("delete_bitmap", 13), calls)
        self.assertIn(("delete_dc", 12), calls)


if __name__ == "__main__":
    unittest.main()
