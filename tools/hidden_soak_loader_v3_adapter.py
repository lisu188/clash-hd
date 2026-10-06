"""V3 joined original receipts and private native issuance boundary.

Imports perform no native calls, compilation, launches, or output writes.  The
actual native adapter is explicitly opt-in; fixture registries cannot issue its
capabilities.  Replay verifies supplied originals and never grants runtime,
storage, loaded-module, release, or promotion acceptance.
"""
from __future__ import annotations

import ast
import base64
import builtins
from dataclasses import fields, is_dataclass
from dataclasses import dataclass
import ctypes
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import struct
import subprocess
import sys
import time
import types
import uuid
import weakref
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).resolve()
GENERATOR = ROOT / "tools/hidden_soak_loader_v3.py"
OBSERVER_MAGIC = b"CLHDOV3\0"
OUTER_MAGIC = b"CLHDOUT3"
CALLER_MAGIC = b"CLHDCLV3"
IO_FOOTER = struct.Struct("<iIIIiI")
MAX_FRAMES = 32768
MAX_FRAME_METADATA = 512 * 1024
MAX_FRAME_RAW = 17121324
MAX_OUTER_METADATA = 32 * 1024**2
MAX_OUTER_RAW = 64 * 1024**2
MAX_OUTER_PACKET_RAW = 4096 * (568 + 8)
MAX_CALLER_METADATA = 64 * 1024**2
MAX_CALLER_RAW = 128 * 1024**2
CALLER_PENDING_BYTES = 64 * 1024**2
CALLER_CLOSE_ORIGINAL_BYTES = 16 * 1024**2
BUILD_PEAK_BYTES = 512 * 1024**2
BUILD_SOURCE_BYTES = 1024**2
BUILD_BINARY_BYTES = 8 * 1024**2
BUILD_OBJECT_BYTES = 64 * 1024**2
COMPILER_PE_BYTES = 32 * 1024**2
COMPILER_ENV_BYTES = 512 * 1024
COMPILER_STREAM_BYTES = 16 * 1024**2
COMPILER_ENV_KEYS = frozenset(("PATH","INCLUDE","LIB","LIBPATH","SYSTEMROOT","WINDIR","TEMP","TMP","COMSPEC",
    "PATHEXT","SYSTEMDRIVE","PROGRAMFILES","PROGRAMFILES(X86)","PROGRAMW6432","VSINSTALLDIR","VCINSTALLDIR",
    "VCTOOLSINSTALLDIR","WINDOWSSDKDIR","WINDOWSSDKVERSION","WINDOWSSDKBINPATH","WINDOWSSDKVERBINPATH",
    "UNIVERSALCRTSDKDIR","UCRTVERSION","FRAMEWORKDIR","FRAMEWORKDIR32","FRAMEWORKVERSION","FRAMEWORKVERSION32"))
MAX_OBSERVER_METADATA = 65 * 1024**2
MAX_OBSERVER_RAW = 516 * 1024**2
MAX_OBSERVER_PACKET_RAW = 4 * 1024**2
SYNTHETIC_FAILURES = {1:"challenge_write_original_failure",2:"challenge_signal_original_failure",
    3:"target_open_original_failure",4:"immutable_read_original_failure",5:"adoption_signal_original_failure",
    6:"adoption_generation_mismatch",7:"adoption_nonce_mismatch",8:"adoption_wait_original_timeout",
    9:"inheritance_original_failure",10:"cleanup_original_failure"}
FALSE_CLAIMS = {name: False for name in (
    "passed", "native_producer_provenance_verified", "native_read_coherence_verified",
    "native_generation_ownership_verified", "native_job_cleanup_verified", "host_cleanup_complete",
    "storage_durability_verified", "receipt_tail_durability_verified", "loaded_candidate_verified",
    "whole_image_verified", "loaded_probe_verified", "probe_executed", "running_duration_verified",
    "paired_clock_same_instant_verified","host_clock_coverage_verified",
    "map_ready", "runtime_acceptance", "release_acceptance", "manual_input_verified", "promotion_ready", "stable")}


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _sha(raw):
    _require(type(raw) is bytes, "complete original bytes required")
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _json(raw):
    _require(type(raw) is bytes, "original JSON bytes required")
    def unique(pairs):
        result = {}
        for name, value in pairs:
            _require(name not in result, "duplicate original JSON key")
            result[name] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite original JSON scalar: " + value)
    value = json.loads(raw.decode("ascii"), object_pairs_hook=unique, parse_constant=invalid)
    _require(_canonical(value) == raw, "canonical original JSON required")
    return value


def _integer(value, minimum=0, maximum=0xffffffff):
    _require(type(value) is int and minimum <= value <= maximum, "original scalar representation out of bounds")
    return value


def _exact(value, names, reason):
    _require(type(value) is dict and set(value) == set(names), reason + " exact original fields required")
    return value


class ArchiveError(ValueError):
    """The entire available originals survive parsing or replay rejection."""
    def __init__(self, message, original_archive, frames=(), *, originals=None):
        super().__init__(message)
        self.original_archive = original_archive
        self.frames = frames
        self.originals = originals


@dataclass(frozen=True)
class OriginalFrame:
    sequence: int
    operation: str
    metadata: bytes
    raw: bytes
    footer: bytes
    offset: int

    def data(self):
        return _json(self.metadata)["data"]

    def io(self):
        return dict(zip(("write_return", "write_error", "requested", "returned", "flush_return", "flush_error"),
                        IO_FOOTER.unpack(self.footer)))


def parse_frames(original, *, actor):
    """Framing only; packets have no native or authority provenance here."""
    frames = []
    try:
        _require(type(original) is bytes, "complete original archive bytes required")
        policy = {
            "observer": (OBSERVER_MAGIC, MAX_OBSERVER_METADATA, MAX_OBSERVER_RAW, MAX_OBSERVER_PACKET_RAW),
            "outer": (OUTER_MAGIC, MAX_OUTER_METADATA, MAX_OUTER_RAW, MAX_OUTER_PACKET_RAW),
            "caller": (CALLER_MAGIC, MAX_CALLER_METADATA, MAX_CALLER_RAW, MAX_FRAME_RAW),
        }
        _require(type(actor) is str and actor in policy, "fixed source actor required")
        magic, metadata_cap, raw_cap, packet_raw_cap = policy[actor]
        _require(original[:8] == magic, "original actor archive magic differs")
        offset, metadata_total, raw_total = 8, 8, 0
        _require(len(original) <= metadata_cap + raw_cap, "complete original archive exceeds source capacity")
        while offset < len(original):
            _require(len(frames) < MAX_FRAMES and len(original)-offset >= 8, "complete bounded frame prefix required")
            jsize, rsize = struct.unpack_from("<II", original, offset)
            _require(0 < jsize <= MAX_FRAME_METADATA and rsize <= packet_raw_cap,
                     "original frame exceeds source capacity")
            end = offset + 8 + jsize + rsize + IO_FOOTER.size
            _require(end <= len(original), "truncated original packet/footer")
            metadata = original[offset+8:offset+8+jsize]
            data = _exact(_json(metadata), ("sequence", "operation", "data"), "original packet")
            _require(type(data["sequence"]) is int and data["sequence"] == len(frames)+1,
                     "original sequence missing/duplicate/reordered")
            _require(type(data["operation"]) is str and data["operation"] and type(data["data"]) is dict,
                     "original operation/data types differ")
            metadata_total += 32 + jsize
            raw_total += rsize
            _require(metadata_total <= metadata_cap and raw_total <= raw_cap,
                     "original aggregate capacity exceeded")
            frames.append(OriginalFrame(data["sequence"], data["operation"], metadata,
                original[offset+8+jsize:end-24], original[end-24:end], offset))
            offset = end
        _require(frames, "empty original archive cannot complete")
        return tuple(frames)
    except Exception as error:
        if isinstance(error, ArchiveError):
            raise
        raise ArchiveError(type(error).__name__ + ": " + str(error), original, tuple(frames)) from error


def _io(frame):
    io = frame.io()
    _integer(io["write_return"], -(2**31), 2**31-1)
    _integer(io["flush_return"], -(2**31), 2**31-1)
    for name in ("write_error", "requested", "returned", "flush_error"):
        _integer(io[name])
    # A successful BOOL is nonzero.  Its LastError may be stale; retain it.
    _require(io["write_return"] != 0 and io["flush_return"] != 0 and
             io["requested"] == io["returned"] == 8 + len(frame.metadata) + len(frame.raw),
             "original main packet write/flush did not succeed completely")


def _terminal(frames, actor):
    """No missing, retried or partial packet can become a completion claim."""
    _require(frames[-1].operation == "finish" and
             sum(row.operation == "finish" for row in frames) == 1, "single final completion packet required")
    for row in frames:
        _io(row)
        _require(row.operation not in ("error", "native_failure", "retention_debt"),
                 "original failure is sticky")
    data = _exact(frames[-1].data(), ("status", "frame_count", "raw_bytes", "metadata_bytes", "comparison_scope"),
                  "original completion")
    _require(data == dict(status="complete", frame_count=len(frames)-1,
                         raw_bytes=sum(len(row.raw) for row in frames[:-1]),
                         metadata_bytes=8+sum(32+len(row.metadata) for row in frames[:-1]),
                         comparison_scope="initial_loader_held_adoption_v3"),
             "original completion counters/status/scope differ")


def _closed(raw, path, names, factory):
    """Validate before executing any potentially substituted project module."""
    tree = ast.parse(raw, filename=str(path))
    terminal = tree.body[-1]
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == factory]
    _require(len(calls) == 1 and isinstance(terminal, ast.Assign) and len(terminal.targets) == 1
             and isinstance(terminal.targets[0], ast.Tuple)
             and tuple(getattr(node, "id", None) for node in terminal.targets[0].elts) == names
             and isinstance(terminal.value, ast.Call) and isinstance(terminal.value.func, ast.Name)
             and terminal.value.func.id == factory and not terminal.value.args and not terminal.value.keywords,
             "sole exact terminal factory required before private execution")
    tree.body.pop()
    name = "_clash_v3_adapter_" + uuid.uuid4().hex
    module = types.ModuleType(name); module.__file__ = str(path)
    _require(name not in sys.modules, "private namespace collision")
    sys.modules[name] = module
    try:
        exec(compile(tree, str(path), "exec"), module.__dict__)
        _require(sys.modules.get(name) is module,"private namespace identity replaced during execution")
        return module
    finally:
        if sys.modules.get(name) is module:
            del sys.modules[name]


def caller_retention_budget():
    """Known caller original packets and one whole replay copy, never assets."""
    archive = MAX_CALLER_METADATA + MAX_CALLER_RAW
    return dict(metadata_bytes=MAX_CALLER_METADATA, raw_bytes=MAX_CALLER_RAW,
                frames=MAX_FRAMES, maximum_original_frame_bytes=MAX_FRAME_RAW,
                complete_archive_bytes=archive, complete_copy_bytes=archive,
                pending_original_bytes=CALLER_PENDING_BYTES,
                close_original_bytes=CALLER_CLOSE_ORIGINAL_BYTES,close_complete_copy_bytes=CALLER_CLOSE_ORIGINAL_BYTES,
                known_peak_bytes=2*archive+CALLER_PENDING_BYTES+2*CALLER_CLOSE_ORIGINAL_BYTES,
                exclusions=["compiler/source/object/binary files", "runtime assets",
                            "unavailable original subprocess remainder and oversized output debt"],
                storage_durability_verified=False, native_producer_provenance_verified=False)


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class NativeCapability:
    binding_json: str


@dataclass(frozen=True)
class NativePaths:
    root: str
    candidate: str
    compiler_x64: str
    compiler_x86: str
    approved_peak_bytes: int
    runtime_asset_bytes: int
    environment_x64: str
    environment_x86: str


@dataclass(frozen=True)
class JoinedOriginals:
    caller: bytes
    outer: bytes
    observer: bytes
    observer_stderr: bytes
    outer_stderr: bytes = b""
    caller_close_receipt: bytes = b""


@dataclass(frozen=True)
class ReplayResult:
    report_json: str
    originals: JoinedOriginals
    frames: tuple

    def report(self):
        return _json(self.report_json.encode("ascii"))


class NativeFailure(RuntimeError):
    """Complete available originals plus explicit unavailable/debt state."""
    def __init__(self, message, *, events=(), pending=(), cause=None):
        super().__init__(message)
        self.events, self.pending, self.cause = tuple(events), tuple(pending), cause


def _plain_path(value, *, directory=False):
    _require(type(value) in (str, Path) or isinstance(value, Path), "literal path required")
    path = Path(value).absolute()
    _require(str(path).isascii() and path.resolve() == path, "literal ASCII absolute path required")
    for ancestor in (path, *path.parents):
        if not ancestor.exists():
            continue
        _require(not ancestor.is_symlink() and not getattr(ancestor, "is_junction", lambda: False)()
                 and not getattr(ancestor.stat(), "st_file_attributes", 0) & 0x400,
                 "symlink/junction/reparse path rejected")
    if directory:
        _require(path.is_dir(), "preexisting dedicated native artifact directory required")
    return path


def _authenticode_command(powershell, compiler):
    """Encode one complete command; never append a path as command text.

    The owning caller verifies these actual file paths first. Single-quoted
    PowerShell literals preserve spaces and metacharacters; doubled quotes
    preserve apostrophes without permitting interpolation or a new command.
    """
    for value,name in ((powershell,"powershell.exe"),(compiler,"cl.exe")):
        _require(type(value) is str and value.isascii() and not any(ord(char)<32 for char in value),
            "one literal ASCII native tool path required")
        path=PureWindowsPath(value)
        _require(path.is_absolute() and len(path.drive)==2 and path.drive[0].isalpha() and path.drive[1]==":" and
            path.name.lower()==name,"verified absolute local compiler/system tool path required")
    literal="'"+compiler.replace("'","''")+"'"
    script="$s=Get-AuthenticodeSignature -LiteralPath "+literal+"; [Console]::Write($s.Status.ToString()+'|'+$s.SignerCertificate.Subject)"
    encoded=base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return [powershell,"-NoProfile","-NonInteractive","-EncodedCommand",encoded]


def _require_authenticode_original(result):
    """Preserve strict original status/publisher checks and all raw output."""
    _require(type(result.returncode) is int and type(result.stdout) is type(result.stderr) is bytes,
        "whole original signature exit and byte streams required")
    _require(result.returncode==0 and result.stdout.startswith(b"Valid|") and b"Microsoft Corporation" in result.stdout,
        "original compiler Authenticode publisher/trust observation failed")


def _authenticode_environment(environment):
    """Let Windows PowerShell construct its own module paths for this child.

    A Python child of PowerShell 7 otherwise forwards incompatible PS7 module
    paths. Copy the parent environment without changing it or recording it.
    """
    return {key:value for key,value in environment.items() if key.upper()!="PSMODULEPATH"}


def _pe_machine(raw):
    _require(type(raw) is bytes and len(raw) >= 64 and raw[:2] == b"MZ", "complete compiled PE required")
    at = struct.unpack_from("<I", raw, 60)[0]
    _require(at <= len(raw)-26 and raw[at:at+4] == b"PE\0\0", "whole compiled PE header required")
    return struct.unpack_from("<H", raw, at+4)[0], struct.unpack_from("<H", raw, at+24)[0]


def _stamp(path):
    s = path.stat()
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns


