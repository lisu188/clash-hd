"""Portable source checks plus explicit synthetic Windows-CI native fixture.

Local invocation never compiles or launches anything. The opt-in CI case keeps
its original compiler and binary stdout archives outside the repository. It
uses a public marked synthetic PE; it cannot supply real canonical-plan issuer
authority, a game observation, instrumented job receipts or release evidence.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import hidden_soak_loader_native as native

ENGINE_OPT_IN = (os.name == "nt" and os.environ.get("GITHUB_ACTIONS") == "true" and
                 os.environ.get("CLASH_LOADER_NATIVE_ENGINE_INTEGRATION") == "1")


def sha(raw): return hashlib.sha256(raw).hexdigest()


def require_space(directory, additional):
    """Strict volume reserve plus this fixture's complete source-owned budget."""
    total, _, free = shutil.disk_usage(directory)
    if free <= total // 10 or free - additional <= total // 10:
        raise AssertionError("Native CI fixture lacks >10% free plus its complete peak allowance")


def compiler_timeout_receipt(error, retain_bytes):
    """Original available timeout outputs only; no unavailable-buffer invention."""
    if type(error) is not subprocess.TimeoutExpired: raise TypeError("Original compiler TimeoutExpired required")
    original = dict(type_name=type(error).__name__, command=error.cmd, timeout_seconds=error.timeout,
                    unavailable_or_unread_remainder=True)
    for label, raw in (("stdout", error.stdout), ("stderr", error.stderr)):
        if raw is None:
            original[label] = dict(original_bytes_available=False, unavailable=True)
        else:
            if type(raw) is not bytes: raise TypeError("Original binary compiler timeout output type differs")
            path = retain_bytes(label, raw)
            original[label] = dict(original_bytes_available=True, bytes=len(raw), sha256=sha(raw), path=path)
    return original


class EngineSourceTests(unittest.TestCase):
    def test_fixed_command_free_batch_and_original_failure_boundaries(self):
        text = native.HARNESS
        for item in ("#include <memory>", "sizeof(EXCEPTION_RECORD64)==152", "sizeof(DEBUG_LAST_EVENT_INFO_EXCEPTION)==160",
                     "DEBUG_ENGOPT_INITIAL_BREAK|DEBUG_ENGOPT_DISALLOW_SHELL_COMMANDS", "DEBUG_END_ACTIVE_TERMINATE",
                     "FILE_TYPE_DISK", 'j.frame("read_virtual"', 'j.frame("native_failure"', 'j.frame("output"',
                     'j.frame("launch"', 'j.frame("callback_exception"', "same&&event->FirstChance==1",
                     "callback_error(s,error)", "valid&&held&&tick>=held", "hr==S_OK&&value==expected"):
            self.assertIn(item, text)
        for method in ("SetExecutionStatus(", "Execute(", "AddBreakpoint(", "WriteVirtual(", "AttachProcess(",
                       "ReadProcessMemory(", "Sleep(", "CreateNamedPipe", "socket("):
            self.assertNotIn(method, text)
        read = text[text.index("void read(ULONG ordinal"):text.index("HRESULT Events::CreateProcess")]
        self.assertLess(read.index('j.frame("read_virtual"'), read.index("demand(hr==S_OK&&actual==size"))
        self.assertIn("actual<=size", read)
        file_read = text[text.index("static Bytes read_file"):text.index("static std::string file_hash")]
        self.assertNotIn("block.resize", file_read)
        self.assertIn('throw NativeFailure("ReadFile",read,error,requested,got,std::move(block))', file_read)
        cleanup = text[text.index("// Query fresh final times/exit"):]
        self.assertLess(text.index("WaitForSingleObject(s.target.value,5000)"), text.index("// Query fresh final times/exit"))
        self.assertLess(cleanup.index("GetProcessTimes"), cleanup.index("GetExitCodeProcess"))

    def test_budget_failure_tail_and_broad_claims_remain_false(self):
        policy = native.retention_budget()
        self.assertEqual(policy["additional_peak_bytes"], 16 * 1024**2 + 65539 + 2 * 9 * 1024**2)
        self.assertEqual(policy["failure_metadata_bytes"], 1024**2)
        self.assertTrue(policy["collector_allowance_is_not_additionally_counted"])
        self.assertTrue(native.FALSE_CLAIMS)
        self.assertTrue(all(value is False for value in native.FALSE_CLAIMS.values()))
        self.assertIn("canonical_comparison_during_native_hold", native.FALSE_CLAIMS)
        self.assertIn("native_generation_ownership_verified", native.FALSE_CLAIMS)

    def test_native_is_ci_only_and_public_issuer_rejects_forged_capabilities(self):
        self.assertIn('os.environ.get("GITHUB_ACTIONS") == "true"', Path(__file__).read_text())
        with self.assertRaises(ValueError): native.inspect_request(native.NativeRequest("{}"))
        with self.assertRaises(ValueError): native.prepare_request(native.NativeReadPlan("{}"), run_id="1" * 32,
            checkpoint_id="2" * 32, epoch_id="3" * 32, controller_pid=1, frequency_hz=10**7,
            origin_tick=100, origin_ns=100)

    def test_own_compiled_bytes_must_match_the_preparation_snapshot(self):
        from unittest.mock import patch
        own_path = Path(native.__file__).resolve()
        actual = Path.read_bytes
        calls = 0
        def changed_after_compile(path):
            nonlocal calls
            raw = actual(path)
            if path == own_path:
                calls += 1
                if calls > 1: return raw + b"\n# changed after private compile\n"
            return raw
        with patch.object(Path, "read_bytes", changed_after_compile):
            with self.assertRaisesRegex(ValueError, "between compilation and source snapshot"):
                native.prepare_native_plan(b"not admitted", None)

    def test_compiler_timeout_original_partial_bytes_and_unavailable_stderr(self):
        retained = {}
        def retain(label, raw):
            retained[label] = raw
            return "mocked external " + label
        raw = b"original\0binary\xffpartial output"
        error = subprocess.TimeoutExpired(["fixed-cl.exe", "fixed-host.cpp"], 90, output=raw, stderr=None)
        observed = compiler_timeout_receipt(error, retain)
        self.assertIs(retained["stdout"], raw)
        self.assertEqual(observed["stdout"]["bytes"], len(raw))
        self.assertEqual(observed["stdout"]["sha256"], sha(raw))
        self.assertEqual(observed["stderr"], dict(original_bytes_available=False, unavailable=True))
        self.assertNotIn("stderr", retained)
        self.assertIs(observed["command"], error.cmd)
        self.assertTrue(observed["unavailable_or_unread_remainder"])
        self.assertEqual(compiler_timeout_receipt(subprocess.TimeoutExpired("fixed", 90, output=b"", stderr=b""),
            retain)["stdout"]["bytes"], 0)
        with self.assertRaises(TypeError):
            compiler_timeout_receipt(subprocess.TimeoutExpired("fixed", 90, output="coerced text"), retain)


