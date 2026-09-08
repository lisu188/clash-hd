from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import framed_loaded_probe as probe
import test_framed_loaded_probe as fixtures

MAGIC = b"CLASH_HD_DEBUGGER_FIXTURE_V1"
RESULT = re.compile(r"^BNDLOAD contract=([0-9a-f]{64}) candidate=([0-9a-f]{64}) result=(pass|fail)(?: chunks=([0-9]+))?$", re.MULTILINE)
MISMATCH = re.compile(r"^BNDLOAD_MISMATCH chunk=([0-9]+)$", re.MULTILINE)


def executable_fixture(resolution: str = "1280x720", *, aslr: bool = False):
    source, report, scalar = fixtures.candidate(resolution)
    data = bytearray(source)
    image = probe.pe.inspect_pe(source)
    opt = image.optional_offset
    data[64:64 + len(MAGIC)] = MAGIC
    struct.pack_into("<I", data, opt + 16, 0x10E0)
    struct.pack_into("<HH", data, opt + 40, 6, 0)
    struct.pack_into("<HH", data, opt + 48, 6, 0)
    struct.pack_into("<HH", data, opt + 68, 3, 0x40 if aslr else 0)
    struct.pack_into("<IIII", data, opt + 72, 0x100000, 0x1000, 0x100000, 0x1000)
    entry = image.file_offset(0x10E0, 2)
    data[entry:entry + 2] = b"\xeb\xfe"
    updated = bytes(data)
    report = deepcopy(report)
    parent = bytearray(updated)
    for edit in report["edits"]:
        original = bytes.fromhex(edit["old_hex"])
        parent[edit["offset"]:edit["offset"] + len(original)] = original
    report["output_sha256"] = probe._sha(updated)
    report["parent_sha256"] = probe._sha(bytes(parent))
    report["parent_build"]["output_sha256"] = report["parent_sha256"]
    return updated, report, scalar


HARNESS = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <dbgeng.h>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

static void check(HRESULT hr, const char *operation) {
    if (hr != S_OK) {
        char text[160]; sprintf_s(text, "%s failed: 0x%08lx", operation, hr);
        throw std::runtime_error(text);
    }
}

struct CaptureOutput : IDebugOutputCallbacks {
    LONG references = 1;
    STDMETHOD(QueryInterface)(REFIID id, void **out) {
        if (!out) return E_POINTER;
        *out = nullptr;
        if (id != __uuidof(IUnknown) && id != __uuidof(IDebugOutputCallbacks)) return E_NOINTERFACE;
        *out = static_cast<IDebugOutputCallbacks *>(this); AddRef(); return S_OK;
    }
    STDMETHOD_(ULONG, AddRef)() { return InterlockedIncrement(&references); }
    STDMETHOD_(ULONG, Release)() { return InterlockedDecrement(&references); }
    STDMETHOD(Output)(ULONG, PCSTR text) { fputs(text, stdout); fflush(stdout); return S_OK; }
};

struct Session {
    HMODULE engine = nullptr;
    IDebugClient *client = nullptr;
    IDebugControl *control = nullptr;
    IDebugDataSpaces *memory = nullptr;
    IDebugSystemObjects *system = nullptr;
    IDebugRegisters *registers = nullptr;
    IDebugSymbols *symbols = nullptr;
    ~Session() {
        if (client) { client->EndSession(DEBUG_END_ACTIVE_TERMINATE); client->SetOutputCallbacks(nullptr); }
        if (symbols) symbols->Release();
        if (registers) registers->Release();
        if (system) system->Release();
        if (memory) memory->Release();
        if (control) control->Release();
        if (client) client->Release();
        if (engine) FreeLibrary(engine);
    }
    std::vector<unsigned char> read(ULONG64 address, ULONG size) {
        std::vector<unsigned char> result(size); ULONG read = 0;
        check(memory->ReadVirtual(address, result.data(), size, &read), "ReadVirtual");
        if (read != size) throw std::runtime_error("short target read");
        return result;
    }
};

