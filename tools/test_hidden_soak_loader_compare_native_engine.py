"""Portable source assertions and an explicit Windows-CI-only synthetic case.

Local invocation never compiles, launches or writes runtime artifacts. The CI
case uses a marked public PE and a separate fixture registry, never production
canonical authority. Every original compiler/archive/error file is retained.
"""
from __future__ import annotations

import ctypes as C
from dataclasses import fields
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
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import hidden_soak_loader_compare_native as native

ENGINE_OPT_IN = (os.name == "nt" and os.environ.get("GITHUB_ACTIONS") == "true" and
                 os.environ.get("CLASH_LOADER_COMPARE_ENGINE_INTEGRATION") == "1")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require_space(path, additional):
    total, _, free = shutil.disk_usage(path)
    if free <= total // 10 or free - additional <= total // 10:
        raise AssertionError("Strict >10% reserve plus complete native fixture allowance required")


def compiler_timeout(error, retain):
    if type(error) is not subprocess.TimeoutExpired:
        raise TypeError("Original TimeoutExpired required")
    result = dict(type_name=type(error).__name__, command=error.cmd, timeout_seconds=error.timeout,
                  unavailable_or_unread_remainder=True)
    for name, value in (("stdout", error.stdout), ("stderr", error.stderr)):
        if value is None:
            result[name] = dict(original_bytes_available=False, unavailable=True)
        else:
            if type(value) is not bytes:
                raise TypeError("Original binary timeout buffer required")
            result[name] = dict(original_bytes_available=True, bytes=len(value), sha256=sha(value), path=str(retain(name, value)))
    return result


class EngineSourceTests(unittest.TestCase):
    def test_fixed_source_comparison_happens_before_stop_and_no_native_commands(self):
        import hidden_soak_loader_native as v1
        text = native._render(v1.HARNESS, {}, bytes(native.REQUEST_SIZE), b"fixture").decode("ascii")
        for forbidden in ("SetExecutionStatus(", "Execute(", "AddBreakpoint(", "WriteVirtual(",
                          "AttachProcess(", "ReadProcessMemory(", "Sleep(", "CreateNamedPipe", "socket("):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("raw.resize(actual)", text)
        read = text[text.index("void read(ULONG ordinal"):text.index("static void callback_error")]
        self.assertLess(read.index('j.frame("read_virtual_capacity"'), read.index("demand(hr==S_OK&&actual==size"))
        self.assertLess(read.index('j.frame("comparison_result"'), read.index("demand(after_valid"))
        self.assertIn("original_before,original_after", read)
        self.assertIn("ULONG delta=static_cast<ULONG>(base)-r.preferred", read)
        self.assertIn("observed==base", read)
        self.assertLess(text.index('s.j.frame("comparison_complete"'), text.index("EndSession(DEBUG_END_ACTIVE_TERMINATE)"))
        self.assertIn("stopped-s.held<=20*s.r.frequency", text)
        self.assertEqual(text.count("s.held=tick"), 1)
        self.assertIn("Footer append", native.retention_budget()["receipt_tail"])

    def test_exact_allocation_and_false_claim_scope(self):
        p = native.retention_budget()
        self.assertEqual((native.REQUEST_SIZE, native.IO_FOOTER.size, native.COMPARISON_RECORD.size), (320, 24, 64))
        self.assertEqual(p["extra_comparison_metadata_bytes"], 4735000)
        self.assertEqual(p["maximum_footer_bytes"], 786432)
        self.assertEqual(p["known_peak_bytes"], 112870182)
        self.assertEqual(p["native_journal_peak_bytes"], p["failure_raw_bytes"] + 2 * p["failure_metadata_bytes"])
        self.assertTrue(native.FALSE_CLAIMS)
        self.assertTrue(all(value is False for value in native.FALSE_CLAIMS.values()))
        self.assertIn("storage_durability_verified", native.FALSE_CLAIMS)
        self.assertIn("loaded_candidate_verified", native.FALSE_CLAIMS)

    def test_timeout_original_partial_and_unavailable_buffers(self):
        original = b"compiler partial\x00\xff"; retained = []
        result = compiler_timeout(subprocess.TimeoutExpired(["x86-cl"], 90, output=original, stderr=None),
                                  lambda name, raw: retained.append((name, raw)) or ("external/" + name))
        self.assertEqual(retained, [("stdout", original)])
        self.assertEqual(result["stdout"]["sha256"], sha(original))
        self.assertEqual(result["stderr"], dict(original_bytes_available=False, unavailable=True))

    def test_second_factory_call_rejects_before_private_execution(self):
        raw = Path(native.__file__).read_bytes()
        terminal = b"prepare_comparison_plan, prepare_comparison_request, inspect_comparison_request = _factory()"
        self.assertEqual(raw.count(terminal), 1)
        changed = raw.replace(terminal, b"_factory()\n" + terminal)
        before = set(sys.modules)
        with self.assertRaisesRegex(ValueError, "only the authenticated terminal factory"):
            native._closed_preparation(changed, Path(native.__file__))
        self.assertEqual(set(sys.modules), before)

    def test_production_admission_ignores_hostile_public_source_aliases(self):
        def substituted(*args, **kwargs):
            self.fail("Substituted public source helper was executed")
        # Invalid original material is deliberately used: this is a source
        # admission rejection test, never a synthetic production capability.
        with self.assertRaises(ValueError) as baseline:
            native.prepare_comparison_plan(b"not an original executable", None)
        before = set(sys.modules)
        with mock.patch.multiple(native, ROOT=Path("C:/substituted"), SOURCE="substituted.py",
                ADAPTER="substituted-adapter.py", EXPECTED="substituted-expected.py", V1="substituted-v1.py",
                EXPECTED_SHA256="0" * 64, V1_SHA256="0" * 64, REQUEST_SIZE=1,
                _private_preparation=substituted, _sha=substituted, types=object(), sys=object(),
                uuid=object(), hashlib=object()):
            with self.assertRaises(ValueError) as rejection:
                native.prepare_comparison_plan(b"not an original executable", None)
        self.assertEqual(str(rejection.exception), str(baseline.exception))
        self.assertEqual(set(sys.modules), before)

    def test_magic_write_and_flush_failure_receipts_survive_before_a_usable_journal(self):
        import hidden_soak_loader_native as v1
        text = native._render(v1.HARNESS, {}, bytes(native.REQUEST_SIZE), b"fixture").decode("ascii")
        begin = text[text.index("void begin()"):text.index("void frame(")]
        self.assertLess(begin.index("auto original=object"), begin.index("if(!written||got!=8||!flushed)"))
        for name, expression in (("write_return", "signed_number(written)"), ("write_error", "number(error)"),
                                 ("flush_return", "signed_number(flushed)"), ("flush_error", "number(flush_error)")):
            self.assertIn('{"' + name + '",' + expression + '}', begin)
        self.assertIn('write_failed?"WriteFile.archive_magic":"FlushFileBuffers.archive_magic"', begin)
        self.assertIn("write_failed?written:flushed", begin)
        self.assertIn("write_failed?error:flush_error", begin)
        self.assertIn("Bytes{'C','L','H','D','C','R','2',0}", begin)
        self.assertIn('{"detail_hex",quote(hex(original.data(),original.size()))}', begin)
        self.assertLess(begin.index('fprintf(stderr,"MAGIC_IO_DEBT'), begin.index("throw failure;"))
        self.assertLess(begin.index("throw failure;"), begin.index('frame("archive_magic_io",original)'))


