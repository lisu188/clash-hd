"""Portable V3 receipt/capability tests; no compiler or native adapter calls."""
from __future__ import annotations

from pathlib import Path, PureWindowsPath
import base64
from copy import deepcopy
from types import SimpleNamespace
import struct
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hidden_soak_loader_v3_adapter as adapter


def packet(sequence, operation, data, raw=b"", *, metadata=None, io=None):
    original = adapter._canonical(dict(sequence=sequence, operation=operation, data=data)) if metadata is None else metadata
    size = 8 + len(original) + len(raw)
    return struct.pack("<II", len(original), len(raw)) + original + raw + adapter.IO_FOOTER.pack(
        *((1, 0, size, size, 1, 0) if io is None else io))


class FramingTests(unittest.TestCase):
    def reject(self, raw, actor="observer"):
        with self.assertRaises(adapter.ArchiveError) as caught:
            adapter.parse_frames(raw, actor=actor)
        self.assertIs(caught.exception.original_archive, raw)
        return caught.exception

    def test_three_actor_magic_and_original_packets_are_distinct(self):
        for actor, magic in (("caller", adapter.CALLER_MAGIC), ("outer", adapter.OUTER_MAGIC),
                             ("observer", adapter.OBSERVER_MAGIC)):
            original = magic + packet(1, "api", dict(value=7), b"original")
            row = adapter.parse_frames(original, actor=actor)[0]
            self.assertEqual(row.data(), dict(value=7))
            self.assertEqual(row.raw, b"original")
            self.assertEqual(row.offset, 8)
            adapter._io(row)
            for wrong in (name for name in ("caller", "outer", "observer") if name != actor):
                self.reject(original, wrong)

    def test_full_failed_read_capacity_and_negative_hresult_remain_exact(self):
        capacity = b"12345678"
        original = adapter.OBSERVER_MAGIC + packet(1, "read_virtual_capacity",
            dict(requested_bytes=8, returned_bytes=3, hresult=-2147467259), capacity)
        row = adapter.parse_frames(original, actor="observer")[0]
        self.assertEqual(row.raw, capacity)
        self.assertEqual(row.data(), dict(requested_bytes=8, returned_bytes=3, hresult=-2147467259))

    def test_truncated_every_boundary_retains_entire_original_and_prefix(self):
        first = packet(1, "api", {}, b"full")
        second = packet(2, "api", {}, b"other")
        original = adapter.OUTER_MAGIC + first + second
        for end in (0, 7, 8, 9, len(original)-25, len(original)-1):
            with self.subTest(end=end):
                self.reject(original[:end], "outer")
        self.assertEqual(len(self.reject(original[:-1], "outer").frames), 1)

    def test_duplicate_missing_reordered_or_bool_sequence_rejects(self):
        for value in (0, 2, True, -1):
            self.reject(adapter.OBSERVER_MAGIC + packet(value, "api", {}))
        first = packet(1, "api", {})
        error = self.reject(adapter.OBSERVER_MAGIC + first + first)
        self.assertEqual(len(error.frames), 1)

    def test_noncanonical_duplicate_extra_and_nonfinite_json_rejects(self):
        for raw in (b'{"sequence":1,"operation":"api","data":{}}',
                    b'{"data":{},"operation":"api","sequence":1,"sequence":1}',
                    b'{"data":{},"operation":"api","sequence":1,"approved":true}',
                    b'{"data":{"v":NaN},"operation":"api","sequence":1}',
                    b'{"data":{"v":"\xff"},"operation":"api","sequence":1}'):
            self.reject(adapter.OBSERVER_MAGIC + packet(1, "api", {}, metadata=raw))

    def test_missing_and_foreign_actor_cannot_select_policy(self):
        original = adapter.OBSERVER_MAGIC + packet(1, "api", {})
        for actor in (None, "debugger", "OBSERVER", True):
            self.reject(original, actor)
        self.reject(b"CLHDCR2\0" + original[8:])

    def test_failed_main_io_and_short_write_do_not_attest_complete_packet(self):
        meta = adapter._canonical(dict(sequence=1, operation="api", data={}))
        size = len(meta)+8
        for io in ((0, 5, size, size, 1, 0), (1, 0, size, size-1, 1, 0),
                   (1, 0, size+1, size+1, 1, 0), (1, 0, size, size, 0, 5)):
            original = adapter.OUTER_MAGIC + packet(1, "api", {}, io=io)
            row = adapter.parse_frames(original, actor="outer")[0]
            self.assertEqual(row.footer, adapter.IO_FOOTER.pack(*io))
            with self.assertRaises(ValueError):
                adapter._io(row)

    def test_negative_success_bool_and_stale_error_are_not_reinterpreted(self):
        meta = adapter._canonical(dict(sequence=1, operation="api", data={}))
        size = len(meta)+8
        original = adapter.OUTER_MAGIC + packet(1, "api", {}, io=(-1, 123, size, size, -1, 456))
        row = adapter.parse_frames(original, actor="outer")[0]
        adapter._io(row)
        self.assertEqual(row.io()["write_return"], -1)
        self.assertEqual(row.io()["flush_error"], 456)

    def test_impossible_cap_prefix_rejects_before_raw_allocation(self):
        for jsize, rsize in ((0, 0), (adapter.MAX_FRAME_METADATA+1, 0),
                             (1, adapter.MAX_FRAME_RAW+1), (1, adapter.MAX_OBSERVER_PACKET_RAW+1)):
            actor = "observer" if rsize == adapter.MAX_OBSERVER_PACKET_RAW+1 else "outer"
            magic = adapter.OBSERVER_MAGIC if actor == "observer" else adapter.OUTER_MAGIC
            self.reject(magic+struct.pack("<II", jsize, rsize), actor)

    def test_complete_counter_recomputed_from_original_packets(self):
        first = packet(1, "api", {}, b"raw")
        finish = dict(status="complete", frame_count=1, raw_bytes=3, metadata_bytes=len(first)-3+8,
                      comparison_scope="initial_loader_held_adoption_v3")
        original = adapter.OUTER_MAGIC + first + packet(2, "finish", finish)
        rows = adapter.parse_frames(original, actor="outer")
        adapter._terminal(rows, "outer")
        for name, value in (("frame_count", 2), ("status", "failed"), ("raw_bytes", 0),
                             ("comparison_scope", "immutable_scope_initial_hold")):
            changed = dict(finish, **{name: value})
            rows = adapter.parse_frames(adapter.OUTER_MAGIC+first+packet(2, "finish", changed), actor="outer")
            with self.assertRaises(ValueError):
                adapter._terminal(rows, "outer")

    def test_resealed_later_completion_cannot_erase_original_error(self):
        for operation in ("error", "native_failure", "retention_debt"):
            first = packet(1, operation, {})
            finish = dict(status="complete", frame_count=1, raw_bytes=0, metadata_bytes=len(first)+8,
                          comparison_scope="initial_loader_held_adoption_v3")
            rows = adapter.parse_frames(adapter.OUTER_MAGIC+first+packet(2, "finish", finish), actor="outer")
            with self.assertRaises(ValueError):
                adapter._terminal(rows, "outer")

    def test_duplicate_or_nonterminal_finish_rejects(self):
        for rows in ((packet(1, "finish", {})+packet(2, "api", {})),
                     (packet(1, "finish", {})+packet(2, "finish", {}))):
            original = adapter.OUTER_MAGIC+rows
            with self.assertRaises(ValueError):
                adapter._terminal(adapter.parse_frames(original, actor="outer"), "outer")

    def test_budget_counts_whole_caller_archive_copy_pending_and_false_claims(self):
        budget = adapter.caller_retention_budget()
        self.assertEqual(budget["known_peak_bytes"], 503316480)
        self.assertEqual(budget["known_peak_bytes"],
                         2*budget["complete_archive_bytes"]+budget["pending_original_bytes"]+
                         budget["close_original_bytes"]+budget["close_complete_copy_bytes"])
        self.assertTrue(all(value is False for value in adapter.FALSE_CLAIMS.values()))
        self.assertFalse(budget["storage_durability_verified"])


