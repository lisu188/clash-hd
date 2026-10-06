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
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import framed_loaded_probe as probe
import test_framed_loaded_probe as fixtures

MAGIC = b"CLASH_HD_DEBUGGER_FIXTURE_V1"
# Parse native LF/CRLF without changing the retained original output bytes.
HEADER = re.compile(r"^BNDLOAD contract=([0-9a-f]{64}) candidate=([0-9a-f]{64}) stage=([^\s]+) resolution=([0-9]+x[0-9]+)(?:\r?\n|\Z)", re.MULTILINE)
RESULT = re.compile(r"^BNDLOAD contract=([0-9a-f]{64}) candidate=([0-9a-f]{64}) result=(pass|fail)(?: chunks=([0-9]+))?(?:\r?\n|\Z)", re.MULTILINE)
MISMATCH = re.compile(r"^BNDLOAD_MISMATCH chunk=([0-9]+)(?:\r?\n|\Z)", re.MULTILINE)

# Synthetic CI diagnostics only. These bounds are storage allowances, not proof
# of native cleanup, game execution, input or release acceptance.
RETENTION_LIMIT = 512 * 1024 * 1024
ATOMIC_LIMIT = 64 * 1024 * 1024
CASE_LIMIT = 128
PHASES = ("execute", "flush", "processor", "restore", "status", "ip", "compare", "end_session")
PHASE = re.compile(r"^HARNESS_PHASE seq=(\d+) name=(\w+) edge=(begin|end) "
                   r"tick=(-?\d+) qpc=(-?\d+) error=(\d+) hr=(-?\d+) value=(\d+)(?:\r?\n|\Z)", re.M)


class RetentionError(RuntimeError):
    """Keep the original unwritten bytes in RAM; never substitute an empty file."""
    def __init__(self, message, original, *, partial_path=None):
        super().__init__(message)
        self.original = original
        self.partial_path = partial_path


