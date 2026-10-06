"""Opt-in public synthetic V3 joined observer/outer fixture.

Portable tests inspect source only. The native test is restricted to hosted
Windows CI, an explicit opt-in and an existing external artifact parent. It
never launches Clash, supplies input, executes a probe or continues the initial
loader event. All originals, including failed compiles and native runs, remain
outside the checkout. No local compiler/native run is part of preparation.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
import hidden_soak_loader_v3 as source

OPT_IN = os.name == "nt" and os.environ.get("GITHUB_ACTIONS") == "true" and \
    os.environ.get("CLASH_LOADER_V3_ENGINE_TEST") == "1" and \
    os.environ.get("CLASH_LOADER_V3_ENGINE_INTEGRATION") == "1"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def external_parent(value):
    path = Path(value).absolute()
    if not path.is_dir() or path.resolve() != path or path == ROOT or path.is_relative_to(ROOT):
        raise ValueError("Existing literal external artifact parent required")
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)() or getattr(part.stat(), "st_file_attributes", 0)&0x400:
            raise ValueError("Reparse artifact ancestry rejected")
    return path


def reserve(path, allowance):
    usage = shutil.disk_usage(path)
    if type(allowance) is not int or allowance < source.retention_budget()["fixed_required_peak_bytes"] or usage.free-allowance <= usage.total//10:
        raise ValueError("Strict ten-percent reserve plus all known pending bytes required")


def retain_original(path, raw, allowance):
    if type(raw) is not bytes:
        raise TypeError("Whole original byte buffer required")
    reserve(path.parent, allowance+len(raw))
    with path.open("xb") as output:
        written=output.write(raw)
    if written!=len(raw):
        raise OSError("Original diagnostic write was partial; available prefix and debt retained")
    return dict(path=str(path),sha256=sha(raw),bytes=len(raw))


def retain_failure_originals(error, root, allowance):
    """Keep originals before fixture exit; absent buffers remain explicitly absent.

    The extra complete-buffer allowance is checked before each exclusive write.
    This archive copy cannot attest its own durability or erase native failure.
    """
    rows=[];debt=[]
    available=[]
    for index,row in enumerate(getattr(error,"events",())):
        for role in ("metadata","raw","footer"):
            available.append(("event-"+str(index)+"-"+role,getattr(row,role)))
    for index,(operation,observation,raw) in enumerate(getattr(error,"pending",())):
        available.append(("pending-"+str(index)+"-metadata",json.dumps(dict(operation=operation,
            observation=observation,original_available=raw is not None),sort_keys=True,
            separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")))
        if raw is not None:available.append(("pending-"+str(index)+"-raw",raw))
        else:rows.append(dict(role="pending-"+str(index)+"-raw",original_available=False))
    for role,raw in available:
        try:rows.append(dict(role=role,original_available=True,**retain_original(root/(role+".bin"),raw,allowance)))
        except BaseException as failure:
            debt.append(dict(role=role,original_bytes=len(raw) if type(raw) is bytes else None,
                error_type=type(failure).__qualname__,error=str(failure),unknown_or_partial_retention=True))
    return dict(originals=rows,debt=debt,storage_durability_verified=False)


@contextmanager
def retain_case_failure(case, root, allowance):
    """Retain the original exception before unittest.subTest can consume it."""
    try:
        yield
    except BaseException as error:
        case["error"]=dict(type=type(error).__qualname__,message=str(error))
        case["failure_retention"]=retain_failure_originals(error,root,allowance)
        raise


class EngineSourceTests(unittest.TestCase):
    def test_each_native_opt_in_is_required_before_any_path_or_native_setup(self):
        import hidden_soak_loader_v3_adapter as adapter
        class UnusedPaths:
            def __getattribute__(self,name):
                raise AssertionError("No native path may be read before all explicit opt-ins")
        baseline=dict(GITHUB_ACTIONS="true",CLASH_LOADER_V3_ENGINE_TEST="1",CLASH_LOADER_V3_ENGINE_INTEGRATION="1")
        for missing in baseline:
            environment={name:value for name,value in baseline.items() if name!=missing}
            with self.subTest(missing=missing),mock.patch.dict(os.environ,environment,clear=True),\
                 mock.patch.object(adapter.os,"name","nt"),\
                 mock.patch.object(adapter.ctypes,"WinDLL",side_effect=AssertionError("Native setup must not occur"),create=True):
                session=adapter._NativeSession.__new__(adapter._NativeSession)
                with self.assertRaisesRegex(ValueError,"explicit WIN64 synthetic CI native opt-in required"):
                    adapter._NativeSession.__init__(session,UnusedPaths(),123,fixture=True)

    def test_restricted_roles_are_exact_and_cursors_independent(self):
        text = source.render_outer_source().decode("ascii")
        self.assertIn("HANDLE list[7]", text)
        self.assertIn("PROC_THREAD_ATTRIBUTE_HANDLE_LIST,list,sizeof(list)", text)
        self.assertIn("independent_reader(challenge_reader,challenge_writer", text)
        self.assertIn("independent_reader(adoption_reader,adoption_writer", text)
        for role, access in (("stdin", "FILE_GENERIC_READ"), ("stdout", "FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES"),
                ("stderr", "FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES"), ("challenge_writer_inherited", "FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES"),
                ("adoption_reader_inherited", "FILE_GENERIC_READ"), ("challenge_event_inherited", "EVENT_MODIFY_STATE"),
                ("adoption_event_inherited", "SYNCHRONIZE")):
            self.assertIn('"'+role+'",'+access+");", text)
        self.assertIn("&h,access,TRUE,0", text)
        self.assertNotIn("DUPLICATE_SAME_ACCESS", text)
        self.assertNotIn("SetFilePointerEx", text)

    def test_handles_adopt_before_diagnostics_and_cleanup_cannot_skip(self):
        text = source.render_outer_source().decode("ascii")
        launch = text[text.index("BOOL cp=CreateProcessW"):text.index("auto hi=process_identity")]
        self.assertLess(launch.index('own(host,pi.hProcess,"observer")'), launch.index('api("CreateProcessW"'))
        self.assertLess(launch.index('own(thread,pi.hThread,"observer_thread")'), launch.index('api("CreateProcessW"'))
        self.assertIn("static void own(Owned &x,HANDLE h,const char *role) noexcept", text)
        self.assertIn("static void close_owned(Owned &x,bool desktop=false) noexcept", text)
        self.assertLess(text.index('membership(host,job,"startup")'), text.index('DWORD resume=ResumeThread'))
        self.assertIn("stop_owned(job,true)", text)
        self.assertIn("empties!=2", text)

    def test_outer_live_gate_never_polls_archive_for_target(self):
        text = source.render_outer_source().decode("ascii")
        self.assertLess(text.index("WaitForMultipleObjects(2,gate_waiters"), text.index('"live target adoption denied"'))
        self.assertLess(text.index('process_identity(target,candidate,"adopt_after"'), text.index("write_exact(adoption_writer"))
        self.assertLess(text.index("write_exact(adoption_writer"), text.index("SetEvent(adoption_event.h)"))
        self.assertNotIn("discover(", text)
        self.assertIn("original earliest hold already exhausted", text)
        self.assertIn("35*static_cast<LONGLONG>(frequency)", text)

    def test_fixed_binary_domains_and_original_read_capacity(self):
        self.assertEqual((source.GATE_HEADER.size, source.GENERATION.size, source.GATE_SIZE, source.CORE_SIZE, source.BOOT_SIZE), (32,12,576,32768,32864))
        text = source.OBSERVER_GATE_METHOD
        self.assertIn("gate_generation(s.j,s.target.value", text)
        self.assertIn('j.frame("adoption_read"', text)
        self.assertLess(text.index('j.frame("adoption_read"'), text.index("demand(rr&&got==576"))
        self.assertIn("asbytes(&adoption,sizeof(adoption))", text)
        self.assertIn("GatePacket expected=challenge", text)
        self.assertIn("expected.kind=2", text)
        self.assertIn("s.phase();s.counter();", text)
        self.assertIn("struct GateCallerGuard",source.OBSERVER_GATE_CPP)
        self.assertIn("HANDLE original=owned.value;owned.value=nullptr",source.OBSERVER_GATE_CPP)
        self.assertIn('journal.frame("gate_close_caller"',source.OBSERVER_GATE_CPP)
        self.assertIn('demand(caller_guard.close(),"original gate caller close/retention failed")',text)
        self.assertLess(text.index('demand(caller_guard.close()'),text.index('s.j.frame("gate_complete"'))
        self.assertNotIn("s.held=", text)
        outer=source.render_outer_source().decode("ascii")
        self.assertIn('{"launch_anchor",q(launch_started)}',outer)
        self.assertIn('{"timeout_counter",q(gate_timeout_counter)}',outer)
        self.assertIn('journal.frame("outer_finish_bound",q(finish_counter))',outer)
        self.assertEqual(outer.count("launch_started=tick()"),1)
        self.assertIn('journal.frame("startup_info",obj({{"bytes",n(sizeof(si))}}),bytes(&si,sizeof(si)))',outer)
        self.assertLess(outer.index('journal.frame("startup_info"'),outer.index('BOOL cp=CreateProcessW'))

    def test_budget_is_exact_and_gaps_remain_false(self):
        values = source.retention_budget()
        caller = 2*values["caller_archive_bytes"]+values["caller_pending_bytes"]+values["caller_close_original_bytes"]+values["caller_close_complete_copy_bytes"]
        outer = 2*values["outer_archive_bytes"]+values["outer_pending_original_bytes"]
        wire = 2*source.BOOT_SIZE+4*source.GATE_SIZE
        self.assertEqual(values["known_peak_bytes"], caller+outer+values["observer_peak_bytes"]+wire+values["observer_and_outer_stderr_with_complete_copies_bytes"])
        self.assertEqual(values["caller_pending_bytes"],64*1024**2)
        self.assertEqual(values["known_peak_bytes"],2111540392)
        self.assertEqual(values["source_owned_build_bytes"],512*1024**2)
        self.assertEqual(values["fixed_required_peak_bytes"],values["known_peak_bytes"]+values["source_owned_build_bytes"])
        self.assertEqual(values["fixed_required_peak_bytes"],2648411304)
        self.assertTrue(all(value is False for value in source.FALSE_CLAIMS.values()))
        self.assertTrue(values["exclusions"])

    def test_public_factory_syntax_is_closed_once(self):
        tree = ast.parse(Path(source.__file__).read_bytes())
        calls = [item for item in ast.walk(tree) if isinstance(item,ast.Call) and isinstance(item.func,ast.Name) and item.func.id=="_api_factory"]
        self.assertEqual(len(calls),1)
        self.assertEqual(tuple(item.id for item in tree.body[-1].targets[0].elts), ("prepare_plan","prepare_request","render_observer","inspect_request"))

    def test_failed_pending_buffers_preserve_absence_and_complete_bytes(self):
        class Error:
            events=()
            pending=(("timeout",dict(stream="stdout"),None),("timeout",dict(stream="stderr"),b"whole\0original"))
        retained={}
        def keep(path,raw,allowance):
            retained[path.name]=raw
            return dict(path=str(path),sha256=sha(raw),bytes=len(raw))
        with mock.patch(__name__+".retain_original",side_effect=keep):
            result=retain_failure_originals(Error(),Path("C:/fixture"),123)
        self.assertFalse(result["storage_durability_verified"])
        self.assertEqual(result["debt"],[])
        self.assertEqual(retained["pending-1-raw.bin"],b"whole\0original")
        self.assertNotIn("pending-0-raw.bin",retained)
        self.assertEqual(next(r for r in result["originals"] if r["role"]=="pending-0-raw"),
            dict(role="pending-0-raw",original_available=False))
        with mock.patch(__name__+".retain_original",side_effect=ValueError("reserve blocked")):
            failed=retain_failure_originals(Error(),Path("C:/fixture"),123)
        self.assertEqual(len(failed["debt"]),3)
        self.assertTrue(all(r["unknown_or_partial_retention"] for r in failed["debt"]))

    def test_swallowed_subtest_error_retains_original_pending_buffers(self):
        class OriginalFailure(RuntimeError):
            events=()
            pending=(("failed_native",dict(result=0,error=6),b"complete\0original\xff"),)
        case={};retained={}
        def keep(path,raw,allowance):
            retained[path.name]=raw
            return dict(path=str(path),sha256=sha(raw),bytes=len(raw))
        class SyntheticSubtest(unittest.TestCase):
            def runTest(self):
                with self.subTest(mode="explicit_model"),retain_case_failure(case,Path("C:/fixture"),123):
                    raise OriginalFailure("native original cannot be replaced by a later assertion")
        result=unittest.TestResult()
        with mock.patch(__name__+".retain_original",side_effect=keep):
            SyntheticSubtest().run(result)
        self.assertEqual(len(result.errors),1)
        self.assertEqual(case["error"]["type"],OriginalFailure.__qualname__)
        self.assertEqual(retained["pending-0-raw.bin"],b"complete\0original\xff")
        self.assertFalse(case["failure_retention"]["storage_durability_verified"])
        self.assertEqual(case["failure_retention"]["debt"],[])


@unittest.skipUnless(OPT_IN, "Explicit hosted Windows synthetic opt-in required")
class NativeEngineTests(unittest.TestCase):
    """Exactly one joined native test; eleven source-owned cases retained."""
    def test_joined_terminate_only_initial_loader(self):
        import hidden_soak_loader_v3_adapter as adapter
        parent = external_parent(os.environ["CLASH_LOADER_V3_ARTIFACT_DIR"])
        # The source-owned fixed build allowance cannot be reduced by a caller's
        # asset declaration. Over-capacity originals remain explicit debt.
        allowance = source.retention_budget()["fixed_required_peak_bytes"]
        reserve(parent,allowance)
        root = parent/("loader-v3-"+uuid.uuid4().hex)
        root.mkdir()
        report = dict(schema="synthetic_loader_v3_engine", fixture_only=True,
            native_engine_fixture_completed=False, cases=[], source_hashes={}, limitations=[
                "Terminate-only initial loader; no map readiness or endurance",
                "Earliest callback20s includes comparison and actual post-EndSession QPC; subsequent cleanup is separate",
                "Original main IO receipts do not attest receipt-tail or independent storage durability",
                "File hashes do not establish loaded producer or whole candidate/probe contents"], **source.FALSE_CLAIMS)
        report_path = root/"engine-report.json"
        try:
            for name in ("hidden_soak_loader_v3.py","hidden_soak_loader_v3_adapter.py",
                         "test_hidden_soak_loader_v3.py","test_hidden_soak_loader_v3_engine.py"):
                report["source_hashes"][name] = sha((ROOT/"tools"/name).read_bytes())
            for mode in range(11):
                case_root = root/("case-"+str(mode));reserve(root,allowance);case_root.mkdir()
                case = dict(mode=mode, completed=False, expected_success=mode==0)
                report["cases"].append(case)
                with self.subTest(mode=mode),retain_case_failure(case,case_root,allowance):
                    paths = adapter.NativePaths(root=str(case_root),candidate=str(case_root/"synthetic-loader.exe"),
                        compiler_x64=os.environ["CLASH_V3_CL_X64"],compiler_x86=os.environ["CLASH_V3_CL_X86"],
                        environment_x64=os.environ["CLASH_V3_ENV_X64"],environment_x86=os.environ["CLASH_V3_ENV_X86"],
                        approved_peak_bytes=allowance,runtime_asset_bytes=0)
                    fixture = adapter.prepare_synthetic_plan(mode=mode)
                    build = adapter.compile_outer(fixture,paths)
                    suspended = adapter.create_outer(build)
                    observer = adapter.prepare_observer(suspended)
                    launch = adapter.finalize_bootstrap(observer)
                    originals = adapter.resume_and_collect(launch)
                    case["caller_close_original"]=retain_original(case_root/"caller-close-original.json",
                        originals.caller_close_receipt,allowance)
                    parsed = adapter.parse_joined(originals,launch)
                    replay_result=adapter.replay_joined(parsed)
                    replay = replay_result.report()
                    case["replay_original"]=retain_original(case_root/"joined-replay.json",
                        replay_result.report_json.encode("ascii"),allowance)
                    case.update(replay)
                    self.assertIs(replay["scoped_composition_complete"],mode==0)
                    self.assertTrue(all(replay[key] is False for key in source.FALSE_CLAIMS))
                    if mode:
                        self.assertIn(adapter.SYNTHETIC_FAILURES[mode], replay["original_failure_kinds"])
                    else:
                        self.assertEqual(replay["immutable_read_count"],replay["required_read_count"])
                        self.assertTrue(replay["live_adoption_before_first_read"])
                    case["completed"] = True
            self.assertEqual(len(report["cases"]),11)
            self.assertTrue(all(row["completed"] for row in report["cases"]))
            report["native_engine_fixture_completed"] = True
        except BaseException as error:
            report["error"] = dict(type=type(error).__qualname__,message=str(error))
            if "case_root" in locals():
                report["failure_retention"]=retain_failure_originals(error,case_root,allowance)
            raise
        finally:
            reserve(root,allowance)
            report_path.write_text(json.dumps(report,sort_keys=True,indent=2),encoding="ascii")


if __name__ == "__main__":
    unittest.main()