class _NativeSession:
    """Lazy WIN64 adapter.  Constructed only by the private production registry.

    CreateProcess output handles are stored into preallocated ownership slots
    before diagnostics or identity checks.  Cleanup does not depend on logging,
    parser success or availability of a completion packet.
    """
    def __init__(self, paths, minimum_peak, *, fixture=False):
        _require(os.name == "nt" and ctypes.sizeof(ctypes.c_void_p) == 8 and
                 os.environ.get("GITHUB_ACTIONS") == "true" and
                 os.environ.get("CLASH_LOADER_V3_ENGINE_TEST") == "1" and
                 os.environ.get("CLASH_LOADER_V3_ENGINE_INTEGRATION") == "1",
                 "explicit WIN64 synthetic CI native opt-in required")
        self.paths = paths
        self.root = _plain_path(paths.root, directory=True)
        _require(self.root != ROOT and not self.root.is_relative_to(ROOT), "native artifacts must be outside repository")
        _integer(paths.runtime_asset_bytes, 0, 2**63-1)
        _integer(paths.approved_peak_bytes, minimum_peak + BUILD_PEAK_BYTES + paths.runtime_asset_bytes, 2**63-1)
        self.minimum_peak = minimum_peak
        self.fixture = fixture
        self.events, self.pending, self.owned = [], [], [0]*32
        self.footer_reserves = []
        self.debt, self.failed, self.closed, self.begun = False, False, False, False
        # A created job does not own the outer until native assignment succeeds.
        # Keep this primitive before all diagnostics that can allocate or fail.
        self.outer_assigned = False
        self.files = dict(outer_source=self.root/"outer.cpp", outer=self.root/"outer.exe",
            observer_source=self.root/"observer.cpp", observer=self.root/"observer.exe",
            request=self.root/"request.bin", payload=self.root/"expected.bin", bootstrap=self.root/"bootstrap.bin",
            outer_archive=self.root/"outer-original.bin", caller_archive=self.root/"caller-original.bin",
            observer_archive=self.root/"observer-original.bin", observer_stderr=self.root/"observer-stderr.bin",
            outer_stderr=self.root/"outer-stderr.bin", challenge=self.root/"challenge.bin", adoption=self.root/"adoption.bin")
        _require(all(not path.exists() for path in self.files.values()), "CREATE_NEW artifacts must not already exist")
        C = ctypes
        class Startup(C.Structure):
            _fields_ = [("cb",C.c_uint32),("reserved",C.c_void_p),("desktop",C.c_wchar_p),("title",C.c_void_p),
                ("x",C.c_uint32),("y",C.c_uint32),("xs",C.c_uint32),("ys",C.c_uint32),
                ("xc",C.c_uint32),("yc",C.c_uint32),("fill",C.c_uint32),("flags",C.c_uint32),
                ("show",C.c_uint16),("r2",C.c_uint16),("p2",C.c_void_p),
                ("stdin",C.c_void_p),("stdout",C.c_void_p),("stderr",C.c_void_p)]
        class StartupEx(C.Structure):
            _fields_ = [("startup",Startup),("attributes",C.c_void_p)]
        class ProcessInfo(C.Structure):
            _fields_ = [("process",C.c_void_p),("thread",C.c_void_p),("pid",C.c_uint32),("tid",C.c_uint32)]
        class Security(C.Structure):
            _fields_ = [("size",C.c_uint32),("descriptor",C.c_void_p),("inherit",C.c_int32)]
        _require((C.sizeof(Startup), C.sizeof(StartupEx), C.sizeof(ProcessInfo), C.sizeof(Security)) == (104,112,24,24),
                 "fixed WIN64 caller ABI required")
        self.Startup, self.StartupEx, self.ProcessInfo, self.Security = Startup, StartupEx, ProcessInfo, Security
        self.kernel = C.WinDLL("kernel32", use_last_error=True)
        prototypes = (
            ("CreateFileW",[C.c_wchar_p,C.c_uint32,C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_void_p],C.c_void_p),
            ("WriteFile",[C.c_void_p,C.c_void_p,C.c_uint32,C.POINTER(C.c_uint32),C.c_void_p],C.c_int32),
            ("FlushFileBuffers",[C.c_void_p],C.c_int32),
            ("GetFileInformationByHandle",[C.c_void_p,C.c_void_p],C.c_int32),
            ("GetFinalPathNameByHandleW",[C.c_void_p,C.c_wchar_p,C.c_uint32,C.c_uint32],C.c_uint32),
            ("OpenProcess",[C.c_uint32,C.c_int32,C.c_uint32],C.c_void_p),
            ("GetProcessId",[C.c_void_p],C.c_uint32),
            ("GetProcessTimes",[C.c_void_p]+[C.POINTER(C.c_uint64)]*4,C.c_int32),
            ("QueryFullProcessImageNameW",[C.c_void_p,C.c_uint32,C.c_wchar_p,C.POINTER(C.c_uint32)],C.c_int32),
            ("WaitForSingleObject",[C.c_void_p,C.c_uint32],C.c_uint32),
            ("GetExitCodeProcess",[C.c_void_p,C.POINTER(C.c_uint32)],C.c_int32),
            ("GetSystemDirectoryW",[C.c_wchar_p,C.c_uint32],C.c_uint32),
            ("QueryPerformanceFrequency",[C.POINTER(C.c_int64)],C.c_int32),
            ("QueryPerformanceCounter",[C.POINTER(C.c_int64)],C.c_int32),
            ("GetDiskFreeSpaceExW",[C.c_wchar_p]+[C.POINTER(C.c_uint64)]*3,C.c_int32),
            ("InitializeProcThreadAttributeList",[C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(C.c_size_t)],C.c_int32),
            ("UpdateProcThreadAttribute",[C.c_void_p,C.c_uint32,C.c_size_t,C.c_void_p,C.c_size_t,C.c_void_p,C.c_void_p],C.c_int32),
            ("DeleteProcThreadAttributeList",[C.c_void_p],None),
            ("CreateProcessW",[C.c_wchar_p,C.c_wchar_p,C.c_void_p,C.c_void_p,C.c_int32,C.c_uint32,
                              C.c_void_p,C.c_wchar_p,C.POINTER(Startup),C.POINTER(ProcessInfo)],C.c_int32),
            ("CreateJobObjectW",[C.c_void_p,C.c_wchar_p],C.c_void_p),
            ("SetInformationJobObject",[C.c_void_p,C.c_int32,C.c_void_p,C.c_uint32],C.c_int32),
            ("AssignProcessToJobObject",[C.c_void_p,C.c_void_p],C.c_int32),
            ("QueryInformationJobObject",[C.c_void_p,C.c_int32,C.c_void_p,C.c_uint32,C.POINTER(C.c_uint32)],C.c_int32),
            ("IsProcessInJob",[C.c_void_p,C.c_void_p,C.POINTER(C.c_int32)],C.c_int32),
            ("ResumeThread",[C.c_void_p],C.c_uint32),
            ("TerminateJobObject",[C.c_void_p,C.c_uint32],C.c_int32),
            ("TerminateProcess",[C.c_void_p,C.c_uint32],C.c_int32),
            ("CloseHandle",[C.c_void_p],C.c_int32))
        for name,args,result in prototypes:
            fn = getattr(self.kernel,name); fn.argtypes,fn.restype = args,result
        self._reserve()
        self._open(0,self.files["caller_archive"],0x40000000,1,inherit=False)
        self._magic()
        self._open(1,self.root,0x80,3,flags=0x02200000)
        self.root_identity = self._identity(1, self.root)
        pid = os.getpid()
        C.set_last_error(0); handle=self.kernel.OpenProcess(0x1000|0x100000,0,pid); error=C.get_last_error()
        self.owned[2] = handle or 0
        self._record("api",dict(name="OpenProcess",role="caller",result=handle or 0,error=error,pid=pid))
        _require(handle, "retained caller process handle unavailable")
        self.caller = self._generation(2,"caller")
        _require(self.caller["pid"] == pid, "retained actual caller PID differs")

    def _reserve(self, *, retain=True):
        C=ctypes; free,total,unused=C.c_uint64(),C.c_uint64(),C.c_uint64()
        C.set_last_error(0); result=self.kernel.GetDiskFreeSpaceExW(str(self.root),C.byref(free),C.byref(total),C.byref(unused)); error=C.get_last_error()
        original=dict(result=result,error=error,free=free.value,total=total.value,unused=unused.value,
                      required_peak=self.paths.approved_peak_bytes)
        if retain: self.pending.append(("reserve",original,b""))
        valid=result and total.value and free.value>self.paths.approved_peak_bytes and \
            free.value-self.paths.approved_peak_bytes>total.value//10
        if not valid:
            if not retain: self.pending.append(("reserve",original,b""))
            self.failed=self.debt=True
        _require(valid and
                 free.value-self.paths.approved_peak_bytes>total.value//10,
                 "strict >10% reserve plus full known/external allowance required")
        return original

    def _magic(self):
        self._reserve()
        C=ctypes; raw=CALLER_MAGIC; got=C.c_uint32(); C.set_last_error(0)
        wr=self.kernel.WriteFile(self.owned[0],raw,len(raw),C.byref(got),None); we=C.get_last_error()
        C.set_last_error(0); fl=self.kernel.FlushFileBuffers(self.owned[0]); fe=C.get_last_error()
        original=dict(write_return=wr,write_error=we,requested=8,returned=got.value,flush_return=fl,flush_error=fe)
        self.pending.append(("archive_magic_io",original,raw))
        _require(wr and got.value==8 and fl,"caller magic original I/O failed")
        self.begun=True
        pending,self.pending=self.pending,[]
        for op,data,capacity in pending:
            self._record(op,data,capacity)

    def _record(self, operation, data, raw=b""):
        _require(type(raw) is bytes,"whole original native capacity required")
        if not self.begun:
            self.pending.append((operation,data,raw))
            return
        start=len(self.pending)
        self.pending.append((operation,data,raw))
        _require(sum(len(item[2]) for item in self.pending if type(item[2]) is bytes)<=CALLER_PENDING_BYTES,
                 "complete pending originals exceed fixed allowance; originals remain retained debt")
        reserve=self._reserve(retain=False)
        meta=_canonical(dict(sequence=len(self.events)+1,operation=operation,
                             data=dict(observation=data,prewrite_reserve=reserve)))
        _require(len(meta)<=MAX_FRAME_METADATA and len(raw)<=MAX_FRAME_RAW,
                 "complete original over caller packet capacity; retained pending debt")
        block=struct.pack("<II",len(meta),len(raw))+meta+raw
        _require(8+sum(32+len(row.metadata) for row in self.events)+len(meta)+32<=MAX_CALLER_METADATA and
                 sum(len(row.raw) for row in self.events)+len(raw)<=MAX_CALLER_RAW,
                 "whole caller retention capacity exceeded")
        C=ctypes; got=C.c_uint32(); C.set_last_error(0)
        wr=self.kernel.WriteFile(self.owned[0],block,len(block),C.byref(got),None); we=C.get_last_error()
        C.set_last_error(0); fl=self.kernel.FlushFileBuffers(self.owned[0]); fe=C.get_last_error()
        footer=IO_FOOTER.pack(wr,we,len(block),got.value,fl,fe)
        self.pending.append(("main_io",dict(write_return=wr,write_error=we,returned=got.value,flush_return=fl,flush_error=fe),block))
        # The main packet cannot contain a query taken afterwards. Keep the
        # original footer query separately in RAM and in the close receipt.
        # Neither this receipt nor the footer attests independent durability.
        self.pending.append(("receipt_tail_capacity",dict(sequence=len(self.events)+1),footer))
        footer_reserve=self._reserve(retain=False)
        self.footer_reserves.append(dict(sequence=len(self.events)+1,reserve=footer_reserve))
        tail_got=C.c_uint32(); C.set_last_error(0)
        tw=self.kernel.WriteFile(self.owned[0],footer,24,C.byref(tail_got),None); te=C.get_last_error()
        C.set_last_error(0); tf=self.kernel.FlushFileBuffers(self.owned[0]); tfe=C.get_last_error()
        self.pending.append(("receipt_tail",dict(write_return=tw,write_error=te,returned=tail_got.value,flush_return=tf,flush_error=tfe),footer))
        row=OriginalFrame(len(self.events)+1,operation,meta,raw,footer,8+sum(32+len(r.metadata)+len(r.raw) for r in self.events))
        self.events.append(row)
        _require(wr and got.value==len(block) and fl and tw and tail_got.value==24 and tf,
                 "original caller packet/footer write failure; all pending bytes retained")
        del self.pending[start:]

    def _open(self, slot, path, access, disposition, *, inherit=False, flags=0x00200000):
        C=ctypes; security=self.Security(C.sizeof(self.Security),None,int(inherit))
        C.set_last_error(0); handle=self.kernel.CreateFileW(str(path),access,0 if disposition==1 else 1|2,
            C.byref(security) if inherit else None,disposition,flags,None); error=C.get_last_error()
        if handle and handle != 0xffffffffffffffff:
            self.owned[slot]=handle
        data=dict(name="CreateFileW",slot=slot,path=str(path),access=access,disposition=disposition,
                  inherit=int(inherit),flags=flags,result=handle or 0,error=error)
        if self.begun: self._record("api",data)
        else: self.pending.append(("api",data,b""))
        _require(self.owned[slot],"native CREATE_NEW/open handle unavailable")
        return handle

    def _identity(self, slot, expected):
        C=ctypes; info=C.create_string_buffer(52)
        C.set_last_error(0); result=self.kernel.GetFileInformationByHandle(self.owned[slot],info); error=C.get_last_error()
        self._record("api",dict(name="GetFileInformationByHandle",slot=slot,result=result,error=error),bytes(info))
        _require(result and not struct.unpack_from("<I",info.raw)[0]&0x400,"native file identity/reparse rejected")
        path=C.create_unicode_buffer(32768); C.set_last_error(0)
        chars=self.kernel.GetFinalPathNameByHandleW(self.owned[slot],path,32768,0); error=C.get_last_error()
        self._record("api",dict(name="GetFinalPathNameByHandleW",slot=slot,result=chars,error=error),bytes(path))
        _require(0<chars<32768,"complete original native final path unavailable")
        final=path[:chars]
        if final.startswith("\\\\?\\"): final=final[4:]
        _require(final.lower()==str(expected).lower(),"native file path differs from issued literal path")
        return struct.unpack_from("<I",info.raw,28)[0], (struct.unpack_from("<I",info.raw,44)[0]<<32)|struct.unpack_from("<I",info.raw,48)[0]

    def _generation(self, slot, role, *, live=True):
        C=ctypes; h=self.owned[slot]; C.set_last_error(0); pid=self.kernel.GetProcessId(h); pe=C.get_last_error()
        self._record("api",dict(name="GetProcessId",slot=slot,role=role,result=pid,error=pe))
        path=C.create_unicode_buffer(32768); chars=C.c_uint32(32768); C.set_last_error(0)
        pr=self.kernel.QueryFullProcessImageNameW(h,0,path,C.byref(chars)); pre=C.get_last_error()
        self._record("api",dict(name="QueryFullProcessImageNameW",slot=slot,role=role,result=pr,error=pre,returned=chars.value),bytes(path))
        times=[C.c_uint64() for _ in range(4)]; C.set_last_error(0)
        tr=self.kernel.GetProcessTimes(h,*(C.byref(v) for v in times)); te=C.get_last_error()
        self._record("api",dict(name="GetProcessTimes",slot=slot,role=role,result=tr,error=te),struct.pack("<4Q",*(v.value for v in times)))
        C.set_last_error(0); wait=self.kernel.WaitForSingleObject(h,0); we=C.get_last_error()
        self._record("api",dict(name="WaitForSingleObject",slot=slot,role=role,result=wait,error=we,timeout=0))
        exit=C.c_uint32(); C.set_last_error(0); er=self.kernel.GetExitCodeProcess(h,C.byref(exit)); ee=C.get_last_error()
        self._record("api",dict(name="GetExitCodeProcess",slot=slot,role=role,result=er,error=ee),struct.pack("<I",exit.value))
        _require(pid and pr and 0<chars.value<32768 and tr and er and times[0].value,"original generation unavailable")
        image=_plain_path(path[:chars.value]); raw=image.read_bytes()
        data=dict(pid=pid,creation=times[0].value,path=str(image),sha256=_sha(raw),wait=wait,exit_code=exit.value,exit_time=times[1].value)
        self._record("generation",dict(role=role,slot=slot,**data))
        _require((wait==258 and exit.value==259 and times[1].value==0) if live else
                 (wait==0 and exit.value!=259 and times[1].value>=times[0].value),"original retained process liveness/exit differs")
        return data

    def clock(self):
        C=ctypes; f=C.c_int64(); t=C.c_int64(); C.set_last_error(0)
        fr=self.kernel.QueryPerformanceFrequency(C.byref(f)); fe=C.get_last_error()
        self._record("api",dict(name="QueryPerformanceFrequency",result=fr,error=fe),struct.pack("<q",f.value))
        before=time.monotonic_ns();C.set_last_error(0); tr=self.kernel.QueryPerformanceCounter(C.byref(t)); te=C.get_last_error()
        after=time.monotonic_ns()
        self._record("api",dict(name="QueryPerformanceCounter",result=tr,error=te),struct.pack("<q",t.value))
        self._record("clock_pair",dict(method="time.monotonic_ns",before_ns=before,after_ns=after,
            frequency_hz=f.value,tick=t.value,counter_return=tr,counter_error=te),struct.pack("<2Q",before,after))
        _require(fr and tr and 0<f.value<=10**9 and 0<t.value<2**63,"native prelaunch clock unavailable")
        _require(type(before) is type(after) is int and 0<before<=after<2**63-20*10**9,"original monotonic/QPC bracket unavailable")
        return f.value,t.value,before

    def write_new(self, name, raw):
        _require(type(raw) is bytes and len(raw)<=MAX_FRAME_RAW,"source output capacity exceeds caller full-packet policy")
        self._reserve(); self._open(10,self.files[name],0x40000000|0x80,1)
        try:
            C=ctypes; got=C.c_uint32(); C.set_last_error(0)
            wr=self.kernel.WriteFile(self.owned[10],raw,len(raw),C.byref(got),None); we=C.get_last_error()
            self._record("api",dict(name="WriteFile",role=name,result=wr,error=we,requested=len(raw),returned=got.value),raw)
            C.set_last_error(0); fl=self.kernel.FlushFileBuffers(self.owned[10]); fe=C.get_last_error()
            self._record("api",dict(name="FlushFileBuffers",role=name,result=fl,error=fe))
            _require(wr and got.value==len(raw) and fl,"original full output write/flush failed")
            identity=self._identity(10,self.files[name])
        finally:
            self.close_slot(10)
        _require(self.files[name].read_bytes()==raw,"original output readback differs")
        return identity

    def _run(self, argv, *, timeout=90, environment=None):
        self._reserve()
        try:
            result=subprocess.run(argv,cwd=self.root,capture_output=True,timeout=timeout,
                                  creationflags=0x08000000,check=False,env=environment)
        except subprocess.TimeoutExpired as error:
            data=dict(command=argv,type_name=type(error).__name__,timeout=error.timeout,
                      unavailable_or_unread_remainder=True)
            originals=tuple(("subprocess_timeout",dict(data,stream=name,original_available=raw is not None),raw)
                for name,raw in (("stdout",error.stdout),("stderr",error.stderr)))
            self.pending.extend(originals)
            try:
                for operation,observation,raw in originals:
                    self._record(operation,observation,b"" if raw is None else raw)
            except BaseException:
                self.failed=self.debt=True
                raise error
            raise
        start=len(self.pending)
        originals=tuple(("subprocess",dict(command=argv,returncode=result.returncode,stream=name),raw)
            for name,raw in (("stdout",result.stdout),("stderr",result.stderr)))
        self.pending.extend(originals)
        for operation,data,raw in originals:
            _require(type(raw) is bytes,"binary original subprocess output required")
            _require(len(raw)<=COMPILER_STREAM_BYTES,"whole oversized compiler/tool original retained as pending debt")
            self._record(operation,data,raw)
        del self.pending[start:]
        return result

    def compile(self, source_name, binary_name, compiler, raw, *, machine):
        compiler=_plain_path(compiler); original=compiler.read_bytes(); stamp=_stamp(compiler)
        _require(len(original)<=COMPILER_PE_BYTES and len(raw)<=BUILD_SOURCE_BYTES and
            compiler.name.lower()=="cl.exe" and _pe_machine(original)[0] in (0x14c,0x8664),"bounded explicit MSVC PE compiler/source required")
        C=ctypes; directory=C.create_unicode_buffer(32768); C.set_last_error(0)
        chars=self.kernel.GetSystemDirectoryW(directory,32768); error=C.get_last_error()
        self._record("api",dict(name="GetSystemDirectoryW",result=chars,error=error),bytes(directory))
        _require(0<chars<32768,"original system tool path unavailable")
        powershell=_plain_path(Path(directory[:chars])/"WindowsPowerShell/v1.0/powershell.exe")
        verified=self._run(_authenticode_command(str(powershell),str(compiler)),
            environment=_authenticode_environment(os.environ))
        _require_authenticode_original(verified)
        self.write_new(source_name,raw)
        env_path=_plain_path(self.paths.environment_x64 if machine==0x8664 else self.paths.environment_x86)
        environment_raw=env_path.read_bytes(); environment_stamp=_stamp(env_path)
        _require(len(environment_raw)<=COMPILER_ENV_BYTES,"whole compiler environment exceeds known allowance")
        environment=_json(environment_raw)
        _compiler_environment(environment,machine)
        self._record("compiler_environment",dict(path=str(env_path),sha256=_sha(environment_raw),machine=machine),environment_raw)
        command=[str(compiler),"/nologo","/EHsc","/std:c++17","/W4","/O2","/MT",str(self.files[source_name]),
                 "/Fe:"+str(self.files[binary_name]),"/Fo:"+str(self.root/(binary_name+".obj")),
                 "/link","/MACHINE:"+("X64" if machine==0x8664 else "X86"),"bcrypt.lib"]
        compiled=self._run(command,environment=environment)
        _require(compiled.returncode==0,"original compiler failure retained")
        _require(compiler.read_bytes()==original and _stamp(compiler)==stamp and self.files[source_name].read_bytes()==raw
                 and env_path.read_bytes()==environment_raw and _stamp(env_path)==environment_stamp,
                 "compiler/source changed across actual compilation")
        binary=self.files[binary_name].read_bytes()
        object_file=self.root/(binary_name+".obj")
        _require(len(binary)<=BUILD_BINARY_BYTES and object_file.stat().st_size<=BUILD_OBJECT_BYTES and
            _pe_machine(binary)==(machine,0x20b if machine==0x8664 else 0x10b),"actual compiled ABI/output allowance differs; originals retained")
        self._record("compiled",dict(role=binary_name,source_sha256=_sha(raw),binary_sha256=_sha(binary),
                      compiler_sha256=_sha(original),machine=machine,command=command))
        return binary

    def create_suspended(self):
        C=ctypes; self._reserve(); self._open(3,"NUL",0x80000000,3,inherit=True,flags=0)
        self._open(4,self.files["outer_archive"],0x40000000|0x80,1,inherit=True)
        self._open(5,self.files["outer_stderr"],0x40000000|0x80,1,inherit=True)
        size=C.c_size_t(); C.set_last_error(0)
        r=self.kernel.InitializeProcThreadAttributeList(None,1,0,C.byref(size)); e=C.get_last_error()
        self._record("api",dict(name="InitializeProcThreadAttributeList.size",result=r,error=e),struct.pack("<Q",size.value))
        _require(r==0 and e==122 and 0<size.value<=65536,"original handle-list capacity query differs")
        memory=C.create_string_buffer(size.value); initialized=False
        try:
            C.set_last_error(0); r=self.kernel.InitializeProcThreadAttributeList(memory,1,0,C.byref(size)); e=C.get_last_error(); initialized=bool(r)
            self._record("api",dict(name="InitializeProcThreadAttributeList",result=r,error=e),bytes(memory))
            _require(r,"native caller attribute list unavailable")
            handles=(C.c_void_p*3)(*(self.owned[i] for i in (3,4,5)))
            C.set_last_error(0); r=self.kernel.UpdateProcThreadAttribute(memory,0,0x20002,handles,C.sizeof(handles),None,None); e=C.get_last_error()
            self._record("api",dict(name="UpdateProcThreadAttribute",result=r,error=e),bytes(handles))
            _require(r,"source three-handle inheritance denied")
            startup=self.StartupEx(); startup.startup.cb=C.sizeof(startup); startup.startup.flags=0x100
            startup.startup.stdin,startup.startup.stdout,startup.startup.stderr=(self.owned[i] for i in (3,4,5))
            startup.attributes=C.cast(memory,C.c_void_p)
            original_command=subprocess.list2cmdline([str(self.files["outer"]),str(self.files["bootstrap"])])
            command=C.create_unicode_buffer(original_command); pi=self.ProcessInfo(); C.set_last_error(0)
            result=self.kernel.CreateProcessW(str(self.files["outer"]),command,None,None,1,0x08080404,None,
                str(self.root),C.byref(startup.startup),C.byref(pi)); error=C.get_last_error()
            # Store both original output handles before serialization/allocation.
            self.owned[6]=pi.process or 0; self.owned[7]=pi.thread or 0
            self._record("api",dict(name="CreateProcessW",role="outer",result=result,error=error,
                command=original_command,flags=0x08080404,inherit_handles=1),bytes(pi))
            _require(result and pi.process and pi.thread and pi.pid and pi.tid,"actual suspended outer creation failed")
            self.outer=self._generation(6,"outer")
            _require(self.outer["pid"]==pi.pid and self.outer["path"].lower()==str(self.files["outer"]).lower(),
                     "actual retained outer generation differs")
            C.set_last_error(0); job=self.kernel.CreateJobObjectW(None,None); error=C.get_last_error(); self.owned[8]=job or 0
            self._record("api",dict(name="CreateJobObjectW",result=job or 0,error=error)); _require(job,"caller outer-job creation failed")
            limits=C.create_string_buffer(144); struct.pack_into("<I",limits,16,0x2000); C.set_last_error(0)
            r=self.kernel.SetInformationJobObject(job,9,limits,144); error=C.get_last_error()
            self._record("api",dict(name="SetInformationJobObject",result=r,error=error,class_id=9),bytes(limits)); _require(r,"caller kill/no-breakaway job limits failed")
            C.set_last_error(0); r=self.kernel.AssignProcessToJobObject(job,pi.process); error=C.get_last_error()
            if r: self.outer_assigned=True
            self._record("api",dict(name="AssignProcessToJobObject",result=r,error=error,job=job,process=pi.process)); _require(r,"outer suspended assignment failed")
            self.job_readbacks(pi.pid)
            return self.outer
        finally:
            if initialized:
                self.kernel.DeleteProcThreadAttributeList(memory)
                self._record("api",dict(name="DeleteProcThreadAttributeList",result=None,error=0))
            for slot in (3,4,5): self.close_slot(slot)

    def job_readbacks(self, pid):
        """Original WIN64 buffers, recorded before every admission predicate."""
        C=ctypes
        for class_id,size in ((9,144),(1,48),(3,520)):
            raw=C.create_string_buffer(size); count=C.c_uint32();C.set_last_error(0)
            result=self.kernel.QueryInformationJobObject(self.owned[8],class_id,raw,size,C.byref(count));error=C.get_last_error()
            self._record("api",dict(name="QueryInformationJobObject",class_id=class_id,job=self.owned[8],
                result=result,error=error,requested=size,returned=count.value),bytes(raw))
            _caller_job_query(class_id,result,count.value,bytes(raw),pid)
        member=C.c_int32();C.set_last_error(0)
        result=self.kernel.IsProcessInJob(self.owned[6],self.owned[8],C.byref(member));error=C.get_last_error()
        self._record("api",dict(name="IsProcessInJob",job=self.owned[8],process=self.owned[6],
            result=result,error=error),struct.pack("<i",member.value))
        _require(result and member.value==1,"original assigned suspended outer membership unavailable")

    def finish_and_close(self):
        """Try a final failed record and close the journal on every terminal path."""
        if not self.owned[0]:
            self.cleanup();return
        self.cleanup()
        try:
            self._record("finish",dict(status="failed" if self.failed or self.debt else "complete",
                frame_count=len(self.events),raw_bytes=sum(len(v.raw) for v in self.events),
                metadata_bytes=8+sum(32+len(v.metadata) for v in self.events),
                comparison_scope="initial_loader_held_adoption_v3"))
        except BaseException:
            self.failed=self.debt=True
        finally:
            self.close_slot(0)

    def close_slot(self, slot):
        handle=self.owned[slot]
        if not handle: return
        C=ctypes; C.set_last_error(0); result=self.kernel.CloseHandle(handle); error=C.get_last_error()
        self.owned[slot]=0
        if slot==0:
            self.caller_close_receipt=_canonical(dict(name="CloseHandle",role="caller_archive",handle=handle,
                result=result,error=error,serialization_scope="retained_RAM_only_after_final_archive_packet",
                receipt_tail_prewrite_reserves=self.footer_reserves))
            if len(self.caller_close_receipt)>CALLER_CLOSE_ORIGINAL_BYTES:
                self.failed=self.debt=True
                self.pending.append(("caller_close_original",dict(over_capacity=True,original_bytes=len(self.caller_close_receipt)),
                                     self.caller_close_receipt))
            if not result: self.failed=True
            return
        try:
            self._record("api",dict(name="CloseHandle",slot=slot,handle=handle,result=result,error=error))
        except BaseException:
            self.debt=self.failed=True
        if not result: self.failed=True

    def cleanup(self):
        if self.closed: return
        self.closed=True; C=ctypes
        # Each cleanup call is independent from earlier diagnostic failure.
        job_terminated=False
        if self.owned[8]:
            C.set_last_error(0); r=self.kernel.TerminateJobObject(self.owned[8],0); e=C.get_last_error()
            job_terminated=bool(r)
            try: self._record("api",dict(name="TerminateJobObject",result=r,error=e))
            except BaseException: self.debt=self.failed=True
            if not r: self.failed=True
        if self.owned[6] and (not self.outer_assigned or not job_terminated):
            C.set_last_error(0); r=self.kernel.TerminateProcess(self.owned[6],1); e=C.get_last_error()
            try: self._record("api",dict(name="TerminateProcess",result=r,error=e))
            except BaseException: self.debt=self.failed=True
            if not r: self.failed=True
        if self.owned[6]:
            C.set_last_error(0); r=self.kernel.WaitForSingleObject(self.owned[6],5000); e=C.get_last_error()
            try: self._record("api",dict(name="WaitForSingleObject",role="outer",result=r,error=e,timeout=5000))
            except BaseException: self.debt=self.failed=True
            if r!=0: self.failed=True
        for slot in (7,6,8,10,5,4,3,2,1): self.close_slot(slot)

    def resume(self):
        self.job_readbacks(self.outer["pid"])
        C=ctypes; C.set_last_error(0); r=self.kernel.ResumeThread(self.owned[7]); e=C.get_last_error()
        self._record("api",dict(name="ResumeThread",role="outer",result=r,error=e))
        _require(r==1,"exactly once suspended outer resume required")
        C.set_last_error(0); wr=self.kernel.WaitForSingleObject(self.owned[6],35000); we=C.get_last_error()
        self._record("api",dict(name="WaitForSingleObject",role="outer",result=wr,error=we,timeout=35000))
        _require(wr==0,"outer did not finish within fixed caller deadline")
        exit=self._generation(6,"outer",live=False)
        _require(exit["pid"]==self.outer["pid"] and exit["creation"]==self.outer["creation"] and exit["exit_code"]==0,
                 "same retained outer ended with native failure")
        return exit