def _plain_path(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("retention path must be absolute")
    for item in (path, *path.parents):
        if item.exists() and (item.is_symlink() or getattr(item.stat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("retention path traverses a reparse point")
    return path.resolve()


def ci_artifact_parent(environment=os.environ):
    if environment.get("GITHUB_ACTIONS") != "true" or environment.get("CLASH_DEBUGGER_INTEGRATION") != "1":
        raise ValueError("native synthetic fixtures require explicit GitHub CI opt-in")
    parent = _plain_path(environment["CLASH_PROBE_ENGINE_ARTIFACT_DIR"])
    runner = _plain_path(environment["RUNNER_TEMP"])
    if parent == runner or runner not in parent.parents or parent == ROOT or ROOT in parent.parents or parent in ROOT.parents:
        raise ValueError("artifact directory must be an external RUNNER_TEMP child")
    return parent


class ArtifactStore:
    """An owned, never automatically removed run directory and atomic byte sink.

    Unknown subprocess output is retained in RAM before this bounded sink. An
    oversized original or failed atomic write is retention debt and cannot pass.
    Compiler-created files are accounted after compilation; this is not a native
    disk quota or an assertion that a killed process was cleaned up.
    """
    def __init__(self, parent, *, disk_usage=shutil.disk_usage):
        self.parent = _plain_path(parent)
        self.disk_usage = disk_usage
        self.retained = 0
        self.artifacts = {}
        self.failed = False
        self.pending = []
        self._reserve(b"")
        self.root = self.parent / ("probe-engine-" + uuid.uuid4().hex)
        self.root.mkdir(parents=True, exist_ok=False)

    def _reserve(self, original, old_size=0):
        usage = self.disk_usage(self.parent if self.parent.exists() else self.parent.parent)
        if (len(original) > ATOMIC_LIMIT or self.retained - old_size + len(original) > RETENTION_LIMIT
                or usage.free <= usage.total // 10 + RETENTION_LIMIT - self.retained + ATOMIC_LIMIT):
            self.failed = True
            self.pending.append(original)
            raise RetentionError("strict disk reserve or retained-byte capacity failed", original)

    def write(self, name, original):
        if type(original) is not bytes:
            raise TypeError("original artifact must be bytes")
        target = self.root / name
        if target.parent != self.root or not name or target.name != name:
            raise ValueError("artifact name must be one owned path component")
        old = self.artifacts.get(name)
        if old and (not target.is_file() or probe._sha(target.read_bytes()) != old["sha256"]):
            self.failed = True
            self.pending.append(original)
            raise RetentionError("previous retained artifact changed", original)
        self._reserve(original, old["bytes"] if old else 0)
        partial = self.root / (name + ".pending-" + uuid.uuid4().hex)
        published = False
        try:
            with partial.open("xb") as stream:
                if stream.write(original) != len(original):
                    raise OSError("short atomic write")
                stream.flush()
                os.fsync(stream.fileno())
            if partial.read_bytes() != original:
                raise OSError("atomic readback differs from original bytes")
            os.replace(partial, target)
            published = True
            if target.read_bytes() != original:
                raise OSError("published readback differs from original bytes")
        except BaseException as error:
            self.failed = True
            self.pending.append(original)
            raise RetentionError(str(error), original, partial_path=str(target if published else partial)) from error
        row = {"path": str(target), "bytes": len(original), "sha256": probe._sha(original)}
        self.retained += len(original) - (old["bytes"] if old else 0)
        self.artifacts[name] = row
        return dict(row)

    def json(self, name, value):
        return self.write(name, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))

    def observation(self, name, original):
        if original is None:
            return {"available": False, "artifact": None}
        return {"available": True, "artifact": self.write(name, original)}

    def account_compiler_files(self):
        for path in sorted(self.root.iterdir()):
            if path.is_file() and path.name not in self.artifacts and not ".pending-" in path.name:
                # Keep the existing original even when accounting fails.
                original = path.read_bytes()
                self._reserve(original)
                self.artifacts[path.name] = {"path": str(path), "bytes": len(original), "sha256": probe._sha(original)}
                self.retained += len(original)


def phase_receipt(log):
    """Recompute only synthetic diagnostic completeness from original output."""
    rows = PHASE.findall(log)
    expected = [(name, edge) for name in PHASES for edge in ("begin", "end")]
    if len(rows) != len(expected) or len(re.findall(r"^HARNESS_PHASE\b[^\r\n]*", log, re.M)) != len(rows):
        return False
    previous = None
    for index, (row, pair) in enumerate(zip(rows, expected), 1):
        sequence, name, edge, tick, native, error, hr, value = row
        tick = int(tick)
        if (int(sequence) != index or (name, edge) != pair or not -(1 << 31) <= int(native) < (1 << 31)
                or int(native) == 0 or not 0 <= int(error) < (1 << 32) or not 0 <= tick < (1 << 63)
                or not 0 <= int(value) < (1 << 32)
                or (previous is not None and tick < previous) or int(hr) != 0
                or (name == "status" and edge == "end" and int(value) != 6)
                or (name == "compare" and edge == "end" and int(value) != 1)):
            return False
        previous = tick
    frequencies = re.findall(r"^HARNESS_CLOCK frequency=(-?\d+) native=(-?\d+) error=(\d+)(?:\r?\n|\Z)", log, re.M)
    return (len(frequencies) == 1 and len(re.findall(r"^HARNESS_CLOCK\b[^\r\n]*", log, re.M)) == 1
            and 0 < int(frequencies[0][0]) < (1 << 63)
            and -(1 << 31) <= int(frequencies[0][1]) < (1 << 31) and int(frequencies[0][1]) != 0
            and 0 <= int(frequencies[0][2]) < (1 << 32)
            and len(re.findall(r"^HARNESS_END\b", log, re.M)) == 1
            and re.findall(r"^(HARNESS_END\b[^\r\n]*)(?:\r?\n|\Z)", log, re.M) == ["HARNESS_END hr=00000000 paused=1 same_ip=1 unchanged=1"]
            and len(re.findall(r"^HARNESS_COMPLETE", log, re.M)) == 1
            and re.findall(r"^(HARNESS_COMPLETE[^\r\n]*)(?:\r?\n|\Z)", log, re.M) == ["HARNESS_COMPLETE"]
            and "HARNESS_ERROR" not in log)


def terminal_cases(records, expected):
    labels = [item.get("case") for item in records]
    return (len(labels) == len(expected) and set(labels) == set(expected)
            and all(item.get("status") == "completed" and type(item.get("returncode")) is int
                    and item["returncode"] == 0 and item.get("phase_receipt_passed") is True
                    and item.get("raw_retention_complete") is True for item in records))


class CaseLedger:
    def __init__(self, store, sources):
        self.store = store
        self.sources = {str(_plain_path(path)): Path(path).read_bytes() for path in sources}
        self.records = []
        self.original_observations = []
        self.failure = None
        self.source_rows = {path: store.write("source-%03d.bin" % index, raw)
                            for index, (path, raw) in enumerate(sorted(self.sources.items()))}
        self.persist()

    def persist(self):
        self.store.json("ledger.json", {"schema": "clash_synthetic_probe_diagnostics_v1",
            "fixture_only": True, "game_runtime_executed": False, "native_cleanup_verified": False,
            "manual_input_proof": False, "promotion_ready": False,
            "first_failure": self.failure, "retention_debt": self.store.failed,
            "sources": self.source_rows, "cases": self.records})

    def check_sources(self):
        try:
            unchanged = all(Path(path).read_bytes() == raw for path, raw in self.sources.items())
        except OSError:
            unchanged = False
        if not unchanged:
            self.fail("source mutation before or after subprocess")
            raise AssertionError(self.failure)

    def fail(self, message):
        if self.failure is None:
            self.failure = message

    def prepare(self, data, script, *, test, label, mode):
        self.check_sources()
        if (len(self.records) >= CASE_LIMIT or mode not in ("file", "block")
                or any(item["test"] == test and item["case"] == label for item in self.records)):
            self.fail("duplicate case identity or invalid bounded invocation")
            self.persist()
            raise AssertionError(self.failure)
        ordinal = len(self.records) + 1
        directory = self.store.root / ("case-%03d" % ordinal)
        record = {"ordinal": ordinal, "test": test, "case": label, "mode": mode,
                  "status": "pending", "returncode": None, "log": "",
                  "fixture_sha256": probe._sha(data), "script_sha256": probe._sha(script),
                  "raw_retention_complete": False, "phase_receipt_passed": False,
                  "directory": str(directory)}
        self.records.append(record)
        self.persist()  # Pending is durable before any subprocess launch.
        directory.mkdir()
        for name, raw in (("probe-fixture.exe", data), ("verify.cdb", script)):
            artifact = self.store.write("case-%03d-%s" % (ordinal, name), raw)
            # Exact additional launch copy is accounted as another original.
            launch = directory / name
            self.store._reserve(raw)
            try:
                with launch.open("xb") as stream:
                    if stream.write(raw) != len(raw):
                        raise OSError("short launch-input write")
                    stream.flush()
                    os.fsync(stream.fileno())
                if launch.read_bytes() != raw:
                    raise OSError("launch-input readback changed")
            except BaseException as error:
                self.fail("launch-input retention failed")
                self.store.failed = True
                self.store.pending.append(raw)
                raise RetentionError(str(error), raw, partial_path=str(launch)) from error
            self.store.retained += len(raw)
            record[name] = artifact
        self.store.json("case-%03d-pending.json" % ordinal, record)
        self.persist()
        return record

    def before_launch(self, record):
        self.check_sources()
        directory = Path(record["directory"])
        for name, field in (("probe-fixture.exe", "fixture_sha256"), ("verify.cdb", "script_sha256")):
            if probe._sha((directory / name).read_bytes()) != record[field]:
                self.fail("launch input substitution")
                record["status"] = "failed"
                self.persist()
                raise AssertionError(self.failure)

    def outcome(self, record, *, returncode=None, stdout=None, stderr=None, error=None):
        if record["status"] != "pending":
            self.fail("repeated terminal result cannot replace an earlier outcome")
            self.persist()
            raise AssertionError(self.failure)
        prefix = "case-%03d" % record["ordinal"]
        self.original_observations.append((record["ordinal"], stdout, stderr, error))
        record["returncode"] = returncode
        record["status"] = "failed"
        if error is not None:
            self.fail(type(error).__name__ + ": " + str(error))
            record["error"] = {"type": type(error).__name__, "message": str(error),
                               "timeout": getattr(error, "timeout", None), "command": getattr(error, "cmd", None)}
        try:
            record["stdout"] = self.store.observation(prefix + "-stdout.bin", stdout)
            record["stderr"] = self.store.observation(prefix + "-stderr.bin", stderr)
            record["raw_retention_complete"] = True
            # Replacement decoding is diagnostic only. Original byte artifacts
            # remain separate; None means unobserved, never an empty raw file.
            record["log"] = (stdout or b"").decode("utf-8", "replace") + (stderr or b"").decode("utf-8", "replace")
            record["phase_receipt_passed"] = phase_receipt(record["log"])
            self.before_launch(record)  # These original inputs must also survive the subprocess.
            if (error is None and type(returncode) is int and returncode == 0 and stdout is not None
                    and stderr is not None and record["phase_receipt_passed"]):
                record["status"] = "completed"
            else:
                self.fail("nonterminal, failed or incomplete synthetic invocation")
        except BaseException:
            self.fail("raw observation retention or source check failed")
            raise
        finally:
            self.store.json(prefix + "-result.json", record)
            self.persist()
        return record["log"]


def publish_report(owner, destination, report):
    owner.ledger.persist()
    row = owner.store.json("report.json", report)
    if destination:
        target = _plain_path(destination)
        runner = _plain_path(os.environ["RUNNER_TEMP"])
        if runner not in target.parents or ROOT in target.parents:
            raise ValueError("report mirror must be an external RUNNER_TEMP child")
        # The authoritative atomic report remains in the owned artifact tree.
        # Account the mirror's bytes and retain the original on mirror failure.
        raw = Path(row["path"]).read_bytes()
        owner.store._reserve(raw)
        partial = target.with_name(target.name + ".pending-" + uuid.uuid4().hex)
        published = False
        try:
            if target.exists():
                raise OSError("external report mirror already exists")
            with partial.open("xb") as stream:
                if stream.write(raw) != len(raw):
                    raise OSError("short report mirror")
                stream.flush()
                os.fsync(stream.fileno())
            if partial.read_bytes() != raw:
                raise OSError("report mirror pending readback differs")
            os.replace(partial, target)
            published = True
            if target.read_bytes() != raw:
                raise OSError("report mirror readback differs")
        except BaseException as error:
            owner.store.failed = True
            owner.store.pending.append(raw)
            owner.ledger.fail("external report mirror failed")
            report.update(first_failure=owner.ledger.failure, retention_debt=True)
            if "completed" in report:
                report.update(completed=False, passed=False)
            try:
                owner.ledger.persist()
                owner.store.json("report.json", report)
            except BaseException:
                pass  # Original bytes and storage debt remain in RAM and the exception.
            raise RetentionError(str(error), raw, partial_path=str(target if published else partial)) from error
        owner.store.retained += len(raw)


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
#include <process.h>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
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

static unsigned phase_sequence = 0;
static void clock_origin() {
    LARGE_INTEGER frequency = {}; SetLastError(0);
    BOOL native = QueryPerformanceFrequency(&frequency); DWORD error = GetLastError();
    printf("HARNESS_CLOCK frequency=%lld native=%ld error=%lu\n", frequency.QuadPart, native, error);
    if (fflush(stdout) || !native || frequency.QuadPart <= 0) throw std::runtime_error("QPF or diagnostic flush failed");
}
static void phase(const char *name, const char *edge, HRESULT hr = S_OK, ULONG value = 0) {
    LARGE_INTEGER tick = {}; SetLastError(0);
    BOOL native = QueryPerformanceCounter(&tick); DWORD error = GetLastError();
    printf("HARNESS_PHASE seq=%u name=%s edge=%s tick=%lld qpc=%ld error=%lu hr=%ld value=%lu\n",
           ++phase_sequence, name, edge, tick.QuadPart, native, error, hr, value);
    if (fflush(stdout) || !native || tick.QuadPart < 0) throw std::runtime_error("QPC or diagnostic flush failed");
}

// Separate atomic observations of callback input, not translated stdout bytes.
__declspec(align(8)) static volatile LONG64 callback_count = 0;
__declspec(align(8)) static volatile LONG64 callback_input_bytes = 0;

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
    STDMETHOD(Output)(ULONG, PCSTR text) {
        InterlockedIncrement64(&callback_count);
        InterlockedAdd64(&callback_input_bytes, static_cast<LONG64>(strlen(text)));
        fputs(text, stdout); fflush(stdout); return S_OK;
    }
};

struct ExecuteWatchdogState {
    HANDLE stop_event = nullptr;
    volatile LONG active = 0, stop_requested = 0, failed = 0;
};

static void watchdog_operation(ExecuteWatchdogState *state, const char *name,
                               unsigned long long native, DWORD error) {
    if (fprintf(stderr, "HARNESS_WATCHDOG op=%s native=%llu error=%lu\n", name, native, error) < 0
            || fflush(stderr)) InterlockedExchange(&state->failed, 1);
}

static unsigned long long filetime_scalar(const FILETIME &value) {
    return (static_cast<unsigned long long>(value.dwHighDateTime) << 32) | value.dwLowDateTime;
}

static void watchdog_sample(ExecuteWatchdogState *state, unsigned scheduled_seconds,
                            bool wait_available, DWORD wait_result, DWORD wait_error) {
    LONG active_before = InterlockedCompareExchange(&state->active, 0, 0);
    LARGE_INTEGER tick = {};
    FILETIME creation = {}, exit = {}, kernel = {}, user = {};
    IO_COUNTERS io = {};
    SetLastError(0); BOOL qpc = QueryPerformanceCounter(&tick); DWORD qpc_error = GetLastError();
    HANDLE self = GetCurrentProcess();
    SetLastError(0); BOOL cpu = GetProcessTimes(self, &creation, &exit, &kernel, &user);
    DWORD cpu_error = GetLastError();
    SetLastError(0); BOOL counters = GetProcessIoCounters(self, &io); DWORD io_error = GetLastError();
    LONG64 calls = InterlockedCompareExchange64(&callback_count, 0, 0);
    LONG64 bytes = InterlockedCompareExchange64(&callback_input_bytes, 0, 0);
    LONG active_after = InterlockedCompareExchange(&state->active, 0, 0);
    // Preserve native results/errors before any interpretation. Initialized
    // zero output from a failed API is unavailable, never measured zero.
    // The live process exit FILETIME is undefined even when CPU query succeeds.
    if (fprintf(stderr,
            "HARNESS_EXECUTE_WAIT scheduled_seconds=%u active_before=%ld active_after=%ld "
            "wait_available=%u wait_result=%lu wait_error=%lu "
            "qpc_native=%ld qpc_error=%lu tick=%lld cpu_native=%ld cpu_error=%lu "
            "creation=%llu exit=%llu kernel=%llu user=%llu io_native=%ld io_error=%lu "
            "read_operations=%llu write_operations=%llu other_operations=%llu "
            "read_bytes=%llu write_bytes=%llu other_bytes=%llu "
            "callback_count=%lld callback_input_bytes=%lld\n",
            scheduled_seconds, active_before, active_after, wait_available ? 1u : 0u, wait_result, wait_error,
            qpc, qpc_error, tick.QuadPart, cpu, cpu_error,
            filetime_scalar(creation), filetime_scalar(exit), filetime_scalar(kernel), filetime_scalar(user),
            counters, io_error, io.ReadOperationCount, io.WriteOperationCount, io.OtherOperationCount,
            io.ReadTransferCount, io.WriteTransferCount, io.OtherTransferCount, calls, bytes) < 0
            || fflush(stderr)) InterlockedExchange(&state->failed, 1);
}

static unsigned __stdcall watchdog_worker(void *raw) {
    auto *state = static_cast<ExecuteWatchdogState *>(raw);
    const DWORD delays[] = {5000, 5000, 10000, 10000}; // 5, 10, 20, 30 seconds.
    unsigned scheduled_seconds = 0;
    for (DWORD delay : delays) {
        SetLastError(0); DWORD result = WaitForSingleObject(state->stop_event, delay);
        DWORD error = GetLastError();
        if (result == WAIT_OBJECT_0) return 0;
        if (result != WAIT_TIMEOUT) {
            InterlockedExchange(&state->failed, 1);
            watchdog_operation(state, "wait_sample", result, error); return 1;
        }
        if (InterlockedCompareExchange(&state->stop_requested, 0, 0)
                || !InterlockedCompareExchange(&state->active, 0, 0)) return 0;
        scheduled_seconds += delay / 1000;
        watchdog_sample(state, scheduled_seconds, true, result, error);
    }
    return 0;
}

struct ExecuteWatchdog {
    ExecuteWatchdogState *state = new ExecuteWatchdogState;
    HANDLE thread = nullptr;
    ExecuteWatchdog(const ExecuteWatchdog &) = delete;
    ExecuteWatchdog &operator=(const ExecuteWatchdog &) = delete;
    ExecuteWatchdog() {
        SetLastError(0); state->stop_event = CreateEventA(nullptr, TRUE, FALSE, nullptr);
        DWORD event_error = GetLastError();
        watchdog_operation(state, "create_event", reinterpret_cast<uintptr_t>(state->stop_event), event_error);
        if (!state->stop_event) { delete state; state = nullptr; throw std::runtime_error("Watchdog event creation failed"); }
        watchdog_sample(state, 0, false, 0, 0);
        // CRT output in the sampler requires the CRT-owned thread lifetime.
        errno = 0; _set_doserrno(0); SetLastError(0);
        uintptr_t native_thread = _beginthreadex(nullptr, 0, watchdog_worker, state, 0, nullptr);
        DWORD thread_error = GetLastError(); int thread_errno = errno;
        unsigned long thread_doserrno = 0; errno_t doserrno_result = _get_doserrno(&thread_doserrno);
        thread = reinterpret_cast<HANDLE>(native_thread);
        if (fprintf(stderr, "HARNESS_WATCHDOG op=create_thread native=%llu error=%lu errno=%d "
                    "doserrno_result=%d doserrno=%lu\n",
                    static_cast<unsigned long long>(native_thread), thread_error, thread_errno,
                    doserrno_result, thread_doserrno) < 0 || fflush(stderr)) InterlockedExchange(&state->failed, 1);
        if (!thread) {
            SetLastError(0); BOOL closed = CloseHandle(state->stop_event); DWORD error = GetLastError();
            watchdog_operation(state, "close_event_after_create_failure", closed, error);
            delete state; state = nullptr; throw std::runtime_error("Watchdog thread creation failed");
        }
    }
    void mark_active() { InterlockedExchange(&state->active, 1); }
    void mark_returned() { InterlockedExchange(&state->active, 0); }
    void stop() {
        if (!state) return;
        InterlockedExchange(&state->active, 0);
        InterlockedExchange(&state->stop_requested, 1);
        SetLastError(0); BOOL signaled = SetEvent(state->stop_event); DWORD signal_error = GetLastError();
        watchdog_operation(state, "signal_stop", signaled, signal_error);
        if (!signaled) InterlockedExchange(&state->failed, 1);
        // Only this self-process sampler is joined. The external case deadline
        // remains 35 seconds; no debugger/target call or retry occurs here.
        SetLastError(0); DWORD joined = WaitForSingleObject(thread, INFINITE); DWORD join_error = GetLastError();
        watchdog_operation(state, "join", joined, join_error);
        if (joined != WAIT_OBJECT_0) {
            // Unknown termination cannot authorize closing its event or deleting
            // state. Retain them for process lifetime; never leave a worker
            // pointing at an unwound stack or a released callback object.
            state = nullptr; thread = nullptr;
            throw std::runtime_error("Watchdog join failed; unproven ownership retained");
        }
        SetLastError(0); BOOL thread_closed = CloseHandle(thread); DWORD thread_close_error = GetLastError();
        thread = nullptr; watchdog_operation(state, "close_thread", thread_closed, thread_close_error);
        SetLastError(0); BOOL event_closed = CloseHandle(state->stop_event); DWORD event_close_error = GetLastError();
        state->stop_event = nullptr; watchdog_operation(state, "close_event", event_closed, event_close_error);
        bool failed = InterlockedCompareExchange(&state->failed, 0, 0) || !thread_closed || !event_closed;
        delete state; state = nullptr;
        if (failed) throw std::runtime_error("Watchdog diagnostics or owned cleanup failed");
    }
    ~ExecuteWatchdog() {
        try { stop(); }
        catch (...) { fprintf(stderr, "HARNESS_ERROR watchdog stop failure\n"); fflush(stderr); }
    }
};

struct Session {
    HMODULE engine = nullptr;
    IDebugClient *client = nullptr;
    IDebugControl *control = nullptr;
    IDebugDataSpaces *memory = nullptr;
    IDebugSystemObjects *system = nullptr;
    IDebugRegisters *registers = nullptr;
    IDebugSymbols *symbols = nullptr;
    bool ended = false;
    ~Session() {
        if (client) {
            if (!ended) {
                try { phase("fallback_end", "begin"); }
                catch (...) { fprintf(stderr, "HARNESS_ERROR fallback begin diagnostic failure\n"); }
                // Diagnostic failures must never suppress the termination attempt.
                HRESULT hr = client->EndSession(DEBUG_END_ACTIVE_TERMINATE);
                try { phase("fallback_end", "end", hr); }
                catch (...) { fprintf(stderr, "HARNESS_ERROR fallback end diagnostic failure\n"); }
            }
            client->SetOutputCallbacks(nullptr);
        }
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
        clock_origin();
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
        phase("execute", "begin");
        {
            ExecuteWatchdog watchdog;
            watchdog.mark_active();
            if (std::string(argv[2]) == "block") {
                std::string command = std::string("$$><") + argv[1];
                executed = session.control->Execute(DEBUG_OUTCTL_THIS_CLIENT, command.c_str(), DEBUG_EXECUTE_NO_REPEAT);
            } else {
                executed = session.control->ExecuteCommandFile(DEBUG_OUTCTL_THIS_CLIENT, argv[1], DEBUG_EXECUTE_NO_REPEAT);
            }
            watchdog.mark_returned();
            phase("execute", "end", executed);
            watchdog.stop();
        }
        phase("flush", "begin");
        HRESULT flushed = session.client->FlushCallbacks();
        phase("flush", "end", flushed);
        check(flushed, "FlushCallbacks");
        ULONG machine_after = 0;
        phase("processor", "begin");
        HRESULT machine_hr = session.control->GetEffectiveProcessorType(&machine_after);
        phase("processor", "end", machine_hr, machine_after);
        check(machine_hr, "GetEffectiveProcessorType");
        printf("HARNESS_CONTEXT before=%04lx after=%04lx\n", machine_before, machine_after);
        phase("restore", "begin");
        HRESULT restored = session.control->SetEffectiveProcessorType(machine_before);
        phase("restore", "end", restored);
        check(restored, "Restore debugger inspection context");
        ULONG state = 0;
        phase("status", "begin");
        HRESULT state_hr = session.control->GetExecutionStatus(&state);
        phase("status", "end", state_hr, state);
        check(state_hr, "GetExecutionStatus");
        phase("ip", "begin");
        HRESULT ip_hr = session.registers->GetInstructionOffset(&ip_after);
        phase("ip", "end", ip_hr);
        check(ip_hr, "GetInstructionOffset");
        bool intact = true;
        phase("compare", "begin");
        for (const auto &part : snapshots)
            intact = intact && session.read(base + part.first, static_cast<ULONG>(part.second.size())) == part.second;
        phase("compare", "end", S_OK, intact ? 1 : 0);
        printf("HARNESS_END hr=%08lx paused=%d same_ip=%d unchanged=%d\n", executed,
               state == DEBUG_STATUS_BREAK, ip_before == ip_after, intact);
        fflush(stdout);
        if (state != DEBUG_STATUS_BREAK || ip_before != ip_after || !intact) return 3;
        phase("end_session", "begin");
        HRESULT ended_hr = session.client->EndSession(DEBUG_END_ACTIVE_TERMINATE);
        phase("end_session", "end", ended_hr);
        check(ended_hr, "EndSession");
        session.ended = true;
        printf("HARNESS_COMPLETE\n"); fflush(stdout);
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
        cls.store = ArtifactStore(ci_artifact_parent())
        cls.root = cls.store.root
        sources = {Path(module.__file__).resolve() for module in tuple(sys.modules.values())
                   if getattr(module, "__file__", None) and str(module.__file__).endswith(".py")
                   and ROOT in Path(module.__file__).resolve().parents}
        cls.ledger = CaseLedger(cls.store, sorted(sources))
        cls.records = cls.ledger.records
        cls.compiler_receipt = {"status": "pending"}
        cls.addClassCleanup(cls.save_report)
        cls.store.json("compiler.json", cls.compiler_receipt)
        compiler = shutil.which("cl.exe")
        if not compiler:
            cls.ledger.fail("MSVC x86 environment is required")
            cls.ledger.persist()
            raise AssertionError("MSVC x86 environment is required")
        source = Path(cls.store.write("engine.cpp", HARNESS.encode("utf-8"))["path"])
        cls.runner = cls.root / "engine.exe"
        command = [compiler, "/nologo", "/EHsc", "/W4", "/O2", "/MT", str(source),
                   "/Fe:" + str(cls.runner), "/Fo:" + str(cls.root / "engine.obj"), "/link", "/MACHINE:X86"]
        cls.compiler_receipt.update(command=command, timeout=60,
                                    source_sha256=probe._sha(source.read_bytes()), status="pending")
        cls.store.json("compiler.json", cls.compiler_receipt)
        cls.ledger.check_sources()
        try:
            result = subprocess.run(command, cwd=cls.root, capture_output=True, timeout=60,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        except BaseException as error:
            cls.compiler_original_error = error
            originals = (getattr(error, "stdout", None), getattr(error, "stderr", None))
            cls.compiler_original_streams = originals
            cls.compiler_receipt.update(status="failed", error_type=type(error).__name__, error=str(error),
                stdout={"available": originals[0] is not None, "artifact": None},
                stderr={"available": originals[1] is not None, "artifact": None}, raw_retention_complete=False)
            cls.ledger.fail("compiler failed: " + type(error).__name__)
            try:
                cls.compiler_receipt["stdout"] = cls.store.observation("compiler-stdout.bin", originals[0])
                cls.compiler_receipt["stderr"] = cls.store.observation("compiler-stderr.bin", originals[1])
                cls.store.account_compiler_files()
                cls.compiler_receipt["raw_retention_complete"] = True
                cls.store.json("compiler.json", cls.compiler_receipt)
                cls.ledger.persist()
            except BaseException as retention_error:
                cls.store.failed = True
                cls.store.pending.extend(raw for raw in originals if raw is not None)
                cls.compiler_receipt["raw_retention_complete"] = False
                cls.compiler_receipt["retention_error"] = {"type": type(retention_error).__name__, "message": str(retention_error)}
                raise retention_error from error
            raise
        cls.compiler_original_streams = (result.stdout, result.stderr)
        cls.compiler_receipt.update(status="failed", returncode=result.returncode, raw_retention_complete=False)
        try:
            cls.compiler_receipt["stdout"] = cls.store.observation("compiler-stdout.bin", result.stdout)
            cls.compiler_receipt["stderr"] = cls.store.observation("compiler-stderr.bin", result.stderr)
            cls.store.account_compiler_files()
            cls.ledger.check_sources()
            cls.compiler_receipt.update(status="completed" if result.returncode == 0 else "failed", raw_retention_complete=True)
            cls.store.json("compiler.json", cls.compiler_receipt)
        except BaseException:
            cls.compiler_receipt.update(status="failed", raw_retention_complete=False)
            cls.store.failed = True
            cls.store.pending.extend(raw for raw in cls.compiler_original_streams if raw is not None)
            cls.ledger.fail("compiler result retention or source check failed")
            raise
        if result.returncode:
            cls.ledger.fail("compiler nonzero exit")
            cls.ledger.persist()
            raise AssertionError((result.stdout + result.stderr).decode("utf-8", "replace"))
        cls.runner_sha256 = probe._sha(cls.runner.read_bytes())

    @classmethod
    def save_report(cls):
        destination = os.environ.get("CLASH_DEBUGGER_REPORT")
        report = {"schema": 1, "engine": "system x86 DbgEng",
            "generator_sha256": probe._sha(Path(probe.__file__).read_bytes()),
            "game_runtime_executed": False, "manual_input_proof": False,
            "fixture_only": True, "first_failure": cls.ledger.failure,
            "retention_debt": cls.store.failed, "artifact_directory": str(cls.root),
            "compiler": cls.compiler_receipt, "cases": cls.records}
        publish_report(cls, destination, report)

    def execute(self, data, script, *, mode="file", label="case"):
        record = self.ledger.prepare(data, script.encode("ascii"), test=self._testMethodName, label=label, mode=mode)
        self.ledger.before_launch(record)
        if probe._sha(self.runner.read_bytes()) != self.runner_sha256:
            self.ledger.fail("compiled harness substitution")
            self.ledger.persist()
            raise AssertionError(self.ledger.failure)
        record["runner_sha256"] = self.runner_sha256
        record["command"] = [str(self.runner), "verify.cdb", mode]
        record["timeout"] = 35
        self.ledger.persist()
        try:
            result = subprocess.run(record["command"], cwd=record["directory"], capture_output=True,
                                    timeout=35, creationflags=subprocess.CREATE_NO_WINDOW)
        except BaseException as error:
            self.ledger.outcome(record, stdout=getattr(error, "stdout", None),
                                stderr=getattr(error, "stderr", None), error=error)
            raise AssertionError(f"Debugger fixture failed: {label}; {error!r}") from error
        combined = self.ledger.outcome(record, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        self.assertEqual(result.returncode, 0, combined)
        self.assertRegex(combined, r"HARNESS_END hr=[0-9a-f]+ paused=1 same_ip=1 unchanged=1")
        self.assertIn("HARNESS_BEGIN", combined)
        self.assertTrue(record["phase_receipt_passed"], combined)
        return combined

    def assert_bound_records(self, log):
        headers, records = HEADER.findall(log), RESULT.findall(log)
        self.assertEqual(len(headers), 1, log)
        self.assertLessEqual(len(records), 1, log)
        self.assertEqual(len(re.findall(r"^BNDLOAD\b", log, re.M)), len(headers) + len(records), log)
        self.assertEqual(headers[0][2], probe.bounded.STAGE, log)
        resolution = probe.recipe.patcher.parse_resolution(headers[0][3])
        self.assertEqual(resolution.key, headers[0][3], log)
        self.assertTrue(all(row[:2] == headers[0][:2] for row in records), log)
        if records:
            self.assertLess(HEADER.search(log).start(), RESULT.search(log).start(), log)
        return headers[0], records

    def assert_pass(self, log, facts):
        header, records = self.assert_bound_records(log)
        self.assertEqual(header, (facts["contract_id"], facts["candidate_sha256"], facts["stage"], facts["resolution"]), log)
        self.assertEqual(records, [(facts["contract_id"], facts["candidate_sha256"], "pass", str(facts["required_chunks"]))], log)
        self.assertIn("HARNESS_END hr=00000000", log)
        self.assertIn("HARNESS_CONTEXT before=014c after=014c", log)
        self.assertFalse(MISMATCH.findall(log), log)
        self.assertNotRegex(log, re.compile(r"^BNDLOAD_MISMATCH\b", re.M), log)
        self.assertNotIn("Syntax error", log)

    def assert_rejected(self, log, *, syntax_valid=True):
        _, records = self.assert_bound_records(log)
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