class SourceTests(unittest.TestCase):
    def test_closed_factory_rejects_second_call_before_project_execution(self):
        raw = b"def _factory():\n return (1,2)\na,b = _factory()\n"
        before = set(sys.modules)
        module = adapter._closed(raw, Path("C:/fixture/source.py"), ("a", "b"), "_factory")
        self.assertEqual(module._factory(), (1, 2))
        self.assertEqual(set(sys.modules), before)
        for changed in (raw.replace(b"a,b =", b"_factory()\na,b ="),
                        raw.replace(b"a,b =", b"a,c ="), raw.replace(b"_factory()\n", b"_factory(None)\n")):
            with self.assertRaises(ValueError):
                adapter._closed(changed, Path("C:/fixture/source.py"), ("a", "b"), "_factory")
            self.assertEqual(set(sys.modules), before)

    def test_private_registry_ignores_hostile_public_project_aliases(self):
        calls=[]
        def poison(*args,**kwargs):calls.append((args,kwargs));raise AssertionError("public alias executed")
        with patch.multiple(adapter,_build_api=poison,_generator_private=poison,_fixture_generator=poison,_sha=poison,
                            _closed=poison,_PrivateGraph=poison,ROOT=Path("C:/foreign")):
            plan=adapter.prepare_synthetic_plan(mode=0)
            report=adapter.inspect_capability(plan)
        self.assertTrue(report["fixture_only"])
        self.assertEqual(report["kind"],"plan")
        self.assertEqual(calls,[])

    def test_copied_or_foreign_registry_capabilities_are_not_native_issuance(self):
        plan=adapter.prepare_synthetic_plan(mode=0)
        copied=type(plan)(plan.binding_json)
        with self.assertRaises(ValueError):adapter.inspect_capability(copied)
        other=adapter._api_factory()
        with self.assertRaises(ValueError):other[-1](plan)
        original=plan.binding_json
        object.__setattr__(plan,"binding_json",original+" ")
        with self.assertRaises(ValueError):adapter.inspect_capability(plan)
        object.__setattr__(plan,"binding_json",original)
        self.assertTrue(adapter.inspect_capability(plan)["fixture_only"])

    def test_fixture_scope_and_fixed_mode_types_are_explicit(self):
        for mode in (-1,11,True,"0"):
            with self.assertRaises(ValueError):adapter.prepare_synthetic_plan(mode=mode)
        for mode in (0,4,10):
            plan=adapter.prepare_synthetic_plan(mode=mode)
            self.assertTrue(all(value is False for value in adapter.inspect_capability(plan)["claims"].values()))
        with self.assertRaises(ValueError):adapter.prepare_plan(b"fixture",None)

    def test_source_drift_fails_before_private_project_dispatch(self):
        raw=Path(adapter.__file__).read_bytes()
        with self.assertRaises(ValueError):adapter._api_factory(_raw=raw+b"\n")
        calls=[]
        original=Path.read_bytes
        def changed(path):
            value=original(path)
            if path==Path(adapter.__file__):return value+b"\n"
            return value
        with patch.object(Path,"read_bytes",changed):
            with self.assertRaises(ValueError):adapter.prepare_synthetic_plan(mode=0)
        self.assertEqual(calls,[])


class PolicyTests(unittest.TestCase):
    def test_job_query_reads_full_capacity_and_actual_used_pid_length(self):
        limits=bytearray(144);struct.pack_into("<I",limits,16,0x2000)
        account=bytearray(48);struct.pack_into("<I",account,40,1)
        pids=bytearray(520);struct.pack_into("<IIQ",pids,0,1,1,987)
        for kind,raw,used in ((9,bytes(limits),144),(1,bytes(account),48),(3,bytes(pids),16)):
            adapter._caller_job_query(kind,1,used,raw,987)
            for result,length,buffer in ((0,used,raw),(True,used,raw),(1,used+1,raw),(1,used,raw[:-1])):
                with self.assertRaises(ValueError):adapter._caller_job_query(kind,result,length,buffer,987)
        for offset,value in ((0,2),(4,2),(8,988)):
            wrong=bytearray(pids);struct.pack_into("<I",wrong,offset,value)
            with self.assertRaises(ValueError):adapter._caller_job_query(3,1,16,bytes(wrong),987)
        wrong=bytearray(limits);struct.pack_into("<I",wrong,16,0x3800)
        with self.assertRaises(ValueError):adapter._caller_job_query(9,1,144,bytes(wrong),987)

    def test_environment_rejects_credentials_case_collisions_wrong_target_and_switches(self):
        environment=dict(PATH="C:/msvc",SystemRoot="C:/Windows",VSCMD_ARG_TGT_ARCH="x64",LIB="C:/lib64")
        adapter._compiler_environment(environment,0x8664)
        for addition in (dict(GITHUB_TOKEN="secret"),dict(CL="/link /evil"),dict(path="other"),
                         dict(VSCMD_ARG_TGT_ARCH="x86")):
            with self.assertRaises(ValueError):adapter._compiler_environment({**environment,**addition},0x8664)

    def test_whole_payload_and_build_allowances_are_not_caller_reducible(self):
        self.assertEqual(adapter.MAX_FRAME_RAW,17121324)
        self.assertEqual(adapter.BUILD_PEAK_BYTES,512*1024**2)
        self.assertEqual(adapter.CALLER_PENDING_BYTES,64*1024**2)
        self.assertGreaterEqual(adapter.CALLER_PENDING_BYTES,2*(adapter.MAX_FRAME_RAW+adapter.MAX_FRAME_METADATA+32))

    def test_boolean_cannot_replace_original_integer_and_original_hresult_is_retained(self):
        for value in (dict(hresult=False),dict(count=True),dict(native=dict(returned=True))):
            with self.assertRaises(ValueError):adapter._wire_scalars(value)
        adapter._wire_scalars(dict(hresult=-2147467259,count=0))
        adapter._wire_scalars(dict(comparison_called=True,post_qpc_called=True),allowed_bools=("comparison_called","post_qpc_called"))

    def test_caller_cleanup_finalizes_and_closes_even_if_diagnostics_fail(self):
        session=adapter._NativeSession.__new__(adapter._NativeSession)
        session.owned=[0]*32;session.owned[0]=123;session.events=[];session.failed=True;session.debt=False
        calls=[]
        session.cleanup=lambda:calls.append("cleanup")
        def fail(*args):calls.append("finish");raise ValueError("original diagnostic unavailable")
        session._record=fail
        session.close_slot=lambda slot:calls.append(("close",slot))
        session.finish_and_close()
        self.assertEqual(calls,["cleanup","finish",("close",0)])
        self.assertTrue(session.debt)