class _PrivateGraph:
    """Fixture-only project imports always read a fresh canonical source graph.

    No caller import or mutable public project module supplies fixture bytes.
    Existing modules are never overwritten.  Every owned namespace is removed
    by identity, and a foreign replacement is preserved and rejected.
    """
    def __init__(self):
        self.prefix="_clash_v3_fixture_"+uuid.uuid4().hex
        self.modules,self.snapshots,self.names={}, {}, []
        self.original_import=builtins.__import__
        self.closed=False

    def path(self,name):
        if name.startswith("src.") or name=="src":
            base=ROOT.joinpath(*name.split("."))
        elif "." not in name:
            base=ROOT/"tools"/name
            if not base.with_suffix(".py").is_file() and not base.is_dir():
                base=ROOT/"src"/"patcher"/name
        else: return None
        if base.with_suffix(".py").is_file(): return base.with_suffix(".py"),False
        if base.is_dir(): return base/"__init__.py",True
        return None

    def load(self,name):
        if name in self.modules: return self.modules[name]
        selected=self.path(name); _require(selected is not None,"fixed fixture source import absent")
        path,package=selected; absolute=_plain_path(path)
        raw=absolute.read_bytes() if absolute.is_file() else b""
        if raw: self.snapshots[absolute]=(raw,_stamp(absolute))
        module=types.ModuleType(self.prefix+"."+name); module.__file__=str(absolute)
        module.__package__=module.__name__ if package else module.__name__.rpartition(".")[0]
        if package: module.__path__=[str(absolute.parent)]
        module.__dict__["__builtins__"]={**vars(builtins),"__import__":self.importer}
        _require(module.__name__ not in sys.modules,"private fixture namespace collision")
        self.modules[name]=module; sys.modules[module.__name__]=module; self.names.append(module)
        previous_path=tuple(sys.path)
        try:
            exec(compile(raw,str(absolute),"exec"),module.__dict__)
        finally:
            sys.path[:]=previous_path
        self.guard()
        return module

    def importer(self,name,globals=None,locals=None,fromlist=(),level=0):
        if level:
            package=(globals or {}).get("__package__","")
            _require(package.startswith(self.prefix+"."),"foreign relative project import")
            parts=package[len(self.prefix)+1:].split(".")
            _require(level<=len(parts)+1,"relative project import escapes source graph")
            base=".".join(parts[:len(parts)-level+1])
            name=base+("." if base and name else "")+name
        if self.path(name) is None:
            return self.original_import(name,globals,locals,fromlist,0)
        module=self.load(name)
        for item in fromlist or ():
            child=name+"."+item
            if item!="*" and self.path(child) is not None and not hasattr(module,item):
                setattr(module,item,self.load(child))
        if fromlist: return module
        if "." in name:
            top=name.split(".")[0]; result=self.load(top)
            parts=name.split(".")
            for index in range(1,len(parts)):
                parent=self.load(".".join(parts[:index])); setattr(parent,parts[index],self.load(".".join(parts[:index+1])))
            return result
        return module

    def guard(self):
        _require(all(path.read_bytes()==raw and _stamp(path)==stamp for path,(raw,stamp) in self.snapshots.items()),
                 "private fixture producer source changed")
        _require(all(sys.modules.get(module.__name__) is module for module in self.names),
                 "private fixture namespace identity replaced")

    def close(self):
        if self.closed: return
        self.closed=True
        replaced=False
        for module in reversed(self.names):
            if sys.modules.get(module.__name__) is module: del sys.modules[module.__name__]
            else: replaced=True
        _require(not replaced,"private fixture namespace identity lost")


@dataclass(frozen=True)
class LoadedImageContract:
    candidate: bytes
    typed_metadata_json: str
    canonical_probe: bytes
    plan_json: str


def _clone_contract(original):
    _require(is_dataclass(original) and not isinstance(original,type) and
             type(original).__name__=="LoadedImageContract" and
             {row.name for row in fields(original)}=={row.name for row in fields(LoadedImageContract)},
             "typed exact immutable candidate contract required")
    data={row.name:getattr(original,row.name) for row in fields(LoadedImageContract)}
    _require(type(data["candidate"]) is type(data["canonical_probe"]) is bytes and
             type(data["typed_metadata_json"]) is type(data["plan_json"]) is str,
             "exact candidate/metadata/probe originals required")
    return LoadedImageContract(**data)


def _source_snapshot(path):
    path=_plain_path(path)
    return path,path.read_bytes(),_stamp(path)


def _unchanged(snapshots):
    _require(all(_plain_path(path)==path and path.read_bytes()==raw and _stamp(path)==stamp
                 for path,raw,stamp in snapshots),"canonical imported source bytes/identity changed")


def _generator_private(snapshot):
    path,raw,stamp=snapshot
    _unchanged((snapshot,))
    result=_closed(raw,path,("prepare_plan","prepare_request","render_observer","inspect_request"),"_api_factory")
    _unchanged((snapshot,))
    return result


def _fixture_generator(generator, mode):
    _integer(mode,0,10)
    graph=_PrivateGraph()
    try:
        synthetic=graph.load("test_framed_loaded_probe_engine")
        image=graph.load("hidden_soak_loaded_image")
        expected=graph.load("hidden_soak_loader_expected")
        v1=graph.load("hidden_soak_loader_native")
        v2=graph.load("hidden_soak_loader_compare_native")
        candidate,_,_=synthetic.executable_fixture("1024x768")
        contract=image._make_contract(candidate,'["dict",[]]',b"source-owned synthetic probe; never executed\n",
            "classic","1024x768","synthetic-source-comparison-only","synthetic-v1",
            {"fixture":_sha(b"canonical marked synthetic V3, no production authority")},synthetic.probe.pe)
        snapshots=tuple((path,raw,stamp) for path,(raw,stamp) in graph.snapshots.items())
        def guard(): _unchanged(snapshots)
        def preparation(original,bound,imported):
            _require(original==candidate and bound==contract,"fixed synthetic fixture only")
            state=expected._build_state(contract,oracle=image,pe=synthetic.probe.pe,
                issuer_sha256=_sha((ROOT/"tools/hidden_soak_loader_expected.py").read_bytes()),check_sources=guard)
            def issue(authority):
                metadata,payload=expected._encode(state,authority)
                decoded,descriptors,fixups,raw=expected._decode(payload)
                return decoded,payload,descriptors,fixups,raw,lambda base:expected._model(payload,base),_sha(imported)
            return issue,v1.HARNESS,guard,_sha(imported),_sha((ROOT/"tools/hidden_soak_loader_compare_native_adapter.py").read_bytes())
        apis=generator._factory(_fixture=v2._factory(_preparation=preparation),_fixture_mode=mode)
        # These private module closures survive namespace cleanup; no ambient
        # project module remains a producer or registry bridge.
        graph.close(); guard()
        return apis,candidate,contract,guard,expected.PayloadAuthority
    except BaseException:
        graph.close()
        raise