@unittest.skipUnless(ENGINE_OPT_IN, "Explicit Windows synthetic CI opt-in required")
class NativeEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import owned_hidden_process as owned
        import hidden_soak_loader_compare_native_adapter as wire
        import hidden_soak_loader_expected as expected
        import hidden_soak_loaded_image as image
        import test_framed_loaded_probe_engine as synthetic
        import test_hidden_soak_loader_native_engine as predecessor
        cls.owned, cls.wire, cls.expected, cls.image, cls.synthetic = owned, wire, expected, image, synthetic
        cls.generation, cls.clock = predecessor.NativeEngineTests.generation, predecessor.NativeEngineTests.clock
        root = os.environ.get("CLASH_LOADER_COMPARE_ARTIFACT_DIR")
        if not root:
            raise AssertionError("Explicit preexisting external artifact parent required")
        base = Path(root).absolute()
        if base.resolve() != base or base == ROOT or base.is_relative_to(ROOT) or not base.is_dir():
            raise AssertionError("External literal existing artifact parent required")
        for path in (base, *base.parents):
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)() or getattr(path.stat(), "st_file_attributes", 0) & 0x400:
                raise AssertionError("Reparse/symlink artifact parent rejected")
        cls.allowance = native.retention_budget()["known_peak_bytes"] + 256 * 1024**2
        require_space(base, cls.allowance)
        cls.root = base / ("loader-compare-native-" + uuid.uuid4().hex); cls.root.mkdir()
        cls.records, cls.fixture_completed = [], False
        cls.addClassCleanup(cls.save_report)
        cls.kernel = C.WinDLL("kernel32", use_last_error=True)
        for name, args, result in (
            ("OpenProcess", [C.c_uint32, C.c_int32, C.c_uint32], C.c_void_p),
            ("GetProcessId", [C.c_void_p], C.c_uint32),
            ("GetProcessTimes", [C.c_void_p] + [C.POINTER(C.c_uint64)] * 4, C.c_int32),
            ("QueryFullProcessImageNameW", [C.c_void_p, C.c_uint32, C.c_wchar_p, C.POINTER(C.c_uint32)], C.c_int32),
            ("WaitForSingleObject", [C.c_void_p, C.c_uint32], C.c_uint32),
            ("CloseHandle", [C.c_void_p], C.c_int32),
            ("QueryPerformanceFrequency", [C.POINTER(C.c_int64)], C.c_int32),
            ("QueryPerformanceCounter", [C.POINTER(C.c_int64)], C.c_int32)):
            fn = getattr(cls.kernel, name); fn.argtypes, fn.restype = args, result

    @classmethod
    def save_report(cls):
        if not hasattr(cls, "root"):
            return
        require_space(cls.root, 1024**2)
        report = dict(schema="synthetic_loader_compare_native_engine_v2", fixture_only=True,
            producer_source_sha256=sha(Path(native.__file__).read_bytes()),
            native_engine_fixture_completed=cls.fixture_completed, cases=cls.records,
            expected_issuer_source_sha256=sha((ROOT / native.EXPECTED).read_bytes()), **native.FALSE_CLAIMS)
        (cls.root / "engine-report.json").write_text(json.dumps(report, sort_keys=True, indent=2), encoding="ascii")

    def test_original_in_hold_comparison_and_live_retained_generation(self):
        import hidden_soak_loader_native as v1
        import test_hidden_soak_loaded_image as image_fixture
        data, _, _ = self.synthetic.executable_fixture("1024x768")
        candidate = self.root / "synthetic-loader.exe"; require_space(self.root, self.allowance); candidate.write_bytes(data)
        bound = image_fixture.contract(data)
        frequency, origin = self.clock()
        authority = self.expected.PayloadAuthority(*(uuid.uuid4().hex for _ in range(3)), os.getpid(), frequency, origin, 100)
        # The isolated fixture registry cannot mint public production requests.
        def preparation(original, contract, imported):
            state = self.expected._build_state(contract, oracle=self.image, pe=self.synthetic.probe.pe,
                issuer_sha256=sha((ROOT / native.EXPECTED).read_bytes()), check_sources=lambda: None)
            def issue(owned):
                metadata, payload = self.expected._encode(state, owned)
                decoded, descriptors, fixups, raw = self.expected._decode(payload)
                def model(base): return self.expected._model(payload, base)
                return decoded, payload, descriptors, fixups, raw, model, sha(imported)
            return issue, v1.HARNESS, lambda: None, sha(imported), sha((ROOT / native.ADAPTER).read_bytes())
        prepare, issue, inspect = native._factory(_preparation=preparation)
        request = issue(prepare(b"marked synthetic, not production authority", bound), authority)
        facts = inspect(request); metadata = json.loads(facts.metadata_json)
        with self.assertRaises(ValueError): native.inspect_comparison_request(request)
        request_path, payload_path = self.root / "request.bin", self.root / "expected.bin"
        require_space(self.root, self.allowance); request_path.write_bytes(facts.request_bytes); payload_path.write_bytes(facts.expected_payload)
        source, runner = self.root / "host.cpp", self.root / "host.exe"
        source.write_bytes(facts.host_source)
        compiler = shutil.which("cl.exe")
        if not compiler: raise AssertionError("Explicit x86 MSVC compiler environment required")
        command = [compiler, "/nologo", "/EHsc", "/std:c++17", "/W4", "/O2", "/MT", str(source),
                   "/Fe:" + str(runner), "/Fo:" + str(self.root / "host.obj"), "/link", "/MACHINE:X86", "bcrypt.lib"]
        try:
            compiled = subprocess.run(command, cwd=self.root, capture_output=True, timeout=90,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired as error:
            def retain(name, raw):
                require_space(self.root, len(raw) + 1024**2)
                path = self.root / ("compiler-" + name + "-timeout.bin"); path.write_bytes(raw); return path
            receipt = compiler_timeout(error, retain); self.records.append(dict(original_compiler_timeout=receipt))
            (self.root / "compiler-timeout.json").write_text(json.dumps(receipt, sort_keys=True), encoding="ascii")
            raise
        (self.root / "compiler-stdout.bin").write_bytes(compiled.stdout)
        (self.root / "compiler-stderr.bin").write_bytes(compiled.stderr)
        self.records.append(dict(original_compiler_returncode=compiled.returncode, command=command,
            generated_source_sha256=sha(source.read_bytes()), expected_payload_sha256=sha(payload_path.read_bytes()),
            request_sha256=sha(request_path.read_bytes())))
        self.assertEqual(compiled.returncode, 0, "Complete original compiler files retained")
        self.assertEqual(source.read_bytes(), facts.host_source)
        self.assertEqual(runner.read_bytes()[:2], b"MZ")
        host_sha = sha(runner.read_bytes()); archive_path = self.root / "original-stdout.bin"
        raw, retained, adoption = b"", None, None
        try:
            require_space(self.root, self.allowance)
            with archive_path.open("xb", buffering=0) as output:
                with self.owned.OwnedHiddenProcess([str(runner), str(candidate), str(request_path), str(payload_path)],
                        self.root, dict(os.environ), output) as host:
                    host_generation = self.generation(host._info.hProcess, host.pid, runner)
                    deadline = time.monotonic() + 35
                    while time.monotonic() < deadline:
                        raw = archive_path.read_bytes(); offset = len(native.ARCHIVE_MAGIC)
                        if raw.startswith(native.ARCHIVE_MAGIC):
                            while offset + 8 <= len(raw):
                                jsize, rsize = struct.unpack_from("<II", raw, offset)
                                if jsize > native.MAX_FRAME_JSON or rsize > native.MAX_FRAME_RAW:
                                    self.fail("Original capacity violation; complete archive retained")
                                end = offset + 8 + jsize + rsize + native.IO_FOOTER.size
                                if end > len(raw): break
                                packet = json.loads(raw[offset + 8:offset + 8 + jsize].decode("ascii"))
                                if packet["operation"] == "callback_create" and retained is None:
                                    discovery = packet["data"]; C.set_last_error(0)
                                    retained = self.kernel.OpenProcess(0x1000 | 0x100000, 0, discovery["pid"])
                                    error = C.get_last_error(); self.records.append(dict(original_parent_open=dict(
                                        pid=discovery["pid"], handle=retained, error=error)))
                                    self.assertTrue(retained, "Target vanished before independent retained-generation observation")
                                    self.assertEqual(error, 0); adoption = self.generation(retained, discovery["pid"], candidate)
                                offset = end
                        if host.poll() is not None: break
                        time.sleep(0.001)  # Polling grants no ownership or holding proof.
                    exit_code = host.wait(5); raw = archive_path.read_bytes()
                    self.assertEqual(exit_code, 0, "Complete original archive/host diagnostics retained")
                    self.assertIsNotNone(adoption, "After-exit bytes cannot prove original retained generation")
            external_values = dict(metadata, candidate_file_sha256=sha(data), host_file_sha256=host_sha,
                archive_sha256=sha(raw), archive_size=len(raw), native_exit_code=exit_code)
            external = self.wire.ArchiveAuthority(**{row.name: external_values[row.name]
                                                    for row in fields(self.wire.ArchiveAuthority)})
            result = self.wire.replay_fixture_archive(raw, facts, external).report()
            self.assertTrue(result["immutable_comparison_replay_passed"], result)
            frames = self.wire.parse_frames(raw)
            create = next(row.data() for row in frames if row.operation == "callback_create")
            self.assertEqual(create["pid"], adoption.pid)
            for row in frames:
                if row.operation in ("startup_owner", "owner"):
                    observed = row.data()
                    self.assertEqual((observed["target"]["pid"], observed["target"]["creation_filetime"]),
                                     (adoption.pid, adoption.creation_filetime))
                    self.assertEqual((observed["debugger"]["pid"], observed["debugger"]["creation_filetime"]),
                                     (host_generation.pid, host_generation.creation_filetime))
            reads = [row for row in frames if row.operation == "read_virtual_capacity"]
            mapped = self.synthetic.fixtures.mapped(data, create["base_offset"])
            self.assertEqual(struct.unpack("<I", reads[0].raw)[0], create["base_offset"])
            for row, descriptor in zip(reads[1:], facts.descriptors):
                self.assertEqual(row.raw, bytes(mapped[descriptor[1]:descriptor[1] + descriptor[2]]))
            self.records.append(dict(original_archive_path=str(archive_path), original_archive_sha256=sha(raw),
                generated_source_sha256=sha(facts.host_source), compiled_host_sha256=host_sha,
                retained_host=dict(pid=host_generation.pid, creation_filetime=host_generation.creation_filetime),
                retained_target=dict(pid=adoption.pid, creation_filetime=adoption.creation_filetime),
                synthetic_native_immutable_comparison_replayed=True, source_comparison_report=result,
                storage_durability_verified=False, native_job_cleanup_verified=False, host_cleanup_complete=False))
        finally:
            if retained:
                C.set_last_error(0); closed = self.kernel.CloseHandle(retained); error = C.get_last_error()
                self.records.append(dict(original_parent_close=dict(native_return=closed, native_error=error)))
                self.assertEqual((closed, error), (1, 0))
        type(self).fixture_completed = True


if __name__ == "__main__":
    unittest.main()