class AuthenticodeCommandTests(unittest.TestCase):
    def test_child_environment_removes_every_module_path_case_without_parent_mutation(self):
        parent=dict(PSModulePath="PS7 upper",psmodulepath="PS7 lower",PsModulePath="PS7 mixed",
            PATH="compiler path",SystemRoot=r"C:\Windows",OTHER_VALUE="retained parent value")
        before=dict(parent)
        child=adapter._authenticode_environment(parent)
        self.assertEqual(child,dict(PATH="compiler path",SystemRoot=r"C:\Windows",OTHER_VALUE="retained parent value"))
        self.assertEqual(parent,before);self.assertIsNot(child,parent)
        child["PATH"]="child-only replacement"
        self.assertEqual(parent,before)
        self.assertEqual(adapter._authenticode_environment({}),{})

    def test_space_and_apostrophe_paths_are_one_encoded_literal_not_extra_arguments(self):
        shell=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        compilers=(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Tools\MSVC\bin\Hostx64\x64\cl.exe",
            r"D:\Toolchain O'Brien\Dollar$() Backtick` Semi; Pipe| Amp&\cl.exe")
        for compiler in compilers:
            with self.subTest(compiler=compiler):
                command=adapter._authenticode_command(shell,compiler)
                self.assertEqual(command[:4],[shell,"-NoProfile","-NonInteractive","-EncodedCommand"])
                self.assertEqual(len(command),5)
                script=base64.b64decode(command[4],validate=True).decode("utf-16le")
                match=re.fullmatch(r"\$s=Get-AuthenticodeSignature -LiteralPath '((?:[^']|'')*)'; \[Console\]::Write\(\$s.Status.ToString\(\)\+'\|'\+\$s.SignerCertificate.Subject\)",script)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1).replace("''","'"),compiler)
                self.assertNotIn("$args[0]",script)
                self.assertNotIn("-Command",command)
                self.assertEqual(script.encode("utf-16le"),base64.b64decode(command[4],validate=True))

    def test_relative_foreign_tool_or_control_character_paths_reject(self):
        shell=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        compiler=r"C:\Program Files\MSVC\cl.exe"
        for value in (r"cl.exe",r"C:cl.exe",r"\\remote\share\cl.exe",r"C:\tools\cmd.exe",
                      compiler+"\n",compiler+"\0",compiler.replace("MSVC","M\u00e1SVC"),True):
            with self.subTest(compiler=value),self.assertRaises(ValueError):adapter._authenticode_command(shell,value)
        for value in (r"powershell.exe",r"C:\tools\cmd.exe",shell+"\r",None):
            with self.subTest(shell=value),self.assertRaises(ValueError):adapter._authenticode_command(value,compiler)

    def test_native_signature_failures_reject_without_mutating_original_streams(self):
        valid=b"Valid|CN=Microsoft Corporation, O=Microsoft Corporation, C=US"
        good=SimpleNamespace(returncode=0,stdout=valid,stderr=b"original warning")
        adapter._require_authenticode_original(good)
        for code,stdout,stderr in ((1,b"",b"Unexpected token 'C:\\Program' in expression or statement."),
            (1,valid,b"original failure"),(0,b"NotSigned|Microsoft Corporation",b""),
            (0,b"HashMismatch|Microsoft Corporation",b""),(0,b"UnknownError|Microsoft Corporation",b""),
            (0,b"Valid|CN=Other Publisher",b""),(0,b"NotValid|Microsoft Corporation",b""),
            (False,valid,b""),(0,"Valid|Microsoft Corporation",b""),(0,valid,None)):
            original=SimpleNamespace(returncode=code,stdout=stdout,stderr=stderr)
            with self.subTest(code=code,stdout=stdout),self.assertRaises(ValueError):
                adapter._require_authenticode_original(original)
            self.assertIs(original.stdout,stdout);self.assertIs(original.stderr,stderr)
            self.assertIs(original.returncode,code)

    def test_compile_dispatches_encoded_signature_command_before_any_source_write(self):
        class OriginalPath(PureWindowsPath):
            def read_bytes(self):return b"whole modeled compiler PE"
        session=adapter._NativeSession.__new__(adapter._NativeSession);commands=[];environments=[]
        system=r"C:\Windows\System32"
        def directory(buffer,capacity):buffer.value=system;return len(system)
        session.kernel=SimpleNamespace(GetSystemDirectoryW=directory)
        session._record=lambda *args,**kwargs:None
        failure=SimpleNamespace(returncode=1,stdout=b"",stderr=b"Unexpected token 'C:\\Program' in expression or statement.")
        def run(command,*,environment):
            commands.append(command);environments.append(environment);return failure
        session._run=run
        session.write_new=lambda *args:(_ for _ in ()).throw(AssertionError("Rejected compiler must not write or compile source"))
        compiler=r"C:\Program Files\Microsoft Visual Studio\VC\Tools\MSVC\bin\Hostx64\x64\cl.exe"
        with patch.object(adapter,"_plain_path",side_effect=lambda value:OriginalPath(str(value))),\
             patch.object(adapter,"_stamp",return_value=(1,2,3)),patch.object(adapter,"_pe_machine",return_value=(0x8664,0x20b)),\
             patch.object(adapter.ctypes,"set_last_error",create=True),patch.object(adapter.ctypes,"get_last_error",return_value=0,create=True),\
             patch.dict(adapter.os.environ,dict(PSModulePath="inherited incompatible PS7 module path",PATH="parent value"),clear=True):
            parent=dict(adapter.os.environ)
            with self.assertRaisesRegex(ValueError,"original compiler Authenticode publisher/trust observation failed"):
                session.compile("outer_source","outer",compiler,b"modeled source",machine=0x8664)
            self.assertEqual(dict(adapter.os.environ),parent)
            self.assertEqual(environments,[{key:value for key,value in parent.items() if key.upper()!="PSMODULEPATH"}])
        self.assertEqual(len(commands),1)
        self.assertEqual(commands[0][3],"-EncodedCommand");self.assertEqual(len(commands[0]),5)
        decoded=base64.b64decode(commands[0][4],validate=True).decode("utf-16le")
        self.assertIn("-LiteralPath '"+compiler+"';",decoded)
        self.assertEqual(failure.stdout,b"")


def frame(operation,data,raw=b"",sequence=1):
    prefix=b"".join(packet(index,"fixture_padding",{}) for index in range(1,sequence))
    return adapter.parse_frames(adapter.OBSERVER_MAGIC+prefix+packet(sequence,operation,data,raw),actor="observer")[-1]


class CapacityTests(unittest.TestCase):
    def cohort(self):
        owners=dict(run_id="1"*32,checkpoint_id="2"*32,clock_epoch="3"*32,native_owner_tid=9,current_native_tid=9,
                    probe_sequence=0,breakpoint_sequence=0,command_sequence=0)
        rows=[]
        for number,role in enumerate(("controller","debugger","target"),1):
            original=dict(pid=number+100,pid_error=0,path_return=1,path_error=0,path_chars=6,
                image_path_utf16le="C:\\a.x".encode("utf-16le").hex(),times_return=1,times_error=0,
                creation_filetime=number+1000,exit_filetime=0,kernel_filetime=77,user_filetime=88,
                parent_pid=number+90,parent_query_return=1,parent_query_error=0,parent_creation_filetime=55,
                parent_times_return=1,parent_times_error=0)
            owners[role]=original
            capacity={name:original[name] for name in adapter.CAPACITY_FIELDS if name in original}
            capacity.update(handle=number+7,times_hex=struct.pack("<4Q",number+1000,0,77,88).hex())
            full=bytes.fromhex(original["image_path_utf16le"])+bytes(65536-12)
            rows.append(("generation_capacity",capacity,full))
            native=bytearray(564);struct.pack_into("<iIII",native,0,1,0,556,number+100)
            struct.pack_into("<I",native,32,number+90)
            parent=dict(handle=number+7,snapshot_handle=99,snapshot_error=0,parent_pid=number+90,
                parent_return=1,parent_error=0,parent_times_return=1,parent_times_error=0,
                parent_times_hex=struct.pack("<4Q",55,0,1,2).hex(),row_bytes=556,cohort_rows=1)
            rows.append(("generation_parent_capacity",parent,bytes(native)))
        rows.append(("owner",owners,b""))
        return rows

    def parse(self,rows):
        return adapter.parse_frames(adapter.OBSERVER_MAGIC+b"".join(packet(i,*row) for i,row in enumerate(rows,1)),actor="observer")

    def test_full_original_cohorts_match_owner_and_preserve_capacity_tails(self):
        rows=self.cohort();rows[0]=(rows[0][0],rows[0][1],rows[0][2][:-1]+b"Z")
        original=self.parse(rows);selected,handles=adapter._capacity_groups(original)
        self.assertEqual(len(selected),1);self.assertEqual(handles,{7:(8,9,10)})
        self.assertEqual(original[0].raw[-1:],b"Z")

    def test_missing_reordered_alias_owner_or_wrong_raw_parent_fails(self):
        rows=self.cohort()
        variants=[rows[1:],rows[:1]+rows[2:],[rows[1],rows[0],*rows[2:]]]
        wrong=deepcopy(rows);wrong[2][1]["handle"]=8;wrong[3][1]["handle"]=8;variants.append(wrong)
        wrong=deepcopy(rows);raw=bytearray(wrong[1][2]);struct.pack_into("<I",raw,32,777);wrong[1]=(wrong[1][0],wrong[1][1],bytes(raw));variants.append(wrong)
        wrong=deepcopy(rows);wrong[0][1]["path_chars"]=5;variants.append(wrong)
        for changed in variants:
            with self.assertRaises(ValueError):adapter._capacity_groups(self.parse(changed))

    def test_orphan_duplicate_parent_match_and_invented_owner_fail(self):
        rows=self.cohort()
        with self.assertRaises(ValueError):adapter._capacity_groups(self.parse(rows[:-1]))
        wrong=deepcopy(rows);wrong[1][1]["cohort_rows"]=2;wrong[1]=(wrong[1][0],wrong[1][1],wrong[1][2]*2)
        with self.assertRaises(ValueError):adapter._capacity_groups(self.parse(wrong))