def _build_api(own_snapshot, generator_snapshot, *, backend=_NativeSession, _fixture_scope=False):
    _require(backend is _NativeSession or _fixture_scope is True,"mock backend requires explicit fixture registry")
    snapshots=(own_snapshot,generator_snapshot)
    generator=_generator_private(generator_snapshot)
    production=generator._factory()
    registry={}
    capability_class=NativeCapability
    digest,canonical,reference=_sha,_canonical,weakref.ref
    def guard():
        try:_unchanged(snapshots)
        except BaseException:
            seen=set()
            for entry in tuple(registry.values()):
                session=entry[3].get("session")
                if session is not None and id(session) not in seen:
                    seen.add(id(session));session.failed=True;session.finish_and_close()
            raise
    def retain(kind,state,fixture=False):
        state=dict(state,_stage_used=False)
        obj=capability_class(canonical(dict(schema="loader_v3_native_capability",kind=kind,fixture_only=fixture,
                                            claims=FALSE_CLAIMS)).decode("ascii"))
        key=id(obj)
        def gone(ref):
            if key in registry and registry[key][0] is ref:
                entry=registry.pop(key)
                session=entry[3].get("session")
                if session is not None and not session.closed and not any(
                        row[0]() is not None and row[3].get("session") is session for row in registry.values()):
                    session.failed=True;session.finish_and_close()
        registry[key]=(reference(obj,gone),obj.binding_json,kind,state,fixture)
        return obj
    def admit(obj,kind):
        guard(); row=registry.get(id(obj))
        _require(type(obj) is capability_class and row is not None and row[0]() is obj
                 and row[1]==obj.binding_json and row[2]==kind,"genuine live same-registry capability required")
        state=row[3]
        try:
            state.get("fixture_guard",lambda:None)()
            if "request" in state: state["apis"][3](state["request"]).check_sources()
        except BaseException:
            session=state.get("session")
            if session is not None:session.failed=True;session.finish_and_close()
            raise
        return state,row[4]
    def consume(obj,kind):
        state,fixture=admit(obj,kind)
        _require(not state["_stage_used"] and not state["session"].closed,"native stage already consumed or closed")
        state["_stage_used"]=True
        return state,fixture
    def prepare(original,contract):
        guard(); clone=_clone_contract(contract); value=production[0](original,clone); guard()
        return retain("plan",dict(plan=value,apis=production,candidate=clone.candidate,contract=clone,mode=0))
    def synthetic(*,mode=0):
        guard(); apis,candidate,contract,fixture_guard,authority=_fixture_generator(generator,mode)
        value=apis[0](candidate,contract); fixture_guard(); guard()
        return retain("plan",dict(plan=value,apis=apis,candidate=candidate,contract=contract,
            fixture_guard=fixture_guard,authority_class=authority,mode=mode),True)
    def outer(plan,paths):
        state,fixture=admit(plan,"plan")
        _require(is_dataclass(paths) and not isinstance(paths,type) and type(paths).__name__=="NativePaths"
                 and {v.name for v in fields(paths)}=={v.name for v in fields(NativePaths)},"typed native path request required")
        paths=NativePaths(**{v.name:getattr(paths,v.name) for v in fields(NativePaths)})
        source=generator.render_outer_source(fixture_mode=state["mode"])
        session=backend.__new__(backend)
        try:
            backend.__init__(session,paths,generator.retention_budget()["known_peak_bytes"],fixture=fixture)
            candidate=_plain_path(paths.candidate)
            _require(candidate.parent==session.root,"candidate must be a direct dedicated root child")
            session.files["candidate"]=candidate
            if fixture:
                _require(not candidate.exists(),"synthetic CREATE_NEW candidate already exists")
                session.write_new("candidate",state["candidate"])
            _require(candidate.read_bytes()==state["candidate"],"exact privately authenticated candidate file differs")
            binary=session.compile("outer_source","outer",paths.compiler_x64,source,machine=0x8664)
            guard(); state.get("fixture_guard",lambda:None)()
            return retain("outer_build",dict(state,session=session,outer_source=source,outer_binary=binary),fixture)
        except BaseException as error:
            if hasattr(session,"kernel"):
                session.failed=True; session.finish_and_close()
            raise NativeFailure(type(error).__name__+": "+str(error),events=getattr(session,"events",()),
                                pending=getattr(session,"pending",()),cause=error) from error
    def suspended(build):
        state,fixture=consume(build,"outer_build"); session=state["session"]
        try:
            _require(session.files["outer"].read_bytes()==state["outer_binary"],"compiled outer changed before launch")
            session.create_suspended(); guard()
            return retain("suspended_outer",dict(state),fixture)
        except BaseException as error:
            session.failed=True; session.finish_and_close()
            raise NativeFailure(str(error),events=session.events,pending=session.pending,cause=error) from error
    def observer(cap):
        state,fixture=consume(cap,"suspended_outer"); session=state["session"]
        try:
            current=session._generation(6,"outer")
            _require(current==session.outer,"same retained suspended outer generation required")
            frequency,origin,origin_ns=session.clock(); ids=tuple(uuid.uuid4().hex for _ in range(3))
            if fixture: authority_class=state["authority_class"]
            else:
                # The privately compiled expected issuer structurally clones
                # this typed record; no public project module supplies it.
                authority_class=PayloadAuthority
            authority=authority_class(*ids,session.outer["pid"],frequency,origin,origin_ns)
            request=state["apis"][1](state["plan"],authority); facts=state["apis"][3](request)
            metadata=json.loads(facts.metadata_json)
            core=bytearray(32768);core[:8]=b"CLHDBV3\0";struct.pack_into("<II",core,8,3,32768)
            struct.pack_into("<IQIQQQQ",core,16,session.caller["pid"],session.caller["creation"],
                session.outer["pid"],session.outer["creation"],frequency,origin,origin_ns)
            core[64:112]=b"".join(bytes.fromhex(v) for v in ids)
            closure=digest(canonical(dict(v3_source_sha256=digest(generator_snapshot[1]),
                v3_adapter_sha256=digest(own_snapshot[1]),predecessor_producer_closure_sha256=metadata["producer_source_closure_sha256"])))
            hashes=(digest(facts.request_bytes),digest(facts.expected_payload),metadata["candidate_sha256"],
                metadata["probe_sha256"],session.caller["sha256"],digest(state["outer_binary"]),closure)
            core[112:336]=b"".join(bytes.fromhex(v) for v in hashes)
            archive_ids=tuple(uuid.uuid4().hex for _ in range(3));core[336:384]=b"".join(bytes.fromhex(v) for v in archive_ids)
            values={**{key:str(session.files[key]) for key in generator.PATH_NAMES if key in session.files},
                    "caller":session.caller["path"],"root":str(session.root)}
            for index,name in enumerate(generator.PATH_NAMES):
                raw=(values[name]+"\0").encode("utf-16le");_require(len(raw)<=2048,"fixed literal native path too long")
                core[384+index*2048:384+index*2048+len(raw)]=raw
            struct.pack_into("<IQQQ",core,27008,*session.root_identity,session.paths.approved_peak_bytes,session.paths.runtime_asset_bytes)
            core=bytes(core); source=state["apis"][2](request,core)
            session.write_new("request",facts.request_bytes);session.write_new("payload",facts.expected_payload)
            binary=session.compile("observer_source","observer",session.paths.compiler_x86,source,machine=0x14c)
            guard();facts=state["apis"][3](request);facts.check_sources()
            return retain("observer_build",dict(state,request=request,facts=facts,core=core,
                observer_source=source,observer_binary=binary,ids=ids,archive_ids=archive_ids),fixture)
        except BaseException as error:
            session.failed=True;session.finish_and_close()
            raise NativeFailure(str(error),events=session.events,pending=session.pending,cause=error) from error
    def finalize(cap):
        state,fixture=consume(cap,"observer_build");session=state["session"]
        try:
            for name,raw in (("outer",state["outer_binary"]),("observer",state["observer_binary"]),
                             ("request",state["facts"].request_bytes),("payload",state["facts"].expected_payload)):
                _require(session.files[name].read_bytes()==raw,"source-issued immutable artifact changed before bootstrap")
            prefix=state["core"]+bytes.fromhex(digest(state["observer_binary"]))+bytes.fromhex(digest(state["observer_source"]))
            boot=prefix+bytes.fromhex(digest(prefix));_require(len(boot)==32864,"complete bootstrap extent differs")
            identity=session.write_new("bootstrap",boot);guard()
            return retain("launch",dict(state,bootstrap=boot,bootstrap_identity=identity),fixture)
        except BaseException as error:
            session.failed=True;session.finish_and_close()
            raise NativeFailure(str(error),events=session.events,pending=session.pending,cause=error) from error
    def collect(cap):
        state,fixture=consume(cap,"launch");session=state["session"]
        error=None
        try:
            _require(not session.closed,"native launch has already finished/failed")
            _require(session.files["bootstrap"].read_bytes()==state["bootstrap"],"sealed bootstrap changed before resume")
            session.resume()
        except BaseException as caught:
            error=caught;session.failed=True
        finally:
            session.finish_and_close()
        # No nonexistent/unavailable stream is converted to a fabricated empty
        # original.  Failures retain pending observations in NativeFailure.
        try:
            originals=JoinedOriginals(*(session.files[name].read_bytes() for name in
                ("caller_archive","outer_archive","observer_archive","observer_stderr","outer_stderr")),
                session.caller_close_receipt)
        except BaseException as caught:
            raise NativeFailure(str(caught),events=session.events,pending=session.pending,cause=error or caught) from caught
        guard();state["facts"].check_sources()
        state["originals"]=originals;state["native_error"]=error
        state["original_seal"]=_joined_seal(originals)
        return originals
    def parse(originals,cap):
        state,fixture=admit(cap,"launch")
        _require(type(originals) is JoinedOriginals and state.get("originals") is originals,
                 "exact native-session issued original streams required")
        _require(_joined_seal(originals)==state["original_seal"],"native-issued original streams changed")
        observed,rows=_joined_protocol(originals,state,generator)
        guard();state["facts"].check_sources()
        return retain("parsed",dict(state,observed=observed,frames=rows),fixture)
    def replay(cap):
        state,fixture=admit(cap,"parsed");originals=state["originals"]
        _require(_joined_seal(originals)==state["original_seal"],"native-issued original streams changed after parsing")
        observed,rows=_joined_protocol(originals,state,generator)
        _require(canonical(observed)==canonical(state["observed"]),"joined original replay changed")
        guard();state["facts"].check_sources()
        report=dict(schema="loader_v3_joined_replay",fixture_only=fixture,supplied_receipt_math_only=True,
                    **observed,**generator.FALSE_CLAIMS,**FALSE_CLAIMS)
        return ReplayResult(canonical(report).decode("ascii"),originals,rows)
    def inspect(cap):
        guard();entry=registry.get(id(cap))
        _require(entry is not None and entry[0]() is cap and entry[1]==cap.binding_json,"genuine native capability required")
        return json.loads(cap.binding_json)
    return prepare,synthetic,outer,suspended,observer,finalize,collect,parse,replay,inspect


@dataclass(frozen=True)
class PayloadAuthority:
    run_id: str
    checkpoint_id: str
    epoch_id: str
    controller_pid: int
    frequency_hz: int
    origin_tick: int
    origin_ns: int


V2_ADAPTER = ROOT/"tools/hidden_soak_loader_compare_native_adapter.py"
V2_ADAPTER_SHA = "6fc94c7d195bff0e3442e77c6fd7bd85015c17a10326ec1baba5cb8e1b3206ae"
CAPACITY_FIELDS = ("handle","pid","pid_error","path_return","path_error","path_chars","times_return","times_error","times_hex")
PARENT_FIELDS = ("handle","snapshot_handle","snapshot_error","parent_pid","parent_return","parent_error",
                 "parent_times_return","parent_times_error","parent_times_hex","row_bytes","cohort_rows")
GATE_FIELDS = {
    "gate_nonce":("status",),"gate_open_caller":("return","error","pid"),
    "gate_generation":("role","handle","pid","pid_error","times_return","times_error","wait","wait_error",
                       "exit_return","exit_error","exit_code"),
    "gate_hash":("input_bytes","open_status","hash_status","close_status","digest_hex"),
    "gate_file_info":("role","handle","return","error"),"gate_file_path":("role","handle","chars","error"),
    "challenge_write":("write_return","write_error","requested","returned","flush_return","flush_error"),
    "challenge_signal":("return","error"),"gate_wait_before":None,
    "adoption_wait":("return","error","timeout_ms"),"adoption_read":("return","error","requested","returned"),
    "gate_complete":("challenge_sha256","outer_archive_id"),
    "gate_close_caller":("handle","return","error"),
    "inherited_flags":("role","handle","return","error","flags"),
    "clear_inherit":("role","handle","return","error"),
    "cleared_flags":("role","handle","return","error","flags"),
    "inherited_close":("role","handle","return","error"),
    "bootstrap":("bytes",)}


def _fixed_helpers():
    snapshot=_source_snapshot(V2_ADAPTER)
    _require(_sha(snapshot[1])==V2_ADAPTER_SHA,"fixed comparison subvalidator source changed")
    module=_closed(snapshot[1],snapshot[0],("prepare_comparison_plan","prepare_comparison_request","inspect_comparison_request",
        "parse_archive","replay_archive","replay_fixture_archive"),"_api_factory")
    helpers,sources=module._source_helpers()
    snapshots=(snapshot,)+tuple(_source_snapshot(path) for path,_ in sources)
    _unchanged(snapshots)
    return module,helpers,snapshots


def _caller_job_query(class_id,result,returned,raw,pid):
    _require(type(result) is int and result!=0 and type(raw) is bytes,
             "original caller job query failed or buffer unavailable")
    if class_id==9:
        _require(len(raw)==returned==144 and struct.unpack_from("<I",raw,16)[0]==0x2000,
                 "original caller no-breakaway/kill limit readback differs")
    elif class_id==1:
        _require(len(raw)==returned==48 and struct.unpack_from("<I",raw,40)[0]==1,
                 "original caller suspended job accounting differs")
    elif class_id==3:
        _require(len(raw)==520 and struct.unpack_from("<II",raw)==(1,1) and returned==16
                 and struct.unpack_from("<Q",raw,8)[0]==pid,
                 "original caller complete suspended PID readback differs")
    else:raise ValueError("source-owned caller job information class required")


def _compiler_environment(environment,machine):
    _require(type(environment) is dict and environment and all(type(k) is str and type(v) is str for k,v in environment.items()),
             "exact original compiler environment required")
    upper={key.upper():value for key,value in environment.items()}
    _require(len(upper)==len(environment) and all(name in COMPILER_ENV_KEYS or name.startswith("VSCMD_") for name in upper)
        and upper.get("VSCMD_ARG_TGT_ARCH")==("x64" if machine==0x8664 else "x86") and machine in (0x8664,0x14c),
        "source-owned target compiler allowlist without credential or injected switches required")


def _hex_original(value,size):
    _require(type(value) is str and len(value)==size*2 and all(c in "0123456789abcdef" for c in value),
             "complete lowercase original buffer required")
    return bytes.fromhex(value)


def _capacity_groups(frames):
    """Correlate every complete path/Toolhelp buffer with its own owner role.

    The parent query stops at the first matching row.  It is a complete record
    of that bounded query, not a claim of an exhaustive process inventory.
    """
    pending=[]; consumed=set(); group={}
    for row in frames:
        if row.operation in ("generation_capacity","generation_parent_capacity"):
            pending.append(row); continue
        if row.operation not in ("owner","startup_owner"):
            _require(not pending or row.operation=="output","original generation cohort interrupted before owner")
            continue
        _require(len(pending)==6 and tuple(r.operation for r in pending)==
                 ("generation_capacity","generation_parent_capacity")*3,"three original capacity cohorts required per owner")
        owners=row.data()
        handles=[]
        for role,(capacity,parent) in zip(("controller","debugger","target"),zip(pending[::2],pending[1::2])):
            value=_exact(capacity.data(),CAPACITY_FIELDS,"original generation capacity")
            ancestor=_exact(parent.data(),PARENT_FIELDS,"original parent capacity")
            original=owners[role]
            for name in ("path_return","times_return"):
                _integer(value[name],-(2**31),0xffffffff)
                _require(value[name]==original[name]==1,"original generation BOOL failed/differs")
            for name in ("handle","pid"):
                _integer(value[name],1,0xffffffff)
            for name in ("pid_error","path_error","times_error"):
                _integer(value[name]); _require(value[name]==original[name]==0,"original generation query error differs")
            _integer(value["path_chars"],1,32767)
            _require(value["pid"]==original["pid"] and value["path_chars"]==original["path_chars"]
                     and len(capacity.raw)==65536 and capacity.raw[:value["path_chars"]*2].hex()==original["image_path_utf16le"],
                     "full original generation path prefix differs from owner")
            times=struct.unpack("<4Q",_hex_original(value["times_hex"],32))
            _require(times==tuple(original[name] for name in ("creation_filetime","exit_filetime","kernel_filetime","user_filetime")),
                     "original whole generation time buffer differs")
            _require(ancestor["handle"]==value["handle"] and ancestor["snapshot_handle"] not in (0,0xffffffff)
                     and ancestor["snapshot_error"]==0 and ancestor["row_bytes"]==556
                     and type(ancestor["cohort_rows"]) is int and 1<=ancestor["cohort_rows"]<=4096
                     and len(parent.raw)==ancestor["cohort_rows"]*564,"full bounded original parent cohort required")
            for name,target in (("parent_pid","parent_pid"),("parent_return","parent_query_return"),
                                ("parent_error","parent_query_error"),("parent_times_return","parent_times_return"),
                                ("parent_times_error","parent_times_error")):
                _require(type(ancestor[name]) is int and ancestor[name]==original[target],"original parent scalar differs from owner")
            _require(ancestor["parent_return"]==ancestor["parent_times_return"]==1 and
                     ancestor["parent_error"]==ancestor["parent_times_error"]==0,"original parent query failed")
            matches=[]
            for index in range(ancestor["cohort_rows"]):
                block=parent.raw[index*564:(index+1)*564]
                result,error,size,pid=struct.unpack_from("<iIII",block)
                _require(result==1 and error==0 and size==556,"original queried parent row failed/short")
                if pid==value["pid"]: matches.append((index,struct.unpack_from("<I",block,32)[0]))
            _require(matches==[(ancestor["cohort_rows"]-1,ancestor["parent_pid"])],
                     "original parent first-match query missing/duplicated/reordered")
            parent_times=struct.unpack("<4Q",_hex_original(ancestor["parent_times_hex"],32))
            _require(parent_times[0]==original["parent_creation_filetime"] and parent_times[0]>0,
                     "original retained parent creation differs")
            handles.append(value["handle"])
        _require(len(set(handles))==3,"owner native role handles alias")
        group[row.sequence]=tuple(handles); consumed.update(r.sequence for r in pending);pending=[]
    _require(not pending,"orphan original generation cohort")
    return tuple(row for row in frames if row.sequence not in consumed),group