int main(int argc, char **argv) {
    if (argc != 3 || (std::string(argv[2]) != "file" && std::string(argv[2]) != "block")) return 2;
    std::ifstream input("probe-fixture.exe", std::ios::binary);
    std::vector<unsigned char> disk((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    const char *magic = "CLASH_HD_DEBUGGER_FIXTURE_V1";
    if (disk.size() < 256 || memcmp(disk.data(), "MZ", 2) || memcmp(disk.data() + 64, magic, strlen(magic))) return 2;
    CaptureOutput output;
    Session session;
    try {
        char system_dir[MAX_PATH], engine_path[MAX_PATH];
        if (!GetSystemDirectoryA(system_dir, MAX_PATH)) throw std::runtime_error("GetSystemDirectory");
        sprintf_s(engine_path, "%s\\dbgeng.dll", system_dir);
        session.engine = LoadLibraryExA(engine_path, nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
        if (!session.engine) throw std::runtime_error("Cannot load the system x86 debugger engine");
        auto create = reinterpret_cast<HRESULT(WINAPI *)(REFIID, PVOID *)>(GetProcAddress(session.engine, "DebugCreate"));
        if (!create) throw std::runtime_error("Missing DebugCreate export");
        check(create(__uuidof(IDebugClient), reinterpret_cast<void **>(&session.client)), "DebugCreate");
        check(session.client->QueryInterface(__uuidof(IDebugControl), reinterpret_cast<void **>(&session.control)), "IDebugControl");
        check(session.client->QueryInterface(__uuidof(IDebugDataSpaces), reinterpret_cast<void **>(&session.memory)), "IDebugDataSpaces");
        check(session.client->QueryInterface(__uuidof(IDebugSystemObjects), reinterpret_cast<void **>(&session.system)), "IDebugSystemObjects");
        check(session.client->QueryInterface(__uuidof(IDebugRegisters), reinterpret_cast<void **>(&session.registers)), "IDebugRegisters");
        check(session.client->QueryInterface(__uuidof(IDebugSymbols), reinterpret_cast<void **>(&session.symbols)), "IDebugSymbols");
        check(session.client->SetOutputCallbacks(&output), "SetOutputCallbacks");
        check(session.symbols->SetSymbolPath("."), "SetSymbolPath");
        check(session.control->AddEngineOptions(DEBUG_ENGOPT_INITIAL_BREAK | DEBUG_ENGOPT_DISALLOW_SHELL_COMMANDS), "AddEngineOptions");
        char target[MAX_PATH];
        if (!GetFullPathNameA("probe-fixture.exe", MAX_PATH, target, nullptr)) throw std::runtime_error("Fixture path resolution failed");
        std::string command_line = std::string("\"") + target + "\"";
        std::vector<char> command(command_line.begin(), command_line.end());
        command.push_back('\0');
        check(session.client->CreateProcess(0, command.data(), DEBUG_ONLY_THIS_PROCESS | CREATE_NO_WINDOW), "CreateProcess");
        check(session.control->WaitForEvent(0, 15000), "WaitForEvent");
        if (session.control->IsPointer64Bit() != S_FALSE) throw std::runtime_error("Not an x86 debugger context");
        ULONG64 peb = 0, ip_before = 0, ip_after = 0;
        check(session.system->GetCurrentProcessPeb(&peb), "GetCurrentProcessPeb");
        auto base_bytes = session.read(peb + 8, 4);
        ULONG base = *reinterpret_cast<const ULONG *>(base_bytes.data());
        ULONG nt_offset = *reinterpret_cast<const ULONG *>(&disk[60]);
        const auto *nt = reinterpret_cast<const IMAGE_NT_HEADERS32 *>(&disk[nt_offset]);
        ULONG size = nt->OptionalHeader.SizeOfImage;
        ULONG machine_before = 0;
        check(session.control->GetEffectiveProcessorType(&machine_before), "GetEffectiveProcessorType");
        check(session.registers->GetInstructionOffset(&ip_before), "GetInstructionOffset");
        if (ip_before >= base && ip_before < base + size) throw std::runtime_error("Fixture instructions reached before verification");
        std::vector<std::pair<ULONG, std::vector<unsigned char>>> snapshots;
        snapshots.emplace_back(0, session.read(base, nt->OptionalHeader.SizeOfHeaders));
        const auto *loaded_nt = reinterpret_cast<const IMAGE_NT_HEADERS32 *>(snapshots[0].second.data() + nt_offset);
        printf("HARNESS_IMAGE_BASE file=%08lx loaded=%08lx expected=%08lx\n",
               nt->OptionalHeader.ImageBase, loaded_nt->OptionalHeader.ImageBase, base);
        for (ULONG i = 0; i < nt->OptionalHeader.SizeOfHeaders; ++i)
            if (snapshots[0].second[i] != disk[i])
                printf("HARNESS_HEADER_CHANGE offset=%08lx file=%02x loaded=%02x\n", i, disk[i], snapshots[0].second[i]);
        const auto *sections = IMAGE_FIRST_SECTION(nt);
        for (int i = 0; i < nt->FileHeader.NumberOfSections; ++i) {
            if (sections[i].PointerToRawData && (sections[i].Characteristics & IMAGE_SCN_MEM_EXECUTE))
                snapshots.emplace_back(sections[i].VirtualAddress,
                                       session.read(base + sections[i].VirtualAddress, sections[i].SizeOfRawData));
        }
        printf("HARNESS_BEGIN base=%08lx mode=%s\n", base, argv[2]); fflush(stdout);
        HRESULT executed;
        if (std::string(argv[2]) == "block") {
            std::string command = std::string("$$><") + argv[1];
            executed = session.control->Execute(DEBUG_OUTCTL_THIS_CLIENT, command.c_str(), DEBUG_EXECUTE_NO_REPEAT);
        } else {
            executed = session.control->ExecuteCommandFile(DEBUG_OUTCTL_THIS_CLIENT, argv[1], DEBUG_EXECUTE_NO_REPEAT);
        }
        session.client->FlushCallbacks();
        ULONG machine_after = 0;
        check(session.control->GetEffectiveProcessorType(&machine_after), "GetEffectiveProcessorType");
        printf("HARNESS_CONTEXT before=%04lx after=%04lx\n", machine_before, machine_after);
        check(session.control->SetEffectiveProcessorType(machine_before), "Restore debugger inspection context");
        ULONG state = 0;
        check(session.control->GetExecutionStatus(&state), "GetExecutionStatus");
        check(session.registers->GetInstructionOffset(&ip_after), "GetInstructionOffset");
        bool intact = true;
        for (const auto &part : snapshots)
            intact = intact && session.read(base + part.first, static_cast<ULONG>(part.second.size())) == part.second;
        printf("HARNESS_END hr=%08lx paused=%d same_ip=%d unchanged=%d\n", executed,
               state == DEBUG_STATUS_BREAK, ip_before == ip_after, intact);
        fflush(stdout);
        if (state != DEBUG_STATUS_BREAK || ip_before != ip_after || !intact) return 3;
        check(session.client->EndSession(DEBUG_END_ACTIVE_TERMINATE), "EndSession");
        return 0;
    } catch (const std::exception &error) {
        fprintf(stderr, "HARNESS_ERROR %s\n", error.what()); return 2;
    }
}
'''


class ExecutableFixtureTests(unittest.TestCase):
    def test_fixture_retains_full_contract_and_unreachable_entry(self):
        for resolution in fixtures.fixture.SIZES:
            with self.subTest(resolution=resolution):
                data, report, scalar = executable_fixture(resolution)
                parsed, checks, _ = probe._contract(data, report, scalar)
                self.assertEqual(data[64:64 + len(MAGIC)], MAGIC)
                self.assertEqual(data[parsed.file_offset(0x10E0, 2):parsed.file_offset(0x10E0, 2) + 2], b"\xeb\xfe")
                self.assertEqual(struct.unpack_from("<H", data, parsed.optional_offset + 68)[0], 3)
                self.assertTrue(checks)
                script, facts = fixtures.render(data, report, scalar)
                self.assertTrue(script.endswith("\r\n"))
                self.assertNotIn("\n", script.replace("\r\n", ""))
                self.assertEqual(fixtures.evaluate_commands(script, fixtures.mapped(data, parsed.image_base), parsed.image_base), facts["required_chunks"])

    def test_dynamic_base_header_preserves_relocation_directory(self):
        fixed, _, _ = executable_fixture()
        dynamic, _, _ = executable_fixture(aslr=True)
        image = probe.pe.inspect_pe(fixed)
        self.assertEqual(probe.pe._old_relocations(fixed, image), probe.pe._old_relocations(dynamic, probe.pe.inspect_pe(dynamic)))
        changes = [i for i, (a, b) in enumerate(zip(fixed, dynamic)) if a != b]
        self.assertEqual(changes, [image.optional_offset + 70])

    def test_harness_is_restricted_to_marked_fixture_and_system_debugger(self):
        self.assertIn('memcmp(disk.data() + 64, magic, strlen(magic))', HARNESS)
        self.assertIn('LOAD_LIBRARY_SEARCH_SYSTEM32', HARNESS)
        self.assertIn('DEBUG_ONLY_THIS_PROCESS | CREATE_NO_WINDOW', HARNESS)
        self.assertIn('DEBUG_END_ACTIVE_TERMINATE', HARNESS)
        self.assertNotIn('AttachProcess(', HARNESS)
        self.assertNotIn('SetExecutionStatus(', HARNESS)


@unittest.skipUnless(os.name == "nt" and os.environ.get("CLASH_DEBUGGER_INTEGRATION") == "1",
                     "opt-in isolated Windows debugger-engine lane required")
class DebuggerEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="clash-probe-engine-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        compiler = shutil.which("cl.exe")
        if not compiler:
            raise AssertionError("MSVC x86 environment is required")
        source = cls.root / "engine.cpp"
        source.write_text(HARNESS, encoding="utf-8")
        cls.runner = cls.root / "engine.exe"
        result = subprocess.run([compiler, "/nologo", "/EHsc", "/W4", "/O2", "/MT", str(source),
                                 "/Fe:" + str(cls.runner), "/Fo:" + str(cls.root / "engine.obj"),
                                 "/link", "/MACHINE:X86"], cwd=cls.root, capture_output=True, text=True, timeout=60,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.records = []
        cls.addClassCleanup(cls.save_report)

    @classmethod
    def save_report(cls):
        destination = os.environ.get("CLASH_DEBUGGER_REPORT")
        if destination:
            Path(destination).write_text(json.dumps({"schema": 1, "engine": "system x86 DbgEng",
                "generator_sha256": probe._sha(Path(probe.__file__).read_bytes()),
                "game_runtime_executed": False, "manual_input_proof": False,
                "fixture_only": True, "cases": cls.records}, indent=2), encoding="utf-8")

    def execute(self, data, script, *, mode="file", label="case"):
        with tempfile.TemporaryDirectory(prefix="session-", dir=self.root) as temporary:
            directory = Path(temporary)
            (directory / "probe-fixture.exe").write_bytes(data)
            (directory / "verify.cdb").write_text(script, encoding="ascii", newline="\n")
            try:
                result = subprocess.run([str(self.runner), "verify.cdb", mode], cwd=directory, capture_output=True,
                                        text=True, errors="replace", timeout=35, creationflags=subprocess.CREATE_NO_WINDOW)
            except subprocess.TimeoutExpired as exc:
                raise AssertionError(f"Debugger fixture timeout: {label}; {exc.stdout!r}; {exc.stderr!r}") from exc
            combined = result.stdout + result.stderr
            self.records.append({"test": self._testMethodName, "case": label, "mode": mode,
                                 "script_sha256": probe._sha(script.encode("ascii")), "fixture_sha256": probe._sha(data),
                                 "returncode": result.returncode, "log": combined})
            self.assertEqual(result.returncode, 0, combined)
            self.assertRegex(combined, r"HARNESS_END hr=[0-9a-f]+ paused=1 same_ip=1 unchanged=1")
            self.assertIn("HARNESS_BEGIN", combined)
            return combined

    def assert_pass(self, log, facts):
        self.assertEqual(RESULT.findall(log), [(facts["contract_id"], facts["candidate_sha256"], "pass", str(facts["required_chunks"]))], log)
        self.assertIn("HARNESS_END hr=00000000", log)
        self.assertIn("HARNESS_CONTEXT before=014c after=014c", log)
        self.assertFalse(MISMATCH.findall(log), log)
        self.assertNotIn("Syntax error", log)

    def assert_rejected(self, log, *, syntax_valid=True):
        records = RESULT.findall(log)
        self.assertFalse(any(row[2] == "pass" for row in records), log)
        if syntax_valid:
            self.assertEqual(len(records), 1, log)
            self.assertEqual(records[0][2], "fail", log)
            self.assertNotIn("Syntax error", log)

    def test_full_generated_probe_at_all_ten_resolutions(self):
        for resolution in fixtures.fixture.SIZES:
            with self.subTest(resolution=resolution):
                data, report, scalar = executable_fixture(resolution)
                script, facts = fixtures.render(data, report, scalar)
                self.assert_pass(self.execute(data, script, label=resolution), facts)

    def test_documented_block_command_executes_the_exported_file(self):
        data, report, scalar = executable_fixture("1366x768")
        script, facts = fixtures.render(data, report, scalar)
        self.assert_pass(self.execute(data, script, mode="block"), facts)

    def test_actual_windows_loader_rebasing(self):
        data, report, scalar = executable_fixture("3840x2160", aslr=True)
        script, facts = fixtures.render(data, report, scalar)
        log = self.execute(data, script, label="aslr")
        self.assert_pass(log, facts)
        actual = int(re.search(r"HARNESS_BEGIN base=([0-9a-f]+)", log)[1], 16)
        self.assertNotEqual(actual, probe.pe.inspect_pe(data).image_base, "ASLR fixture did not relocate; coverage is incomplete")
        self.assertIn(f"HARNESS_IMAGE_BASE file=00400000 loaded={actual:08x} expected={actual:08x}", log)
        offsets = [int(value, 16) for value in re.findall(r"HARNESS_HEADER_CHANGE offset=([0-9a-f]+)", log)]
        header = probe.pe.inspect_pe(data).optional_offset + 28
        self.assertTrue(offsets, "The loader did not normalize ImageBase")
        self.assertTrue(all(header <= value < header + 4 for value in offsets), log)

    def test_corruption_in_headers_hooks_scalars_and_payload_cannot_pass(self):
        data, report, scalar = executable_fixture()
        script, facts = fixtures.render(data, report, scalar)
        parsed = probe.pe.inspect_pe(data)
        for offset in (48, parsed.file_offset(0x1040, 1), parsed.file_offset(0x1051, 1),
                       parsed.file_offset(report["code_va"] - parsed.image_base, 1)):
            changed = bytearray(data)
            changed[offset] ^= 0x10
            with self.subTest(offset=offset):
                log = self.execute(bytes(changed), script, label=f"corrupt-{offset:x}")
                self.assert_rejected(log)
                self.assertTrue(MISMATCH.findall(log), log)

    def test_missing_duplicate_and_reordered_chunks_do_not_replace_coverage(self):
        data, report, scalar = executable_fixture()
        script, _ = fixtures.render(data, report, scalar)
        lines = script.splitlines()
        chunks = [i for i, line in enumerate(lines) if ".echo BNDLOAD_MISMATCH" in line]
        missing, duplicate, reordered = [list(lines) for _ in range(3)]
        del missing[chunks[2]]
        duplicate[chunks[2]] = duplicate[chunks[1]]
        reordered[chunks[0]], reordered[chunks[1]] = reordered[chunks[1]], reordered[chunks[0]]
        for label, altered in (("missing", missing), ("duplicate", duplicate), ("reordered", reordered)):
            with self.subTest(case=label):
                log = self.execute(data, "\r\n".join(altered) + "\r\n", label=label)
                self.assert_rejected(log)

    def test_unreadable_memory_and_syntax_error_never_report_pass(self):
        data, report, scalar = executable_fixture()
        script, _ = fixtures.render(data, report, scalar)
        first = next(line for line in script.splitlines() if ".echo BNDLOAD_MISMATCH" in line)
        for label, changed in (("unreadable", first.replace("dwo(@$t19 + 0x00000000)", "dwo(0x00000001)", 1)),
                               ("bad-register", first.replace("dwo(@$t19", "dwo(@$nonexistent", 1))):
            self.assertNotEqual(changed, first)
            with self.subTest(case=label):
                log = self.execute(data, script.replace(first, changed), label=label)
                self.assert_rejected(log, syntax_valid=False)

    def test_wrong_pointer_context_cannot_pass(self):
        data, report, scalar = executable_fixture()
        script, _ = fixtures.render(data, report, scalar)
        log = self.execute(data, ".effmach amd64\r\n" + script, label="wrong-context")
        self.assertIn("HARNESS_CONTEXT before=014c after=8664", log)
        self.assert_rejected(log, syntax_valid=False)

    def test_parent_stage_mouse_bytes_are_rejected(self):
        data, report, scalar = executable_fixture()
        script, _ = fixtures.render(data, report, scalar)
        stale = bytearray(data)
        for edit in report["edits"]:
            previous = bytes.fromhex(edit["old_hex"])
            stale[edit["offset"]:edit["offset"] + len(previous)] = previous
        log = self.execute(bytes(stale), script, label="parent-mouse-gate")
        self.assert_rejected(log)


if __name__ == "__main__":
    unittest.main()