class FailureTests(unittest.TestCase):
    def kinds(self,rows):
        parsed=adapter.parse_frames(adapter.OBSERVER_MAGIC+b"".join(packet(i,*row) for i,row in enumerate(rows,1)),actor="observer")
        return adapter._failure_kinds(parsed,(),v2=None,generator=None,core={},state={})

    def test_failed_challenge_full_buffer_proves_scoped_failure_not_a_mode(self):
        data=dict(write_return=0,write_error=6,requested=576,returned=0,flush_return=0,flush_error=6)
        self.assertEqual(self.kinds([("challenge_write",data,bytes(576))]),[adapter.SYNTHETIC_FAILURES[1]])
        with self.assertRaises(ValueError):self.kinds([("challenge_write",data,bytes(575))])
        self.assertEqual(self.kinds([("challenge_write",{**data,"write_return":1,"returned":576,"flush_return":1},bytes(576))]),[])

    def test_signed_failed_read_and_timeout_require_complete_original_capacity(self):
        original=dict(ordinal=0,address=0x200008,requested_bytes=4,hresult=-2147467259,returned_bytes=0)
        self.assertEqual(self.kinds([("read_virtual_capacity",original,b"ABCD")]),[adapter.SYNTHETIC_FAILURES[4]])
        self.assertEqual(self.kinds([("adoption_wait",{"return":258,"error":0,"timeout_ms":19999},b"")]),[adapter.SYNTHETIC_FAILURES[8]])
        with self.assertRaises(ValueError):self.kinds([("read_virtual_capacity",original,b"")])
        self.assertEqual(self.kinds([("finish",dict(mode=4,status="failed"),b"")]),[])

    def test_full_wrong_peb_read_is_classified_before_comparison_exists(self):
        context=[("callback_create",dict(base_offset=0x400000),b""),("peb",dict(hresult=0,address=0x200000),b"")]
        original=dict(ordinal=0,address=0x200008,requested_bytes=4,hresult=0,returned_bytes=4)
        self.assertEqual(self.kinds(context+[("read_virtual_capacity",original,struct.pack("<I",0x400000))]),[])
        for data,raw in ((original,struct.pack("<I",123)),({**original,"address":0x7ffe0008},struct.pack("<I",0x400000))):
            self.assertEqual(self.kinds(context+[("read_virtual_capacity",data,raw)]),[adapter.SYNTHETIC_FAILURES[4]])
        for rows in (context[1:]+[("read_virtual_capacity",original,bytes(4))],
                     context[:1]+[("read_virtual_capacity",original,bytes(4))],
                     context+context[:1]+[("read_virtual_capacity",original,bytes(4))]):
            with self.assertRaises(ValueError):self.kinds(rows)


class SuspendedCleanupTests(unittest.TestCase):
    """Execute caller control flow with explicit API models, never native calls."""
    def session(self, failure):
        C=adapter.ctypes
        class Startup(C.Structure):
            _fields_=[("cb",C.c_uint32),("flags",C.c_uint32),("stdin",C.c_void_p),
                     ("stdout",C.c_void_p),("stderr",C.c_void_p)]
        class StartupEx(C.Structure):
            _fields_=[("startup",Startup),("attributes",C.c_void_p)]
        class ProcessInfo(C.Structure):
            _fields_=[("process",C.c_void_p),("thread",C.c_void_p),("pid",C.c_uint32),("tid",C.c_uint32)]
        state=adapter._NativeSession.__new__(adapter._NativeSession)
        state.owned=[0]*32;state.closed=state.failed=state.debt=False;state.outer_assigned=False
        state.StartupEx,state.ProcessInfo=StartupEx,ProcessInfo
        state.root=Path("C:/explicit-model")
        state.files={name:state.root/name for name in ("outer","bootstrap","outer_archive","outer_stderr")}
        state._reserve=lambda:None
        state._open=lambda slot,*args,**kwargs:state.owned.__setitem__(slot,500+slot)
        state._generation=lambda slot,role:dict(pid=606,path=str(state.files["outer"]))
        state.job_readbacks=lambda pid:None
        calls=[];last_error=[0]
        def record(operation,data,raw=b""):
            calls.append(("record",data.get("name")))
            if failure=="job_receipt" and data.get("name")=="CreateJobObjectW":
                raise ValueError("original job receipt unavailable")
            if failure=="assignment_receipt" and data.get("name")=="AssignProcessToJobObject":
                raise ValueError("original assignment receipt unavailable")
        state._record=record
        def attributes(memory,count,flags,size):
            C.cast(size,C.POINTER(C.c_size_t)).contents.value=64
            last_error[0]=122 if memory is None else 0
            return 0 if memory is None else 1
        def create(*args):
            output=C.cast(args[-1],C.POINTER(ProcessInfo)).contents
            output.process=600;output.thread=700;output.pid=606;output.tid=707
            return 1
        def limits(*args):
            return 0 if failure=="limits_native" else 1
        def assign(*args):
            return 0 if failure=="assignment_native" else 1
        def native(name,result):
            def call(*args):calls.append((name,*args));return result
            return call
        state.kernel=SimpleNamespace(InitializeProcThreadAttributeList=attributes,
            UpdateProcThreadAttribute=lambda *args:1,CreateProcessW=create,CreateJobObjectW=lambda *args:800,
            SetInformationJobObject=limits,AssignProcessToJobObject=assign,
            DeleteProcThreadAttributeList=lambda *args:None,
            TerminateJobObject=native("TerminateJobObject",1),TerminateProcess=native("TerminateProcess",1),
            WaitForSingleObject=native("WaitForSingleObject",0),CloseHandle=native("CloseHandle",1))
        return state,calls,last_error

    def test_unassigned_outer_is_terminated_even_when_empty_job_exists(self):
        for failure in ("job_receipt","limits_native","assignment_native"):
            with self.subTest(failure=failure):
                state,calls,last_error=self.session(failure)
                with patch.object(adapter.ctypes,"set_last_error",side_effect=lambda value:last_error.__setitem__(0,value),create=True),\
                     patch.object(adapter.ctypes,"get_last_error",side_effect=lambda:last_error[0],create=True):
                    with self.assertRaises(ValueError):state.create_suspended()
                    self.assertEqual((state.owned[6],state.owned[8]),(600,800))
                    self.assertFalse(state.outer_assigned)
                    state._record=lambda *args,**kwargs:(_ for _ in ()).throw(ValueError("cleanup diagnostic unavailable"))
                    state.cleanup()
                    state.cleanup()
                natives=[row for row in calls if row[0]!="record"]
                termination=[row for row in natives if row[0]!="CloseHandle"]
                self.assertEqual(termination[:3],[("TerminateJobObject",800,0),("TerminateProcess",600,1),
                                              ("WaitForSingleObject",600,5000)])
                self.assertEqual(natives.count(("TerminateProcess",600,1)),1)
                self.assertEqual(natives.count(("CloseHandle",600)),1)
                self.assertTrue(state.failed and state.debt)
                self.assertTrue(all(value==0 for value in state.owned))

    def test_assignment_is_owned_before_its_receipt_can_fail(self):
        state,calls,last_error=self.session("assignment_receipt")
        with patch.object(adapter.ctypes,"set_last_error",side_effect=lambda value:last_error.__setitem__(0,value),create=True),\
             patch.object(adapter.ctypes,"get_last_error",side_effect=lambda:last_error[0],create=True):
            with self.assertRaises(ValueError):state.create_suspended()
            self.assertTrue(state.outer_assigned)
            state.cleanup()
        self.assertIn(("TerminateJobObject",800,0),calls)
        self.assertNotIn(("TerminateProcess",600,1),calls)
        self.assertIn(("WaitForSingleObject",600,5000),calls)

    def test_failed_assigned_job_termination_falls_back_without_erasing_failure(self):
        for diagnostic_failure in (False,True):
            with self.subTest(diagnostic_failure=diagnostic_failure):
                state,calls,last_error=self.session("none")
                state.kernel.TerminateJobObject=lambda *args:calls.append(("TerminateJobObject",*args)) or 0
                with patch.object(adapter.ctypes,"set_last_error",side_effect=lambda value:last_error.__setitem__(0,value),create=True),\
                     patch.object(adapter.ctypes,"get_last_error",side_effect=lambda:last_error[0],create=True):
                    state.create_suspended();self.assertTrue(state.outer_assigned)
                    if diagnostic_failure:
                        state._record=lambda *args,**kwargs:(_ for _ in ()).throw(ValueError("cleanup receipt unavailable"))
                    state.cleanup();state.cleanup()
                self.assertIn(("TerminateJobObject",800,0),calls)
                self.assertEqual(calls.count(("TerminateProcess",600,1)),1)
                self.assertIn(("WaitForSingleObject",600,5000),calls)
                self.assertTrue(state.failed)
                self.assertIs(state.debt,diagnostic_failure)
                self.assertTrue(all(value==0 for value in state.owned))


