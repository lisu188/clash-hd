#!/usr/bin/env python3
"""Pure mocked lease/receipt tests; never load native adapters or stop processes."""
from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hidden_soak_process_lease as lease

REAL_SOURCE = Path(lease.__file__).resolve()
MOCK_SOURCE = Path("C:/fixture/tools/hidden_soak_process_lease.py")


@dataclass
class Process:
    generation: lease.Generation
    parent_pid: int
    alive: bool = True
    exit_code: int = 259


@dataclass(eq=False)
class Handle:
    process: Process
    closed: bool = False


class MockAdapter:
    def __init__(self):
        self.root = Process(lease.Generation(1, 100, "C:/host/python.exe", "a"*64), 0)
        self.debugger = Process(lease.Generation(33, 200, "C:/tools/cdb.exe", "b"*64), 1)
        self.candidate = Process(lease.Generation(7, 300, "C:/ClashTests/run/candidate.exe", "c"*64), 33)
        self.table = {row.generation.pid:row for row in (self.root,self.debugger,self.candidate)}
        self.sources = {lease._path(str(MOCK_SOURCE)):hashlib.sha256(REAL_SOURCE.read_bytes()).hexdigest()}
        self.calls, self.handles = [], []
        self.hook = None
        self.open_denied, self.terminate_denied, self.wait_timeout, self.close_denied = set(),set(),set(),set()

    def step(self, name, value=None):
        self.calls.append((name,value))
        if self.hook: self.hook(self,name,value)

    def current_pid(self): return 1
    def source_sha256(self,path): self.step("source",path); return self.sources[path]

    def open_process(self,pid):
        self.step("open",pid)
        if pid in self.open_denied or pid not in self.table: raise OSError("open denied/gone")
        handle=Handle(self.table[pid]); self.handles.append(handle); return handle

    def observe(self,handle):
        assert type(handle) is Handle and not handle.closed, "operation requires actual retained handle"
        self.step("observe",handle)
        row=handle.process
        return lease.Observation(row.generation,row.parent_pid,258 if row.alive else 0,
                                 None if row.alive else row.exit_code,0 if row.alive else row.generation.creation_filetime+1000)

    def parent_generation(self,handle):
        assert type(handle) is Handle and not handle.closed
        self.step("parent",handle)
        parent=self.table.get(handle.process.parent_pid)
        if parent is None: raise OSError("parent vanished")
        return parent.generation

    def enumerate(self,parents,known):
        self.step("enumerate",(parents,known))
        return tuple(lease.Snapshot(row.generation.pid,row.parent_pid,self.observe(Handle(row)))
                     for row in self.table.values() if row.alive and (row.parent_pid in parents or row.generation.pid in known))

    def terminate(self,handle):
        assert type(handle) is Handle and not handle.closed, "never terminate by reusable PID"
        self.step("terminate",handle)
        if handle.process.generation.pid in self.terminate_denied:
            return {"return_value":0,"error_code":5}
        handle.process.alive=False
        return {"return_value":1,"error_code":0}

    def wait(self,handle,milliseconds):
        assert type(handle) is Handle and not handle.closed
        self.step("wait",handle)
        if handle.process.generation.pid in self.wait_timeout:
            return {"wait_result":258,"error_code":0,"exit_code":None}
        if handle.process.alive:
            return {"wait_result":258,"error_code":0,"exit_code":None}
        return {"wait_result":0,"error_code":0,"exit_code":handle.process.exit_code}

    def close(self,handle):
        assert type(handle) is Handle and not handle.closed, "double-close attempt"
        self.step("close",handle); handle.closed=True
        denied=handle.process.generation.pid in self.close_denied
        return [{"kind":"process","return_value":0 if denied else 1,"error_code":5 if denied else 0}]

    def authority(self):
        return lease.RunAuthority("0123456789abcdef0123456789abcdef","c"*64,"d"*64,"modalwidgets",
            "1920x1080","fixture-validation",self.root.generation,
            (lease.ImageAuthority("debugger",self.debugger.generation.image_path,"b"*64),
             lease.ImageAuthority("candidate",self.candidate.generation.image_path,"c"*64)),
            tuple(lease.SourcePin(path,digest) for path,digest in self.sources.items()))