def _caller_protocol(frames,state):
    expected=state["session"]
    _require(frames and frames[-1].operation=="finish" and sum(r.operation=="finish" for r in frames)==1,
             "single terminal original caller receipt required")
    observations=[]
    for row in frames:
        _io(row)
        envelope=_exact(row.data(),("observation","prewrite_reserve"),"caller original wrapper")
        reserve=_exact(envelope["prewrite_reserve"],("result","error","free","total","unused","required_peak"),"caller original reserve")
        for name,value in reserve.items(): _integer(value,-2**31 if name=="result" else 0,2**63-1)
        _require(reserve["result"]!=0 and reserve["required_peak"]==expected.paths.approved_peak_bytes and
                 reserve["free"]-reserve["required_peak"]>reserve["total"]//10,"original strict caller reserve failed/differs")
        _require(row.operation in ("api","reserve","archive_magic_io","generation","subprocess","subprocess_timeout",
                                  "compiler_environment","compiled","clock_pair","finish"),"unknown original caller operation")
        observations.append(envelope["observation"])
    _require(tuple((r.sequence,r.operation,r.metadata,r.raw,r.footer,r.offset) for r in frames)==
             tuple((r.sequence,r.operation,r.metadata,r.raw,r.footer,r.offset) for r in expected.events),
             "original caller archive differs from native-issued event seal")
    result=observations[-1]
    _exact(result,("status","frame_count","raw_bytes","metadata_bytes","comparison_scope"),"caller original finish")
    _require(result==dict(status="failed" if expected.failed or expected.debt else "complete",frame_count=len(frames)-1,
             raw_bytes=sum(len(r.raw) for r in frames[:-1]),metadata_bytes=8+sum(32+len(r.metadata) for r in frames[:-1]),
             comparison_scope="initial_loader_held_adoption_v3"),"caller original finish counters/status differ")
    compiled=[v for r,v in zip(frames,observations) if r.operation=="compiled"]
    _require(len(compiled)==2 and tuple(v["role"] for v in compiled)==("outer","observer") and
             tuple((v["source_sha256"],v["binary_sha256"],v["machine"]) for v in compiled)==
             ((_sha(state["outer_source"]),_sha(state["outer_binary"]),0x8664),
              (_sha(state["observer_source"]),_sha(state["observer_binary"]),0x14c)),
             "both original compiler/binary/source receipts required")
    clocks=[(index,row,value) for index,(row,value) in enumerate(zip(frames,observations)) if row.operation=="clock_pair"]
    _require(len(clocks)==1,"unique original monotonic/QPC pairing receipt required")
    index,row,value=clocks[0]
    _exact(value,("method","before_ns","after_ns","frequency_hz","tick","counter_return","counter_error"),"original paired clock")
    _require(value["method"]=="time.monotonic_ns" and type(value["before_ns"]) is type(value["after_ns"]) is int and
        0<value["before_ns"]<=value["after_ns"]<2**63-20*10**9 and row.raw==struct.pack("<2Q",value["before_ns"],value["after_ns"]),
        "original paired monotonic bracket/scalars differ")
    _require(index>=2 and tuple(v["name"] for v in observations[index-2:index])==("QueryPerformanceFrequency","QueryPerformanceCounter") and
        frames[index-2].raw==struct.pack("<q",value["frequency_hz"]) and frames[index-1].raw==struct.pack("<q",value["tick"]) and
        value["counter_return"]==observations[index-1]["result"]!=0 and value["counter_error"]==observations[index-1]["error"],
        "original paired clock native QPC/frequency receipts differ")
    core=state["core"]
    _require(struct.unpack_from("<3Q",core,40)==(value["frequency_hz"],value["tick"],value["before_ns"]),
        "source core clock is not the original QPC/monotonic bracket")
    resumes=[i for i,(row,value) in enumerate(zip(frames,observations)) if row.operation=="api" and value.get("name")=="ResumeThread"]
    _require(len(resumes)==1 and observations[resumes[0]]["result"]==1,"original exactly-once outer resume required")
    for ending in [i for i,(row,value) in enumerate(zip(frames,observations)) if row.operation=="api" and value.get("name")=="IsProcessInJob"]:
        _require(ending>=3 and tuple(v.get("name") for v in observations[ending-3:ending])==("QueryInformationJobObject",)*3
            and tuple(v.get("class_id") for v in observations[ending-3:ending])==(9,1,3),
            "complete original caller job readback group required")
        for source,packet in zip(observations[ending-3:ending],frames[ending-3:ending]):
            _caller_job_query(source["class_id"],source["result"],source["returned"],packet.raw,state["session"].outer["pid"])
        _require(observations[ending]["result"]!=0 and frames[ending].raw==struct.pack("<i",1),"original caller job membership failed")
    _require(resumes[0]>=4 and tuple(v.get("name") for v in observations[resumes[0]-4:resumes[0]])==
        ("QueryInformationJobObject",)*3+("IsProcessInJob",),"source job readbacks must immediately precede outer resume")
    _require(sum(row.operation=="api" and value.get("name")=="IsProcessInJob" for row,value in zip(frames,observations))==2,
        "both suspended issuance and pre-resume membership groups required")
    return result


def _outer_protocol(frames,state,core,generator):
    identities={}; artifacts={}; apis=[]; packet=None; channel=None;startup=None
    previous=0
    bool_names=("WriteFile","FlushFileBuffers","GetFileInformationByHandle","GetFileSizeEx","ReadFile",
        "QueryFullProcessImageNameW","GetProcessTimes","GetExitCodeProcess","QueryPerformanceFrequency",
        "SetInformationJobObject","AssignProcessToJobObject","IsProcessInJob","SetHandleInformation",
        "GetHandleInformation","InitializeProcThreadAttributeList","UpdateProcThreadAttribute","DuplicateHandle",
        "SetEvent","CloseHandle","CloseDesktop","TerminateJobObject","TerminateProcess")
    handle_names=("CreateFileW","OpenProcess","CreateDesktopW","CreateJobObjectW","CreateEventW","CreateToolhelp32Snapshot")
    source_names=set(bool_names+handle_names+("GetFinalPathNameByHandleW","GetProcessId","GetModuleFileNameW","GetFileType",
        "Process32FirstW/Process32NextW","InitializeProcThreadAttributeList.size","DeleteProcThreadAttributeList",
        "CreateProcessW","ResumeThread","WaitForSingleObject","WaitForMultipleObjects","QueryInformationJobObject.limits",
        "QueryInformationJobObject.pids","QueryInformationJobObject.accounting","BCryptOpenAlgorithmProvider",
        "BCryptGetProperty","BCryptCreateHash","BCryptHashData","BCryptFinishHash","BCryptDestroyHash",
        "BCryptCloseAlgorithmProvider"))
    failures=[]
    for row in frames:
        _io(row); value=row.data()
        _wire_scalars(value)
        _require(row.operation in ("api","artifact","identity","bootstrap","channel_identity","adoption_packet","rejected","finish","fixture_withhold_adoption_signal","outer_finish_bound","startup_info"),
                 "unknown source outer operation")
        if row.operation=="api":
            _exact(value,("name","role","phase","handle","result","error","requested","returned","length_kind","begin","end","detail"),
                   "original outer API")
            name=value["name"]; _require(name in source_names,"unknown source outer native API")
            for clock in (value["begin"],value["end"]):
                _exact(clock,("result","error","tick"),"original outer QPC")
                _integer(clock["result"],-2**31,2**31-1);_integer(clock["error"]);_integer(clock["tick"],-2**63,2**63-1)
                _require(clock["result"]!=0 and clock["tick"]>=previous and clock["tick"]>0,"original outer QPC failed/order differs")
                previous=clock["tick"]
            for field in ("requested","returned","error"): _integer(value[field])
            _integer(value["handle"],0,2**64-1)
            _require(type(value["detail"]) is dict,"original outer detail required")
            _require(value["length_kind"] in ("original_native_count","source_capacity_no_native_count"),"outer original count policy differs")
            if name=="DeleteProcThreadAttributeList": _require(value["result"] is None,"void native result cannot be invented")
            else: _integer(value["result"],-2**31,2**64-1)
            good=True
            if name in bool_names: good=value["result"]!=0
            elif name in handle_names: good=value["result"]==value["handle"] and value["handle"] not in (0,2**64-1)
            elif name=="CreateProcessW":
                _require(len(row.raw)==24,"whole WIN64 PROCESS_INFORMATION required")
                process,thread,pid,tid=struct.unpack("<QQII",row.raw)
                good=value["result"]!=0 and process==value["handle"] and process and thread and pid and tid
            elif name=="ResumeThread": good=value["result"]==1
            elif name=="InitializeProcThreadAttributeList.size": good=value["result"]==0 and value["error"]==122 and len(row.raw)==8
            elif name.startswith("BCrypt"): good=value["result"]==0
            elif name in ("GetFinalPathNameByHandleW","GetModuleFileNameW"):
                good=0<value["result"]<32768 and len(row.raw)==65536 and value["returned"]==value["result"]
            elif name=="GetProcessId": good=0<value["result"]<=0xffffffff
            elif name=="GetFileType":
                _require((value["role"],value["phase"])==("stdin_original","channel") and not row.raw,
                    "only the original NUL character channel has a file-type query")
                good=value["result"]==2
            elif name=="WaitForSingleObject":
                expected=0 if value["phase"] in ("gate","natural_finish","cleanup") else 258
                if value["phase"]=="exit": expected=0
                good=value["result"]==expected
            elif name=="WaitForMultipleObjects":
                _require(len(row.raw)==16 and value["detail"].get("count")==2 and
                         value["detail"].get("wait_all")==0,"original two-handle challenge wait required")
                good=value["result"]==0
            elif name.startswith("QueryInformationJobObject."):
                good=value["result"]!=0
                if name.endswith(".limits"):
                    good=good and value["requested"]==value["returned"]==len(row.raw)==144 and struct.unpack_from("<I",row.raw,16)[0]==0x2000
                elif name.endswith(".accounting"):
                    good=good and value["requested"]==value["returned"]==len(row.raw)==48
                else:
                    _require(len(row.raw)==520,"whole original WIN64 PID capacity required")
                    assigned,count=struct.unpack_from("<II",row.raw)
                    good=good and assigned==count<=64 and value["returned"]==8+8*count and value["requested"]==520
                    pids=struct.unpack_from("<"+"Q"*count,row.raw,8)
                    good=good and len(set(pids))==count and all(0<v<=0xffffffff for v in pids)
            elif name=="Process32FirstW/Process32NextW":
                _require(len(row.raw)%576==0 and 1<=len(row.raw)//576<=4096,"whole original WIN64 Toolhelp cohort required")
                good=value["result"]==0 and value["error"]==18
                for index in range(len(row.raw)//576):
                    result,error,size=struct.unpack_from("<iII",row.raw,index*576)
                    good=good and size==568 and (result==1 and error==0 if index<len(row.raw)//576-1 else result==0 and error==18)
            if name=="ReadFile":
                _require(len(row.raw) in (value["requested"],65536),"whole original ReadFile capacity required")
                good=good and value["returned"]==value["requested"]
            if name=="WriteFile": good=good and value["returned"]==value["requested"]==len(row.raw)
            if name=="IsProcessInJob":good=good and len(row.raw)==4 and struct.unpack("<i",row.raw)[0]==1
            if name=="DuplicateHandle":good=good and 0<value["handle"]<2**64-1
            if name=="GetProcessTimes":_require(len(row.raw)==32,"whole original FILETIME capacity required")
            if name=="GetExitCodeProcess":_require(len(row.raw)==4,"whole original exit DWORD required")
            if not good: failures.append((name,value["role"],value["phase"],value["result"],value["error"]))
            apis.append(row)
        elif row.operation=="artifact":
            _exact(value,("role","path","sha256","volume","file_id","size"),"original outer artifact")
            _require(value["role"] not in artifacts,"duplicate source outer artifact")
            artifacts[value["role"]]=value
        elif row.operation=="identity":
            _exact(value,("role","phase","pid","creation","exit_time","wait","exit_code","path","sha256","parent_pid","parent_creation","parent_scope"),"original outer identity")
            key=value["role"],value["phase"]
            _require(key not in identities,"duplicate original outer generation boundary")
            identities[key]=(row,value)
        elif row.operation=="bootstrap":
            _exact(value,("sha256",),"original outer bootstrap")
            _require(row.raw==state["bootstrap"] and value["sha256"]==_sha(row.raw),"whole outer bootstrap differs from native-issued bytes")
        elif row.operation=="channel_identity":
            _exact(value,("outer_archive_id","observer_archive_id","challenge_writer","challenge_reader","adoption_writer","adoption_reader"),"original channel identities")
            _require(channel is None and value["outer_archive_id"]==core["archives"][1] and
                     value["observer_archive_id"]==core["archives"][0] and
                     len({value[name] for name in ("challenge_writer","challenge_reader","adoption_writer","adoption_reader")})==4,
                     "original separate reader/writer/channel cohort differs")
            channel=row
        elif row.operation=="adoption_packet":
            _require(packet is None,"duplicate original adoption packet")
            _exact(value,("challenge_sha256","target_creation"),"outer original adoption")
            packet=row
        elif row.operation=="startup_info":
            _exact(value,("bytes",),"original outer WIN64 startup info")
            _require(startup is None and type(value["bytes"]) is int and value["bytes"]==len(row.raw)==112 and
                struct.unpack_from("<I",row.raw)[0]==112 and struct.unpack_from("<I",row.raw,60)[0]==0x100,
                "one complete original WIN64 STARTUPINFOEXW required")
            startup=row
        elif row.operation=="rejected":_exact(value,("message",),"original outer rejection")
        elif row.operation=="fixture_withhold_adoption_signal":
            _exact(value,("initial_tick",),"original withheld signal diagnostic");_integer(value["initial_tick"],1,2**63-1)
        elif row.operation=="outer_finish_bound":
            _exact(value,("result","error","tick"),"original outer finish bound")
            _require(value["result"]!=0 and value["tick"]>=previous,"original outer finish QPC failed/reordered")
            previous=value["tick"]
    finish=_exact(frames[-1].data(),("failed","debt","scope"),"original outer finish")
    _require(frames[-1].operation=="finish" and sum(r.operation=="finish" for r in frames)==1 and
             type(finish["failed"]) is type(finish["debt"]) is int and finish["failed"] in (0,1) and finish["debt"] in (0,1)
             and finish["scope"]=="V3_initial_loader_terminate_only","single typed original outer terminal required")
    if not finish["failed"] and not finish["debt"]:
        _require(not failures and not any(r.operation=="rejected" for r in frames),"later outer completion cannot erase failure")
        expected_artifacts={"observer_file":state["observer_binary"],"candidate_file":state["candidate"],
            "request_file":state["facts"].request_bytes,"payload_file":state["facts"].expected_payload,
            "outer_file":state["outer_binary"]}
        _require(set(artifacts)==set(expected_artifacts)|{"caller_file"},"complete fixed outer artifact inventory required")
        for role,raw in expected_artifacts.items():
            _require(artifacts[role]["sha256"]==_sha(raw) and artifacts[role]["size"]==len(raw),"source outer artifact bytes/hash differ")
        _require(channel is not None and packet is not None,"successful outer needs original channel and adoption")
        _require(("observer","adopt_before") in identities and ("observer","adopt_after") in identities
                 and ("target","adopt_before") in identities and ("target","adopt_after") in identities,
                 "live retained pre/post adoption cohorts required")
        # Complete drain is two separate final PID/accounting pairs following
        # the final owned wait; late retry or an earlier empty job is insufficient.
        drained=[r for r in apis if r.data()["phase"]=="drain"]
        _require(len(drained)>=4 and tuple(r.data()["name"] for r in drained[-4:])==
            ("QueryInformationJobObject.pids","QueryInformationJobObject.accounting")*2,
            "two original final job drain snapshots required")
        for pids,account in zip(drained[-4::2],drained[-3::2]):
            _require(struct.unpack_from("<II",pids.raw)==(0,0) and struct.unpack_from("<I",account.raw,40)[0]==0,
                     "original final owned job is not drained")
        _outer_bounds(frames,apis,core)
    return dict(identities=identities,apis=apis,channel=channel,adoption=packet,failures=failures,artifacts=artifacts,
                startup_info=startup,failed=bool(finish["failed"] or finish["debt"]),debt=bool(finish["debt"]))


def _outer_inheritance(outer,inherited):
    """Join native duplicates, startup buffers and receiver handles.

    GetHandleInformation supplies flags only. The desired-access claim comes
    from each original successful DuplicateHandle call with options zero.
    """
    apis=outer["apis"];startup=outer["startup_info"]
    _require(startup is not None,"original observer startup buffer missing")
    roles=("stdin","stdout","stderr","challenge_writer_inherited","adoption_reader_inherited",
        "challenge_event_inherited","adoption_event_inherited")
    sources=("stdin_original","observer_archive","observer_stderr","challenge_writer","adoption_reader",
        "challenge_event","adoption_event")
    access=(0x120089,0x120196,0x120196,0x120196,0x120089,2,0x100000)
    duplicates=[row for row in apis if row.data()["name"]=="DuplicateHandle" and row.data()["phase"]=="inherit"]
    _require(len(duplicates)==7 and tuple(row.data()["role"] for row in duplicates)==roles,
        "exact seven original restricted duplicate roles/order required")
    handles=[]
    for index,(row,role,source,wanted) in enumerate(zip(duplicates,roles,sources,access)):
        value=row.data();detail=_exact(value["detail"],("original","desired_access","inherit","options"),"original restricted duplicate")
        _require(type(value["result"]) is int and value["result"]!=0 and
            type(value["handle"]) is int and 0<value["handle"]<=0xfffffffe and
            all(type(detail[name]) is int for name in detail) and
            (detail["desired_access"],detail["inherit"],detail["options"])==(wanted,1,0),
            "original duplicate failure, access expansion or alternate inheritance policy")
        opened=[entry for entry in apis if entry.data()["name"]==("CreateEventW" if index>=5 else "CreateFileW") and
            (entry.data()["role"],entry.data()["phase"])==(source,"channel")]
        _require(len(opened)==1 and opened[0].sequence<row.sequence and
            opened[0].data()["result"]==opened[0].data()["handle"]==detail["original"] and
            detail["original"]!=value["handle"],"restricted duplicate lacks its own original channel creation")
        if index>=5:
            _require(opened[0].data()["detail"]==dict(manual_reset=1,initial_state=0,unnamed=1),
                "only private manual-reset initially nonsignaled events may be inherited")
        flags=[entry for entry in apis if entry.data()["name"]=="GetHandleInformation" and
            (entry.data()["role"],entry.data()["phase"])==(role,"inherit")]
        _require(len(flags)==1 and row.sequence<flags[0].sequence<startup.sequence and
            flags[0].data()["handle"]==value["handle"] and flags[0].data()["result"]!=0 and
            flags[0].data()["requested"]==flags[0].data()["returned"]==len(flags[0].raw)==4 and
            struct.unpack("<I",flags[0].raw)[0]&1,"original duplicate inheritance flag missing/differs")
        _require(inherited[index]==value["handle"],"observer received a substituted original duplicate handle")
        handles.append(value["handle"])
    _require(len(set(handles))==7 and set(inherited)==set(range(7)),"original observer inheritance roles alias or expand")
    attrs=[row for row in apis if row.data()["name"]=="UpdateProcThreadAttribute"]
    _require(len(attrs)==1 and attrs[0].data()["result"]!=0 and attrs[0].data()["phase"]=="setup" and
        attrs[0].data()["requested"]==attrs[0].data()["returned"]==len(attrs[0].raw)==56 and
        attrs[0].raw==struct.pack("<7Q",*handles) and duplicates[-1].sequence<attrs[0].sequence<startup.sequence,
        "original exact seven-handle attribute buffer missing/expanded/substituted")
    raw=startup.raw
    _require(len(raw)==112 and struct.unpack_from("<I",raw)[0]==112 and
        struct.unpack_from("<I",raw,60)[0]==0x100 and struct.unpack_from("<3Q",raw,80)==tuple(handles[:3]) and
        struct.unpack_from("<Q",raw,104)[0]==attrs[0].data()["handle"]!=0 and
        struct.unpack_from("<Q",raw,16)[0]!=0 and not any(raw[4:16]+raw[24:60]+raw[64:80]),
        "original startup buffer flags, unused bytes, std roles or attribute pointer differ")
    launches=[row for row in apis if row.data()["name"]=="CreateProcessW" and row.data()["role"]=="observer"]
    _require(len(launches)==1 and startup.sequence<launches[0].sequence and
        launches[0].data()["result"]!=0 and launches[0].data()["detail"].get("inherit_handles")==1,
        "source inheritance was not supplied to the actual suspended observer launch")
    nul=[row for row in apis if row.data()["name"]=="GetFileType"]
    _require(len(nul)==1 and (nul[0].data()["role"],nul[0].data()["phase"],nul[0].data()["result"])==
        ("stdin_original","channel",2) and nul[0].data()["handle"]==duplicates[0].data()["detail"]["original"] and
        nul[0].sequence<duplicates[0].sequence,"original input channel is not the separately opened NUL character device")
    return tuple(handles)


def _outer_bounds(frames,apis,core):
    launches=[r for r in apis if r.data()["name"]=="CreateProcessW" and r.data()["role"]=="observer"]
    _require(len(launches)==1,"unique original suspended observer launch required")
    launch=launches[0];detail=launch.data()["detail"]
    _exact(detail,("flags","inherit_handles","command","desktop","launch_anchor"),"original observer launch arguments")
    anchor=_exact(detail["launch_anchor"],("result","error","tick"),"original unchanged outer launch QPC")
    _require(anchor["result"]!=0 and 0<anchor["tick"]<=launch.data()["begin"]["tick"] and detail["flags"]==0x08080404 and
        detail["inherit_handles"]==1 and detail["desktop"]=="ClashLoaderV3_"+core["run_id"],"original suspended private-desktop launch differs")
    waits=[r for r in apis if r.data()["name"] in ("WaitForMultipleObjects","WaitForSingleObject") and
        r.data()["phase"] in ("gate","natural_finish")]
    _require(len(waits)==2 and tuple(r.data()["name"] for r in waits)==("WaitForMultipleObjects","WaitForSingleObject"),
        "both original unchanged outer deadline waits required")
    for row in waits:
        value=row.data();sample=_exact(value["detail"]["timeout_counter"],("result","error","tick"),"original outer timeout QPC")
        _require(sample["result"]!=0 and anchor["tick"]<=sample["tick"]<=value["begin"]["tick"] and
            value["end"]["tick"]<=anchor["tick"]+35*core["frequency"] and
            value["detail"]["timeout_ms"]==((35*core["frequency"]-(sample["tick"]-anchor["tick"]))*1000)//core["frequency"],
            "original fixed35s timeout arithmetic/order differs")
    finishes=[r for r in frames if r.operation=="outer_finish_bound"]
    _require(len(finishes)==1 and waits[-1].sequence<finishes[0].sequence and
        waits[-1].data()["end"]["tick"]<=finishes[0].data()["tick"]<=anchor["tick"]+35*core["frequency"],
        "original outer physical completion missed unchanged launch35s bound")


def _joined_seal(originals):
    return tuple((_sha(getattr(originals,row.name)),len(getattr(originals,row.name))) for row in fields(JoinedOriginals))


def _outer_identities(observed,core,state):
    """The summary identity is checked against its five untouched API packets."""
    apis=observed["apis"];identities=observed["identities"]
    for (role,phase),(row,value) in identities.items():
        relevant=[r for r in apis if r.sequence<row.sequence][-5:]
        _require(tuple(r.data()["name"] for r in relevant)==("GetProcessId","QueryFullProcessImageNameW",
            "GetProcessTimes","WaitForSingleObject","GetExitCodeProcess"),"complete original process identity cohort required")
        _require(all(r.data()["role"]==role and r.data()["phase"]==phase for r in relevant),
                 "original process role/phase cohort differs")
        pid,path,times,wait,exit=relevant
        handle=pid.data()["handle"]
        _require(handle>0 and all(r.data()["handle"]==handle for r in relevant),"retained process handle changed within cohort")
        chars=path.data()["returned"]
        _integer(chars,1,32767)
        _require(len(path.raw)==65536 and len(times.raw)==32 and len(exit.raw)==4,"whole original generation buffers required")
        original_path=path.raw[:chars*2].decode("utf-16le","strict")
        native_times=struct.unpack("<4Q",times.raw)
        _require(value["pid"]==pid.data()["result"] and value["creation"]==native_times[0] and
                 value["exit_time"]==native_times[1] and value["wait"]==wait.data()["result"] and
                 value["exit_code"]==struct.unpack("<I",exit.raw)[0] and value["path"]==original_path.lower(),
                 "original identity summary differs from raw generation")
        _require(value["creation"]>0 and (value["wait"]==0 and value["exit_code"]!=259 and value["exit_time"]>=value["creation"]
                 if phase=="exit" else value["wait"]==258 and value["exit_code"]==259 and value["exit_time"]==0),
                 "original process liveness/exit differs")
        path_name={"caller":"caller","outer":"outer","observer":"observer","target":"candidate"}.get(role)
        _require(path_name is not None and value["path"]==core["paths"][path_name].lower(),"source actor file path differs")
        digest=core["hashes"][role] if role in ("caller","outer") else \
               (_sha(state["observer_binary"]) if role=="observer" else _sha(state["candidate"]))
        _require(value["sha256"]==digest,"source actor file bytes differ")
        parent_role={"outer":"caller","observer":"outer","target":"observer"}.get(role)
        if parent_role:
            parent=identities[(parent_role,"startup")][1]
            _require((value["parent_pid"],value["parent_creation"])==(parent["pid"],parent["creation"]),
                     "original parent generation differs")
        _require(value["parent_scope"]==("fresh_snapshot" if phase=="startup" else "previously_proved_retained_generation"),
                 "original ancestry scope differs")
        if role in ("caller","outer"):
            _require((value["pid"],value["creation"])==(core[role+"_pid"],core[role+"_creation"]),
                     "source-issued caller/outer generation differs")
    for role in ("observer","target"):
        before=identities[(role,"adopt_before")][1];after=identities[(role,"adopt_after")][1]
        _require((before["pid"],before["creation"],before["path"],before["sha256"])==
                 (after["pid"],after["creation"],after["path"],after["sha256"]),"original adoption generation changed")
    _outer_ancestry(observed)


def _outer_ancestry(observed):
    identities=observed["identities"];apis=observed["apis"]
    cohorts=[r for r in apis if r.data()["name"]=="Process32FirstW/Process32NextW"]
    _require(len(cohorts)==3,"three fixed original parent query cohorts required")
    for role,parent_role in (("outer","caller"),("observer","outer"),("target","observer")):
        phase="adopt_before" if role=="target" else "startup"
        summary,value=identities[(role,phase)];parent=identities[(parent_role,"startup")][1]
        matches=[r for r in cohorts if r.data()["detail"]==dict(pid=value["pid"])]
        _require(len(matches)==1,"unique source-bound original parent query required")
        row=matches[0];found=[]
        _require(len(row.raw)%576==0 and 1<=len(row.raw)//576<=4096,"whole original parent cohort required")
        for offset in range(0,len(row.raw),576):
            result,error,size,pid=struct.unpack_from("<iIII",row.raw,offset)
            _require(size==568 and (result==1 and error==0 if offset+576<len(row.raw) else result==0 and error==18),
                     "original full parent cohort terminal/row failed")
            if result and pid==value["pid"]:found.append(struct.unpack_from("<I",row.raw,offset+40)[0])
        _require(found==[parent["pid"]],"raw original parent PID missing/duplicated/substituted")
        if role=="target":_require(row.sequence<summary.sequence,"target raw parent query must precede live adoption summary")
        else:
            future=[r for r in apis if r.sequence>row.sequence and r.data()["name"]==("CreateProcessW" if role=="outer" else "ResumeThread")]
            _require(summary.sequence<row.sequence and future,"raw parent query must follow summary and precede child continuation")


def _observer_schemas(frames,v2,helpers):
    schemas={**helpers.STARTUP_SCHEMAS,**helpers.COLLECTOR_SCHEMAS,**v2.EXTRA_SCHEMAS,
        **GATE_FIELDS,"generation_capacity":CAPACITY_FIELDS,"generation_parent_capacity":PARENT_FIELDS,
        "fixture_close_challenge":("return","error"),"fixture_close_challenge_event":("return","error")}
    schemas.pop("read_virtual",None)
    for row in frames:
        _io(row);_require(row.operation in schemas,"unknown source observer operation")
        _wire_scalars(row.data(),allowed_bools={"comparison_result":("comparison_called","post_qpc_called"),
            "error":("retention_debt",)}.get(row.operation,()))
        if row.operation=="gate_wait_before":_exact(row.data(),("epoch_id","frequency_hz","tick","frequency_native_return",
            "frequency_native_error","counter_native_return","counter_native_error"),"original gate QPC")
        elif schemas[row.operation] is not None:_exact(row.data(),schemas[row.operation],"original observer "+row.operation)
        if row.operation=="output":
            data=row.data();_integer(data["mask"])
            text=helpers._hex(data["text_hex"],32768,"original output callback")
            _require(text and text[-1]==0 and b"\0" not in text[:-1],"whole original output C-string required")
        fixed_raw={"inherited_flags":4,"cleared_flags":4,"bootstrap":32864,"gate_nonce":16,"gate_generation":32,
            "gate_file_info":52,"gate_file_path":65536,"challenge_write":576,"adoption_read":576,
            "comparison_result":64,"generation_capacity":65536}
        if row.operation in fixed_raw:_require(len(row.raw)==fixed_raw[row.operation],"whole original observer buffer size differs")
        elif row.operation not in ("read_virtual_capacity","generation_parent_capacity","native_failure"):
            _require(not row.raw,"unexpected original observer raw bytes cannot be ignored")


def _gate_pair(challenge,adoption,core,generator):
    before=generator.parse_gate(challenge,kind=1);after=generator.parse_gate(adoption,kind=2)
    _require(before["ids"]==(core["run_id"],core["checkpoint_id"],core["epoch_id"]),"source gate identifiers differ")
    _require((before["frequency"],before["origin"])==(core["frequency"],core["origin"]),"source gate clock origin differs")
    _require(before["hashes"][:6]==tuple(core["hashes"][name] for name in
        ("request","payload","candidate","probe","caller","outer")) and before["hashes"][7]==core["hashes"]["producer"],
        "source-issued gate bindings differ")
    expected=bytearray(challenge);struct.pack_into("<I",expected,12,2)
    expected[192:216]=adoption[192:216];expected[512:544]=bytes.fromhex(_sha(challenge));expected[544:]=adoption[544:]
    _require(bytes(expected)==adoption and after["hashes"][9]==_sha(challenge),
             "original gate nonce/generation/epoch/bytes changed across adoption")
    return before,after


def _binding(value,facts,metadata,core):
    predecessor=facts.predecessor_facts
    size=struct.unpack_from("<I",facts.expected_payload,12)[0]
    expected=dict(request_sha256=_sha(facts.request_bytes),expected_payload_sha256=_sha(facts.expected_payload),
        metadata_hex=facts.expected_payload[48:48+size].hex(),payload_bytes=len(facts.expected_payload),
        chunk_count=len(predecessor.descriptors),highlow_count=len(predecessor.fixups),
        request_path_utf16le=(core["paths"]["request"]+"\0").encode("utf-16le").hex(),
        payload_path_utf16le=(core["paths"]["payload"]+"\0").encode("utf-16le").hex())
    _require(all(type(value[name]) is type(wanted) and value[name]==wanted for name,wanted in expected.items()),
             "original immutable payload/request/path binding differs")
    buffers=(facts.request_bytes,facts.request_bytes[:-32],facts.expected_payload,facts.expected_payload[:-32])
    _require(type(value["hash_receipts"]) is list and len(value["hash_receipts"])==4,"four original hash operations required")
    for receipt,raw in zip(value["hash_receipts"],buffers):
        _exact(receipt,("input_bytes","open_status","hash_status","close_status","digest_hex"),"original input hash")
        _require(type(receipt["input_bytes"]) is int and receipt["input_bytes"]==len(raw) and receipt["digest_hex"]==_sha(raw),
                 "original hashed input/length/digest differs")
        for name in ("open_status","hash_status","close_status"):
            _integer(receipt[name],-2**31,0xffffffff);_require(receipt[name]==0,"original input hash failed")


def _observer_success(original_frames,state,core,generator,v2,helpers,outer):
    metadata=_exact(_json(state["facts"].metadata_json.encode("ascii")),v2.FACT_FIELDS,"source-issued predecessor facts")
    frames,capacity_handles=_capacity_groups(tuple(r for r in original_frames if r.operation!="output"))
    _require(len(OBSERVER_MAGIC)+sum(32+len(r.metadata) for r in original_frames)<=64*1024**2 and
             sum(len(r.raw) for r in original_frames)<=512*1024**2,"observer failure-only capacity cannot complete")
    _require(frames[0].operation=="archive_magic_io","original observer magic receipt missing")
    magic=frames[0].data();_require(magic["requested"]==magic["returned"]==8 and magic["write_return"]!=0 and
        magic["flush_return"]!=0,"original observer magic IO failed")
    index=1;inherited={}
    for role in range(7):
        rows=frames[index:index+3];index+=3
        _require(tuple(r.operation for r in rows)==("inherited_flags","clear_inherit","cleared_flags"),
                 "original seven inherited-role flag sequence required")
        handle=rows[0].data()["handle"]
        _integer(handle,1,0xfffffffe)
        for row in rows:
            value=row.data();_require(type(value["role"]) is int and value["role"]==role and value["handle"]==handle
                and type(value["return"]) is int and value["return"]!=0 and value["error"]==0,"original inherited handle operation failed/differs")
        _require(len(rows[0].raw)==len(rows[2].raw)==4 and
            struct.unpack("<I",rows[0].raw)[0]==rows[0].data()["flags"] and rows[0].data()["flags"]&1 and
            struct.unpack("<I",rows[2].raw)[0]==rows[2].data()["flags"] and not rows[2].data()["flags"]&1 and not rows[1].raw,
            "original inherit flag buffers differ or target leak")
        inherited[role]=handle
    _require(len(set(inherited.values()))==7,"original inherited roles alias")
    _outer_inheritance(outer,inherited)
    _require(frames[index].operation=="bootstrap" and frames[index].raw==state["bootstrap"] and
        frames[index].data()==dict(bytes=len(state["bootstrap"])),"original whole observer bootstrap differs")
    index+=1
    for raw in (state["core"],state["bootstrap"][:-32]):
        row=frames[index];index+=1
        _require(row.operation=="gate_hash","original bootstrap hash receipt missing")
        _hash_gate(row,raw)
    _require(tuple(r.operation for r in frames[index:index+4])==("expected_binding","invocation","comparison_begin","origin"),
             "original observer input/startup order differs")
    _binding(frames[index].data(),state["facts"],metadata,core)
    count=len(state["facts"].predecessor_facts.descriptors)+1
    _require(frames[index+2].data()==dict(expected_payload_sha256=_sha(state["facts"].expected_payload),read_count=count,
        scope=v2.IMMUTABLE_SCOPE),"original comparison begin inventory differs")
    control=frames[index+1:index+2]+frames[index+3:]
    closes=tuple(r for r in control if r.operation=="inherited_close")
    _require(tuple(r.data()["role"] for r in closes)==(0,3,4,5,6) and
             all(r.data()["handle"]==inherited[r.data()["role"]] and type(r.data()["return"]) is int and
                 r.data()["return"]!=0 and r.data()["error"]==0 and not r.raw for r in closes),
             "original five inherited receiver closes missing/reordered/failed")
    _require(tuple(r.operation for r in control[-8:])==("stop","cleanup")+("inherited_close",)*5+("finish",),
             "original inherited closes must follow Session cleanup and precede finish")
    control=tuple(r for r in control if r.operation!="inherited_close")
    external=SimpleNamespace(request_sha256=_sha(state["facts"].request_bytes),candidate_file_sha256=_sha(state["candidate"]),
        host_file_sha256=_sha(state["observer_binary"]),controller_pid=core["outer_pid"],run_id=core["run_id"],
        checkpoint_id=core["checkpoint_id"],epoch_id=core["epoch_id"],observed_host_exit_code=0)
    create,event,peb,initial,held,startup_owner,index,target_path=helpers._v2_startup(control,external,metadata)
    _require(target_path==core["paths"]["candidate"] and create["module_size"]==metadata["image_size"],
             "original target launch/image extent differs")
    base=create["base_offset"];_integer(base,0x10000,helpers.image.USER_LIMIT-metadata["image_size"])
    _require(base%0x10000==0,"original image base alignment differs")
    identities={}
    for role in ("controller","debugger","target"):
        value=startup_owner.data()[role]
        identities[role]=helpers.image.Generation(value["pid"],value["creation_filetime"],
            bytes.fromhex(value["image_path_utf16le"]).decode("utf-16le"),value["image_sha256"])
    _require((identities["controller"].pid,identities["controller"].creation_filetime,identities["controller"].image_sha256)==
        (core["outer_pid"],core["outer_creation"],_sha(state["outer_binary"])) and
        identities["debugger"].image_sha256==_sha(state["observer_binary"]) and identities["target"].image_sha256==_sha(state["candidate"]),
        "source-bound retained observer actor identities differ")
    owner_tid=startup_owner.data()["native_owner_tid"];_integer(owner_tid,1)
    startup_handles=capacity_handles[startup_owner.sequence]
    owners=[];calls=control[index:-3];position=0;previous=held.tick
    def take(operation):
        nonlocal position
        _require(position<len(calls) and calls[position].operation==operation,"required V3 operation absent/reordered: "+operation)
        row=calls[position];position+=1;return row
    def clock(value):
        nonlocal previous
        sample=helpers._qpc(value,metadata)
        _require(previous<=sample.tick<=initial.tick+20*core["frequency"],"original QPC order/unchanged earliest20s failed")
        previous=sample.tick;return sample
    def counter():return clock(take("counter").data())
    def owner(row):
        value=row.data()
        _require((value["run_id"],value["checkpoint_id"],value["clock_epoch"])==
            (core["run_id"],core["checkpoint_id"],core["epoch_id"]) and
            all(type(value[name]) is int and value[name]==0 for name in ("probe_sequence","breakpoint_sequence","command_sequence")) and
            type(value["native_owner_tid"]) is type(value["current_native_tid"]) is int and
            value["native_owner_tid"]==value["current_native_tid"]==owner_tid,"original closed owner/thread sequence differs")
        for role,parent in (("controller",None),("debugger",identities["controller"]),("target",identities["debugger"])):
            helpers._generation(value[role],identities[role],parent)
        _require(row.sequence in capacity_handles,"owner lacks full original query capacities");owners.append(row)
        _require(capacity_handles[row.sequence]==startup_handles,"retained native role handle changed across owner boundaries")
    def phase():
        owner(take("owner"));counter()
        for name,wanted in zip(helpers.image.PHASE_QUERY_NAMES,(6,create["pid"],create["tid"],event["engine_pid"],event["engine_tid"])):
            counter();value=take("query").data();query=helpers.image.NativeQuery(**value)
            _require((query.name,query.hresult,query.value)==(name,0,wanted),"original selected engine phase failed/differs");counter()
        counter();_require(take("GetNumberBreakpoints").data()==dict(hresult=0,count=0),"original breakpoint query differs")
        counter();counter();value=take("pointer64").data()
        _require(type(value["hresult"]) is int and value["hresult"]==1,"original x86 pointer query failed");counter();owner(take("owner"))
    owner(startup_owner);counter()
    nonce=take("gate_nonce");_require(nonce.data()["status"]==0 and type(nonce.data()["status"]) is int and len(nonce.raw)==16 and any(nonce.raw),"original challenge RNG failed")
    opened=take("gate_open_caller").data();_require(opened["return"]>0 and opened["error"]==0 and opened["pid"]==core["caller_pid"],"original gate caller open failed")
    expected_generations=((core["caller_pid"],core["caller_creation"]),(core["outer_pid"],core["outer_creation"]),
        (identities["debugger"].pid,identities["debugger"].creation_filetime),(identities["target"].pid,identities["target"].creation_filetime))
    gate_handles=[]
    for role,wanted in zip(("caller","outer","observer","target"),expected_generations):
        gate_handles.append(_gate_generation(take("gate_generation"),role,wanted))
    _require(len(set(gate_handles))==4 and gate_handles[0]==opened["return"],"original gate role handles differ/alias")
    _require(tuple(gate_handles[1:])==startup_handles,"gate uses a different retained original owner handle cohort")
    _hash_gate(take("gate_hash"),state["bootstrap"])
    for role,handle,path_name in (("challenge_writer",inherited[3],"challenge"),("adoption_reader",inherited[4],"adoption")):
        info=take("gate_file_info");path=take("gate_file_path");value=info.data();text=path.data()
        _require(value["role"]==text["role"]==role and value["handle"]==text["handle"]==handle and value["return"]!=0
            and value["error"]==text["error"]==0 and len(info.raw)==52 and not struct.unpack_from("<I",info.raw)[0]&0x410,
            "original gate file identity/reparse failed")
        _integer(text["chars"],1,32767);_require(len(path.raw)==65536,"whole original gate path capacity required")
        observed=path.raw[:text["chars"]*2].decode("utf-16le");observed=observed[4:] if observed.startswith("\\\\?\\") else observed
        _require(observed.lower()==core["paths"][path_name].lower(),"original channel path differs")
        outer_info=[r for r in outer["apis"] if r.data()["name"]=="GetFileInformationByHandle" and r.data()["role"]==role]
        _require(outer_info and _file_id(info.raw)==_file_id(outer_info[0].raw),"original separately opened channel file identity differs")
    phase();phase_ref=owners[-1].sequence
    challenge_hash=take("gate_hash");challenge=take("challenge_write");_hash_gate(challenge_hash,challenge.raw[:544])
    _require(len(challenge.raw)==576,"whole original challenge capacity required")
    _write_gate(challenge.data(),576);counter()
    signal=take("challenge_signal").data();_require(type(signal["return"]) is int and signal["return"]!=0 and signal["error"]==0,"original challenge signal failed")
    before_wait=clock(take("gate_wait_before").data());wait=take("adoption_wait").data()
    _require(wait=={"return":0,"error":0,"timeout_ms":((20*core["frequency"]-(before_wait.tick-initial.tick))*1000)//core["frequency"]},"original adoption wait/unchanged timeout differs")
    counter();adoption=take("adoption_read");_read_gate(adoption.data(),adoption.raw)
    _hash_gate(take("gate_hash"),adoption.raw[:544]);_hash_gate(take("gate_hash"),challenge.raw)
    first,second=_gate_pair(challenge.raw,adoption.raw,core,generator)
    _require(first["nonce"]==nonce.raw and first["generations"]==expected_generations and first["initial_tick"]==initial.tick and
        first["sequences"][:3]==(held.data()["initial_exception_sequence"] if isinstance(held,OriginalFrame) else
        next(r.data()["initial_exception_sequence"] for r in control if r.operation=="held"),
        next(r.sequence for r in control if r.operation=="callback_create"),phase_ref) and
        first["hashes"][6]==_sha(state["observer_binary"]) and first["hashes"][8]==_sha(state["bootstrap"]),
        "original challenge earliest anchor/native/source references differ")
    _outer_gate_join(first,second,challenge,adoption,outer,core)
    for role,wanted,handle in zip(("caller","outer","observer","target"),expected_generations,gate_handles):
        _require(_gate_generation(take("gate_generation"),role,wanted)==handle,"original post-adoption retained handle changed")
    phase();counter()
    closed=take("gate_close_caller").data()
    _require(closed["handle"]==opened["return"] and type(closed["return"]) is int and closed["return"]!=0 and closed["error"]==0,
        "original new gate caller handle close missing/failed/differs")
    gate_complete=take("gate_complete")
    _require(gate_complete.data()==dict(challenge_sha256=_sha(challenge.raw),outer_archive_id=core["archives"][1]),"original gate completion differs")
    phase();expected_chunks=state["facts"].predecessor_facts.model_chunks(base);compared=0;reads=[]
    for ordinal in range(count):
        phase();counter();row=take("read_virtual_capacity");value=row.data()
        address,expected=(peb["address"]+8,struct.pack("<I",base)) if ordinal==0 else expected_chunks[ordinal-1]
        _require(value==dict(ordinal=ordinal,address=address,requested_bytes=len(expected),hresult=0,returned_bytes=len(expected))
            and row.raw==expected,"original full immutable capacity read differs/failed/partial")
        counter();phase();before=take("comparison_counter")
        _require(type(before.data()["ordinal"]) is int and before.data()["ordinal"]==ordinal,"original comparison ordinal differs")
        start=clock(before.data()["qpc"]);result=take("comparison_result");value=result.data()
        _require(value["comparison_called"] is True and value["post_qpc_called"] is True and
            (value["read_sequence"],value["before_sequence"])==(row.sequence,before.sequence),"original comparison sequence/call differs")
        end=clock(value["post_qpc"])
        expected_result=dict(version=1,ordinal=ordinal,descriptor_index=0xffffffff if ordinal==0 else ordinal-1,
            read_frame_sequence=row.sequence,requested_bytes=len(expected),returned_bytes=len(expected),comparison_status=0,
            mismatch_count=0,first_mismatch=0xffffffff,applied_highlow_count=0 if ordinal==0 else state["facts"].predecessor_facts.descriptors[ordinal-1][5],
            address=address,before_tick=start.tick,after_tick=end.tick)
        _require(v2.decode_comparison_record(result.raw)==expected_result,"original comparison result differs from raw bytes/source fixups")
        compared+=len(expected);reads.append(row)
    phase();_require(take("comparison_complete").data()==dict(read_count=count,result_count=count,compared_bytes=compared,
        expected_payload_sha256=_sha(state["facts"].expected_payload)),"original complete comparison inventory differs")
    counter();_require(position==len(calls),"extra original V3 operations after comparison")
    cleanup=helpers._v2_cleanup(control,metadata,previous,initial)
    _require((cleanup["target_pid"],cleanup["target_creation_filetime"])==expected_generations[3],"original cleanup target generation differs")
    finish=original_frames[-1].data()
    _require(finish==dict(status="complete",frame_count=len(original_frames)-1,raw_bytes=sum(len(r.raw) for r in original_frames[:-1]),
        metadata_bytes=8+sum(32+len(r.metadata) for r in original_frames[:-1]),comparison_scope=v2.SCOPE),"original observer finish inventory/status differs")
    return dict(read_count=len(reads),required=count,compared_bytes=compared,gate_complete_sequence=gate_complete.sequence,
        first_read_sequence=reads[0].sequence,initial_tick=initial.tick,actor_references=[
            dict(actor=actor,archive_id=core["archives"][0 if actor=="observer" else 1],sequence=seq)
            for actor,seq in zip(generator.ACTORS,second["sequences"])])


def _wire_scalars(value,*,allowed_bools=(),path=()):
    if type(value) is dict:
        for key,child in value.items():_wire_scalars(child,allowed_bools=allowed_bools,path=path+(key,))
    elif type(value) is list:
        for index,child in enumerate(value):_wire_scalars(child,allowed_bools=allowed_bools,path=path+(index,))
    elif type(value) is bool:_require(len(path)==1 and path[0] in allowed_bools,"boolean cannot replace original native integer")
    elif type(value) is int:_integer(value,-2**63,2**64-1)
    else:_require(value is None or type(value) is str,"unsupported native wire scalar")


def _file_id(raw):
    _require(len(raw)==52,"complete BY_HANDLE_FILE_INFORMATION required")
    return struct.unpack_from("<I",raw,28)[0],struct.unpack_from("<I",raw,44)[0],struct.unpack_from("<I",raw,48)[0]


def _hash_gate(row,raw):
    value=row.data();_exact(value,("input_bytes","open_status","hash_status","close_status","digest_hex"),"original gate hash")
    _require(type(value["input_bytes"]) is int and value["input_bytes"]==len(raw) and value["digest_hex"]==_sha(raw),
             "original gate hash input/digest differs")
    for name in ("open_status","hash_status","close_status"):
        _integer(value[name],-2**31,0xffffffff);_require(value[name]==0,"original gate hash failed")
    _require(not row.raw,"original hash receipt has unexpected raw buffer")


def _gate_generation(row,role,wanted):
    value=row.data();_exact(value,GATE_FIELDS["gate_generation"],"original gate generation")
    _require(len(row.raw)==32,"whole original gate FILETIME capacity required")
    created,ended,kernel,user=struct.unpack("<4Q",row.raw)
    _require(value["role"]==role and (value["pid"],created)==wanted and value["pid_error"]==0 and ended==0
        and type(value["times_return"]) is type(value["exit_return"]) is int and value["times_return"]!=0 and value["times_error"]==0
        and value["wait"]==258 and value["wait_error"]==0 and value["exit_return"]!=0 and value["exit_error"]==0 and value["exit_code"]==259,
        "original gate retained generation/liveness failed/differs")
    return _integer(value["handle"],1,0xfffffffe)


def _write_gate(value,size):
    _exact(value,GATE_FIELDS["challenge_write"],"original complete challenge write")
    _require(type(value["write_return"]) is type(value["flush_return"]) is int and value["write_return"]!=0 and value["flush_return"]!=0
        and value["requested"]==value["returned"]==size,"original complete challenge write/flush failed")


def _read_gate(value,raw):
    _exact(value,GATE_FIELDS["adoption_read"],"original complete adoption read")
    _require(type(value["return"]) is int and value["return"]!=0 and value["requested"]==value["returned"]==len(raw)==576,
        "original whole adoption read failed/partial")


def _outer_gate_join(first,second,challenge,adoption,outer,core):
    _require(outer["channel"] is not None and first["sequences"][6]==outer["channel"].sequence,
        "actor-qualified outer channel reference missing/differs")
    _require(outer["adoption"] is not None and outer["adoption"].raw==adoption.raw and
        outer["adoption"].data()==dict(challenge_sha256=_sha(challenge.raw),target_creation=first["generations"][3][1]),
        "original actor adoption bytes differ")
    observer_before=outer["identities"][("observer","adopt_before")][0]
    target_after=outer["identities"][("target","adopt_after")][0]
    members=[row for row in outer["apis"] if row.data()["name"]=="IsProcessInJob" and
        row.data()["role"]=="target" and row.data()["phase"]=="adoption"]
    _require(len(members)==1 and second["sequences"][3:6]==(observer_before.sequence,target_after.sequence,members[0].sequence),
        "actor-qualified live adoption/member references missing/reordered/substituted")
    _require(observer_before.sequence<members[0].sequence<target_after.sequence<outer["adoption"].sequence,
        "original outer live adoption operation order differs")
    for role,expected in zip(("caller","outer","observer","target"),first["generations"]):
        phase="startup" if role in ("caller","outer") else "adopt_before"
        value=outer["identities"][(role,phase)][1]
        _require((value["pid"],value["creation"])==expected,"joined original actor generation differs")
    written=[row for row in outer["apis"] if row.data()["name"]=="WriteFile" and
        (row.data()["role"],row.data()["phase"])==("adoption_writer","adoption")]
    read=[row for row in outer["apis"] if row.data()["name"]=="ReadFile" and
        (row.data()["role"],row.data()["phase"])==("challenge_reader","challenge")]
    _require(len(written)==len(read)==1 and written[0].raw==adoption.raw and read[0].raw==challenge.raw and
        read[0].sequence<observer_before.sequence<target_after.sequence<written[0].sequence,
        "original separate-reader/complete-writer challenge/adoption bytes or order differ")


def _failure_kinds(observer,outer,*,v2,generator,core,state):
    """Classify only complete original failed packets; a mode is no evidence."""
    kinds=set();challenge=next((r for r in observer if r.operation=="challenge_write"),None)
    for row in observer:
        value=row.data()
        if row.operation=="challenge_write":
            _require(len(row.raw)==576 and value["requested"]==576,"complete failed challenge capacity required")
            if value["write_return"]==0 or value["returned"]!=576 or value["flush_return"]==0:kinds.add(SYNTHETIC_FAILURES[1])
        elif row.operation=="challenge_signal" and value["return"]==0:kinds.add(SYNTHETIC_FAILURES[2])
        elif row.operation=="adoption_wait" and value["return"]==258:
            _require(0<=value["timeout_ms"]<=20000,"original unchanged adoption timeout required");kinds.add(SYNTHETIC_FAILURES[8])
        elif row.operation=="inherited_flags" and (value["return"]==0 or not value["flags"]&1):
            _require(len(row.raw)==4 and 0<=value["role"]<7,"complete original failed inheritance buffer required")
            kinds.add(SYNTHETIC_FAILURES[9])
        elif row.operation=="read_virtual_capacity":
            _require(type(value["requested_bytes"]) is int and len(row.raw)==value["requested_bytes"]<=65539,
                     "complete original failed immutable-read capacity required")
            if value["hresult"]!=0 or value["returned_bytes"]!=value["requested_bytes"]:kinds.add(SYNTHETIC_FAILURES[4])
            elif value.get("ordinal")==0:
                creates=[entry for entry in observer if entry.operation=="callback_create" and entry.sequence<row.sequence]
                pebs=[entry for entry in observer if entry.operation=="peb" and entry.sequence<row.sequence]
                _require(len(creates)==len(pebs)==1 and len(row.raw)==4,
                    "original full PEB read failure needs unique prior callback and PEB observations")
                base=creates[0].data()["base_offset"];peb=pebs[0].data()
                _integer(base,0x10000,0x7ffe0000);_integer(peb["address"],0x10000,0x7ffe0000-12)
                _require(type(peb["hresult"]) is int and peb["hresult"]==0 and base%0x10000==0,
                    "original callback base or PEB query unavailable")
                if value["address"]!=peb["address"]+8 or row.raw!=struct.pack("<I",base):
                    kinds.add(SYNTHETIC_FAILURES[4])
        elif row.operation=="comparison_result":
            record=v2.decode_comparison_record(row.raw)
            read=next((r for r in observer if r.sequence==value["read_sequence"] and r.operation=="read_virtual_capacity"),None)
            create=next((r for r in observer if r.operation=="callback_create"),None)
            before=next((r for r in observer if r.sequence==value["before_sequence"] and r.operation=="comparison_counter"),None)
            _require(read is not None and create is not None and before is not None and read.sequence<before.sequence<row.sequence,
                     "complete failed comparison read/clock ancestry required")
            ordinal=read.data()["ordinal"]
            chunks=state["facts"].predecessor_facts.model_chunks(create.data()["base_offset"])
            _integer(ordinal,0,len(chunks))
            expected=struct.pack("<I",create.data()["base_offset"]) if ordinal==0 else chunks[ordinal-1][1]
            mismatches=[index for index,(actual,wanted) in enumerate(zip(read.raw,expected)) if actual!=wanted]
            _require(len(read.raw)==len(expected) and record["read_frame_sequence"]==read.sequence and
                record["ordinal"]==ordinal and record["requested_bytes"]==record["returned_bytes"]==len(expected) and
                record["mismatch_count"]==len(mismatches) and record["first_mismatch"]==(mismatches[0] if mismatches else 0xffffffff)
                and record["comparison_status"]==int(bool(mismatches)),"failed comparison claim differs from exact original bytes")
            if mismatches:kinds.add(SYNTHETIC_FAILURES[4])
        elif row.operation=="adoption_read" and challenge is not None and len(row.raw)==576 and value["return"]!=0 and value["returned"]==576:
            first=generator.parse_gate(challenge.raw,kind=1);second=generator.parse_gate(row.raw,kind=2)
            if first["generations"]!=second["generations"]:kinds.add(SYNTHETIC_FAILURES[6])
            if first["nonce"]!=second["nonce"]:kinds.add(SYNTHETIC_FAILURES[7])
    for row in outer:
        if row.operation!="api":continue
        value=row.data()
        _exact(value,("name","role","phase","handle","result","error","requested","returned","length_kind","begin","end","detail"),
               "complete original failed outer API")
        _wire_scalars(value)
        if value["name"]=="OpenProcess" and value["role"]=="target" and value["result"]==0 and value["handle"]==0:
            kinds.add(SYNTHETIC_FAILURES[3])
        elif value["name"]=="SetEvent" and value["role"]=="adoption_event" and value["result"]==0:kinds.add(SYNTHETIC_FAILURES[5])
        elif value["name"]=="TerminateJobObject" and value["role"]=="fixture_invalid_job" and value["result"]==0 and value["handle"]==0:
            kinds.add(SYNTHETIC_FAILURES[10])
        elif value["name"]=="CreateProcessW" and value["role"]=="observer" and value["result"]==0:
            changed=[r for r in outer if r.sequence<row.sequence and r.operation=="api" and
                r.data()["name"]=="SetHandleInformation" and r.data()["role"]=="adoption_event_inherited" and r.data()["phase"]=="fixture"]
            if len(changed)==1:kinds.add(SYNTHETIC_FAILURES[9])
    return sorted(kinds)


def _stderr(original,actor,frames,core):
    """Complete original diagnostics stay independent of packet/main IO."""
    _require(type(original) is bytes,"whole original stderr bytes required")
    if len(original)>16*1024**2:return True
    try:lines=original.decode("ascii","strict").splitlines()
    except UnicodeError:return True
    debt=False;tails=[];reserves=0;magic=False;path_seen=False
    for line in lines:
        if actor=="observer" and line.startswith("ORIGINAL_OBSERVER_RESERVE "):
            match=re.fullmatch(r"ORIGINAL_OBSERVER_RESERVE return=(-?\d+) error=(\d+) available=(\d+) total=(\d+) free=(\d+) approved_peak=(\d+)",line)
            if match is None:debt=True;continue
            result,error,free,total,unused,peak=map(int,match.groups());reserves+=1
            if result==0 or peak!=core["peak"] or free-peak<=total//10:debt=True
        elif actor=="outer" and line.startswith("ORIGINAL_PREWRITE_RESERVE "):
            data=_json(line[len("ORIGINAL_PREWRITE_RESERVE "):].encode("ascii"))
            _exact(data,("return","error","free","total","unused","required_peak"),"original outer reserve")
            _wire_scalars(data);reserves+=1
            if data["return"]==0 or data["required_peak"]!=core["peak"] or data["free"]-core["peak"]<=data["total"]//10:debt=True
        elif actor=="outer" and line.startswith("ORIGINAL_RECEIPT_TAIL "):
            data=_json(line[len("ORIGINAL_RECEIPT_TAIL "):].encode("ascii"))
            _exact(data,("sequence","write_return","write_error","requested","returned","flush_return","flush_error"),"original outer receipt tail")
            _wire_scalars(data);tails.append(data["sequence"])
            if data["write_return"]==0 or data["flush_return"]==0 or data["requested"]!=24 or data["returned"]!=24:debt=True
        elif actor=="outer" and line.startswith("ORIGINAL_MAGIC_IO "):
            body,sep,raw=line[len("ORIGINAL_MAGIC_IO "):].partition(" raw=");_require(sep,"original outer magic capacity required")
            data=_json(body.encode("ascii"));_exact(data,("type","type_error","write_return","write_error","requested","returned","flush_return","flush_error"),"original outer magic IO")
            _wire_scalars(data)
            _require(not magic,"duplicate original outer magic IO");magic=True
            if raw!=OUTER_MAGIC.hex() or data["type"]!=1 or data["write_return"]==0 or data["flush_return"]==0 or data["requested"]!=8 or data["returned"]!=8:debt=True
        elif actor=="outer" and line.startswith("ORIGINAL_ARCHIVE_PATH "):
            body,sep,raw=line[len("ORIGINAL_ARCHIVE_PATH "):].partition(" raw=");_require(sep,"whole original archive path capacity required")
            data=_json(body.encode("ascii"));_exact(data,("return","error","capacity"),"original archive path")
            capacity=_hex_original(raw,65536);_integer(data["return"],1,32767);_require(not path_seen,"duplicate original archive path");path_seen=True
            text=capacity[:data["return"]*2].decode("utf-16le");text=text[4:] if text.startswith("\\\\?\\") else text
            if data["capacity"]!=65536 or text.lower()!=core["paths"]["outer_archive"].lower():debt=True
        else:debt=True
    if actor=="observer":debt=debt or reserves==0
    else:debt=debt or not magic or not path_seen or reserves==0 or tails!=[r.sequence for r in frames]
    return bool(debt)


def _joined_protocol(originals,state,generator):
    rows=[];complete={};partial={}
    try:
        state["facts"].check_sources()
        _require(_joined_seal(originals)==state["original_seal"],"source-issued complete originals changed")
        core=generator.parse_core(state["core"])
        _require(state["bootstrap"]==state["core"]+bytes.fromhex(_sha(state["observer_binary"]))+
            bytes.fromhex(_sha(state["observer_source"]))+bytes.fromhex(_sha(state["bootstrap"][:-32])),"source-issued bootstrap observer binary/source seal differs")
        v2,helpers,sources=_fixed_helpers();_unchanged(sources)
        for actor in ("caller","outer","observer"):
            raw=getattr(originals,actor)
            try:frames=parse_frames(raw,actor=actor);partial[actor]=False
            except ArchiveError as error:
                # A source-issued truncated original can be reported only after
                # an independent matching complete failure packet is found.
                magic={"caller":CALLER_MAGIC,"outer":OUTER_MAGIC,"observer":OBSERVER_MAGIC}[actor]
                _require(("truncated" in str(error) or "complete bounded frame prefix" in str(error)) and error.frames
                    or len(raw)<8 and magic.startswith(raw),"foreign/malformed archive cannot be a failed native prefix")
                frames=error.frames;partial[actor]=True
            complete[actor]=bool(frames and frames[-1].operation=="finish" and not partial[actor])
            rows.append(tuple(frames))
        caller,outer,observer=rows
        _require(complete["caller"],"caller original terminal/closure stream missing")
        _caller_protocol(caller,state)
        _require(type(originals.caller_close_receipt) is bytes and len(originals.caller_close_receipt)<=CALLER_CLOSE_ORIGINAL_BYTES,
            "complete original caller close exceeds its explicit retention allowance")
        close=_json(originals.caller_close_receipt)
        _exact(close,("name","role","handle","result","error","serialization_scope","receipt_tail_prewrite_reserves"),"original caller journal close")
        _require(originals.caller_close_receipt==state["session"].caller_close_receipt and close["name"]=="CloseHandle" and
            close["role"]=="caller_archive" and close["serialization_scope"]=="retained_RAM_only_after_final_archive_packet",
            "caller close receipt was not native-session issued")
        _require(type(close["receipt_tail_prewrite_reserves"]) is list and
            close["receipt_tail_prewrite_reserves"]==state["session"].footer_reserves and
            len(close["receipt_tail_prewrite_reserves"])==len(caller),
            "every caller footer needs its separately retained original prewrite reserve")
        for sequence,receipt in enumerate(close["receipt_tail_prewrite_reserves"],1):
            _exact(receipt,("sequence","reserve"),"original caller footer reserve receipt")
            _require(type(receipt["sequence"]) is int and receipt["sequence"]==sequence,
                "caller footer reserve missing/duplicate/reordered")
            sample=_exact(receipt["reserve"],("result","error","free","total","unused","required_peak"),"original caller footer reserve")
            for name,value in sample.items():_integer(value,-2**31 if name=="result" else 0,2**63-1)
            _require(sample["result"]!=0 and sample["required_peak"]==state["session"].paths.approved_peak_bytes and
                sample["free"]-sample["required_peak"]>sample["total"]//10,
                "original caller footer reserve failed or differs")
        _observer_schemas(observer,v2,helpers)
        failures=_failure_kinds(observer,outer,v2=v2,generator=generator,core=core,state=state)
        outer_observed=_outer_protocol(outer,state,core,generator) if complete["outer"] else None
        stderr_debt=any((_stderr(originals.outer_stderr,"outer",outer,core),_stderr(originals.observer_stderr,"observer",observer,core)))
        sticky=bool(state["session"].failed or state["session"].debt or close["result"]==0 or
            any(r.operation in ("error","native_failure","rejected") for stream in rows for r in stream) or
            any(not value for value in complete.values()) or stderr_debt or
            (outer_observed is not None and outer_observed["failed"]) or
            (complete["observer"] and observer[-1].data()["status"]!="complete"))
        seen_reads=sum(r.operation=="read_virtual_capacity" for r in observer)
        count=len(state["facts"].predecessor_facts.descriptors)+1
        result=dict(scoped_composition_complete=False,immutable_read_count=seen_reads,required_read_count=count,
            live_adoption_before_first_read=False,original_failure_kinds=failures,retention_debt=bool(stderr_debt or not all(complete.values()) or state["session"].debt),
            unknown_partial=bool(not all(complete.values())),observer_archive_complete=complete["observer"],outer_archive_complete=complete["outer"],
            caller_archive_complete=complete["caller"],immutable_comparison_scope=v2.IMMUTABLE_SCOPE,
            original_artifacts={name:dict(sha256=_sha(getattr(originals,name)),bytes=len(getattr(originals,name))) for name in
                ("caller","outer","observer","observer_stderr","outer_stderr","caller_close_receipt")},
            producer_files={name:dict(path=str(state["session"].files[name]),sha256=_sha(raw),bytes=len(raw)) for name,raw in
                (("outer_source",state["outer_source"]),("outer",state["outer_binary"]),("observer_source",state["observer_source"]),
                 ("observer",state["observer_binary"]),("request",state["facts"].request_bytes),("payload",state["facts"].expected_payload),
                 ("bootstrap",state["bootstrap"]),("candidate",state["candidate"]))},
            receipt_tail_limit="Final journal close is retained RAM only; packet footer cannot attest its own append/flush.")
        if sticky:
            _require(failures,"failed or truncated join lacks an independently matching complete original failure packet")
        else:
            _require(not failures and outer_observed is not None,"a complete join cannot erase an original failed packet")
            _outer_identities(outer_observed,core,state)
            observed=_observer_success(observer,state,core,generator,v2,helpers,outer_observed)
            result.update(scoped_composition_complete=True,immutable_read_count=observed["read_count"],
                live_adoption_before_first_read=True,compared_bytes=observed["compared_bytes"],
                initial_tick=observed["initial_tick"],actor_references=observed["actor_references"])
        _unchanged(sources);state["facts"].check_sources()
        return result,tuple(rows)
    except ArchiveError as error:
        if error.originals is originals:raise
        raise ArchiveError(str(error),originals.observer,tuple(rows),originals=originals) from error
    except Exception as error:
        raise ArchiveError(type(error).__name__+": "+str(error),originals.observer,tuple(rows),originals=originals) from error


_IMPORTED_SOURCE_BYTES = SOURCE.read_bytes()
_IMPORTED_GENERATOR_BYTES = GENERATOR.read_bytes()


def _api_factory(_path=SOURCE,_raw=_IMPORTED_SOURCE_BYTES,_generator=GENERATOR,_generator_raw=_IMPORTED_GENERATOR_BYTES,
                 _read=Path.read_bytes,_parse=ast.parse,_walk=ast.walk,_assign=ast.Assign,_tuple=ast.Tuple,
                 _call=ast.Call,_name=ast.Name,_new=uuid.uuid4,_modules=sys.modules,_module=types.ModuleType,
                 _compile=compile,_exec=exec,_error=ArchiveError,_failure=NativeFailure):
    """One private registry reconstructed before mutable project exports run."""
    if _read(_path)!=_raw or _read(_generator)!=_generator_raw:
        raise ValueError("imported canonical adapter/generator bytes differ before reconstruction")
    names=("prepare_plan","prepare_synthetic_plan","compile_outer","create_outer","prepare_observer",
        "finalize_bootstrap","resume_and_collect","parse_joined","replay_joined","inspect_capability")
    tree=_parse(_raw,filename=str(_path));terminal=tree.body[-1]
    calls=[node for node in _walk(tree) if isinstance(node,_call) and isinstance(node.func,_name) and node.func.id=="_api_factory"]
    if not (len(calls)==1 and isinstance(terminal,_assign) and len(terminal.targets)==1 and
        isinstance(terminal.targets[0],_tuple) and tuple(getattr(node,"id",None) for node in terminal.targets[0].elts)==names and
        isinstance(terminal.value,_call) and isinstance(terminal.value.func,_name) and terminal.value.func.id=="_api_factory" and
        not terminal.value.args and not terminal.value.keywords):
        raise ValueError("sole exact canonical adapter terminal factory required")
    tree.body.pop();name="_clash_v3_closed_"+_new().hex
    if name in _modules:raise ValueError("private canonical adapter namespace collision")
    module=_module(name);module.__file__=str(_path);_modules[name]=module
    try:
        if _read(_path)!=_raw or _read(_generator)!=_generator_raw:raise ValueError("canonical source changed before private execution")
        _exec(_compile(tree,str(_path),"exec"),module.__dict__)
        if _modules.get(name) is not module:raise ValueError("owned private module identity lost")
        module.ArchiveError,module.NativeFailure=_error,_failure
        own=module._source_snapshot(_path);generator=module._source_snapshot(_generator)
        if own[1]!=_raw or generator[1]!=_generator_raw:raise ValueError("canonical source changed during private execution")
        apis=module._build_api(own,generator)
        module._unchanged((own,generator))
        return apis
    finally:
        if _modules.get(name) is module:del _modules[name]


prepare_plan, prepare_synthetic_plan, compile_outer, create_outer, prepare_observer, finalize_bootstrap, resume_and_collect, parse_joined, replay_joined, inspect_capability = _api_factory()