class GateJoinTests(unittest.TestCase):
    """Focused archive math using explicit framed originals, no native proof."""
    def originals(self):
        challenge=frame("challenge_write",{},bytes(range(256))*2+bytes(64),sequence=90)
        adoption=frame("adoption_read",{},bytes(576),sequence=100)
        generations=((11,111),(22,222),(33,333),(44,444))
        first=dict(sequences=(1,2,3,0,0,0,10),generations=generations)
        second=dict(sequences=(1,2,3,12,16,14,10))
        identities={}
        for role,phase,sequence,(pid,creation) in (
            ("caller","startup",1,generations[0]),("outer","startup",2,generations[1]),
            ("observer","adopt_before",12,generations[2]),("target","adopt_before",13,generations[3]),
            ("target","adopt_after",16,generations[3])):
            data=dict(pid=pid,creation=creation)
            identities[(role,phase)]=(frame("identity",data,sequence=sequence),data)
        apis=[frame("api",dict(name="ReadFile",role="challenge_reader",phase="challenge"),challenge.raw,sequence=11),
              frame("api",dict(name="IsProcessInJob",role="target",phase="adoption"),sequence=14),
              frame("api",dict(name="WriteFile",role="adoption_writer",phase="adoption"),adoption.raw,sequence=18)]
        outer=dict(channel=frame("channel_identity",{},sequence=10),identities=identities,apis=apis,
            adoption=frame("adoption_packet",dict(challenge_sha256=adapter._sha(challenge.raw),target_creation=444),
                           adoption.raw,sequence=17))
        return first,second,challenge,adoption,outer

    def test_actual_source_reader_writer_roles_and_phases_join(self):
        adapter._outer_gate_join(*self.originals(),{})

    def test_legacy_role_aliases_wrong_phases_duplicates_or_changed_bytes_fail(self):
        for index,name,value in ((0,"role","challenge"),(2,"role","adoption"),
                                  (0,"phase","adoption"),(2,"phase","challenge")):
            first,second,challenge,adoption,outer=self.originals()
            row=outer["apis"][index];data=dict(row.data(),**{name:value})
            outer["apis"][index]=frame("api",data,row.raw,sequence=row.sequence)
            with self.assertRaises(ValueError):adapter._outer_gate_join(first,second,challenge,adoption,outer,{})
        for variant in ("duplicate","changed_raw","reordered"):
            first,second,challenge,adoption,outer=self.originals();row=outer["apis"][2]
            if variant=="duplicate":outer["apis"].append(row)
            elif variant=="changed_raw":outer["apis"][2]=frame("api",row.data(),b"Z"+row.raw[1:],sequence=row.sequence)
            else:outer["apis"][2]=frame("api",row.data(),row.raw,sequence=15)
            with self.assertRaises(ValueError):adapter._outer_gate_join(first,second,challenge,adoption,outer,{})


class CallerWriteTests(unittest.TestCase):
    def session(self, fail_footer=False):
        C=adapter.ctypes;state=adapter._NativeSession.__new__(adapter._NativeSession)
        state.begun=True;state.pending=[];state.events=[];state.footer_reserves=[]
        state.owned=[777]+[0]*31;state.failed=state.debt=False
        calls=[];samples=[]
        def reserve(*,retain=False):
            sample=dict(result=1,error=0,free=10000,total=10000,unused=10000,required_peak=100)
            samples.append(sample);calls.append("reserve")
            if fail_footer and len(samples)==2:
                sample["free"]=900;state.failed=state.debt=True
                state.pending.append(("reserve",sample,b""))
                raise ValueError("original footer reserve failed")
            return sample
        def write(handle,raw,size,returned,unused):
            C.cast(returned,C.POINTER(C.c_uint32)).contents.value=size
            calls.append(("write",bytes(raw),size));return 1
        state._reserve=reserve
        state.kernel=SimpleNamespace(WriteFile=write,FlushFileBuffers=lambda handle:calls.append("flush") or 1)
        return state,calls,samples

    def test_both_packet_and_footer_get_original_prewrite_reserve(self):
        state,calls,samples=self.session()
        with patch.object(adapter.ctypes,"set_last_error",create=True),patch.object(adapter.ctypes,"get_last_error",return_value=0,create=True):
            state._record("api",dict(result=1),b"whole original")
        self.assertEqual([row if type(row) is str else row[0] for row in calls],
            ["reserve","write","flush","reserve","write","flush"])
        self.assertEqual(state.footer_reserves,[dict(sequence=1,reserve=samples[1])])
        self.assertIs(state.footer_reserves[0]["reserve"],samples[1])
        self.assertEqual(state.pending,[]);self.assertEqual(len(state.events),1)
        self.assertEqual(state.events[0].raw,b"whole original")

    def test_failed_footer_reserve_keeps_full_main_io_and_footer_capacity(self):
        state,calls,samples=self.session(True)
        with patch.object(adapter.ctypes,"set_last_error",create=True),patch.object(adapter.ctypes,"get_last_error",return_value=0,create=True):
            with self.assertRaises(ValueError):state._record("api",dict(result=1),b"whole original")
        writes=[row for row in calls if type(row) is tuple and row[0]=="write"]
        self.assertEqual(len(writes),1);self.assertEqual(state.events,[])
        pending={name:(value,raw) for name,value,raw in state.pending}
        self.assertEqual(pending["api"][1],b"whole original")
        self.assertEqual(pending["main_io"][1],writes[0][1])
        self.assertEqual(pending["main_io"][0],dict(write_return=1,write_error=0,returned=writes[0][2],flush_return=1,flush_error=0))
        self.assertEqual(pending["receipt_tail_capacity"][1],adapter.IO_FOOTER.pack(1,0,writes[0][2],writes[0][2],1,0))
        self.assertIs(pending["reserve"][0],samples[-1]);self.assertTrue(state.failed and state.debt)
        self.assertEqual(state.footer_reserves,[])

    def test_clock_origin_is_the_original_before_qpc_bracket(self):
        C=adapter.ctypes;state=adapter._NativeSession.__new__(adapter._NativeSession);calls=[];rows=[]
        def frequency(output):C.cast(output,C.POINTER(C.c_int64)).contents.value=10000000;return 1
        def counter(output):calls.append("qpc");C.cast(output,C.POINTER(C.c_int64)).contents.value=987654;return 1
        state.kernel=SimpleNamespace(QueryPerformanceFrequency=frequency,QueryPerformanceCounter=counter)
        state._record=lambda operation,data,raw:rows.append((operation,data,raw))
        def monotonic():calls.append("monotonic");return 123456789 if len(calls)==1 else 123456999
        with patch.object(adapter.ctypes,"set_last_error",create=True),patch.object(adapter.ctypes,"get_last_error",return_value=0,create=True),\
             patch.object(adapter.time,"monotonic_ns",side_effect=monotonic):
            result=state.clock()
        self.assertEqual(calls,["monotonic","qpc","monotonic"])
        self.assertEqual(result,(10000000,987654,123456789))
        self.assertEqual(rows[-1][2],struct.pack("<2Q",123456789,123456999))
        self.assertEqual(rows[-1][1]["before_ns"],result[2])

    def test_final_close_preserves_original_footer_queries_with_ram_only_scope(self):
        state,calls,samples=self.session()
        state.kernel.CloseHandle=lambda handle:calls.append(("close",handle)) or 1
        with patch.object(adapter.ctypes,"set_last_error",create=True),patch.object(adapter.ctypes,"get_last_error",return_value=0,create=True):
            state._record("api",dict(result=1),b"whole original")
            state.close_slot(0);state.close_slot(0)
        receipt=adapter._json(state.caller_close_receipt)
        self.assertEqual(receipt["receipt_tail_prewrite_reserves"],[dict(sequence=1,reserve=samples[1])])
        self.assertEqual(receipt["serialization_scope"],"retained_RAM_only_after_final_archive_packet")
        self.assertEqual((receipt["handle"],receipt["result"],receipt["error"]),(777,1,0))
        self.assertEqual(calls.count(("close",777)),1)
        self.assertLessEqual(len(state.caller_close_receipt),adapter.CALLER_CLOSE_ORIGINAL_BYTES)


