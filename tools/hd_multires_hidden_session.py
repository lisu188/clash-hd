#!/usr/bin/env python3
"""Candidate-bound hidden diagnostic. Dry-run by default; never input or promotion.

The first implemented route observes natural menu entry after replaying the
candidate's complete canonical initial-image probe. Map routes remain pending;
the legacy 800x600 runner and its reports are not reused or relabeled.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import hd_multires_qualification as qualification
from hd_multires_win32 import HiddenJob

SCHEMA = "hd_multires_hidden_session_v1"
CDB = Path("C:/Program Files (x86)/Windows Kits/10/Debuggers/x86/cdb.exe")
GAME = Path("C:/Clash")
EXTERNAL = Path("C:/ClashTests")
MAX_LOG = 128 * 1024 * 1024
ROUTES = {"menu-idle": (120,), "map-idle": (120, 600, 7200), "map-pan": (600, 1800, 7200)}
ASSET_PATTERNS = (("AVI", "*.avi"), ("DATA", "*.res"), ("DATA", "*.wav"),
    ("GFX/CACHE", "*.s32"), ("save", "*.dat"), ("save", "*.fac"))
ASSET_FILES = ("STRATEG/CLASH.DAT", "STRATEG/PRIOR", "CLASH.CFG", "options.cfg", "default.rec")
PRODUCERS = ("tools/hd_multires_hidden_session.py", "tools/hd_multires_win32.py",
    "tools/hd_multires_qualification.py", "scripts/build/build_ddraw_surfdump_proxy.ps1",
    "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp", "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.def")
TARGET = re.compile(r"^HDSESSION_TARGET pid=([0-9a-fA-F]+) base=([0-9a-fA-F`]+)$", re.M)
MENU = re.compile(r"^HDSESSION_MENU_READY pid=([0-9a-fA-F]+) surface=([0-9a-fA-F`]+) width=(\d+) height=(\d+) pixels=([0-9a-fA-F`]+)$", re.M)
ACQUIRE = re.compile(r"^HDSESSION_ACQUIRE kind=(mouse|keyboard) pid=([0-9a-fA-F]+) pc=([0-9a-fA-F`]+) hr=0x([0-9a-fA-F]{8}) hwnd=([0-9a-fA-F`]+) device=([0-9a-fA-F`]+)$", re.M)
ACQUIRE_BLOCK = re.compile(r"^HDSESSION_ACQUIRE_BEGIN_(mouse|keyboard)\n([^\n]*)\nHDSESSION_ACQUIRE_END_\1$", re.M)
ACQUIRE_RETURNS = {"mouse": (0x7bd6f, 8), "keyboard": (0x7bdb7, 4)}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _file_sha(path, maximum=1024 * 1024 * 1024):
    path = qualification.plain_path(path)
    before = path.stat()
    if before.st_size > maximum:
        raise ValueError("Runtime file exceeds its declared read bound.")
    digest, count = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            count += len(block)
            if count > maximum:
                raise ValueError("Runtime file grew beyond its declared read bound.")
            digest.update(block)
    after = path.stat()
    if count != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError("Runtime file changed during hashing.")
    return digest.hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _new(path, payload):
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _json(path, value):
    _new(path, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode())


def _ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def verify_launch_artifacts(references):
    for name, ref in references.items():
        if _file_sha(Path(ref["path"]), 64 * 1024 * 1024) != ref["sha256"]:
            raise ValueError("The exact launched artifact changed: " + name)
    return True


def _external(path):
    path = qualification.plain_path(path, existing=False)
    if os.name != "nt" or not path.is_relative_to(EXTERNAL) or path.is_relative_to(ROOT):
        raise ValueError("Hidden-session outputs must be outside the checkout under C:/ClashTests.")
    return path


def _pe_x86(path):
    raw = qualification.read_file(path, 32 * 1024 * 1024)
    if len(raw) < 64 or raw[:2] != b"MZ":
        raise ValueError("Native tool is not a PE executable: " + str(path))
    offset = struct.unpack_from("<I", raw, 60)[0]
    if offset > len(raw) - 6 or raw[offset:offset + 4] != b"PE\0\0" or struct.unpack_from("<H", raw, offset + 4)[0] != 0x14c:
        raise ValueError("Native debugger/proxy must be x86 PE32: " + str(path))
    return _sha(raw)


def asset_inventory(source=GAME):
    source = Path(source)
    selected = set(ASSET_FILES)
    for directory, pattern in ASSET_PATTERNS:
        selected.update(p.relative_to(source).as_posix() for p in (source / directory).glob(pattern) if p.is_file())
    rows = []
    for name in sorted(selected):
        path = qualification.plain_path(source / name)
        rows.append(dict(path=name, bytes=path.stat().st_size))
    if not any(row["path"].startswith("DATA/") and row["path"].lower().endswith(".res") for row in rows):
        raise ValueError("The isolated runtime requires the user's actual resource archives.")
    return rows


def _live_save_hashes():
    return {p.name: _sha(qualification.read_file(p, 16 * 1024 * 1024))
            for p in sorted((GAME / "save").iterdir()) if p.is_file()}


def stage_assets(destination, rows, *, create=True):
    """Copy selected lawful runtime files once, never tool/reverse/output trees."""
    destination = _external(destination)
    manifest = destination / "asset-stage.json"
    if destination.exists():
        save_directory = qualification.plain_path(destination / "save", existing=False)
        if not save_directory.is_dir():
            raise ValueError("The isolated save directory must remain a plain owned directory.")
        save_entries = list(save_directory.iterdir())
        if len(save_entries) > 1024:
            raise ValueError("Isolated save directory exceeds its bounded flat-file inventory.")
        for save_entry in save_entries:
            qualification.plain_path(save_entry)  # Includes files created after initial staging.
        recorded = qualification.read_json(manifest)
        if recorded.get("schema") != "hd_multires_isolated_assets_v1" or recorded.get("source") != str(GAME):
            raise ValueError("Existing asset directory has no matching owned staging manifest.")
        if (type(recorded.get("files")) is not list or len(recorded["files"]) != len(rows)
                or [(r.get("path"), r.get("bytes")) for r in recorded["files"]] != [(r["path"], r["bytes"]) for r in rows]
                or any(set(r) != {"path", "bytes", "sha256"} or not qualification.policy.SHA_RE.fullmatch(str(r.get("sha256", "")))
                       for r in recorded["files"])):
            raise ValueError("Existing staged asset inventory differs from the fixed runtime allowlist.")
        for row in recorded["files"]:
            # Mutable state may differ in content, but may never be redirected
            # through a symlink, junction or hard link into live game state.
            qualification.plain_path(destination / row["path"])
            if row["path"].startswith(("save/",)) or row["path"] in ("CLASH.CFG", "options.cfg", "default.rec"):
                continue  # Isolated game state may change; source copies never do.
            if _file_sha(destination / row["path"]) != row["sha256"]:
                raise ValueError("Staged immutable game data changed: " + row["path"])
        return recorded
    if not create:
        raise ValueError("Existing isolated asset staging is required; read-only preflight never creates it.")
    qualification._reserve(destination, sum(row["bytes"] for row in rows) + 512 * 1024 * 1024)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "save").mkdir()
    records = []
    for row in rows:
        source = qualification.plain_path(GAME / row["path"])
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        before = source.stat()
        digest = hashlib.sha256()
        with source.open("rb") as input_stream, target.open("xb") as output:
            while block := input_stream.read(1024 * 1024):
                output.write(block)
                digest.update(block)
        after = source.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError("Live runtime input changed while staging: " + row["path"])
        records.append(row | {"sha256": digest.hexdigest()})
    recorded = dict(schema="hd_multires_isolated_assets_v1", source=str(GAME), files=records,
        total_bytes=sum(row["bytes"] for row in records), live_saves_used=False)
    _json(manifest, recorded)
    return recorded


def plan(bundle: Path, route="menu-idle", duration=120, *, smoke_only=False, acquire_only=False):
    if smoke_only and acquire_only:
        raise ValueError("Select either initial smoke or acquisition observation, not both.")
    if route not in ROUTES or type(duration) is not int or duration not in ROUTES[route]:
        raise ValueError("Route/duration must preserve the fixed short-ladder or two-hour policy.")
    bundle = qualification.plain_path(bundle)
    context = qualification.authenticate_bundle(bundle)
    declared = qualification.read_json(bundle)
    loaded = {name: qualification._reference(ref, bundle.parent, qualification.MAX_BYTES[name])
              for name, ref in declared["artifacts"].items()}
    metadata = qualification.policy.parse_evidence_json(loaded["metadata"][1], "candidate metadata")
    producers = {name: _sha(qualification.read_file(ROOT / name, 4 * 1024 * 1024)) for name in PRODUCERS}
    cdb_hash = _pe_x86(CDB)
    rows = asset_inventory()
    pending = [] if route == "menu-idle" else ["candidate-bound native map collector is not implemented"]
    report = dict(schema=SCHEMA, executed=False, identity=context["identity"], bundle=str(bundle),
        bundle_sha256=_sha(bundle.read_bytes()), route=route, duration_sec=duration, smoke_only=smoke_only,
        acquire_only=acquire_only, diagnostic_scope=("initial_image_only" if smoke_only else
            "initial_image_and_native_acquisition_returns" if acquire_only else "natural_menu_idle_no_input"),
        acquisition_return_rvas={kind: rva for kind, (rva, _) in ACQUIRE_RETURNS.items()},
        debugger_holds_at_acquisition_completion=acquire_only,
        environment="hidden_cdb_host", input_responsiveness="not_applicable_hidden", input_injected=False,
        source_authentication_passed=True, cdb=dict(path=str(CDB), sha256=cdb_hash, machine="x86"),
        producer_source_hashes=producers, isolated_asset_files=len(rows),
        isolated_asset_bytes=sum(r["bytes"] for r in rows), pending=pending,
        runtime_evidence_verified=False, manual_input_proof=False, promotion_ready=False,
        short_ladder_completed=False, endurance_completed=False, stable_stage_should_change=False)
    return report, context, loaded, metadata, rows


def command_script(probe: bytes, identity, metadata, *, smoke_only=False, acquire_only=False):
    chunks = metadata["probe_contract"]["required_chunks"]
    if type(chunks) is not int or chunks <= 0:
        raise ValueError("Canonical initial-image chunk inventory is invalid.")
    suffix = [f'.if ((@$t19 == 0) | (@$t18 != 0n{chunks})) {{ .echo HDSESSION_INITIAL_REJECT; q }}',
        '.printf "HDSESSION_TARGET pid=%x base=%p\\n", @$tpid, @$t19']
    if smoke_only:
        suffix += ['.echo HDSESSION_INITIAL_SMOKE_COMPLETE', '.sleep 0n300000', 'q']
    else:
        # These are observers only; no input bytes, instruction pointer,
        # acquisition return values or game state are forced.
        suffix += ['sxe -c ".echo HDSESSION_AV; .exr -1; r; kb; q" av',
            'bp /1 @$t19+0x1dda ".echo HDSESSION_APP_REQUEST_QUIT; kb; q"',
            'bp /1 @$t19+0x47d61 ".printf \\"HDSESSION_MENU_READY pid=%x surface=%p width=%d height=%d pixels=%p\\\\n\\", @$tpid, @$t19+0x11d4c0, wo(@$t19+0x11d4c0), wo(@$t19+0x11d4c2), dwo(@$t19+0x11d4c4); gc"', 'g']
        acquisition = []
        # The legacy 0x47BD66/0x47BDAE sites precede the native Acquire
        # calls. Observe EAX at the actual return PCs, nine bytes later.
        for kind, (rva, slot) in ACQUIRE_RETURNS.items():
            body = ('.printf "HDSESSION_CONTEXT_WARMUP pid=%x pc=%p hr=%x hwnd=%p device=%p\\n", '
                f'@$tpid, @eip, @eax, dwo(@$t19+0x1452dc), dwo(@esi+0n{slot}); '
                f'.echo HDSESSION_ACQUIRE_BEGIN_{kind}; '
                f'.printf "HDSESSION_ACQUIRE kind={kind} pid=%x pc=%p hr=0x%08x hwnd=%p device=%p\\n", '
                f'@$tpid, @eip, @eax, dwo(@$t19+0x1452dc), dwo(@esi+0n{slot}); ')
            body += f'.echo HDSESSION_ACQUIRE_END_{kind}; '
            if acquire_only:
                # Hold only after the final return or the first failure so the
                # host can retain candidate identity before task-only cleanup.
                body += ('.sleep 0n300000; ' if kind == "keyboard" else
                    '.if ((@eax & 0x80000000) != 0) { .sleep 0n300000 }; ')
            body += 'gc'
            acquisition.append(f'bp /1 @$t19+0x{rva:x} "' + body.replace('\\', '\\\\').replace('"', '\\"') + '"')
        suffix[-1:-1] = acquisition
    return probe + ("\r\n" + "\r\n".join(suffix) + "\r\n").encode("ascii")


def parse_observations(log: str, identity, metadata):
    marker = metadata["probe_contract"]["acceptance_marker"]
    lines = log.splitlines()
    verified = lines.count(marker) == 1
    targets = TARGET.findall(log)
    menus = MENU.findall(log)
    failures = []
    if len(targets) > 1 or len(menus) > 1:
        failures.append("duplicate target/menu observation")
    if any(token in lines for token in ("HDSESSION_AV", "HDSESSION_INITIAL_REJECT", "HDSESSION_APP_REQUEST_QUIT")):
        failures.append("native exception, initial rejection or application quit observed")
    target = None
    if len(targets) == 1:
        target = dict(pid=int(targets[0][0], 16), base=int(targets[0][1].replace("`", ""), 16))
    menu = None
    if len(menus) == 1:
        row = menus[0]
        menu = dict(pid=int(row[0], 16), surface=int(row[1].replace("`", ""), 16),
            width=int(row[2]), height=int(row[3]), pixels=int(row[4].replace("`", ""), 16))
        selected = tuple(map(int, identity["resolution"].split("x")))
        if (menu["width"], menu["height"]) not in ((640, 480), selected) or not 0x10000 <= menu["pixels"] < 0x80000000:
            failures.append("menu surface differs from native-menu or selected-canvas bounds")
        if target is None or menu["pid"] != target["pid"]:
            failures.append("menu observation belongs to a different process")
    acquisition = []
    for block_kind, block_line in ACQUIRE_BLOCK.findall(log):
        match = ACQUIRE.fullmatch(block_line)
        if match is None:
            failures.append("malformed complete acquisition observation block")
            continue
        kind, pid, pc, hr, hwnd, device = match.groups()
        if kind != block_kind:
            failures.append("acquisition observation block kind mismatch")
            continue
        row = dict(kind=kind, pid=int(pid, 16), pc=int(pc.replace('`', ''), 16),
            hresult=int(hr, 16), hwnd=int(hwnd.replace('`', ''), 16), device=int(device.replace('`', ''), 16))
        row["failed_hresult"] = bool(row["hresult"] & 0x80000000)
        if (target is None or row["pid"] != target["pid"] or
                row["pc"] != target["base"] + ACQUIRE_RETURNS[kind][0]):
            failures.append("acquisition return belongs to a different process/native PC")
        acquisition.append(row)
    if len({r["kind"] for r in acquisition}) != len(acquisition):
        failures.append("duplicate one-shot acquisition return")
    return dict(initial_image_bytes_verified=verified, target=target, menu=menu,
                acquisition_returns=acquisition, failures=failures)


def _read_log(path):
    if not path.exists():
        return ""
    if path.stat().st_size > MAX_LOG:
        raise ValueError("CDB diagnostic log exceeded its retained output budget.")
    return path.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")


def execute(preflight, context, loaded, metadata, rows, *, output_root, asset_root, ready_timeout=300):
    if preflight["pending"]:
        raise ValueError("; ".join(preflight["pending"]))
    output_root, asset_root = _external(output_root), _external(asset_root)
    qualification._reserve(output_root, sum(row["bytes"] for row in rows) + 512 * 1024 * 1024)
    print(json.dumps(dict(event="isolated_asset_stage", files=len(rows), bytes=sum(r["bytes"] for r in rows))), flush=True)
    stage_assets(asset_root, rows)
    run = output_root / ("session-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    run.mkdir(parents=True, exist_ok=False)
    report = preflight | dict(executed=True, started_at=_now(), run_directory=str(run), failures=[],
        initial_image_bytes_verified=False, natural_menu_idle_verified=False, native_processes=[], frames=[], samples=[],
        acquisition_returns=[], acquisition_observation_completed=False, input_acquisition_verified=False)
    _json(run / "preflight.json", preflight)
    local_candidate = run / "clash95_hd_session.exe"
    _new(local_candidate, loaded["executable"][1])
    commands = run / "session.cdb"
    _new(commands, command_script(loaded["probe"][1], context["identity"], metadata,
        smoke_only=preflight["smoke_only"], acquire_only=preflight.get("acquire_only", False)))
    _new(run / "candidate.cdb", loaded["probe"][1])
    launch_artifacts = {"candidate": dict(path=str(local_candidate), sha256=_sha(loaded["executable"][1])),
        "canonical_probe": dict(path=str(run / "candidate.cdb"), sha256=_sha(loaded["probe"][1])),
        "session_commands": dict(path=str(commands), sha256=_file_sha(commands, 64 * 1024 * 1024)),
        "debugger": preflight["cdb"] | {"path": str(CDB)}}
    report["launch_artifacts"] = launch_artifacts
    log = run / "cdb.log"
    before_saves = _live_save_hashes()
    native = None
    try:
        builder = HiddenJob()
        try:
            builder.open()
            build_env = dict(os.environ, CLASH_PROXY_PRESENT="0")
            system_root = Path(os.environ.get("SystemRoot", "C:/Windows"))
            choices = [Path(shutil.which("pwsh") or "C:/Program Files/PowerShell/7/pwsh.exe"),
                Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe",
                system_root / "System32/WindowsPowerShell/v1.0/powershell.exe"]
            powershell = next((p for p in choices if p.is_file()), None)
            if powershell is None:
                raise FileNotFoundError("A local PowerShell installation is required to build the memory proxy.")
            report["proxy_build_tool"] = dict(path=str(powershell), sha256=_file_sha(powershell, 32 * 1024 * 1024))
            build_env["PSModulePath"] = str(powershell.parent / "Modules") + ";C:\\Program Files\\WindowsPowerShell\\Modules"
            invocation = ("$ErrorActionPreference='Stop'; try { & " + _ps_quote(ROOT / "scripts/build/build_ddraw_surfdump_proxy.ps1")
                + " -OutputDll " + _ps_quote(run / "ddraw.dll") + " -LogDir " + _ps_quote(run / "proxy-build")
                + "; [System.IO.File]::WriteAllText(" + _ps_quote(run / "proxy-invocation.log")
                + ", 'BUILD_SCRIPT_COMPLETED'); exit 0 } catch { [System.IO.File]::WriteAllText("
                + _ps_quote(run / "proxy-invocation.log") + ", $_.Exception.ToString()); exit 1 }")
            build_handle, build_identity = builder.spawn(
                powershell,
                ["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", invocation],
                run, build_env)
            deadline = time.monotonic() + 180
            while builder.alive(build_handle):
                if time.monotonic() >= deadline:
                    raise TimeoutError("Source-built proxy compilation exceeded its bounded interval.")
                time.sleep(0.1)
            build_code = builder.exit_code(build_handle)
        finally:
            build_cleanup = builder.close()
            report["proxy_build_cleanup"] = build_cleanup
        _json(run / "proxy-build-session.json", dict(identity=build_identity, exit_code=build_code, cleanup=build_cleanup))
        if build_code or not build_cleanup["cleanup_verified"]:
            raise ValueError("Memory-only proxy compilation failed; retained build logs identify the failure.")
        report["proxy_sha256"] = _pe_x86(run / "ddraw.dll")
        launch_artifacts["memory_proxy"] = dict(path=str(run / "ddraw.dll"), sha256=report["proxy_sha256"])
        for name, expected in preflight["producer_source_hashes"].items():
            if _sha((ROOT / name).read_bytes()) != expected:
                raise ValueError("Session producer source changed before launch.")
        # Rebuild and reauthenticate immediately before any native game process.
        if qualification.authenticate_bundle(Path(preflight["bundle"]))["identity"] != context["identity"]:
            raise ValueError("Candidate bundle changed before native launch.")
        verify_launch_artifacts(launch_artifacts)
        environment = dict(os.environ, CLASH_PROXY_PRESENT="0", _NT_SYMBOL_PATH=".", _NT_ALT_SYMBOL_PATH="")
        native = HiddenJob()
        native.open()
        print(json.dumps(dict(event="hidden_debugger_start", identity=context["identity"], smoke_only=preflight["smoke_only"])), flush=True)
        cdb_handle, cdb_identity = native.spawn(CDB, ["-y", ".", "-logo", str(log), "-cf", str(commands), str(local_candidate)], asset_root, environment)
        report["native_processes"].append(cdb_identity | {"role": "debugger"})
        start, menu_started, next_sample, next_frame = time.monotonic(), None, 0, 0
        menu_controls = None
        target_handle = None
        while True:
            text = _read_log(log)
            observed = parse_observations(text, context["identity"], metadata)
            report["acquisition_returns"] = observed["acquisition_returns"]
            report["acquisition_failed_hresult_count"] = sum(r["failed_hresult"] for r in observed["acquisition_returns"])
            if observed["initial_image_bytes_verified"] and not report["initial_image_bytes_verified"]:
                print(json.dumps(dict(event="initial_image_bytes_verified", identity=context["identity"])), flush=True)
            report["initial_image_bytes_verified"] = observed["initial_image_bytes_verified"]
            if observed["failures"]:
                raise ValueError("; ".join(observed["failures"]))
            if observed["target"] and target_handle is None:
                target_handle, target_identity = native.adopt(observed["target"]["pid"], local_candidate,
                    cdb_identity["creation_filetime"])
                report["native_processes"].append(target_identity | {"role": "candidate"})
            if preflight["smoke_only"] and "HDSESSION_INITIAL_SMOKE_COMPLETE" in text.splitlines():
                if not observed["initial_image_bytes_verified"] or target_handle is None:
                    raise ValueError("Initial smoke lacks the exact marker and retained candidate path/generation binding.")
                break
            if preflight.get("acquire_only") and observed["acquisition_returns"] and target_handle is not None:
                if (len(observed["acquisition_returns"]) == 2 or report["acquisition_failed_hresult_count"]):
                    report["acquisition_observation_completed"] = True
                    break
            now = time.monotonic()
            if observed["menu"] and menu_started is None:
                if not observed["initial_image_bytes_verified"] or target_handle is None:
                    raise ValueError("Menu observation precedes authenticated image/process binding.")
                menu_started, next_sample, next_frame = now, now, now
                report["menu_surface"] = observed["menu"]
                print(json.dumps(dict(event="natural_menu_observed", identity=context["identity"], duration_sec=preflight["duration_sec"])), flush=True)
            if not native.alive(cdb_handle) or (target_handle and not native.alive(target_handle)):
                raise ValueError("Debugger/candidate exited before the requested diagnostic completed.")
            if menu_started is None and now - start > ready_timeout:
                raise TimeoutError(("Native acquisition returns" if preflight.get("acquire_only") else "Natural menu readiness")
                    + " were not observed within the bounded startup interval.")
            if menu_started is not None:
                if now >= next_sample:
                    controls = native.read(target_handle, observed["target"]["base"] + 0x143d78, 8)
                    if menu_controls is None:
                        menu_controls = controls
                    if controls != menu_controls or struct.unpack_from("<I", controls)[0] != 0:
                        raise ValueError("Native main-menu control/exit state changed during the idle diagnostic.")
                    menu = observed["menu"]
                    descriptor = native.read(target_handle, menu["surface"], 8)
                    if struct.unpack("<HHI", descriptor) != (menu["width"], menu["height"], menu["pixels"]):
                        raise ValueError("Native menu surface descriptor changed during sampling.")
                    report["samples"].append(dict(elapsed_sec=now - menu_started,
                        menu_exit=struct.unpack_from("<I", controls)[0], menu_choice=struct.unpack_from("<I", controls, 4)[0],
                        **native.telemetry(target_handle)))
                    next_sample = now + 1
                if now >= next_frame or now - menu_started >= preflight["duration_sec"]:
                    surface = observed["menu"]
                    count = surface["width"] * surface["height"]
                    qualification._reserve(run, count + 32 * 1024 * 1024)
                    frame = native.read(target_handle, surface["pixels"], count)
                    filename = f"menu-frame-{len(report['frames']):04d}.indexed8"
                    _new(run / filename, frame)
                    report["frames"].append(dict(path=filename, sha256=_sha(frame), bytes=count,
                        elapsed_sec=now - menu_started, width=surface["width"], height=surface["height"],
                        coherent_snapshot_verified=False))
                    next_frame = now + 30
                if now - menu_started >= preflight["duration_sec"]:
                    report["natural_menu_idle_verified"] = True
                    report["measured_menu_host_seconds"] = now - menu_started
                    break
            time.sleep(0.25)
        proxy_log = _read_log(run / "ddraw_surfdump_proxy.log")
        if not preflight["smoke_only"] and ("loaded present_enabled=0" not in proxy_log or "present_enabled=1" in proxy_log):
            raise ValueError("Proxy did not retain the non-presenting hidden configuration.")
    except Exception as error:
        report["failures"].append(type(error).__name__ + ": " + str(error))
    finally:
        report["cleanup"] = native.close() if native else dict(cleanup_verified=True, reason="no native session was created")
        if not report["cleanup"]["cleanup_verified"]:
            report["failures"].append("Task-owned native cleanup was not verified.")
        try:
            report["live_saves_unchanged"] = _live_save_hashes() == before_saves
        except OSError as error:
            report["live_saves_unchanged"] = False
            report["failures"].append("Live-save recheck failed: " + str(error))
        if not report["live_saves_unchanged"]:
            report["failures"].append("Live source-save hashes changed during the isolated run.")
        try:
            report["launch_artifacts_unchanged"] = verify_launch_artifacts(launch_artifacts)
            if _sha(Path(preflight["bundle"]).read_bytes()) != preflight["bundle_sha256"]:
                raise ValueError("Candidate bundle index changed during session.")
            for name, expected in context["source_hashes"].items():
                if _file_sha(ROOT / name, 4 * 1024 * 1024) != expected:
                    raise ValueError("Candidate source closure changed during session: " + name)
        except (OSError, ValueError) as error:
            report["launch_artifacts_unchanged"] = False
            report["failures"].append(str(error))
        for name, expected in preflight["producer_source_hashes"].items():
            try:
                unchanged = _sha((ROOT / name).read_bytes()) == expected
            except OSError:
                unchanged = False
            if not unchanged:
                report["failures"].append("Producer source changed during session: " + name)
        report["finished_at"] = _now()
        report["diagnostic_passed"] = not report["failures"] and report["initial_image_bytes_verified"] and (
            preflight["smoke_only"] or report["natural_menu_idle_verified"] or report["acquisition_observation_completed"])
        _json(run / "session-report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--route", choices=tuple(ROUTES), default="menu-idle")
    parser.add_argument("--duration", type=int, default=120)
    parser.add_argument("--smoke-only", action="store_true", help="stop after canonical initial bytes; supplies no menu/endurance pass")
    parser.add_argument("--acquire-only", action="store_true", help="observe genuine mouse/keyboard HRESULT returns; never force acquisition or input")
    parser.add_argument("--output-root", type=Path, default=Path("C:/ClashTests/hd-multires-hidden"))
    parser.add_argument("--asset-root", type=Path, default=Path("C:/ClashTests/hd-multires-runtime-assets-20261025"))
    parser.add_argument("--ready-timeout", type=int, default=300)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not 30 <= args.ready_timeout <= 600:
        parser.error("--ready-timeout must be between 30 and 600 seconds")
    try:
        preflight, context, loaded, metadata, rows = plan(args.bundle, args.route, args.duration,
            smoke_only=args.smoke_only, acquire_only=args.acquire_only)
        if args.execute:
            report = execute(preflight, context, loaded, metadata, rows, output_root=args.output_root,
                             asset_root=args.asset_root, ready_timeout=args.ready_timeout)
        else:
            report = preflight
        print(json.dumps(report, indent=2), flush=True)
        return (0 if report.get("diagnostic_passed") else 1) if args.execute else (2 if report["pending"] else 0)
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        print(json.dumps(dict(schema=SCHEMA, executed=False, failure=str(error), runtime_evidence_verified=False)), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