@unittest.skipUnless(ENGINE_OPT_IN, "Explicit isolated Windows CI loader-engine fixture required")
class NativeEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Native APIs and output paths are unavailable until the exact opt-in.
        import owned_hidden_process as owned
        import hidden_soak_loader_native_adapter as wire
        import hidden_soak_loaded_image as image
        import test_framed_loaded_probe_engine as synthetic
        cls.owned, cls.wire, cls.image, cls.synthetic = owned, wire, image, synthetic
        root = os.environ.get("CLASH_LOADER_NATIVE_ARTIFACT_DIR")
        if not root: raise AssertionError("An explicit external original-artifact directory is required")
        base = Path(root).absolute()
        if base.resolve() != base or base == ROOT or base.is_relative_to(ROOT):
            raise AssertionError("CI original artifacts must remain outside the repository")
        for parent in (base, *base.parents):
            if parent.exists() and (parent.is_symlink() or getattr(parent, "is_junction", lambda: False)() or
                    getattr(parent.stat(), "st_file_attributes", 0) & 0x400):
                raise AssertionError("Reparsed artifact parent rejected")
        if not base.is_dir(): raise AssertionError("External artifact parent must already exist")
        cls.allowance = native.retention_budget()["additional_peak_bytes"] + 256 * 1024**2
        require_space(base, cls.allowance)
        cls.root = base / ("loader-native-" + uuid.uuid4().hex)
        cls.root.mkdir()  # Never remove unique failed or passing native evidence.
        cls.records = []
        cls.fixture_completed = False
        cls.addClassCleanup(cls.save_report)
        source = cls.root / "host.cpp"
        source.write_bytes(native.HARNESS.encode("ascii"))
        cls.runner = cls.root / "host.exe"
        compiler = shutil.which("cl.exe")
        if not compiler: raise AssertionError("Opt-in requires an actual MSVC x86 compiler environment")
        require_space(cls.root, cls.allowance)
        command = [compiler, "/nologo", "/EHsc", "/std:c++17", "/W4", "/O2", "/MT", str(source),
            "/Fe:" + str(cls.runner), "/Fo:" + str(cls.root / "host.obj"), "/link", "/MACHINE:X86", "bcrypt.lib"]
        try:
            result = subprocess.run(command, cwd=cls.root, capture_output=True, timeout=90,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired as error:
            def retain(label, raw):
                require_space(cls.root, len(raw) + 1024**2)
                path = cls.root / ("compiler-" + label + "-timeout.bin")
                path.write_bytes(raw)
                return str(path)
            original = compiler_timeout_receipt(error, retain)
            cls.records.append(dict(original_compiler_timeout=original))
            (cls.root / "compiler-timeout.json").write_text(json.dumps(original, sort_keys=True), encoding="ascii")
            raise
        (cls.root / "compiler-stdout.bin").write_bytes(result.stdout)
        (cls.root / "compiler-stderr.bin").write_bytes(result.stderr)
        if result.returncode: raise AssertionError("Native compile failed; complete original outputs retained at " + str(cls.root))
        cls.host_sha = sha(cls.runner.read_bytes())
        cls.kernel = C.WinDLL("kernel32", use_last_error=True)
        for name, args, result_type in (
            ("OpenProcess", [C.c_uint32, C.c_int32, C.c_uint32], C.c_void_p),
            ("GetProcessId", [C.c_void_p], C.c_uint32),
            ("GetProcessTimes", [C.c_void_p] + [C.POINTER(C.c_uint64)] * 4, C.c_int32),
            ("QueryFullProcessImageNameW", [C.c_void_p, C.c_uint32, C.c_wchar_p, C.POINTER(C.c_uint32)], C.c_int32),
            ("WaitForSingleObject", [C.c_void_p, C.c_uint32], C.c_uint32),
            ("CloseHandle", [C.c_void_p], C.c_int32),
            ("QueryPerformanceFrequency", [C.POINTER(C.c_int64)], C.c_int32),
            ("QueryPerformanceCounter", [C.POINTER(C.c_int64)], C.c_int32)):
            fn = getattr(cls.kernel, name); fn.argtypes, fn.restype = args, result_type

    @classmethod
    def save_report(cls):
        require_space(cls.root, 1024**2)
        report = dict(schema="synthetic_loader_native_engine_v1", fixture_only=True,
            producer_source_sha256=sha(Path(native.__file__).read_bytes()), host_source_sha256=sha(native.HARNESS.encode("ascii")),
            native_engine_fixture_completed=cls.fixture_completed, cases=cls.records, **native.FALSE_CLAIMS)
        # Original archives and compiler outputs remain alongside this report.
        (cls.root / "engine-report.json").write_text(json.dumps(report, sort_keys=True, indent=2), encoding="ascii")

    def generation(self, handle, expected_pid, expected_path):
        """Independently retain observations while the actual handle is live."""
        C.set_last_error(0); pid = self.kernel.GetProcessId(handle); pe = C.get_last_error()
        times = [C.c_uint64() for _ in range(4)]
        C.set_last_error(0); tr = self.kernel.GetProcessTimes(handle, *(C.byref(v) for v in times)); te = C.get_last_error()
        path = C.create_unicode_buffer(32768); count = C.c_uint32(32768)
        C.set_last_error(0); pr = self.kernel.QueryFullProcessImageNameW(handle, 0, path, C.byref(count)); qe = C.get_last_error()
        C.set_last_error(0); waited = self.kernel.WaitForSingleObject(handle, 0); we = C.get_last_error()
        original = dict(pid=pid, pid_error=pe, times_return=tr, times_error=te, times=[v.value for v in times],
            path_return=pr, path_error=qe, path_chars=count.value,
            image_path_utf16le=C.string_at(C.addressof(path), min(count.value, 32768) * C.sizeof(C.c_wchar)).hex(),
            wait_result=waited, wait_error=we)
        self.records.append(dict(parent_generation_observation=original))
        self.assertEqual((pid, pe, tr, te, pr, qe, waited, we), (expected_pid, 0, 1, 0, 1, 0, 258, 0))
        self.assertGreater(times[0].value, 0); self.assertEqual(times[1].value, 0)
        self.assertEqual(Path(path.value).resolve(), Path(expected_path).resolve())
        return self.image.Generation(pid, times[0].value, path.value, sha(Path(path.value).read_bytes()))

    def clock(self):
        f, q = C.c_int64(), C.c_int64()
        C.set_last_error(0); fr = self.kernel.QueryPerformanceFrequency(C.byref(f)); fe = C.get_last_error()
        C.set_last_error(0); qr = self.kernel.QueryPerformanceCounter(C.byref(q)); qe = C.get_last_error()
        self.records.append(dict(original_prelaunch_clock=dict(frequency=f.value, tick=q.value, frequency_return=fr,
            frequency_error=fe, counter_return=qr, counter_error=qe)))
        self.assertEqual((fr, fe, qr, qe), (1, 0, 1, 0)); self.assertGreater(f.value, 0); self.assertGreater(q.value, 0)
        return f.value, q.value

    def test_original_initial_event_command_free_raw_reads_and_live_parent_adoption(self):
        data, _, _ = self.synthetic.executable_fixture("1024x768")
        candidate = self.root / "synthetic-loader.exe"
        candidate.write_bytes(data)
        scope = self.image._derive_plan(data, self.synthetic.probe.pe)
        rows = tuple((row["rva"], row["size"]) for row in scope["chunks"])
        run, checkpoint, epoch = (uuid.uuid4().hex for _ in range(3))
        frequency, origin = self.clock()
        # This request is a fixed synthetic CI seam. It is never a public
        # source-issued canonical game request or an accepted release bundle.
        request = (native.REQUEST_MAGIC + struct.pack("<IIIIQQQ", len(rows), scope["preferred_base"], scope["image_size"],
            os.getpid(), frequency, origin, 100) + sha(data).encode("ascii") + (run + checkpoint + epoch).encode("ascii") +
            b"".join(struct.pack("<II", *row) for row in rows))
        request_path = self.root / "request.bin"; request_path.write_bytes(request)
        archive_path = self.root / "original-stdout.bin"
        original_archive, retained, adoption = b"", None, None
        require_space(self.root, self.allowance)
        try:
            with archive_path.open("xb", buffering=0) as output:
                with self.owned.OwnedHiddenProcess([str(self.runner), str(candidate), str(request_path)], self.root,
                        dict(os.environ), output) as host:
                    host_generation = self.generation(host._info.hProcess, host.pid, self.runner)
                    # Read the growing regular archive without inventing a
                    # readiness/command transport or delaying host termination.
                    deadline = time.monotonic() + 35
                    while time.monotonic() < deadline:
                        original_archive = archive_path.read_bytes()
                        offset = len(native.ARCHIVE_MAGIC)
                        if original_archive.startswith(native.ARCHIVE_MAGIC):
                            while offset + 8 <= len(original_archive):
                                meta_size, raw_size = struct.unpack_from("<II", original_archive, offset)
                                if meta_size > native.MAX_FRAME_JSON or raw_size > native.MAX_FRAME_RAW:
                                    self.fail("Original native frame capacity violation; full archive retained")
                                end = offset + 8 + meta_size + raw_size
                                if end > len(original_archive): break
                                packet = json.loads(original_archive[offset + 8:offset + 8 + meta_size].decode("ascii"))
                                if packet["operation"] == "callback_create" and retained is None:
                                    discovery = packet["data"]
                                    C.set_last_error(0)
                                    retained = self.kernel.OpenProcess(0x1000 | 0x100000, 0, discovery["pid"])
                                    error = C.get_last_error()
                                    self.records.append(dict(original_parent_open=dict(pid=discovery["pid"], handle=retained, error=error)))
                                    self.assertTrue(retained, "Target vanished before independent retained-generation adoption")
                                    self.assertEqual(error, 0)
                                    adoption = self.generation(retained, discovery["pid"], candidate)
                                offset = end
                        if host.poll() is not None: break
                        time.sleep(0.001)  # Poll interval grants no ownership proof.
                    self.assertEqual(host.wait(5), 0, "Native failure: complete original stdout retained")
                    original_archive = archive_path.read_bytes()
                    self.assertIsNotNone(adoption, "After-exit archive cannot prove retained target generation")
            frames = self.wire._frames(original_archive)
            metadata = dict(epoch_id=epoch, frequency_hz=frequency, origin_tick=origin, origin_ns=100)
            external = self.wire.ArchiveAuthority(sha(request), sha(data), self.host_sha,
                sha(native.HARNESS.encode("ascii")), sha(Path(native.__file__).read_bytes()),
                sha(Path(self.wire.__file__).read_bytes()), sha(original_archive), len(original_archive),
                run, checkpoint, epoch, os.getpid(), 0)
            self.wire._protocol(frames, external, metadata)
            values = [row.data() for row in frames if row.operation == "read_virtual"]
            self.assertEqual([(v["ordinal"], v["requested_bytes"], v["hresult"], v["returned_bytes"]) for v in values],
                [(0, 4, 0, 4)] + [(i + 1, size, 0, size) for i, (_, size) in enumerate(rows)])
            create = next(row.data() for row in frames if row.operation == "callback_create")
            self.assertEqual(create["pid"], adoption.pid)
            self.assertEqual(next(row.data() for row in frames if row.operation == "finish")["status"], "complete")
            startup = next(row.data() for row in frames if row.operation == "startup_owner")
            self.wire._generation(startup["debugger"], host_generation, None)
            self.wire._generation(startup["target"], adoption, host_generation)
            # Full original raw bytes, including executable interior bytes and
            # zero extents, are compared to this marked synthetic source.
            mapped = self.synthetic.fixtures.mapped(data, create["base_offset"])
            reads = [row for row in frames if row.operation == "read_virtual"]
            self.assertEqual(struct.unpack("<I", reads[0].raw)[0], create["base_offset"])
            for row, (rva, size) in zip(reads[1:], rows):
                expected = bytes(mapped[rva:rva + size])
                self.assertEqual(row.raw, expected)
            self.records.append(dict(original_archive_path=str(archive_path), original_archive_sha256=sha(original_archive),
                retained_target=dict(pid=adoption.pid, creation_filetime=adoption.creation_filetime),
                canonical_comparison_during_native_hold=False, synthetic_original_native_reads_checked=True,
                native_job_cleanup_verified=False, host_cleanup_complete=False))
        finally:
            if retained:
                C.set_last_error(0); result = self.kernel.CloseHandle(retained); error = C.get_last_error()
                self.records.append(dict(original_parent_close=dict(native_return=result, native_error=error)))
                self.assertEqual((result, error), (1, 0))
        type(self).fixture_completed = True


def original_backed():
    """One optional real original reconstruction, entirely in RAM."""
    from unittest.mock import patch
    from src.patcher import battle_profile_context as context
    import hidden_soak_loaded_image as oracle
    import hidden_soak_loaded_read_session as collector
    original_path = Path("C:/Clash/clash95.exe")
    before = original_path.read_bytes()
    original_digest = sha(before)
    if original_digest != "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae":
        raise AssertionError("Expected original differs")
    watched = [Path(native.__file__), ROOT / native.ADAPTER, Path(__file__)]
    source_hashes = tuple(sha(path.read_bytes()) for path in watched)
    parent = context.build_parent_context(before, "classic", "1024x768")
    bound = oracle.prepare_contract(before, "classic", "1024x768", candidate=parent.candidate,
        metadata=parent.parent_metadata(), canonical_probe=parent.canonical_probe.encode())
    def poison(*args, **kwargs): raise AssertionError("Public producer alias became authority")
    with patch.object(native, "HARNESS", "public source must not be producer authority"), \
         patch.object(collector, "prepare_read_plan", poison), patch.object(context, "build_parent_context", poison):
        plan = native.prepare_native_plan(before, bound)
        request = native.prepare_request(plan, run_id="1" * 32, checkpoint_id="2" * 32, epoch_id="3" * 32,
            controller_pid=100, frequency_hz=1_000_000, origin_tick=1000, origin_ns=1)
        facts = native.inspect_request(request)
    assert facts.host_source == native.HARNESS.encode("ascii")
    assert json.loads(facts.metadata_json)["candidate_sha256"] == sha(parent.candidate)
    assert struct.unpack_from("<I", facts.request_bytes, 8)[0] == len(facts.requests)
    from dataclasses import replace
    for forged in (native.NativeRequest(request.binding_json), replace(request), {"binding_json": request.binding_json}):
        try: native.inspect_request(forged)
        except ValueError: pass
        else: raise AssertionError("Reconstructed request clone inherited issuer identity")
    assert all(value is False for value in json.loads(plan.binding_json)["claims"].values())
    assert original_path.read_bytes() == before
    assert tuple(sha(path.read_bytes()) for path in watched) == source_hashes
    print("Original-backed Classic1024 source-issued native request and hostile public aliases PASS; original/sources unchanged")


if __name__ == "__main__":
    if "--original-backed" in sys.argv:
        sys.argv.remove("--original-backed"); original_backed()
    unittest.main()