class DesktopReceiptTests(unittest.TestCase):
    run_id="0123456789abcdef0123456789abcdef"

    def receipt(self,*,handle=700,result=700,error=0):
        return dict(name="CreateDesktopW",role="desktop",phase="setup",handle=handle,result=result,error=error,
            requested=0,returned=0,length_kind="source_capacity_no_native_count",begin=dict(result=1,error=0,tick=1),
            end=dict(result=1,error=0,tick=2),detail=dict(name="ClashLoaderV3_"+self.run_id,desired_access=0xC3))

    def parse(self,data,raw=b""):
        original=adapter.OUTER_MAGIC+packet(1,"api",data,raw)+packet(2,"finish",
            dict(failed=1,debt=0,scope="V3_initial_loader_terminate_only"))
        return adapter._outer_protocol(adapter.parse_frames(original,actor="outer"),{},dict(run_id=self.run_id),None)

    def test_original_restricted_request_is_bound_to_source_run_and_retained(self):
        data=self.receipt();before=deepcopy(data);parsed=self.parse(data)
        self.assertEqual(parsed["apis"][0].data(),before)
        self.assertEqual(data,before);self.assertEqual(parsed["failures"],[])
        self.assertTrue(parsed["failed"])

    def test_missing_expanded_untyped_foreign_and_duplicate_desktop_requests_reject(self):
        for access in (0,0x83,0xC7,0x1C3,0xCC,0x1000C3,0xF01FF,True,"195"):
            with self.subTest(access=access):
                data=self.receipt();data["detail"]["desired_access"]=access
                with self.assertRaises(ValueError):self.parse(data)
        for variant in ("missing","extra","name","role","phase","requested","returned","kind","raw","duplicate"):
            with self.subTest(variant=variant):
                data=self.receipt();raw=b""
                if variant=="missing":del data["detail"]["desired_access"]
                elif variant=="extra":data["detail"]["switch_desktop"]=0
                elif variant=="name":data["detail"]["name"]="ClashLoaderV3_foreign"
                elif variant=="role":data["role"]="observer"
                elif variant=="phase":data["phase"]="inherit"
                elif variant in ("requested","returned"):data[variant]=1
                elif variant=="kind":data["length_kind"]="original_native_count"
                elif variant=="raw":raw=b"invented desktop output"
                else:
                    second=deepcopy(data);second["begin"]["tick"]=3;second["end"]["tick"]=4
                    original=adapter.OUTER_MAGIC+packet(1,"api",data)+packet(2,"api",second)+packet(3,"finish",
                        dict(failed=1,debt=0,scope="V3_initial_loader_terminate_only"))
                    with self.assertRaises(ValueError):
                        adapter._outer_protocol(adapter.parse_frames(original,actor="outer"),{},dict(run_id=self.run_id),None)
                    continue
                with self.assertRaises(ValueError):self.parse(data,raw)

    def test_failed_creation_keeps_original_handle_error_and_failure(self):
        data=self.receipt(handle=0,result=0,error=5);parsed=self.parse(data)
        self.assertEqual(parsed["apis"][0].data(),data)
        self.assertEqual(parsed["failures"],[("CreateDesktopW","desktop","setup",0,5)])
        self.assertTrue(parsed["failed"])

    def test_success_claim_missing_original_desktop_creation_rejects(self):
        original=adapter.OUTER_MAGIC+packet(1,"finish",dict(failed=0,debt=0,scope="V3_initial_loader_terminate_only"))
        with self.assertRaisesRegex(ValueError,"complete outer needs the original restricted private desktop request"):
            adapter._outer_protocol(adapter.parse_frames(original,actor="outer"),{},dict(run_id=self.run_id),None)


class InheritanceJoinTests(unittest.TestCase):
    def originals(self):
        roles=("stdin","stdout","stderr","challenge_writer_inherited","adoption_reader_inherited",
            "challenge_event_inherited","adoption_event_inherited")
        sources=("stdin_original","observer_archive","observer_stderr","challenge_writer","adoption_reader",
            "challenge_event","adoption_event")
        access=(0x120089,0x120196,0x120196,0x120196,0x120089,2,0x100000)
        rows=[];inherited=dict(enumerate(range(900,907)))
        def api(name,role,phase,sequence,handle,result=1,raw=b"",detail=None):
            return frame("api",dict(name=name,role=role,phase=phase,handle=handle,result=result,
                requested=len(raw),returned=len(raw),detail={} if detail is None else detail),raw,sequence=sequence)
        for index,source in enumerate(sources):
            detail=dict(manual_reset=1,initial_state=0,unnamed=1) if index>=5 else {}
            rows.append(api("CreateEventW" if index>=5 else "CreateFileW",source,"channel",index+1,800+index,800+index,detail=detail))
        rows.append(api("GetFileType","stdin_original","channel",8,800,2))
        for index,(role,wanted) in enumerate(zip(roles,access)):
            rows.append(api("DuplicateHandle",role,"inherit",9+index*2,900+index,
                detail=dict(original=800+index,desired_access=wanted,inherit=1,options=0)))
            rows.append(api("GetHandleInformation",role,"inherit",10+index*2,900+index,raw=struct.pack("<I",1)))
        rows.append(api("UpdateProcThreadAttribute","attributes","setup",23,22222,raw=struct.pack("<7Q",*inherited.values())))
        raw=bytearray(112);struct.pack_into("<I",raw,0,112);struct.pack_into("<Q",raw,16,11111)
        struct.pack_into("<I",raw,60,0x100);struct.pack_into("<4Q",raw,80,900,901,902,22222)
        startup=frame("startup_info",dict(bytes=112),bytes(raw),sequence=24)
        rows.append(api("CreateProcessW","observer","launch",25,33333,detail=dict(inherit_handles=1)))
        return dict(apis=rows,startup_info=startup),inherited

    def test_exact_original_access_flags_attribute_list_and_receiver_join(self):
        outer,inherited=self.originals()
        self.assertEqual(adapter._outer_inheritance(outer,inherited),tuple(range(900,907)))

    def test_access_expansion_same_access_options_wrong_channels_and_aliases_fail(self):
        for field,value in (("desired_access",0x1fffff),("inherit",0),("options",2),("original",999)):
            outer,inherited=self.originals();row=outer["apis"][8];data=row.data()
            data["detail"][field]=value;outer["apis"][8]=frame("api",data,row.raw,sequence=row.sequence)
            with self.assertRaises(ValueError):adapter._outer_inheritance(outer,inherited)
        for change in ("receiver","duplicate","flag","event","nul"):
            outer,inherited=self.originals()
            if change=="receiver":inherited[6]=inherited[0]
            elif change=="duplicate":outer["apis"].append(outer["apis"][8])
            elif change=="flag":
                row=outer["apis"][9];outer["apis"][9]=frame("api",row.data(),bytes(4),sequence=row.sequence)
            elif change=="event":
                row=outer["apis"][5];data=row.data();data["detail"]["initial_state"]=1
                outer["apis"][5]=frame("api",data,row.raw,sequence=row.sequence)
            else:
                row=outer["apis"][7];data=dict(row.data(),result=0)
                outer["apis"][7]=frame("api",data,row.raw,sequence=row.sequence)
            with self.assertRaises(ValueError):adapter._outer_inheritance(outer,inherited)

    def test_original_startup_and_exact_handle_list_reject_substitution_or_expansion(self):
        for variant in ("stdio","reserved","attribute","extra","swapped","missing"):
            outer,inherited=self.originals()
            if variant in ("stdio","reserved","attribute"):
                row=outer["startup_info"];raw=bytearray(row.raw)
                if variant=="stdio":struct.pack_into("<Q",raw,80,901)
                elif variant=="reserved":raw[72]=1
                else:struct.pack_into("<Q",raw,104,44444)
                outer["startup_info"]=frame("startup_info",row.data(),bytes(raw),sequence=row.sequence)
            elif variant=="missing":outer["startup_info"]=None
            else:
                row=outer["apis"][-2];data=row.data();raw=row.raw
                if variant=="extra":raw+=struct.pack("<Q",907);data["requested"]=data["returned"]=len(raw)
                else:raw=struct.pack("<7Q",901,900,902,903,904,905,906)
                outer["apis"][-2]=frame("api",data,raw,sequence=row.sequence)
            with self.assertRaises(ValueError):adapter._outer_inheritance(outer,inherited)

    def test_outer_protocol_accepts_actual_emitted_startup_and_nul_operations(self):
        outer,_=self.originals();startup=outer["startup_info"]
        data=dict(name="GetFileType",role="stdin_original",phase="channel",handle=800,result=2,error=0,
            requested=0,returned=0,length_kind="source_capacity_no_native_count",begin=dict(result=1,error=0,tick=1),
            end=dict(result=1,error=0,tick=2),detail={})
        rows=(frame("startup_info",startup.data(),startup.raw),frame("api",data,sequence=2),
            frame("finish",dict(failed=1,debt=0,scope="V3_initial_loader_terminate_only"),sequence=3))
        parsed=adapter._outer_protocol(rows,{}, {},None)
        self.assertEqual(parsed["startup_info"].raw,startup.raw);self.assertEqual(parsed["failures"],[])