def collection(adapter=None, **options):
    adapter=adapter or MockAdapter(); authority=adapter.authority()
    manager=lease.ProcessLeases(authority,adapter,**options)
    debugger=manager.adopt(adapter.debugger.generation,"debugger")
    return adapter,authority,manager,debugger


def reseal(report):
    report=deepcopy(report)
    report.pop("owned_handles_cleanup_verified",None); report.pop("failures",None)
    for i,event in enumerate(report["events"]):
        event["sequence"]=i; event["monotonic_ns"]=i
    return report


class LeaseTests(unittest.TestCase):
    def setUp(self):
        # The production authority models Windows paths. Its actual module
        # bytes remain read from this checkout; only the fixture's path identity
        # is replaced, for the lifetime of one mocked test, on either OS.
        source_patch=patch.object(lease,"SOURCE",MOCK_SOURCE)
        source_patch.start(); self.addCleanup(source_patch.stop)

    def test_native_file_identity_helper_with_fully_mocked_files(self):
        class Stream(io.BytesIO):
            def fileno(self): return 501
        for case in ("good","open","grow","shrink","mutation","alias","late_alias","reparse","large","directory"):
            with self.subTest(case=case):
                info=SimpleNamespace(st_dev=1,st_ino=2,st_size=3,st_mtime_ns=1,
                    st_mode=stat.S_IFDIR if case=="directory" else stat.S_IFREG,
                    st_file_attributes=0x400 if case=="reparse" else 0)
                if case=="large": info.st_size=256*1024*1024+1
                changed=SimpleNamespace(**vars(info)); changed.st_mtime_ns=2
                opened=SimpleNamespace(**vars(info)); opened.st_ino=3
                class File:
                    parents=()
                    resolves=0
                    def __str__(self): return "C:/fixture/source.py"
                    def lstat(self): return info
                    def stat(self): return info
                    def resolve(self,strict):
                        self.resolves+=1
                        return "C:/outside/alias.py" if case=="alias" or case=="late_alias" and self.resolves==2 else str(self)
                    def open(self,mode): return Stream(b"abcxyz" if case=="grow" else b"ab" if case=="shrink" else b"abc")
                file=File()
                with patch.object(lease,"Path",lambda value:file), patch.object(lease.os,"fstat",
                    side_effect=[opened if case=="open" else info,changed if case=="mutation" else info]):
                    if case=="good":
                        self.assertEqual(lease.WindowsAdapter.source_sha256(str(file)),hashlib.sha256(b"abc").hexdigest())
                    else:
                        with self.assertRaises(ValueError): lease.WindowsAdapter.source_sha256(str(file))

    def test_signalled_native_handle_never_queries_reused_parent_pid(self):
        native=object.__new__(lease.WindowsAdapter)  # no WindowsAdapter.__init__/kernel32
        native._parents={5:33}
        def forbidden(): raise AssertionError("signalled handle must not enumerate reusable PID")
        native._entries=forbidden
        self.assertEqual(native._parent_pid(5,exited=True),33)
        self.assertEqual(native._parent_pid(6,exited=True),0)
        native._handles={5:True}
        native.k=SimpleNamespace(OpenProcess=lambda rights,inherit,pid:5)
        self.assertEqual(native.open_process(7),5)
        self.assertNotIn(5,native._parents)
        self.assertIs(native._handles[5],False)

    def test_debugger_first_handles_and_scoped_receipts(self):
        adapter,authority,manager,debugger=collection()
        report=manager.cleanup()
        self.assertTrue(report["owned_handles_cleanup_verified"],report["failures"])
        self.assertFalse(report["host_cleanup_complete"])
        self.assertFalse(report["release_acceptance"])
        stopped=[handle.process.generation.pid for op,handle in adapter.calls if op=="terminate"]
        self.assertEqual(stopped,[33,7])
        self.assertTrue(all(handle.closed for handle in adapter.handles))
        before=len(adapter.calls)
        self.assertEqual(manager.cleanup(),report)
        self.assertEqual(len(adapter.calls),before)
        loaded=lease.load_receipts(json.dumps(report).encode())
        self.assertTrue(lease.replay_receipts(loaded,authority)["owned_handles_cleanup_verified"])

    def test_vanished_owned_process_uses_signalled_handle_and_exit259(self):
        adapter,authority,manager,debugger=collection()
        manager.adopt(adapter.candidate.generation,"candidate",debugger)
        adapter.debugger.alive=False; adapter.candidate.alive=False
        report=manager.cleanup()
        self.assertTrue(report["owned_handles_cleanup_verified"],report["failures"])
        self.assertEqual([op for op,_ in adapter.calls if op=="terminate"],[])

    def test_open_and_parent_denials_close_partial_handles(self):
        for kind in ("open","parent","path"):
            with self.subTest(kind=kind):
                adapter=MockAdapter(); manager=lease.ProcessLeases(adapter.authority(),adapter)
                if kind=="open": adapter.open_denied.add(33)
                elif kind=="parent": adapter.debugger.parent_pid=999
                else: adapter.debugger.generation=replace(adapter.debugger.generation,image_path="C:/other/cdb.exe")
                expected=lease.Generation(33,200,"C:/tools/cdb.exe","b"*64)
                self.assertIsNone(manager.adopt(expected,"debugger"))
                report=manager.cleanup()
                self.assertFalse(report["owned_handles_cleanup_verified"])
                self.assertTrue(all(handle.closed for handle in adapter.handles))
                self.assertFalse(any(op=="terminate" for op,_ in adapter.calls))

    def test_parent_pid_reuse_is_not_parent_generation(self):
        adapter,authority,manager,debugger=collection()
        adapter.table[33]=Process(replace(adapter.debugger.generation,creation_filetime=250),1)
        self.assertIsNone(manager.adopt(adapter.candidate.generation,"candidate",debugger))
        self.assertFalse(manager.cleanup()["owned_handles_cleanup_verified"])

    def test_child_mutations_during_open_and_parent_attestation_reject(self):
        for when in ("open","parent"):
            with self.subTest(when=when):
                adapter,authority,manager,debugger=collection()
                expected=adapter.candidate.generation
                def mutate(mock,name,value):
                    if name==when and ((name=="open" and value==7) or (name=="parent" and value.process is mock.candidate)):
                        mock.candidate.generation=replace(expected,creation_filetime=350)
                adapter.hook=mutate
                self.assertIsNone(manager.adopt(expected,"candidate",debugger))
                adapter.hook=None
                self.assertFalse(manager.cleanup()["owned_handles_cleanup_verified"])

    def test_source_change_denies_borrow_and_retains_failure(self):
        adapter,authority,manager,debugger=collection()
        adapter.sources[next(iter(adapter.sources))]="0"*64
        with self.assertRaises(ValueError): manager.attested_handle(debugger)
        report=manager.cleanup()
        self.assertFalse(report["owned_handles_cleanup_verified"])
        self.assertTrue(all(handle.closed for handle in adapter.handles))
        self.assertTrue(any("source" in row for row in report["failures"]))

    def test_identity_mutation_before_terminate_never_stops_reused_generation(self):
        adapter,authority,manager,debugger=collection()
        expected=adapter.debugger.generation
        def mutate(mock,name,value):
            if name=="observe" and value.process is mock.debugger:
                mock.debugger.generation=replace(expected,creation_filetime=500)
        adapter.hook=mutate
        report=manager.cleanup()
        self.assertFalse(report["owned_handles_cleanup_verified"])
        self.assertFalse(any(op=="terminate" and handle.process is adapter.debugger for op,handle in adapter.calls))

    def test_termination_wait_and_close_native_failures_stay_failed(self):
        for field in ("terminate_denied","wait_timeout","close_denied"):
            with self.subTest(field=field):
                adapter,authority,manager,debugger=collection()
                getattr(adapter,field).add(33)
                report=manager.cleanup()
                self.assertFalse(report["owned_handles_cleanup_verified"],report)
                self.assertTrue(all(handle.closed for handle in adapter.handles))

    def test_late_child_of_exited_parent_is_never_adopted_or_stopped(self):
        adapter,authority,manager,debugger=collection()
        adapter.table.pop(7)
        def late(mock,name,value):
            if name=="terminate" and value.process is mock.debugger:
                mock.table[7]=mock.candidate
        adapter.hook=late
        report=manager.cleanup()
        self.assertFalse(report["owned_handles_cleanup_verified"])
        self.assertTrue(adapter.candidate.alive)
        self.assertFalse(any(op=="terminate" and handle.process is adapter.candidate for op,handle in adapter.calls))
        self.assertTrue(any("vanished" in failure for failure in report["failures"]))

    def test_bounded_adoption_reconciliation_and_duplicate_snapshot(self):
        adapter,authority,manager,debugger=collection(max_adoptions=1)
        self.assertFalse(manager.cleanup()["owned_handles_cleanup_verified"])
        adapter,authority,manager,debugger=collection()
        original=adapter.enumerate
        adapter.enumerate=lambda parents,known: original(parents,known)*2
        self.assertFalse(manager.cleanup()["owned_handles_cleanup_verified"])

    def test_failed_adoptions_are_bounded_and_receipt_exhaustion_still_closes(self):
        adapter=MockAdapter(); authority=adapter.authority()
        adapter.open_denied.add(33)
        manager=lease.ProcessLeases(authority,adapter,max_adoptions=1)
        for _ in range(1000): self.assertIsNone(manager.adopt(adapter.debugger.generation,"debugger"))
        self.assertEqual(sum(op=="open" for op,_ in adapter.calls),2)
        report=manager.cleanup()
        self.assertFalse(report["owned_handles_cleanup_verified"])
        self.assertTrue(all(handle.closed for handle in adapter.handles))
        adapter,authority,manager,debugger=collection()
        exhausted=False
        for _ in range(lease.MAX_EVENTS):
            try: manager.attested_handle(debugger)
            except ValueError:
                exhausted=True; break
        self.assertTrue(exhausted)
        report=manager.cleanup()
        self.assertFalse(report["owned_handles_cleanup_verified"])
        self.assertTrue(all(handle.closed for handle in adapter.handles))
        self.assertLessEqual(len(json.dumps(report).encode()),lease.MAX_JSON_BYTES)
        self.assertTrue(any("budget" in row for row in report["failures"]))

    def test_sources_changing_between_snapshot_and_open_prevent_adoption(self):
        adapter,authority,manager,debugger=collection()
        def change(mock,name,value):
            if name=="enumerate": mock.sources[next(iter(mock.sources))]="0"*64
        adapter.hook=change
        report=manager.cleanup()
        self.assertFalse(report["owned_handles_cleanup_verified"])
        self.assertFalse(any(op=="open" and value==7 for op,value in adapter.calls))
        self.assertFalse(any(op=="terminate" for op,_ in adapter.calls))
        self.assertTrue(all(handle.closed for handle in adapter.handles))

    def test_pid_reuse_during_terminate_keeps_owned_handle_and_rejects_final_reuse(self):
        adapter,authority,manager,debugger=collection()
        replacement=Process(replace(adapter.debugger.generation,creation_filetime=500),1)
        def reuse(mock,name,value):
            if name=="terminate" and value.process is mock.debugger: mock.table[33]=replacement
        adapter.hook=reuse
        report=manager.cleanup()
        self.assertFalse(report["owned_handles_cleanup_verified"])
        self.assertFalse(adapter.debugger.alive)
        self.assertTrue(replacement.alive)
        self.assertFalse(any(op=="terminate" and handle.process is replacement for op,handle in adapter.calls))
        self.assertTrue(any("PID reuse" in row for row in report["failures"]))

    def test_unowned_snapshot_errors_and_vanished_anchor_remain_failed(self):
        for kind in ("scope","denial","anchor"):
            with self.subTest(kind=kind):
                adapter=MockAdapter(); authority=adapter.authority()
                if kind=="anchor": adapter.root.alive=False
                manager=lease.ProcessLeases(authority,adapter)
                if kind=="scope":
                    foreign=Process(lease.Generation(99,400,"C:/outside/foreign.exe","f"*64),999)
                    adapter.enumerate=lambda parents,known: (lease.Snapshot(99,999,adapter.observe(Handle(foreign))),)
                elif kind=="denial":
                    adapter.enumerate=lambda parents,known: (lease.Snapshot(7,33,None,"native access denied"),)
                report=manager.cleanup()
                self.assertFalse(report["owned_handles_cleanup_verified"])
                self.assertTrue(all(handle.closed for handle in adapter.handles))

    def test_receipt_omissions_reorders_duplicates_and_extras_reject(self):
        adapter,authority,manager,debugger=collection(); good=manager.cleanup()
        for op in ("sources","open","anchor","adopt","terminate","wait","close","finish","enumerate"):
            with self.subTest(omitted=op):
                bad=reseal(good); bad["events"]=[row for row in bad["events"] if row["op"]!=op]
                bad=reseal(bad)
                self.assertFalse(lease.replay_receipts(bad,authority)["owned_handles_cleanup_verified"])
        for op in ("adopt","terminate","wait","close","finish"):
            with self.subTest(duplicated=op):
                bad=reseal(good); index=next(i for i,row in enumerate(bad["events"]) if row["op"]==op)
                bad["events"].insert(index,deepcopy(bad["events"][index]))
                self.assertFalse(lease.replay_receipts(reseal(bad),authority)["owned_handles_cleanup_verified"])
        bad=reseal(good); bad["events"][0]["invented_pass"]=True
        self.assertFalse(lease.replay_receipts(bad,authority)["owned_handles_cleanup_verified"])

    def test_closed_handles_and_postfinish_operations_reject(self):
        adapter,authority,manager,debugger=collection(); good=manager.cleanup()
        bad=reseal(good); close=next(row for row in bad["events"] if row["op"]=="close" and row["slot"]==debugger)
        bad["events"].remove(close); index=next(i for i,row in enumerate(bad["events"]) if row["op"]=="terminate")
        bad["events"].insert(index,close)
        self.assertFalse(lease.replay_receipts(reseal(bad),authority)["owned_handles_cleanup_verified"])
        bad=reseal(good); source=deepcopy(bad["events"][0]); bad["events"].append(source)
        self.assertFalse(lease.replay_receipts(reseal(bad),authority)["owned_handles_cleanup_verified"])

    def test_resealed_cohorts_sources_and_missing_generation_do_not_pass(self):
        adapter,authority,manager,debugger=collection(); good=manager.cleanup()
        bad=reseal(good)
        starts=[i-1 for i,row in enumerate(bad["events"]) if row["op"]=="terminate"]
        self.assertEqual(len(starts),2)
        first,second=(deepcopy(bad["events"][i:i+3]) for i in starts)
        bad["events"][starts[0]:starts[0]+3]=second
        bad["events"][starts[1]:starts[1]+3]=first
        self.assertFalse(lease.replay_receipts(reseal(bad),authority)["owned_handles_cleanup_verified"])
        bad=reseal(good)
        candidate=next(row["slot"] for row in bad["events"] if row["op"]=="adopt" and row["role"]=="candidate")
        index=next(i for i,row in enumerate(bad["events"]) if row["op"]=="open" and row["slot"]==candidate)
        self.assertEqual(bad["events"][index-1]["op"],"sources")
        bad["events"].pop(index-1)
        self.assertFalse(lease.replay_receipts(reseal(bad),authority)["owned_handles_cleanup_verified"])
        for prune_snapshot in (False,True):
            with self.subTest(prune_snapshot=prune_snapshot):
                bad=reseal(good)
                bad["events"]=[row for row in bad["events"] if row.get("slot")!=candidate]
                if prune_snapshot:
                    for row in bad["events"]:
                        if row["op"]=="enumerate": row["rows"]=[item for item in row["rows"] if item["pid"]!=7]
                self.assertFalse(lease.replay_receipts(reseal(bad),authority)["owned_handles_cleanup_verified"])
        bad=reseal(good)
        close=next(row for row in bad["events"] if row["op"]=="close")
        close["results"]*=2
        self.assertFalse(lease.replay_receipts(bad,authority)["owned_handles_cleanup_verified"])
        before=len(adapter.calls)
        for action in (lambda:manager.adopt(adapter.candidate.generation,"candidate"),manager.discover,
                       lambda:manager.attested_handle(debugger)):
            with self.assertRaises(ValueError): action()
        self.assertEqual(len(adapter.calls),before)

    def test_final_empty_snapshots_cannot_be_moved_before_owned_waits(self):
        adapter,authority,manager,debugger=collection(); good=manager.cleanup()
        bad=reseal(good)
        pairs=[(i-1,i) for i,row in enumerate(bad["events"]) if row["op"]=="enumerate" and row["rows"]==[]]
        self.assertGreaterEqual(len(pairs),2)
        indices={index for pair in pairs[-2:] for index in pair}
        moved=[row for i,row in enumerate(bad["events"]) if i in indices]
        rest=[row for i,row in enumerate(bad["events"]) if i not in indices]
        start=next(i-1 for i,row in enumerate(rest) if row["op"]=="terminate")
        bad["events"]=rest[:start]+moved+rest[start:]
        self.assertFalse(lease.replay_receipts(reseal(bad),authority)["owned_handles_cleanup_verified"])
        bad=reseal(good)
        finish=next(i for i,row in enumerate(bad["events"]) if row["op"]=="finish")
        bad["events"].insert(finish,deepcopy(bad["events"][0]))
        self.assertFalse(lease.replay_receipts(reseal(bad),authority)["owned_handles_cleanup_verified"])

    def test_failed_open_adoption_outcome_cannot_be_deleted(self):
        adapter,authority,manager,debugger=collection()
        self.assertIsNone(manager.adopt(adapter.candidate.generation,"candidate","controller"))
        report=manager.cleanup()
        self.assertFalse(report["owned_handles_cleanup_verified"])
        bad=reseal(report)
        failed=[row for row in bad["events"] if row["op"]=="adopt" and row["error"] is not None]
        self.assertEqual(len(failed),1)
        slot=failed[0]["slot"]
        self.assertTrue(any(row["op"]=="open" and row["slot"]==slot and row["error"] is None for row in bad["events"]))
        self.assertTrue(any(row["op"]=="close" and row["slot"]==slot for row in bad["events"]))
        bad["events"].remove(failed[0])
        self.assertFalse(lease.replay_receipts(reseal(bad),authority)["owned_handles_cleanup_verified"])

    def test_unknown_top_level_claims_and_changed_failure_diagnostics_reject(self):
        adapter,authority,manager,debugger=collection(); good=manager.cleanup()
        for field in ("passed","accepted","approved","job_verified","release_evidence_verified"):
            with self.subTest(field=field):
                bad=reseal(good); bad[field]=True
                self.assertFalse(lease.replay_receipts(bad,authority)["owned_handles_cleanup_verified"])
        bad=deepcopy(good); bad["failures"]=["invented retained diagnostic"]
        self.assertFalse(lease.replay_receipts(bad,authority)["owned_handles_cleanup_verified"])

    def test_typed_receipts_and_external_authority_cannot_be_resealed(self):
        adapter,authority,manager,debugger=collection(); good=manager.cleanup()
        for change in ("pid_bool","wait_bool","parent_time","parent_pid_bool","source","run","acceptance"):
            with self.subTest(change=change):
                bad=reseal(good)
                if change=="pid_bool": next(row for row in bad["events"] if row["op"]=="open")["pid"]=True
                elif change=="wait_bool": next(row for row in bad["events"] if row["op"]=="wait")["result"]["wait_result"]=False
                elif change=="parent_time": next(row for row in bad["events"] if row["op"]=="adopt")["parent_current"]["creation_filetime"]=101
                elif change=="parent_pid_bool": next(row for row in bad["events"] if row["op"]=="adopt")["parent_current"]["pid"]=True
                elif change=="source": bad["events"][0]["rows"][0]["sha256"]="0"*64
                elif change=="run": bad["authority"]["run_id"]="f"*32
                else: bad["host_cleanup_complete"]=True
                self.assertFalse(lease.replay_receipts(bad,authority)["owned_handles_cleanup_verified"])
        with self.assertRaises(ValueError): lease.ProcessLeases(good["authority"],MockAdapter())
        with self.assertRaises(ValueError): lease.load_receipts(b'{"schema":1,"schema":2}')
        with self.assertRaises(ValueError): lease.load_receipts(b'{"x":NaN}')

    def test_import_and_fixture_use_no_native_adapter(self):
        self.assertEqual(lease.WindowsAdapter.__module__,"hidden_soak_process_lease")
        for options in ({"max_adoptions":True},{"reconciliation_rounds":1},{"wait_ms":0}):
            adapter=MockAdapter()
            with self.assertRaises(ValueError): lease.ProcessLeases(adapter.authority(),adapter,**options)
            self.assertEqual(adapter.calls,[])


if __name__=="__main__": unittest.main(verbosity=2)
