#!/usr/bin/env python3
"""Plan or run one approved, manually operated HD layout observation session.

The default path reads files only. Execution needs both switches and an existing
fresh user approval bound to the exact plan. No input is injected. Only the
candidate launched by this CDB process is observed, captured, and stopped.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import hd_layout_command_input_summary as summary

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/smoke/run_hd_layout_input_probe.ps1"
CANDIDATE_ROOT = Path(r"C:\ClashTests")
OUTPUT_ROOT = Path(r"C:\ClashCaptures")
PLAN_KEYS = ("candidate", "stage", "wrapper", "wrapper_config", "wrapper_mode", "cdb", "output_dir", "run_id", "timeout_seconds")
REQUIRED_ASSET_FILES = (
    "STRATEG/CLASH.DAT", "STRATEG/PRIOR", "CLASH.CFG", "options.cfg", "default.rec", "palette.data", "dxcfg.ini",
    "save/0.dat", "save/0.fac", "save/2.dat", "save/2.fac",
    *("DATA/" + name for name in ("GFX3.RES", "INFOANG.RES", "INFOPOL.RES", "IS.RES", "MAPS.RES",
        "maximum.res", "minimum.res", "MISINFOA.RES", "MISWAVA.RES", "MUSIC.RES", "normal.res",
        "mainmap1.wav", "mainmap2.wav", "mainmap3.wav")),
    *("AVI/" + name + ".AVI" for name in ("ATAK_ZAM", "ATAK_ZAS", "BATTLE", "CHLOP", "CRE_AN", "INT_A",
        "INT_CLSA", "KON_POR1", "KOP_BUD", "LOGO", "P_POSLA", "SW_CHS", "SW_POG", "UKRYCIE", "UWIEZIC",
        "WPAD_PUL", "ZAKL_PUL", "ZARAZA", "ZCIECIE", "ZNISZCZE", "ZWY01", "ZWY02")),
)
REQUIRED_ASSET_DIRECTORIES = ("DATA", "AVI", "STRATEG", "GFX/CACHE", "save")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_ref(path: Path) -> dict[str, str]:
    path = path.resolve()
    return {"path": str(path), "sha256": summary.sha256(path.read_bytes())}


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def plan_bytes(plan: dict) -> bytes:
    return (json.dumps(plan, indent=2) + "\n").encode("utf-8")


def prepare_launch_environment(wrapper_mode: str, inherited: dict | None = None) -> tuple[dict, dict]:
    policy = summary.launch_environment_policy(wrapper_mode)
    source = os.environ if inherited is None else inherited
    environment = {key: value for key, value in source.items()
                   if key.upper() not in policy["remove_names"]
                   and not any(key.upper().startswith(prefix) for prefix in policy["remove_prefixes"])}
    environment.update(policy["set"])
    # Hash the complete effective environment for provenance only. Its unrelated
    # host/Codex values may differ across planning and approved execution shells.
    normalized = {key.upper(): value for key, value in environment.items()}
    digest = summary.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return environment, {"policy": policy, "effective_environment_sha256": digest}


def validate_candidate(candidate: Path, stage: str) -> None:
    import patch_stage_report
    patcher = patch_stage_report.load_patcher()
    data = candidate.read_bytes()
    original = bytearray(data)
    for patch in patcher.select_patches(stage):
        if len(patch.old) != len(patch.new) or data[patch.offset:patch.offset + len(patch.new)] != patch.new:
            raise ValueError(f"candidate byte mismatch at {patch.offset:#x}")
        original[patch.offset:patch.offset + len(patch.old)] = patch.old
    if summary.sha256(original).lower() != patcher.EXPECTED_SHA256.lower():
        raise ValueError("candidate does not reconstruct the exact known original SHA-256")


def require_x86_pe(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 64 or data[:2] != b"MZ":
        raise ValueError(f"not a PE executable: {path}")
    offset = struct.unpack_from("<I", data, 60)[0]
    if data[offset:offset + 4] != b"PE\0\0" or data[offset + 4:offset + 6] != b"L\x01":
        raise ValueError(f"x86 PE required: {path}")


def asset_inventory(work: Path) -> dict:
    """Bind the isolated local game files needed by the reviewed manual route.

    Never search old captures, require unrelated diagnostics, copy assets, or
    mutate settings. Runtime may change its local settings/cache after launch;
    these hashes describe the approved starting workspace.
    """
    work = work.resolve()
    for relative in REQUIRED_ASSET_DIRECTORIES:
        path = (work / relative).resolve()
        if not path.is_relative_to(work) or not path.is_dir():
            raise ValueError(f"missing or non-isolated required asset directory: {relative}")
    paths = {work / relative for relative in REQUIRED_ASSET_FILES}
    for folder, extensions in (("DATA", {".res", ".wav"}), ("AVI", {".avi"})):
        paths.update(path for path in (work / folder).iterdir() if path.is_file() and path.suffix.lower() in extensions)
    paths.update(path for path in (work / "GFX/CACHE").iterdir() if path.is_file())
    files = []
    for path in sorted(paths, key=lambda value: str(value).lower()):
        resolved = path.resolve()
        if not resolved.is_relative_to(work) or not resolved.is_file() or resolved.stat().st_size == 0:
            raise ValueError(f"missing, empty, or non-isolated required asset: {path.relative_to(work)}")
        files.append({**file_ref(resolved), "relative_path": path.relative_to(work).as_posix(), "size_bytes": resolved.stat().st_size})
    return {"work_dir": str(work), "directories": list(REQUIRED_ASSET_DIRECTORIES), "files": files,
            "scope": "approved prelaunch local assets and settings; game runtime may update local settings/cache"}


def build_plan(args: argparse.Namespace) -> dict:
    """Read-only plan construction; never creates output directories or processes."""
    candidate, output = args.candidate.resolve(), args.output_dir.resolve()
    wrapper, config, cdb = args.wrapper.resolve(), args.wrapper_config.resolve(), args.cdb.resolve()
    if not candidate.is_relative_to(CANDIDATE_ROOT.resolve()) or candidate.suffix.lower() != ".exe":
        raise ValueError("candidate must be a distinct executable under C:\\ClashTests")
    if not output.is_relative_to(OUTPUT_ROOT.resolve()) or output == OUTPUT_ROOT.resolve() or output.exists():
        raise ValueError("output must be a new run directory under C:\\ClashCaptures")
    if args.stage not in summary.SUPPORTED_STAGES or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", args.run_id):
        raise ValueError("unsupported validation stage or malformed run ID")
    if type(args.timeout_seconds) is not int or not 30 <= args.timeout_seconds <= 900:
        raise ValueError("timeout must be 30 through 900 seconds")
    if wrapper != candidate.parent / "ddraw.dll" or config.parent != candidate.parent:
        raise ValueError("wrapper must be the candidate's local ddraw.dll; config must be in the same isolated directory")
    if args.wrapper_mode not in ("proxy-present", "gog"):
        raise ValueError("unsupported visible wrapper mode")
    if cdb.name.lower() != "cdb.exe":
        raise ValueError("the debugger must be an explicitly selected x86 cdb.exe")
    require_x86_pe(cdb)
    require_x86_pe(wrapper)
    validate_candidate(candidate, args.stage)
    assets = asset_inventory(candidate.parent)
    identity = {
        "run_id": args.run_id, "candidate_path": str(candidate), "candidate_sha256": file_ref(candidate)["sha256"],
        "stage": args.stage, "resolution": [800, 600], "environment": "host_visible", "input_method": "manual_directinput",
        "wrapper": {**file_ref(wrapper), "config": file_ref(config), "mode": args.wrapper_mode},
        "input_plan": copy.deepcopy(summary.INPUT_PLAN),
    }
    parameters = {key: str(getattr(args, key).resolve()) if isinstance(getattr(args, key), Path) else getattr(args, key)
                  for key in PLAN_KEYS}
    return {"schema_version": 1, "executed": False, "identity": identity, "parameters": parameters,
            "cdb": file_ref(cdb), "python": file_ref(Path(sys.executable)), "output_dir": str(output), "timeout_seconds": args.timeout_seconds,
            "producer_source": file_ref(Path(__file__)), "wrapper_script": file_ref(SCRIPT),
            "observation_template": file_ref(summary.PROBE), "summary_source": file_ref(Path(summary.__file__)),
            "launch_mode": "x86_cdb_visible_manual_observation", "inject_input": False,
            "requires_fresh_user_approval": True, "creates_approval": False,
            "capture": {"native_client_size": [800, 600], "states": ["map", "panel_hover"], "stable_pairs": True},
            "launch_environment": summary.launch_environment_policy(args.wrapper_mode),
            "assets": assets,
            "cleanup": "only exact candidate child and the CDB process launched by this session"}


def verify_plan(plan: dict) -> argparse.Namespace:
    if not isinstance(plan.get("parameters"), dict) or set(plan["parameters"]) != set(PLAN_KEYS):
        raise ValueError("plan parameters are missing or unexpected")
    args = argparse.Namespace(**plan["parameters"])
    for key in ("candidate", "wrapper", "wrapper_config", "cdb", "output_dir"):
        setattr(args, key, Path(getattr(args, key)))
    if build_plan(args) != plan:
        raise ValueError("plan differs from current candidate, source files, wrapper, or safe parameters")
    return args


def validate_approval(approval_path: Path, identity: dict, timeout_seconds: int, now: str | None = None) -> dict:
    record = summary.read_object(approval_path)
    if (record.get("approved") is not True or record.get("record_kind") != "user_approval"
            or not isinstance(record.get("approval_text"), str) or not record["approval_text"].strip()):
        raise ValueError("an existing explicit user approval record is required")
    if record.get("identity") != {key: identity[key] for key in summary.APPROVAL_BINDINGS}:
        raise ValueError("approval does not bind the exact prelaunch plan identity")
    issued, expires, current = (summary.timestamp(record.get("approved_at")), summary.timestamp(record.get("expires_at")),
                                summary.timestamp(now or utc_now()))
    from datetime import timedelta
    if not issued <= current < expires or expires - issued > summary.MAX_APPROVAL_AGE:
        raise ValueError("approval is stale or outside its fresh 12-hour interval")
    if current + timedelta(seconds=timeout_seconds + 30) > expires:
        raise ValueError("approval expires before the bounded session and cleanup can finish")
    return record


class WindowsSession:
    """Win32 is loaded only after all execution and approval checks succeed."""

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes as w
        self.ctypes, self.w = ctypes, w
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.shcore = ctypes.WinDLL("shcore", use_last_error=True)
        self.shcore.GetProcessDpiAwareness.argtypes = [w.HANDLE, ctypes.POINTER(ctypes.c_int)]
        self.shcore.GetProcessDpiAwareness.restype = ctypes.c_long
        self.user.GetWindowDpiAwarenessContext.argtypes = [w.HWND]
        self.user.GetWindowDpiAwarenessContext.restype = w.HANDLE
        self.user.GetAwarenessFromDpiAwarenessContext.argtypes = [w.HANDLE]
        self.user.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
        self.user.GetThreadDpiAwarenessContext.argtypes = []
        self.user.GetThreadDpiAwarenessContext.restype = w.HANDLE
        self.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.kernel.OpenProcess.restype = w.HANDLE
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
        self.kernel.GetProcessTimes.argtypes = [w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4
        self.kernel.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
        self.kernel.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
        self.kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        self.user.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
        self.user.GetClientRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
        self.user.ClientToScreen.argtypes = [w.HWND, ctypes.POINTER(w.POINT)]
        self.user.IsWindowVisible.argtypes = [w.HWND]
        self.user.WindowFromPoint.argtypes = [w.POINT]
        self.user.WindowFromPoint.restype = w.HWND
        self.user.GetAncestor.argtypes = [w.HWND, w.UINT]
        self.user.GetAncestor.restype = w.HWND
        self.callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        self.user.EnumWindows.argtypes = [self.callback_type, w.LPARAM]
        self.user.SetProcessDpiAwarenessContext.argtypes = [w.HANDLE]
        self.user.SetProcessDpiAwarenessContext.restype = w.BOOL
        self.enable_native_capture_coordinates()

    def enable_native_capture_coordinates(self) -> None:
        # An inherited manifest/compatibility mode may already establish PM
        # awareness and make the setter return access denied. Measure the actual
        # calling thread; system-aware observers can still virtualize coordinates
        # on another monitor, so only PM awareness is sufficient here.
        self.user.SetProcessDpiAwarenessContext(self.ctypes.c_void_p(-4))
        context = self.user.GetThreadDpiAwarenessContext()
        if not context or self.user.GetAwarenessFromDpiAwarenessContext(context) != 2:
            raise OSError("cannot establish per-monitor native client capture coordinates")

    def process(self, proc_id: int, *, terminate: bool = False) -> tuple[Any, str, int]:
        c, w = self.ctypes, self.w
        handle = self.kernel.OpenProcess(0x1000 | 0x100000 | (1 if terminate else 0), False, proc_id)
        if not handle:
            raise OSError(f"cannot open candidate PID {proc_id}")
        try:
            buffer, size = c.create_unicode_buffer(32768), w.DWORD(32768)
            times = [w.FILETIME() for _ in range(4)]
            if not self.kernel.QueryFullProcessImageNameW(handle, 0, buffer, c.byref(size)) or not self.kernel.GetProcessTimes(handle, *(c.byref(t) for t in times)):
                raise OSError("cannot measure process image/creation time")
            return handle, str(Path(buffer.value).resolve()), (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        except BaseException:
            self.kernel.CloseHandle(handle)
            raise

    def candidate_child(self, parent_id: int, candidate: Path, earliest: int) -> dict | None:
        c, w = self.ctypes, self.w
        class Entry(c.Structure):
            _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
                        ("th32DefaultHeapID", c.c_size_t), ("th32ModuleID", w.DWORD), ("cntThreads", w.DWORD),
                        ("th32ParentProcessID", w.DWORD), ("pcPriClassBase", w.LONG), ("dwFlags", w.DWORD),
                        ("szExeFile", w.WCHAR * 260)]
        self.kernel.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
        self.kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
        self.kernel.Process32FirstW.argtypes = [w.HANDLE, c.POINTER(Entry)]
        self.kernel.Process32NextW.argtypes = [w.HANDLE, c.POINTER(Entry)]
        snapshot = self.kernel.CreateToolhelp32Snapshot(2, 0)
        if snapshot == c.c_void_p(-1).value:
            raise OSError("cannot enumerate owned debugger child")
        found = []
        try:
            entry = Entry(); entry.dwSize = c.sizeof(entry)
            valid = self.kernel.Process32FirstW(snapshot, c.byref(entry))
            while valid:
                if entry.th32ParentProcessID == parent_id:
                    handle, path, created = self.process(entry.th32ProcessID, terminate=True)
                    if Path(path) == candidate and created >= earliest:
                        found.append({"pid": int(entry.th32ProcessID), "parent_pid": parent_id, "path": path,
                                      "creation_filetime": created, "handle": handle})
                    else:
                        self.kernel.CloseHandle(handle)
                valid = self.kernel.Process32NextW(snapshot, c.byref(entry))
        finally:
            self.kernel.CloseHandle(snapshot)
        if len(found) > 1:
            for item in found:
                self.kernel.CloseHandle(item["handle"])
            raise ValueError("multiple exact candidate children; window ownership is ambiguous")
        return found[0] if found else None

    def process_dpi_awareness(self, owned: dict) -> int:
        value = self.ctypes.c_int(-1)
        if self.shcore.GetProcessDpiAwareness(owned["handle"], self.ctypes.byref(value)) != 0 or value.value not in (1, 2):
            raise ValueError("owned candidate is not DPI-aware; native physical capture is unavailable")
        return value.value

    def window_dpi_awareness(self, hwnd: int) -> int:
        context = self.user.GetWindowDpiAwarenessContext(hwnd)
        awareness = self.user.GetAwarenessFromDpiAwarenessContext(context) if context else -1
        if awareness not in (1, 2):
            raise ValueError("owned candidate window is not DPI-aware")
        return awareness

    def window(self, proc_id: int) -> int | None:
        matches = []
        @self.callback_type
        def callback(hwnd, _):
            value = self.w.DWORD()
            self.user.GetWindowThreadProcessId(hwnd, self.ctypes.byref(value))
            rect = self.w.RECT()
            if (value.value == proc_id and self.user.IsWindowVisible(hwnd) and self.user.GetClientRect(hwnd, self.ctypes.byref(rect))
                    and (rect.right, rect.bottom) == (800, 600)):
                matches.append(int(hwnd))
            return True
        if not self.user.EnumWindows(callback, 0):
            raise OSError("cannot enumerate owned candidate windows")
        if len(matches) > 1:
            raise ValueError("multiple 800x600 windows for owned candidate")
        return matches[0] if matches else None

    def capture(self, hwnd: int, proc_id: int, identity: dict, path: Path) -> dict:
        from PIL import ImageGrab
        c, w = self.ctypes, self.w
        value, rect, origin = w.DWORD(), w.RECT(), w.POINT(0, 0)
        self.user.GetWindowThreadProcessId(hwnd, c.byref(value))
        if (value.value != proc_id or not self.user.IsWindowVisible(hwnd)
                or not self.user.GetClientRect(hwnd, c.byref(rect)) or (rect.right, rect.bottom) != (800, 600)
                or not self.user.ClientToScreen(hwnd, c.byref(origin))):
            raise ValueError("owned candidate client changed before capture")
        center = self.user.WindowFromPoint(w.POINT(origin.x + 400, origin.y + 300))
        root = self.user.GetAncestor(center, 2)
        if root != hwnd or center != hwnd:
            raise ValueError("candidate is occluded at center; user must expose its approved window")
        window_dpi = self.window_dpi_awareness(hwnd)
        captured_at = utc_now()
        frame = ImageGrab.grab(bbox=(origin.x, origin.y, origin.x + 800, origin.y + 600), all_screens=True)
        if frame.size != (800, 600) or self.user.WindowFromPoint(w.POINT(origin.x + 400, origin.y + 300)) != hwnd:
            raise ValueError("capture size/owned visible window changed")
        frame.save(path)
        sidecar = path.with_suffix(".json")
        write_json(sidecar, {"Hash": file_ref(path)["sha256"], "Width": 800, "Height": 600, "CaptureMode": "screen",
            "TargetHwnd": f"0x{hwnd:x}", "CenterWindowHwnd": f"0x{center:x}", "CenterRootHwnd": f"0x{root:x}",
            "CenterWindowMatchesTarget": True, "OriginX": origin.x, "OriginY": origin.y,
            "CaptureId": str(uuid.uuid4()), "RunId": identity["run_id"], "CandidateSha256": identity["candidate_sha256"],
            "Stage": identity["stage"], "ClientSize": [800, 600], "WindowDpiAwareness": window_dpi, "CapturedAt": captured_at})
        return {**file_ref(path), "sidecar": file_ref(sidecar)}

    def stop_candidate(self, owned: dict) -> bool:
        # The retained kernel handle identifies this exact process even if its PID is reused.
        code = self.w.DWORD()
        if not self.kernel.GetExitCodeProcess(owned["handle"], self.ctypes.byref(code)):
            return False
        if code.value == 259 and not self.kernel.TerminateProcess(owned["handle"], 0):
            return False
        return self.kernel.WaitForSingleObject(owned["handle"], 10000) == 0


def read_snapshot(log: Path) -> dict:
    raw = log.read_bytes() if log.exists() else b""
    # CDB can be halfway through writing its final line during a poll.
    raw = raw[:raw.rfind(b"\n") + 1]
    rows, _, errors = summary.parse_events(raw.decode("utf-8-sig"))
    if errors:
        raise ValueError("malformed input observation: " + errors[0])
    return {"rows": rows, "prefix_bytes": len(raw), "prefix_sha256": summary.sha256(raw)}


def read_rows(log: Path) -> list[dict]:
    return read_snapshot(log)["rows"]


def descriptor_reference(snapshot: dict) -> dict:
    descriptors = [row for row in snapshot["rows"] if row["marker"] == "DESCRIPTOR"]
    if not descriptors:
        raise ValueError("capture lacks a passive descriptor observation")
    return {"line": descriptors[-1]["line"], "prefix_bytes": snapshot["prefix_bytes"],
            "prefix_sha256": snapshot["prefix_sha256"]}


def descriptor_selection(rows: list[dict]) -> tuple[int, int]:
    descriptor = next(row["values"] for row in reversed(rows) if row["marker"] == "DESCRIPTOR")
    return descriptor["selected_unit"], descriptor["state3"]


def descriptor_cursor(rows: list[dict]) -> tuple[int, int, int, int]:
    descriptor = next(row["values"] for row in reversed(rows) if row["marker"] == "DESCRIPTOR")
    return tuple(descriptor[key] for key in ("cursor_meta", "cursor_sprite", "cursor_x", "cursor_y"))


def state_ready(rows: list[dict], state: str) -> bool:
    descriptors = [row["values"] for row in rows if row["marker"] == "DESCRIPTOR"]
    if not descriptors:
        return False
    row = descriptors[-1]
    if ((row["desc"], row["x"], row["y"], row["width"], row["height"], row["callback"]) != (0x511D40, 608, 528, 800, 600, 0x409D80)
            or row["selected_unit"] < 0 or row["state3"] not in (1, 2)):
        return False
    x, y = row["mouse_x"], row["mouse_y"]
    if state not in ("map", "panel_hover"):
        return False
    expected_cursor = (0x5196C8, 3, x, y) if state == "map" else (0x5196A0, 2, x, y)
    if descriptor_cursor(rows) != expected_cursor:
        return False  # Another natural cursor is outside this narrow proof recipe.
    return ((row["state"] == 2 and 240 <= x <= 480 and 200 <= y <= 400) if state == "map"
            else (row["state"] == 6 and 608 <= x < 671 and 528 <= y < 559))


def stable_pair(session: Any, hwnd: int, owned: dict, identity: dict, output: Path, state: str, deadline: float, log: Path,
                expected_selection: tuple[int, int]) -> list[dict]:
    from PIL import Image
    previous = None
    for index in range(12):
        before = read_snapshot(log)
        rows_before = before["rows"]
        if (time.monotonic() >= deadline or not state_ready(rows_before, state)
                or descriptor_selection(rows_before) != expected_selection):
            raise ValueError(f"{state} observation changed or capture deadline expired")
        item = session.capture(hwnd, owned["pid"], identity, output / f"{state}-{index:02d}.png")
        time.sleep(0.05)
        after = read_snapshot(log)
        rows_after = after["rows"]
        if (len(rows_after) <= len(rows_before) or not state_ready(rows_after, state)
                or descriptor_selection(rows_after) != expected_selection
                or descriptor_cursor(rows_after) != descriptor_cursor(rows_before)
                or descriptor_reference(after)["line"] <= descriptor_reference(before)["line"]):
            raise ValueError(f"no fresh matching {state} input observation across capture")
        for row in rows_after[len(rows_before):]:
            if row["marker"] == "DESCRIPTOR" and (not state_ready([row], state)
                    or descriptor_selection([row]) != expected_selection
                    or descriptor_cursor([row]) != descriptor_cursor(rows_before)):
                raise ValueError(f"{state} descriptor or cursor changed during capture")
        sidecar = Path(item["sidecar"]["path"])
        metadata = summary.read_object(sidecar)
        metadata.update(InputObservationBefore=descriptor_reference(before), InputObservationAfter=descriptor_reference(after))
        write_json(sidecar, metadata)
        item["sidecar"] = file_ref(sidecar)
        if previous:
            with Image.open(previous["path"]) as a, Image.open(item["path"]) as b:
                identical = a.mode == b.mode and a.size == b.size and a.tobytes() == b.tobytes()
            if identical:
                return [previous, item]
        previous = item
        time.sleep(0.2)
    raise ValueError(f"no pixel-stable {state} pair; retain actual captures as incomplete evidence")


def execute(plan_path: Path, approval_path: Path, *, allow_visible_runtime: bool, session_factory=WindowsSession) -> dict:
    if not allow_visible_runtime:
        raise ValueError("execution requires --allow-visible-runtime and fresh explicit user approval")
    source_plan_bytes = plan_path.read_bytes()
    plan = json.loads(source_plan_bytes.decode("utf-8-sig"))
    args = verify_plan(plan)
    identity = {**copy.deepcopy(plan["identity"]), "execution_plan_sha256": summary.sha256(source_plan_bytes)}
    validate_approval(approval_path, identity, args.timeout_seconds)
    approval_ref = file_ref(approval_path)
    # No Win32/process/capture APIs have been used above this boundary.
    session = session_factory()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    copied_plan = output / "execution-plan.json"
    copied_plan.write_bytes(source_plan_bytes)
    approval_copy = output / "user-approval.json"
    approval_copy.write_bytes(approval_path.read_bytes())
    # Preserve the original approval reference; copying never changes its semantics.
    rendered = output / "observation.cdb"
    rendered.write_text(summary.render_probe(identity), encoding="utf-8")
    startup = output / "startup.cdb"
    startup.write_text(rendered.read_text(encoding="utf-8") + "\ng\n", encoding="utf-8")
    log = output / "observation.log"
    identity["started_at"] = utc_now()
    earliest = int((summary.timestamp(identity["started_at"]).timestamp() + 11644473600) * 10000000)
    environment, environment_receipt = prepare_launch_environment(args.wrapper_mode)
    cdb = None; owned = None; hwnd = None; frames = {}; failures = []; measured_sha = None; click_start_line = None
    candidate_dpi = None; window_dpi = None
    launch_command = [str(args.cdb), "-hd", "-logo", str(log), "-cf", str(startup), str(args.candidate)]
    cleanup = {"candidate_stopped": False, "cdb_stopped": False}
    deadline = time.monotonic() + args.timeout_seconds
    try:
        if file_ref(args.candidate)["sha256"] != identity["candidate_sha256"]:
            raise ValueError("candidate changed immediately before launch")
        for ref in (plan["cdb"], identity["wrapper"], identity["wrapper"]["config"], approval_ref):
            summary.reference(copied_plan, ref)
        if asset_inventory(args.candidate.parent) != plan["assets"]:
            raise ValueError("approved local asset inventory changed immediately before launch")
        if environment_receipt["policy"] != plan["launch_environment"]:
            raise ValueError("child environment differs from the approved native-DPI launch policy")
        validate_approval(approval_path, identity, args.timeout_seconds)
        cdb = subprocess.Popen(launch_command,
                               cwd=args.candidate.parent, env=environment, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        while time.monotonic() < deadline:
            if cdb.poll() is not None:
                raise ValueError("owned debugger exited before candidate/window discovery")
            owned = owned or session.candidate_child(cdb.pid, args.candidate.resolve(), earliest)
            if owned:
                hwnd = session.window(owned["pid"])
                if hwnd:
                    # Let the loader apply the inherited compatibility layer
                    # before measuring awareness; HWND creation finishes that.
                    candidate_dpi = session.process_dpi_awareness(owned)
                    window_dpi = session.window_dpi_awareness(hwnd)
                    break
            time.sleep(0.2)
        if not owned or not hwnd:
            raise ValueError("no unambiguous owned 800x600 candidate window before deadline")
        identity["hwnd"] = f"0x{hwnd:x}"
        measured_sha = file_ref(Path(owned["path"]))["sha256"]
        if measured_sha != identity["candidate_sha256"]:
            raise ValueError("measured process image differs from approved candidate")
        expected_selection = None
        for state, instruction in (("map", summary.INPUT_PLAN["steps"][0]), ("panel_hover", summary.INPUT_PLAN["steps"][1])):
            print(instruction, flush=True)
            cursor = len(read_rows(log))
            while time.monotonic() < deadline:
                rows = read_rows(log)
                # Require a new observation after this phase begins.
                if len(rows) > cursor and state_ready(rows, state):
                    selection = descriptor_selection(rows)
                    if expected_selection is None:
                        expected_selection = selection
                    elif selection != expected_selection:
                        raise ValueError("selected unit or descriptor-3 state changed between capture phases")
                    time.sleep(0.5)
                    frames[state] = stable_pair(session, hwnd, owned, identity, output, state, deadline, log, expected_selection)
                    break
                cursor = len(rows)
                time.sleep(0.2)
            if state not in frames:
                raise ValueError(f"no fresh {state} observation and capture pair before deadline")
            print(f"{state} capture pair finished.", flush=True)
        before_click = read_rows(log)
        click_start = len(before_click)
        click_start_line = before_click[-1]["line"] if before_click else 0
        print(summary.INPUT_PLAN["steps"][2], flush=True)
        while time.monotonic() < deadline:
            matched = summary.match_sequence(read_rows(log)[click_start:])[0]
            if matched:
                if descriptor_selection(matched) != expected_selection:
                    raise ValueError("click selection or descriptor-3 state differs from the captured phases")
                break
            if cdb.poll() is not None:
                raise ValueError("owned debugger ended before click observation")
            time.sleep(0.1)
        else:
            raise ValueError("no native click-to-callback observation before deadline")
    except (OSError, ValueError, KeyboardInterrupt) as exc:
        failures.append(str(exc) or "observation interrupted")
    finally:
        if owned:
            try:
                cleanup["candidate_stopped"] = session.stop_candidate(owned)
            except OSError as exc:
                failures.append(f"owned candidate cleanup failed: {exc}")
            finally:
                session.kernel.CloseHandle(owned["handle"])
        if cdb:
            try:
                if cdb.poll() is None:
                    cdb.terminate()
                cdb.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    cdb.kill(); cdb.wait(timeout=10)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    failures.append(f"owned debugger cleanup did not finish: {exc}")
            except OSError as exc:
                failures.append(f"owned debugger cleanup failed: {exc}")
            cleanup["cdb_stopped"] = cdb.poll() is not None
        identity["finished_at"] = utc_now()
    receipt = {"schema_version": 1, "executed": True, "producer_source": file_ref(Path(__file__)),
        "plan": file_ref(copied_plan), "approval": approval_ref, "identity": identity,
        "candidate_pid": owned["pid"] if owned else None, "cdb_pid": cdb.pid if cdb else None,
        "candidate_parent_pid": owned["parent_pid"] if owned else None, "hwnd_pid": owned["pid"] if owned and hwnd else None,
        "candidate_creation_filetime": owned["creation_filetime"] if owned else None,
        "process_image_path": owned["path"] if owned else None,
        "process_image_sha256": measured_sha, "launch_command": launch_command,
        "launch_environment": environment_receipt, "candidate_dpi_awareness": candidate_dpi,
        "window_dpi_awareness": window_dpi, "physical_client_size": [800, 600] if hwnd else None,
        "click_observation_start_line": click_start_line,
        "startup_probe": file_ref(startup), "cleanup": cleanup, "failures": failures}
    receipt_path = output / "session-receipt.json"; write_json(receipt_path, receipt)
    manifest = {"schema_version": 1, "executed": True, "identity": identity,
        "raw_log": file_ref(log) if log.exists() else {"path": str(log), "sha256": None}, "approval": approval_ref,
        "probe": {"template_path": str(summary.PROBE), "template_sha256": file_ref(summary.PROBE)["sha256"],
                  "rendered_path": str(rendered), "rendered_sha256": file_ref(rendered)["sha256"]},
        "session_receipt": file_ref(receipt_path)}
    manifest_path = output / "command-input-manifest.json"; write_json(manifest_path, manifest)
    composition = {"schema_version": 1, "evidence_class": "approved_visible_automated_layout_composition",
                   "identity": identity, "command_manifest": file_ref(manifest_path), "approval": approval_ref, "frames": frames}
    write_json(output / "composition.json", composition)
    report = summary.build_report(manifest_path)
    write_json(output / "command-input-summary.json", report)
    return {"passed": report["passed"], "status": report["status"], "output_dir": str(output), "failures": report["failures"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--stage")
    parser.add_argument("--wrapper", type=Path)
    parser.add_argument("--wrapper-config", type=Path)
    parser.add_argument("--wrapper-mode", choices=("proxy-present", "gog"), default="proxy-present")
    parser.add_argument("--cdb", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--write-plan", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--approval-path", type=Path, help="dry-run command destination for a future real approval record; never creates it")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-visible-runtime", action="store_true")
    args = parser.parse_args()
    try:
        if args.execute:
            if not args.plan or not args.approval:
                raise ValueError("execution requires --plan and --approval")
            result = execute(args.plan, args.approval, allow_visible_runtime=args.allow_visible_runtime)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 2
        if args.allow_visible_runtime or args.approval:
            raise ValueError("runtime flags are accepted only with --execute")
        if args.plan:
            plan = summary.read_object(args.plan); verify_plan(plan)
        else:
            if any(getattr(args, key) is None for key in PLAN_KEYS):
                raise ValueError("dry-run requires candidate, stage, wrapper/config, CDB, output directory, and run ID")
            plan = build_plan(args)
        if args.write_plan:
            if args.write_plan.exists():
                raise ValueError("refusing to replace an existing plan")
            args.write_plan.write_bytes(plan_bytes(plan))
        saved_plan = args.write_plan or args.plan or Path(plan["output_dir"]).parent / (plan["identity"]["run_id"] + "-plan.json")
        digest = file_ref(saved_plan)["sha256"] if saved_plan.exists() else summary.sha256(plan_bytes(plan))
        future_approval = args.approval_path or saved_plan.with_name(plan["identity"]["run_id"] + "-user-approval.json")
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--plan", str(saved_plan.resolve()),
                   "--approval", str(future_approval.resolve()), "--execute", "--allow-visible-runtime"]
        print(json.dumps({"plan": plan, "execution_plan_sha256": digest,
                          "approval_identity": {**plan["identity"], "execution_plan_sha256": digest},
                          "plan_path": str(saved_plan.resolve()), "plan_saved": saved_plan.exists(),
                          "execution_command": command,
                          "execution_command_powershell": "& " + " ".join("'" + value.replace("'", "''") + "'" for value in command),
                          "executed": False}, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"hd-layout-input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