class ExitIdentityTests(unittest.TestCase):
    """Source-owned original-packet models, never native identity proof."""
    def originals(self):
        role="observer";handle=77;pid=501;creation=1000;path=r"c:\fixture\observer.exe"
        rows=[]
        def api(name,phase,result,raw=b"",detail=None,*,requested=None,returned=None,error=0):
            sequence=len(rows)+1
            value=dict(name=name,role=role,phase=phase,handle=handle,result=result,error=error,
                requested=len(raw) if requested is None else requested,returned=len(raw) if returned is None else returned,
                length_kind="original_native_count" if name=="QueryFullProcessImageNameW" else "source_capacity_no_native_count",
                begin=dict(result=1,error=0,tick=sequence*2),end=dict(result=1,error=0,tick=sequence*2+1),
                detail={} if detail is None else detail)
            rows.append(frame("api",value,raw,sequence=sequence))
        api("GetProcessId","adopt_after",pid)
        raw=path.encode("utf-16le");api("QueryFullProcessImageNameW","adopt_after",1,
            raw+bytes(65536-len(raw)),requested=65536,returned=len(path))
        api("GetProcessTimes","adopt_after",1,struct.pack("<4Q",creation,0,7,9))
        api("WaitForSingleObject","adopt_after",258,detail=dict(timeout=0))
        api("GetExitCodeProcess","adopt_after",1,struct.pack("<I",259))
        live=dict(role=role,phase="adopt_after",pid=pid,creation=creation,exit_time=0,wait=258,exit_code=259,
            path=path,sha256="a"*64,path_scope="native_live_query",path_sequence=2,live_identity_sequence=0,
            parent_pid=205,parent_creation=334,parent_scope="previously_proved_retained_generation")
        live_row=frame("identity",live,sequence=6);rows.append(live_row)
        api("WaitForSingleObject","cleanup",0,detail=dict(timeout=5000))
        api("GetProcessId","exit",pid)
        api("GetProcessTimes","exit",1,struct.pack("<4Q",creation,1500,8,10))
        api("WaitForSingleObject","exit",0,detail=dict(timeout=0))
        api("GetExitCodeProcess","exit",1,struct.pack("<I",0))
        final=dict(live,phase="exit",exit_time=1500,wait=0,exit_code=0,
            path_scope="retained_live_identity",live_identity_sequence=live_row.sequence)
        final_row=frame("identity",final,sequence=12);rows.append(final_row)
        api("CloseHandle","close",1)
        originals=adapter.OUTER_MAGIC+b"".join(packet(r.sequence,r.operation,r.data(),r.raw) for r in rows)
        parsed=adapter.parse_frames(originals,actor="outer")
        observed=dict(apis=[r for r in parsed if r.operation=="api"],
            identities={(r.data()["role"],r.data()["phase"]):(r,r.data()) for r in parsed if r.operation=="identity"})
        return observed,*observed["identities"][(role,"exit")]

    def replace_api(self,observed,index,*,raw=None,**changes):
        row=observed["apis"][index];data=row.data();data.update(changes)
        observed["apis"][index]=frame("api",data,row.raw if raw is None else raw,sequence=row.sequence)

    def complete_originals(self):
        """All nine model boundaries and three complete original parent cohorts."""
        actors=("caller","outer","observer","target");rows=[];live={}
        paths={role:"c:\\fixture\\"+role+".exe" for role in actors}
        blobs={role:("whole source-bound "+role).encode("ascii") for role in actors}
        pids={role:100+index for index,role in enumerate(actors)}
        creations={role:1000+index for index,role in enumerate(actors)}
        handles={role:700+index for index,role in enumerate(actors)}
        def api(name,role,phase,result,raw=b"",detail=None,*,requested=None,returned=None):
            sequence=len(rows)+1
            data=dict(name=name,role=role,phase=phase,handle=handles.get(role,800),result=result,error=0,
                requested=len(raw) if requested is None else requested,returned=len(raw) if returned is None else returned,
                length_kind="original_native_count" if name=="QueryFullProcessImageNameW" else "source_capacity_no_native_count",
                begin=dict(result=1,error=0,tick=sequence*2),end=dict(result=1,error=0,tick=sequence*2+1),
                detail={} if detail is None else detail)
            rows.append(frame("api",data,raw,sequence=sequence));return sequence
        def identity(role,phase):
            exited=phase=="exit"
            if exited:api("WaitForSingleObject",role,"cleanup",0,detail=dict(timeout=5000))
            api("GetProcessId",role,phase,pids[role])
            if exited:reference,path_sequence=live[role]
            else:
                raw=paths[role].encode("utf-16le")
                path_sequence=api("QueryFullProcessImageNameW",role,phase,1,raw+bytes(65536-len(raw)),
                    requested=65536,returned=len(paths[role]));reference=0
            api("GetProcessTimes",role,phase,1,struct.pack("<4Q",creations[role],2000 if exited else 0,7,9))
            api("WaitForSingleObject",role,phase,0 if exited else 258,detail=dict(timeout=0))
            api("GetExitCodeProcess",role,phase,1,struct.pack("<I",0 if exited else 259))
            parent={"caller":None,"outer":"caller","observer":"outer","target":"observer"}[role]
            data=dict(role=role,phase=phase,pid=pids[role],creation=creations[role],exit_time=2000 if exited else 0,
                wait=0 if exited else 258,exit_code=0 if exited else 259,path=paths[role],sha256=adapter._sha(blobs[role]),
                path_scope="retained_live_identity" if exited else "native_live_query",path_sequence=path_sequence,
                live_identity_sequence=reference,parent_pid=pids[parent] if parent else 0,
                parent_creation=creations[parent] if parent else 0,
                parent_scope="fresh_snapshot" if phase=="startup" else "previously_proved_retained_generation")
            rows.append(frame("identity",data,sequence=len(rows)+1))
            if not exited:live[role]=(rows[-1].sequence,path_sequence)
        def parent(role,parent_role):
            raw=bytearray(1152);struct.pack_into("<iIII",raw,0,1,0,568,pids[role])
            struct.pack_into("<I",raw,40,pids[parent_role]);struct.pack_into("<iIII",raw,576,0,18,568,0)
            api("Process32FirstW/Process32NextW","snapshot","parent",0,bytes(raw),dict(pid=pids[role]))
        identity("caller","startup");identity("outer","startup");parent("outer","caller")
        api("CreateProcessW","observer","launch",1)
        identity("observer","startup");parent("observer","outer");api("ResumeThread","observer_thread","startup",1)
        identity("observer","adopt_before");parent("target","observer");identity("target","adopt_before")
        identity("observer","adopt_after");identity("target","adopt_after")
        identity("observer","exit");identity("target","exit")
        for role in actors:api("CloseHandle",role,"close",1)
        parsed=adapter.parse_frames(adapter.OUTER_MAGIC+b"".join(packet(r.sequence,r.operation,r.data(),r.raw) for r in rows),actor="outer")
        observed=dict(apis=[r for r in parsed if r.operation=="api"],
            identities={(r.data()["role"],r.data()["phase"]):(r,r.data()) for r in parsed if r.operation=="identity"})
        core=dict(paths={**{role:paths[role] for role in actors if role!="target"},"candidate":paths["target"]},
            hashes={role:adapter._sha(blobs[role]) for role in ("caller","outer")},caller_pid=pids["caller"],
            caller_creation=creations["caller"],outer_pid=pids["outer"],outer_creation=creations["outer"])
        return observed,core,dict(observer_binary=blobs["observer"],candidate=blobs["target"])

    def test_all_nine_boundaries_join_full_original_ancestry_source_paths_and_hashes(self):
        observed,core,state=self.complete_originals()
        adapter._outer_identities(observed,core,state)
        self.assertEqual(len(observed["identities"]),9)
        self.assertEqual(sum(r.data()["name"]=="Process32FirstW/Process32NextW" for r in observed["apis"]),3)

    def test_complete_identity_source_hash_path_parent_generation_or_exit_omission_rejects(self):
        for variant in ("observer_source","candidate_source","core_path","parent","core_generation","missing_exit"):
            observed,core,state=self.complete_originals()
            if variant=="observer_source":state["observer_binary"]+=b"changed"
            elif variant=="candidate_source":state["candidate"]+=b"changed"
            elif variant=="core_path":core["paths"]["observer"]=r"c:\fixture\different.exe"
            elif variant=="parent":observed["identities"][("target","adopt_after")][1]["parent_pid"]+=1
            elif variant=="core_generation":core["outer_creation"]+=1
            else:observed["identities"].pop(("target","exit"))
            with self.subTest(variant=variant),self.assertRaises(ValueError):
                adapter._outer_identities(observed,core,state)

    def test_fresh_signaled_exit_joins_full_live_path_and_same_retained_generation(self):
        observed,row,value=self.originals()
        actual=adapter._outer_identity_cohort(observed,row,value)
        self.assertEqual(tuple(r.data()["name"] for r in actual),
            ("GetProcessId","GetProcessTimes","WaitForSingleObject","GetExitCodeProcess"))
        self.assertEqual(observed["apis"][1].raw[:len(value["path"])*2].decode("utf-16le"),value["path"])
        self.assertFalse(any(r.data()["name"]=="QueryFullProcessImageNameW" and r.data()["phase"]=="exit"
            for r in observed["apis"]))

    def test_original_outer_parser_requires_all_successor_identity_scope_fields(self):
        observed,row,value=self.originals()
        rows=sorted(observed["apis"]+[item[0] for item in observed["identities"].values()],key=lambda item:item.sequence)
        rows.append(frame("finish",dict(failed=1,debt=0,scope="V3_initial_loader_terminate_only"),sequence=14))
        parsed=adapter._outer_protocol(tuple(rows),{}, {},None)
        self.assertEqual(parsed["identities"][("observer","exit")][1],value)
        for field in ("path_scope","path_sequence","live_identity_sequence"):
            changed=dict(value);changed.pop(field)
            altered=[frame("identity",changed,sequence=item.sequence) if item.sequence==row.sequence else item for item in rows]
            with self.subTest(field=field),self.assertRaises(ValueError):
                adapter._outer_protocol(tuple(altered),{}, {},None)

    def test_missing_substituted_live_reference_handle_generation_path_and_hash_reject(self):
        for variant in ("absent","reference","path_reference","scope","path","hash","pid","creation","other_handle"):
            observed,row,value=self.originals()
            if variant=="absent":observed["identities"].pop(("observer","adopt_after"))
            elif variant=="reference":value["live_identity_sequence"]=5
            elif variant=="path_reference":value["path_sequence"]=1
            elif variant=="scope":value["path_scope"]="native_live_query"
            elif variant=="path":value["path"]=r"c:\fixture\foreign.exe"
            elif variant=="hash":value["sha256"]="b"*64
            elif variant=="pid":value["pid"]=502;self.replace_api(observed,6,result=502)
            elif variant=="creation":value["creation"]=1001;self.replace_api(observed,7,raw=struct.pack("<4Q",1001,1500,8,10))
            else:
                for index in range(5):self.replace_api(observed,index,handle=78)
            with self.subTest(variant=variant),self.assertRaises(ValueError):
                adapter._outer_identity_cohort(observed,row,value)

    def test_missing_full_buffers_count_policy_failed_queries_and_nonterminated_exit_reject(self):
        variants=((1,dict(raw=b"short")),(1,dict(result=0,error=31)),(1,dict(requested=65535)),
            (1,dict(length_kind="source_capacity_no_native_count")),(1,dict(returned=0)),
            (6,dict(raw=b"unexpected")),(6,dict(returned=1)),(7,dict(raw=bytes(31))),
            (7,dict(result=0,error=6)),(8,dict(result=258)),(9,dict(raw=bytes(3))),
            (9,dict(result=0,error=6)))
        for index,changes in variants:
            observed,row,value=self.originals();self.replace_api(observed,index,**changes)
            with self.subTest(index=index,changes=changes),self.assertRaises(ValueError):
                adapter._outer_identity_cohort(observed,row,value)
        for exit_time in (0,999):
            observed,row,value=self.originals();value["exit_time"]=exit_time
            self.replace_api(observed,7,raw=struct.pack("<4Q",1000,exit_time,8,10))
            with self.assertRaises(ValueError):adapter._outer_identity_cohort(observed,row,value)

    def test_early_duplicate_failed_close_or_added_postexit_path_query_rejects(self):
        for variant in ("early","duplicate","failed","missing","cleanup","postexit_query","identity_raw"):
            observed,row,value=self.originals();close=observed["apis"][-1]
            if variant=="early":observed["apis"][-1]=frame("api",close.data(),sequence=7)
            elif variant=="duplicate":observed["apis"].append(close)
            elif variant=="failed":self.replace_api(observed,-1,result=0,error=6)
            elif variant=="missing":observed["apis"].pop()
            elif variant=="cleanup":self.replace_api(observed,5,result=258)
            elif variant=="identity_raw":row=frame("identity",value,b"unexpected",sequence=row.sequence)
            else:
                live_path=observed["apis"][1];data=dict(live_path.data(),phase="exit",result=0,error=31)
                observed["apis"].insert(6,frame("api",data,bytes(65536),sequence=7))
            with self.subTest(variant=variant),self.assertRaises(ValueError):
                adapter._outer_identity_cohort(observed,row,value)


class ReplayFailureTests(unittest.TestCase):
    def test_overlapping_false_inventories_preserve_scoped_observation_and_all_broader_false_claims(self):
        import hidden_soak_loader_v3 as source
        self.assertTrue(set(source.FALSE_CLAIMS)&set(adapter.FALSE_CLAIMS))
        report=adapter._replay_report(dict(scoped_composition_complete=True,passed=True),True,source.FALSE_CLAIMS)
        self.assertTrue(report["scoped_composition_complete"])
        self.assertTrue(report["fixture_only"])
        self.assertTrue(all(report[key] is False for key in set(source.FALSE_CLAIMS)|set(adapter.FALSE_CLAIMS)))
        for claims in (dict(source.FALSE_CLAIMS,passed=True),dict(source.FALSE_CLAIMS,passed=0),None):
            with self.assertRaises(ValueError):adapter._replay_report({},True,claims)
        with patch.dict(adapter.FALSE_CLAIMS,passed=True):
            with self.assertRaises(ValueError):adapter._replay_report({},True,source.FALSE_CLAIMS)

    def test_postcollection_plain_error_preserves_exact_joined_streams_frames_and_original_cause(self):
        originals=adapter.JoinedOriginals(b"caller",b"outer",b"observer",b"observer stderr",b"outer stderr",b"close")
        cause=TypeError("dict() got multiple values for keyword argument 'passed'")
        rows=(frame("api",{}),)
        with self.assertRaises(adapter.ArchiveError) as caught:
            with adapter._joined_failure_context(originals,rows):raise cause
        self.assertIs(caught.exception.originals,originals)
        self.assertIs(caught.exception.original_archive,originals.observer)
        self.assertIs(caught.exception.frames,rows)
        self.assertIs(caught.exception.cause,cause);self.assertIs(caught.exception.__cause__,cause)
        self.assertIn("TypeError",str(caught.exception))

    def test_existing_joined_rejection_and_cancellation_keep_original_exception(self):
        originals=adapter.JoinedOriginals(b"caller",b"outer",b"observer",b"stderr")
        for error in (adapter.ArchiveError("original rejection",originals.observer,originals=originals),
                      KeyboardInterrupt("original cancellation"),SystemExit(7)):
            with self.subTest(kind=type(error).__name__),self.assertRaises(type(error)) as caught:
                with adapter._joined_failure_context(originals):raise error
            self.assertIs(caught.exception,error)
            self.assertIs(error.originals,originals)


if __name__ == "__main__":
    unittest.main()
