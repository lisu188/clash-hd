#!/usr/bin/env python3
"""Candidate-bound hidden diagnostic. Dry-run by default; never input or promotion.

Every route first replays the candidate's complete canonical initial-image
probe. menu-idle then only observes natural menu entry. map-idle and map-pan
reach the adventure map through the disclosed debugger-forced route of the
proven legacy hidden soak: fast-forwarded intro sleeps, bypassed DirectInput
acquisition, forced main-menu and load-slot clicks, then its steady-state
soak extra with native arrow-key pans. A 120 s map-idle run may add one
disclosed continuity extra from tools/hd_multires_route_extras.py, whose
isolated saves are retained with the run. These are hidden_cdb_host
observations, never input proof; legacy reports are not reused or relabeled.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
from datetime import datetime, timezone
import fnmatch
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
import hd_multires_route_extras as route_extras
from hd_multires_win32 import HiddenJob
import hidden_soak_log_observations as soak_log
import hidden_soak_probe_composition as soak_composition

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
    "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp", "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.def",
    "tools/hidden_soak_probe_composition.py", "tools/hidden_soak_log_observations.py",
    "probes/cdb/soak/clash95_hidden_soak_route_extra.cdb", "tools/hd_multires_route_extras.py")
# Continuity extras live in their own pinned module, so adding one never
# changes this file; every run also pins each extra template it lists.
PRODUCER_SOURCES = PRODUCERS + route_extras.SOURCES
SOAK_TEMPLATE = "probes/cdb/soak/clash95_hidden_soak_route_extra.cdb"
# The forced route uses absolute legacy addresses. All its breakpoint sites and
# the main-menu, load-list and PlayGame ranges are byte-identical to the
# original in every successor candidate, which loads at its preferred base.
MAP_IMAGE_BASE = 0x400000
MAP_LOAD_SLOT = 0
MAP_PAN_INTERVAL_SEC = 10
MAP_FRAME_INTERVAL_SEC = 60
MAP_END_GRACE_SEC = 120
# The route's own duration is the 64 Hz system tick delta at its end marker.
# The host clock only corroborates it, within the 0.25 s log-polling jitter at
# both ends plus margin.
MAP_HOST_JITTER_SEC = 2
MAP_MECHANISMS = dict(map_entry="cdb_forced_menu_load_route", start_animations="cdb_fast_forward_sleeps",
    acquisition="cdb_forced_bypass", drag_scroll="cdb_forced_skip")
# A hidden desktop denies DirectInput acquisition and the game then never
# enters its menu dispatch, so a hidden natural menu needs both disclosed steps.
HIDDEN_MENU_MECHANISMS = dict(start_animations="cdb_fast_forward_sleeps", acquisition="cdb_forced_bypass")
# The legacy acquisition bypass: Acquire is skipped and reports success.
ACQUISITION_BYPASS = (
    r'bp 0047BD66 ".printf \"HDSESSION_FORCE_ACQUIRE_BYPASS kind=mouse hwnd=%p device=%p\\n\", poi(005452dc), poi(@esi+8); r eax=0; r eip=0047bd73; gc"',
    r'bp 0047BDAE ".printf \"HDSESSION_FORCE_ACQUIRE_BYPASS kind=keyboard hwnd=%p device=%p\\n\", poi(005452dc), poi(@esi+4); r eax=0; r eip=0047bdbf; gc"',
)
PLAYGAME = re.compile(r"^HDSESSION_PLAYGAME pid=([0-9a-fA-F]+) gd=([0-9a-fA-F`]+) map=\((\d+),(\d+)\) "
    r"scroll=\((-?\d+),(-?\d+)\) surface=([0-9a-fA-F`]+) size=\((\d+),(\d+)\)$", re.M)
TARGET = re.compile(r"^HDSESSION_TARGET pid=([0-9a-fA-F]+) base=([0-9a-fA-F`]+)$", re.M)
MENU = re.compile(r"^HDSESSION_MENU_READY pid=([0-9a-fA-F]+) surface=([0-9a-fA-F`]+) width=(\d+) height=(\d+) pixels=([0-9a-fA-F`]+)$", re.M)
ACQUIRE = re.compile(r"^HDSESSION_ACQUIRE kind=(mouse|keyboard) pid=([0-9a-fA-F]+) pc=([0-9a-fA-F`]+) hr=0x([0-9a-fA-F]{8}) hwnd=([0-9a-fA-F`]+) device=([0-9a-fA-F`]+)$", re.M)
ACQUIRE_BLOCK = re.compile(r"^HDSESSION_ACQUIRE_BEGIN_(mouse|keyboard)\n([^\n]*)\nHDSESSION_ACQUIRE_END_\1$", re.M)
ACQUIRE_RETURNS = {"mouse": (0x7bd6f, 8), "keyboard": (0x7bdb7, 4)}
# The main-menu hit test runs every frame while the menu waits. The former
# 0x47d61 anchor is the dispatch poll, which only runs after a menu choice,
# so an idle menu never reached it.
MENU_READY_RVA = 0x19b80


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
        # Windows matches names case-insensitively, so GFX3.RES is a *.res
        # archive; apply that rule on every host instead of Path.glob's.
        base = source / directory
        if base.is_dir():
            selected.update(p.relative_to(source).as_posix() for p in base.iterdir()
                            if fnmatch.fnmatchcase(p.name.lower(), pattern.lower()) and p.is_file())
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


def _save_state(asset_root, name):
    """Hash one isolated save file, or None when its slot is empty."""
    path = asset_root / name
    if not path.exists():
        return None
    path = qualification.plain_path(path)
    stat = path.stat()
    return dict(sha256=_file_sha(path, route_extras.MAX_SAVE_BYTES), bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)


def _collect_route_extra(extra, asset_root, run, log_bytes, report):
    """Retain the extra's written saves and replay its markers; only failures are reported."""
    files = report["route_extra_files"]
    names = extra["pre_files"] + extra["post_files"]
    files["after"] = {name: _save_state(asset_root, name) for name in names}
    retained = {}
    for name in extra["post_files"]:
        state = files["after"][name]
        if state is None:
            raise ValueError("The route extra wrote no save: " + name)
        before = files["before"][name]
        if before is not None and state["mtime_ns"] <= before["mtime_ns"]:
            raise ValueError("The route extra did not rewrite its save: " + name)
        data = qualification.read_file(asset_root / name, route_extras.MAX_SAVE_BYTES)
        if _sha(data) != state["sha256"]:
            raise ValueError("A written save changed while it was retained: " + name)
        target = run / "route-extra" / Path(name).name
        target.parent.mkdir(exist_ok=True)
        _new(target, data)
        retained[name] = dict(path=f"route-extra/{target.name}", sha256=state["sha256"], bytes=len(data))
    files["retained"] = retained
    for name in extra["pre_files"]:
        if files["after"][name] != files["before"][name]:
            raise ValueError("The route extra's load slot changed during the run: " + name)
    observed, failures = route_extras.observe(extra, log_bytes.decode("latin-1"))
    report["route_extra_observations"] = observed
    return failures


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


def plan(bundle: Path, route="menu-idle", duration=120, *, smoke_only=False, acquire_only=False,
         hidden_menu_entry=False, route_extra=None):
    if smoke_only and acquire_only:
        raise ValueError("Select either initial smoke or acquisition observation, not both.")
    if hidden_menu_entry and (route != "menu-idle" or smoke_only or acquire_only):
        raise ValueError("Hidden menu entry applies only to the menu idle observation.")
    if route not in ROUTES or type(duration) is not int or duration not in ROUTES[route]:
        raise ValueError("Route/duration must preserve the fixed short-ladder or two-hour policy.")
    map_route = route != "menu-idle"
    if map_route and (smoke_only or acquire_only):
        raise ValueError("Initial-smoke and acquisition diagnostics use only the observation-only menu route.")
    extra = None if route_extra is None else route_extras.prepare(route_extra, route=route, duration=duration)
    bundle = qualification.plain_path(bundle)
    context = qualification.authenticate_bundle(bundle)
    declared = qualification.read_json(bundle)
    loaded = {name: qualification._reference(ref, bundle.parent, qualification.MAX_BYTES[name])
              for name, ref in declared["artifacts"].items()}
    metadata = qualification.policy.parse_evidence_json(loaded["metadata"][1], "candidate metadata")
    producers = {name: _sha(qualification.read_file(ROOT / name, 4 * 1024 * 1024)) for name in PRODUCER_SOURCES}
    cdb_hash = _pe_x86(CDB)
    rows = asset_inventory()
    pending = []
    if map_route:
        # Composing once here rejects a changed or malformed soak extra before any process exists.
        map_command_script(loaded["probe"][1], context["identity"], metadata, route=route, duration=duration,
                           soak_template=qualification.read_file(ROOT / SOAK_TEMPLATE, soak_composition.MAX_TEMPLATE_BYTES),
                           extra=extra, extra_template=_extra_template(extra))
    report = dict(schema=SCHEMA, executed=False, identity=context["identity"], bundle=str(bundle),
        bundle_sha256=_sha(bundle.read_bytes()), route=route, duration_sec=duration, smoke_only=smoke_only,
        acquire_only=acquire_only, diagnostic_scope=("initial_image_only" if smoke_only else
            "initial_image_and_native_acquisition_returns" if acquire_only else
            "forced_map_entry_and_native_arrow_pan" if route == "map-pan" else
            "forced_map_entry_and_steady_state" if map_route else
            "hidden_menu_entry_natural_menu_idle" if hidden_menu_entry else "natural_menu_idle_no_input"),
        forced_mechanisms=(MAP_MECHANISMS | ({"pan": "cdb_forced_native_arrow_key"} if route == "map-pan" else {})
                           | (extra["mechanisms"] if extra else {})
                           if map_route else dict(HIDDEN_MENU_MECHANISMS) if hidden_menu_entry else {}),
        hidden_menu_entry=hidden_menu_entry, route_extra=extra,
        input_or_callback_forced=map_route,
        load_slot=(extra["load_slot"] if extra else MAP_LOAD_SLOT) if map_route else None,
        pan_interval_sec=MAP_PAN_INTERVAL_SEC if route == "map-pan" else None,
        acquisition_return_rvas={kind: rva for kind, (rva, _) in ACQUIRE_RETURNS.items()},
        debugger_holds_at_acquisition_completion=acquire_only,
        environment="hidden_cdb_host", input_responsiveness="not_applicable_hidden", input_injected=False,
        source_authentication_passed=True, cdb=dict(path=str(CDB), sha256=cdb_hash, machine="x86"),
        producer_source_hashes=producers, isolated_asset_files=len(rows),
        isolated_asset_bytes=sum(r["bytes"] for r in rows), pending=pending,
        runtime_evidence_verified=False, manual_input_proof=False, promotion_ready=False,
        short_ladder_completed=False, endurance_completed=False, stable_stage_should_change=False)
    return report, context, loaded, metadata, rows


def command_script(probe: bytes, identity, metadata, *, smoke_only=False, acquire_only=False,
                   hidden_menu_entry=False):
    chunks = metadata["probe_contract"]["required_chunks"]
    if type(chunks) is not int or chunks <= 0:
        raise ValueError("Canonical initial-image chunk inventory is invalid.")
    if hidden_menu_entry and (smoke_only or acquire_only):
        raise ValueError("Hidden menu entry applies only to the menu idle observation.")
    suffix = [f'.if ((@$t19 == 0) | (@$t18 != 0n{chunks})) {{ .echo HDSESSION_INITIAL_REJECT; q }}',
        '.printf "HDSESSION_TARGET pid=%x base=%p\\n", @$tpid, @$t19']
    if hidden_menu_entry:
        # The proven fast-forward and bypass blocks use absolute legacy addresses.
        suffix[1:1] = [f".if (@$t19 != 0x{MAP_IMAGE_BASE:x}) {{ .echo HDSESSION_BASE_REJECT; q }}"]
    if smoke_only:
        suffix += ['.echo HDSESSION_INITIAL_SMOKE_COMPLETE', '.sleep 0n300000', 'q']
    else:
        # These are observers only; no input bytes, acquisition return values
        # or game state are forced. The opt-in hidden menu entry only skips the
        # intro sleeps and reports the denied acquisition as successful, both
        # disclosed; it writes no input, clicks or menu state.
        suffix += ['sxe -c ".echo HDSESSION_AV; .exr -1; r; kb; q" av',
            'bp /1 @$t19+0x1dda ".echo HDSESSION_APP_REQUEST_QUIT; kb; q"']
        if hidden_menu_entry:
            mechanisms = " ".join(f"{key}={value}" for key, value in HIDDEN_MENU_MECHANISMS.items())
            suffix += [f".echo HDSESSION_FORCED_ROUTE {mechanisms}", "r @$t12 = 0", "r @$t14 = 0",
                       *ACQUISITION_BYPASS, soak_composition.START_ANIMS_BREAKPOINTS]
        suffix += [f'bp /1 @$t19+0x{MENU_READY_RVA:x} ".printf \\"HDSESSION_MENU_READY pid=%x surface=%p width=%d height=%d pixels=%p\\\\n\\", @$tpid, @$t19+0x11d4c0, wo(@$t19+0x11d4c0), wo(@$t19+0x11d4c2), dwo(@$t19+0x11d4c4); gc"', 'g']
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


def _extra_template(extra):
    if extra is None:
        return None
    return qualification.read_file(ROOT / extra["template"], route_extras.MAX_TEMPLATE_BYTES)


def map_command_script(probe: bytes, identity, metadata, *, route, duration, soak_template: bytes,
                       extra=None, extra_template=None):
    """Canonical image replay, then the legacy forced map route and soak extra.

    The forced steps match probes/cdb/render/clash95_surface_dump_probe.cdb
    and the proven -FastForwardStartAnims block. Its 800x600 visibility
    and surface-dump gates are left out; the soak extra is the canonical
    composer's own substituted text. An optional continuity extra follows it
    on breakpoint sites nothing else uses. Every forced write is disclosed.
    """
    chunks = metadata["probe_contract"]["required_chunks"]
    if type(chunks) is not int or chunks <= 0:
        raise ValueError("Canonical initial-image chunk inventory is invalid.")
    if route not in ("map-idle", "map-pan") or duration not in ROUTES[route]:
        raise ValueError("Map routes preserve the fixed short-ladder or two-hour policy.")
    if (extra is None) != (extra_template is None):
        raise ValueError("A route extra needs exactly its own template.")
    width, height = (int(value) for value in identity["resolution"].split("x"))
    if width < 640 or height < 480:
        raise ValueError("The centered native menu needs at least a 640x480 canvas.")
    load_slot = extra["load_slot"] if extra else MAP_LOAD_SLOT
    soak = soak_composition.prepare_soak_text(soak_template, route=route, duration_sec=duration,
        pan_interval_sec=MAP_PAN_INTERVAL_SEC, load_slot=load_slot)
    # 0x419B80 compares the menu descriptors shifted by the centered 640x480
    # offset; the load list at 0x448A68 tests native, unshifted coordinates.
    main_x, main_y = (220 + (width - 640) // 2) << 6, (158 + (height - 480) // 2) << 6
    load_x, load_y = soak_composition.load_mouse_raw(load_slot)
    mouse = r"poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c)"
    mechanisms = " ".join(f"{key}={value}" for key, value in (MAP_MECHANISMS | (extra["mechanisms"] if extra else {})).items())
    pan = "cdb_forced_native_arrow_key" if route == "map-pan" else "none"
    lines = [
        f".if ((@$t19 == 0) | (@$t18 != 0n{chunks})) {{ .echo HDSESSION_INITIAL_REJECT; q }}",
        f".if (@$t19 != 0x{MAP_IMAGE_BASE:x}) {{ .echo HDSESSION_BASE_REJECT; q }}",
        '.printf "HDSESSION_TARGET pid=%x base=%p\\n", @$tpid, @$t19',
        f".echo HDSESSION_FORCED_ROUTE {mechanisms} pan={pan} load_slot={load_slot}",
        'sxe -c ".echo HDSESSION_AV; .exr -1; r; kb; q" av',
        *(f"r @$t{index} = 0" for index in range(18)),
        'bp 00401DDA ".echo HDSESSION_APP_REQUEST_QUIT; kb; q"',
        *ACQUISITION_BYPASS,
        soak_composition.START_ANIMS_BREAKPOINTS,
        (rf'bp 00419B80 ".if (@$t14 == 0) {{ .if (poi(00543d7c) != 5) {{ ed 00544cfc {main_x:08x}; ed 00544d00 {main_y:08x}; '
         rf'eb 005451c0 80; ed 00544d04 1; .if (@$t0 < 0n16) {{ .printf \"HDSESSION_FORCE_MAIN_POINT seq=%d choice=%d '
         rf'entry=0x%08x ex=%d ey=%d mouse=(%d,%d)\\n\", @$t0, poi(00543d7c), @eax, poi(@eax), poi(@eax+4), {mouse}; '
         rf'r @$t0 = @$t0 + 1; }}; }} .else {{ ed 00544cfc {load_x}; ed 00544d00 {load_y}; eb 005451c0 80; '
         rf'ed 00544d04 1; .if (@$t1 < 0n16) {{ .printf \"HDSESSION_FORCE_LOAD_POINT seq=%d choice=%d mouse=(%d,%d) '
         rf'selected=%d accept=%d\\n\", @$t1, poi(00543d7c), {mouse}, poi(005441e0), poi(00544190); '
         rf'r @$t1 = @$t1 + 1; }}; }}; }} .else {{ eb 005451c0 00; ed 00544d04 0; }}; gc"'),
        (rf'bp 00419C51 ".if (@$t14 == 0) {{ .if (poi(00543d7c) != 5) {{ r eax=1; .if (@$t2 < 0n8) {{ '
         rf'.printf \"HDSESSION_FORCE_MAIN_CLICK seq=%d desc=0x%08x mouse=(%d,%d)\\n\", @$t2, @ebx, {mouse}; '
         rf'r @$t2 = @$t2 + 1; }}; }}; }}; gc"'),
        (r'bp 00447780 ".printf \"HDSESSION_FORCE_SKIP_MAIN_LOAD_CALLBACK ret=%p choice_before=%d exit_before=%d\\n\", '
         r'poi(@esp), poi(00543d7c), poi(00543d78); ed 00543d7c 5; ed 00543d78 1; r eip=poi(@esp); r esp=@esp+4; gc"'),
        (rf'bp 00448A68 ".if (@$t14 == 0) {{ .if (poi(00543d7c) == 5) {{ ed 00544cfc {load_x}; ed 00544d00 {load_y}; '
         rf'eb 005451c0 80; ed 00544d04 1; r eax=1; .if (@$t4 < 0n8) {{ .printf \"HDSESSION_FORCE_LOAD_SELECT seq=%d '
         rf'mouse=(%d,%d) selected=%d accept=%d\\n\", @$t4, {mouse}, poi(005441e0), poi(00544190); '
         rf'r @$t4 = @$t4 + 1; }}; }}; }}; gc"'),
        (r'bp 00448AE3 ".if (@$t14 == 0) { .if (poi(00543d7c) == 5) { r eax=1; .if (@$t5 < 0n8) { '
         r'.printf \"HDSESSION_FORCE_LOAD_ACCEPT seq=%d selected=%d accept=%d\\n\", @$t5, poi(005441e0), poi(00544190); '
         r'r @$t5 = @$t5 + 1; }; }; }; gc"'),
        (r'bp 00444490 ".printf \"HDSESSION_LOADSAVE selected_arg=%d selected_global=%d accept=%d choice=%d gd=%p\\n\", '
         r'@eax, poi(005441e0), poi(00544190), poi(00543d7c), poi(005202e4); gc"'),
        (r'bp 0040B660 ".if (poi(005202e4) != 0) { .if (@$t14 == 0) { r @$t14 = 1; eb 005451c0 00; ed 00544d04 0; '
         r'.printf \"HDSESSION_PLAYGAME pid=%x gd=%p map=(%d,%d) scroll=(%d,%d) surface=%p size=(%d,%d)\\n\", @$tpid, '
         r'poi(005202e4), poi(poi(005202e4)+0n140000), poi(poi(005202e4)+0n140004), poi(poi(005202e4)+0n140008), '
         r'poi(poi(005202e4)+0n140012), poi(005202e0), wo(poi(005202e0)), wo(poi(005202e0)+2); }; } '
         r'.else { .echo HDSESSION_PLAYGAME_NO_GAME_DATA; }; gc"'),
        # The unacquired DirectInput mouse can report a held right button; the
        # original drag handler (0x407B90) then reads a far-left pointer and
        # scrolls the map by a page. After map entry every drag start takes the
        # handler's own not-held exit (0x407BC6) and is logged.
        (r'bp 00407BD7 ".if (@$t14 != 0) { .if (@$t3 < 0n16) { .printf \"HDSESSION_FORCE_SKIP_DRAG_SCROLL seq=%d '
         r'flags=%08x buttons=%02x/%02x mouse=(%d,%d) scroll=(%d,%d)\\n\", @$t3, poi(00544d04), by(005451c0), '
         r'by(005451c8), poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c), poi(poi(005202e4)+0n140008), '
         r'poi(poi(005202e4)+0n140012); r @$t3 = @$t3 + 1; }; r eip = 00407bc6; }; gc"'),
        soak,
        *([route_extras.compose(extra, extra_template)] if extra else []),
        "g",
    ]
    text = "\r\n".join(lines)
    if not soak_composition._PLAIN_TEXT.fullmatch(text) or soak_composition._LEFTOVER_PLACEHOLDER.search(text):
        raise ValueError("Forced map route must be plain ASCII without unsubstituted placeholders.")
    # A second bp on one address silently replaces the first, so an extra may
    # never reuse a site of the route or soak extra.
    sites = route_extras.breakpoint_sites(text)
    if len(sites) != len(set(sites)):
        raise ValueError("Forced map route breakpoint sites must be unique; a route extra collides.")
    return probe + ("\r\n" + text + "\r\n").encode("ascii")


def parse_observations(log: str, identity, metadata):
    marker = metadata["probe_contract"]["acceptance_marker"]
    lines = log.splitlines()
    verified = lines.count(marker) == 1
    targets = TARGET.findall(log)
    menus = MENU.findall(log)
    failures = []
    if len(targets) > 1 or len(menus) > 1:
        failures.append("duplicate target/menu observation")
    if any(token in lines for token in ("HDSESSION_AV", "HDSESSION_INITIAL_REJECT", "HDSESSION_BASE_REJECT",
                                         "HDSESSION_APP_REQUEST_QUIT")):
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
        # The descriptor holds a pixel pointer only while the menu surface is locked.
        if ((menu["width"], menu["height"]) not in ((640, 480), selected)
                or not (menu["pixels"] == 0 or 0x10000 <= menu["pixels"] < 0x80000000)):
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


PROXY_CREATED = re.compile(r"^FakeSurface created this=([0-9A-Fa-f]{8}) size=(\d+)x(\d+) pitch=(\d+) caps=0x[0-9A-Fa-f]{8}$", re.M)
PROXY_LOCK = re.compile(r"^FakeSurface Lock this=([0-9A-Fa-f]{8}) rect=-1,-1,-1,-1 surface=([0-9A-Fa-f]{8})$", re.M)
PROXY_DESTROYED = re.compile(r"^FakeSurface destroyed this=([0-9A-Fa-f]{8})$", re.M)


def proxy_surface_buffer(log: str, width: int, height: int):
    """The source-built proxy's one buffer for the live full-canvas surface, or None.

    An idle menu stops locking its surface, so the game descriptor's pixel
    pointer is usually 0; the proxy keeps the last drawn image in this buffer.
    The log is replayed in order: the heap can recreate a destroyed surface at
    the same address, so only each address's latest creation and the Locks
    after it count.
    """
    live = {}
    for line in log.splitlines():
        if created := PROXY_CREATED.fullmatch(line):
            this, w, h, pitch = created.groups()
            live[this] = dict(canvas=(int(w), int(h), int(pitch)) == (width, height, width), buffers=set())
        elif destroyed := PROXY_DESTROYED.fullmatch(line):
            live.pop(destroyed[1], None)
        elif (locked := PROXY_LOCK.fullmatch(line)) and locked[1] in live:
            live[locked[1]]["buffers"].add(locked[2])
    canvases = [surface for surface in live.values() if surface["canvas"]]
    if len(canvases) != 1 or len(canvases[0]["buffers"]) != 1:
        return None
    return int(canvases[0]["buffers"].pop(), 16)


def _read_log(path):
    if not path.exists():
        return ""
    if path.stat().st_size > MAX_LOG:
        raise ValueError("CDB diagnostic log exceeded its retained output budget.")
    return path.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")


class _LogTail:
    """Complete new log lines since the last read, so long routes never rescan the probe echo."""

    def __init__(self, path, offset=0):
        self.path, self.offset, self.partial = path, offset, b""

    def lines(self):
        size = self.path.stat().st_size
        if size > MAX_LOG:
            raise ValueError("CDB diagnostic log exceeded its retained output budget.")
        if size < self.offset:
            raise ValueError("CDB diagnostic log shrank below lines already observed.")
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            chunk = stream.read(size - self.offset)
        self.offset += len(chunk)
        *complete, self.partial = (self.partial + chunk).split(b"\n")
        return [line.rstrip(b"\r").decode("latin-1").strip() for line in complete]


MAP_FAILURE_TOKENS = ("HDSESSION_AV", "HDSESSION_INITIAL_REJECT", "HDSESSION_BASE_REJECT",
    "HDSESSION_APP_REQUEST_QUIT", "HDSESSION_PLAYGAME_NO_GAME_DATA")


def map_ready(log: str, identity, target):
    """Bind the single map entry and soak-ready rows to the adopted process and selected canvas."""
    failures = []
    lines = log.splitlines()
    if any(token in lines for token in MAP_FAILURE_TOKENS):
        failures.append("native exception, rejected image/base, application quit or missing game data observed")
    if any(line.startswith("SOAK_PAN_UNSAFE") for line in lines):
        failures.append("forced pan found no safe inward direction on the loaded map")
    games = PLAYGAME.findall(log)
    rows = soak_log.parse_soak_log(log.encode("latin-1", errors="replace"))
    failures.extend(rows["failures"])
    ready = [row for row in rows["ReadyRows"] if row["Source"] == "SOAK_SURFDUMP_READY"]
    if len(games) > 1 or len(ready) > 1 or len(rows["RouteStarts"]) > 1:
        failures.append("duplicate map entry, route start or soak-ready observation")
    playgame = surface = None
    if len(games) == 1:
        pid, gd, map_w, map_h, scroll_x, scroll_y, descriptor, width, height = games[0]
        playgame = dict(pid=int(pid, 16), game_data=int(gd.replace("`", ""), 16), map=(int(map_w), int(map_h)),
                        scroll=(int(scroll_x), int(scroll_y)), surface=int(descriptor.replace("`", ""), 16),
                        size=(int(width), int(height)))
        if target is None or playgame["pid"] != target["pid"] or playgame["game_data"] == 0:
            failures.append("map entry belongs to a different process or has no game data")
    if len(ready) == 1 and len(rows["RouteStarts"]) == 1:
        row = ready[0]
        surface = dict(descriptor=int(row["Surface"].replace("`", ""), 16), width=row["Width"], height=row["Height"],
                       pixels=int(row["Base"].replace("`", ""), 16), bytes=row["Bytes"],
                       route_start=rows["RouteStarts"][0])
        selected = tuple(map(int, identity["resolution"].split("x")))
        if ((surface["width"], surface["height"]) != selected or surface["bytes"] != selected[0] * selected[1]
                or not 0x10000 <= surface["pixels"] < 0x80000000 or not 0x10000 <= surface["descriptor"] < 0x80000000):
            failures.append("map surface differs from the selected canvas or has an invalid pointer")
        if playgame is None:
            failures.append("soak route started without the bound forced map entry")
    return dict(playgame=playgame, surface=surface, failures=failures)


MENU_FAILURE_TOKENS = ("HDSESSION_AV", "HDSESSION_INITIAL_REJECT", "HDSESSION_BASE_REJECT",
    "HDSESSION_APP_REQUEST_QUIT")


def _menu_idle(native, target, debugger, tail, bound, menu, pixels, run, report, preflight):
    """Sample one idle main menu for the route duration, reading only new log lines."""
    duration = preflight["duration_sec"]
    started = next_sample = next_frame = time.monotonic()
    first_controls = None
    while True:
        now = time.monotonic()
        for line in tail.lines():
            if line in MENU_FAILURE_TOKENS:
                raise ValueError("Menu idle recorded a runtime failure: " + line)
        if not native.alive(debugger) or not native.alive(target):
            raise ValueError("Debugger/candidate exited before the requested diagnostic completed.")
        if now >= next_sample:
            controls = native.read(target, bound["base"] + 0x143d78, 8)
            first_controls = first_controls or controls
            if controls != first_controls or struct.unpack_from("<I", controls)[0] != 0:
                raise ValueError("Native main-menu control/exit state changed during the idle diagnostic.")
            width, height, locked = struct.unpack("<HHI", native.read(target, menu["surface"], 8))
            if (width, height) != (menu["width"], menu["height"]) or locked not in (0, pixels):
                raise ValueError("Native menu surface descriptor changed during sampling.")
            report["samples"].append(dict(elapsed_sec=now - started,
                menu_exit=struct.unpack_from("<I", controls)[0], menu_choice=struct.unpack_from("<I", controls, 4)[0],
                **native.telemetry(target)))
            next_sample += 1  # A fixed one-second grid, so sampling never drifts behind the route.
        if now >= next_frame or now - started >= duration:
            count = menu["width"] * menu["height"]
            qualification._reserve(run, count + 32 * 1024 * 1024)
            frame = native.read(target, pixels, count)
            filename = f"menu-frame-{len(report['frames']):04d}.indexed8"
            _new(run / filename, frame)
            report["frames"].append(dict(path=filename, sha256=_sha(frame), bytes=count,
                elapsed_sec=now - started, width=menu["width"], height=menu["height"],
                coherent_snapshot_verified=False))
            next_frame = now + 30
        if now - started >= duration:
            report["natural_menu_idle_verified"] = True
            report["measured_menu_host_seconds"] = now - started
            return
        time.sleep(0.25)


def _map_steady_state(native, target, debugger, log_path, tail, seen, run, report, preflight, ready):
    """Sample one forced map route until its own end marker, then replay the whole retained log.

    ``seen`` holds the lines the readiness poll already consumed from ``tail``.
    """
    surface, route, duration = ready["surface"], preflight["route"], preflight["duration_sec"]
    report["map_entry"] = ready["playgame"]
    report["map_surface"] = {key: surface[key] for key in ("descriptor", "width", "height", "pixels", "bytes")}
    descriptor = struct.pack("<HHI", surface["width"], surface["height"], surface["pixels"])
    started = next_sample = next_frame = time.monotonic()
    ended = None
    print(json.dumps(dict(event="forced_map_ready", route=route, duration_sec=duration,
                          surface=report["map_surface"])), flush=True)
    while True:
        now = time.monotonic()
        lines, seen = seen + tail.lines(), []
        for line in lines:
            if line in MAP_FAILURE_TOKENS or line in ("AV_SURFDUMP", "SURFDUMP_INVALID") or line.startswith("SOAK_PAN_UNSAFE"):
                raise ValueError("Map route recorded a runtime failure: " + line)
            if line.startswith("SOAK_ROUTE_END "):
                ended = now
        if not native.alive(debugger) or not native.alive(target):
            raise ValueError("Debugger/candidate exited before the soak route end.")
        if now >= next_sample:
            if native.read(target, surface["descriptor"], 8) != descriptor:
                raise ValueError("Map surface descriptor changed during sampling.")
            report["samples"].append(dict(elapsed_sec=now - started, **native.telemetry(target)))
            next_sample += 1  # A fixed one-second grid, so sampling never drifts behind the route.
        if now >= next_frame or ended is not None:
            qualification._reserve(run, surface["bytes"] + 32 * 1024 * 1024)
            frame = native.read(target, surface["pixels"], surface["bytes"])
            filename = f"map-frame-{len(report['frames']):04d}.indexed8"
            _new(run / filename, frame)
            report["frames"].append(dict(path=filename, sha256=_sha(frame), bytes=surface["bytes"],
                elapsed_sec=now - started, width=surface["width"], height=surface["height"],
                coherent_snapshot_verified=False))
            next_frame = now + MAP_FRAME_INTERVAL_SEC
        if ended is not None:
            report["measured_map_host_seconds"] = ended - started
            break
        if now - started > duration + MAP_END_GRACE_SEC:
            raise TimeoutError("The soak route end was not observed within its bounded interval.")
        time.sleep(0.25)
    rows = soak_log.parse_soak_log(log_path.read_bytes())
    failures = list(rows["failures"]) + soak_log._global_order_failures(rows)
    ticks = duration * soak_composition.TICKS_PER_SECOND
    end = rows["RouteEnds"][0] if len(rows["RouteEnds"]) == 1 else None
    if end is None or end["RouteTicks"] != ticks or end["TickDelta"] < ticks or end["Pan"] != (route == "map-pan"):
        failures.append("soak route end does not cover the fixed route duration")
    if report["measured_map_host_seconds"] < duration - MAP_HOST_JITTER_SEC:
        failures.append("host clock does not corroborate the fixed route duration")
    if route == "map-pan":
        if len(rows["PanPlans"]) != 1 or len(rows["PanEvents"]) < duration // MAP_PAN_INTERVAL_SEC - 2:
            failures.append("forced pan route lacks its single plan or its scheduled native arrow-key steps")
    elif rows["PanPlans"] or rows["PanEvents"]:
        failures.append("idle map route recorded forced pan rows")
    report["drag_scroll_skips"] = sum(line.startswith(b"HDSESSION_FORCE_SKIP_DRAG_SCROLL ")
                                      for line in log_path.read_bytes().split(b"\n"))
    report["soak_route"] = dict(route_start=rows["RouteStarts"][0] if rows["RouteStarts"] else None, route_end=end,
        heartbeats=len(rows["Heartbeats"]), pan_plans=rows["PanPlans"], pan_events=len(rows["PanEvents"]),
        final_scroll=[end["ScrollX"], end["ScrollY"]] if end else None, failures=failures)
    if failures:
        raise ValueError("; ".join(failures))
    report["map_route_completed"] = True
    print(json.dumps(dict(event="forced_map_route_completed", route=route, frames=len(report["frames"]),
                          heartbeats=len(rows["Heartbeats"]), pan_events=len(rows["PanEvents"]))), flush=True)


def execute(preflight, context, loaded, metadata, rows, *, output_root, asset_root, ready_timeout=300):
    if preflight["pending"]:
        raise ValueError("; ".join(preflight["pending"]))
    output_root, asset_root = _external(output_root), _external(asset_root)
    qualification._reserve(output_root, sum(row["bytes"] for row in rows) + 512 * 1024 * 1024)
    print(json.dumps(dict(event="isolated_asset_stage", files=len(rows), bytes=sum(r["bytes"] for r in rows))), flush=True)
    stage_assets(asset_root, rows)
    run = output_root / ("session-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    run.mkdir(parents=True, exist_ok=False)
    map_route = preflight["route"] != "menu-idle"
    report = preflight | dict(executed=True, started_at=_now(), run_directory=str(run), failures=[],
        initial_image_bytes_verified=False, natural_menu_idle_verified=False, native_processes=[], frames=[], samples=[],
        acquisition_returns=[], acquisition_observation_completed=False, input_acquisition_verified=False,
        map_entry=None, map_surface=None, map_route_completed=False, soak_route=None)
    _json(run / "preflight.json", preflight)
    local_candidate = run / "clash95_hd_session.exe"
    _new(local_candidate, loaded["executable"][1])
    commands = run / "session.cdb"
    extra = preflight.get("route_extra")
    report["asset_root"] = str(asset_root)
    if map_route:
        soak_template = qualification.read_file(ROOT / SOAK_TEMPLATE, soak_composition.MAX_TEMPLATE_BYTES)
        if _sha(soak_template) != preflight["producer_source_hashes"][SOAK_TEMPLATE]:
            raise ValueError("Soak route template changed after preflight.")
        extra_template = _extra_template(extra)
        if extra and _sha(extra_template) != preflight["producer_source_hashes"][extra["template"]]:
            raise ValueError("Route extra template changed after preflight.")
        _new(commands, map_command_script(loaded["probe"][1], context["identity"], metadata,
            route=preflight["route"], duration=preflight["duration_sec"], soak_template=soak_template,
            extra=extra, extra_template=extra_template))
        if extra:
            # Before any process exists: the slot the route will load and the
            # slot it will save, so the run proves both its source and its write.
            report["route_extra_files"] = dict(before={name: _save_state(asset_root, name)
                for name in extra["pre_files"] + extra["post_files"]}, after=None, retained=None)
            if report["route_extra_files"]["before"][extra["pre_files"][0]] is None:
                raise ValueError("The route extra's load slot has no isolated save to load.")
    else:
        _new(commands, command_script(loaded["probe"][1], context["identity"], metadata,
            smoke_only=preflight["smoke_only"], acquire_only=preflight.get("acquire_only", False),
            hidden_menu_entry=preflight.get("hidden_menu_entry", False)))
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
        start, menu_started = time.monotonic(), None
        target_handle = None
        map_tail, map_lines, map_target = None, [], None
        while True:
            if map_tail is not None:
                # The canonical image and target are bound; read only new lines from here on.
                now = time.monotonic()
                map_lines.extend(map_tail.lines())
                if not native.alive(cdb_handle) or not native.alive(target_handle):
                    raise ValueError("Debugger/candidate exited before the forced map route was ready.")
                ready = map_ready("\n".join(map_lines), context["identity"], map_target)
                if ready["failures"]:
                    raise ValueError("; ".join(ready["failures"]))
                if ready["surface"] is not None:
                    _map_steady_state(native, target_handle, cdb_handle, log, map_tail, map_lines, run, report,
                                      preflight, ready)
                    break
                if now - start > ready_timeout:
                    raise TimeoutError("Forced map entry and soak readiness were not observed within the bounded startup interval.")
                time.sleep(0.25)
                continue
            raw = log.read_bytes() if log.exists() else b""
            if len(raw) > MAX_LOG:
                raise ValueError("CDB diagnostic log exceeded its retained output budget.")
            text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
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
            if map_route:
                if not native.alive(cdb_handle) or (target_handle and not native.alive(target_handle)):
                    raise ValueError("Debugger/candidate exited before the forced map route was ready.")
                if observed["initial_image_bytes_verified"] and target_handle is not None:
                    complete = text.split("\n")[:-1]  # The tail rereads any partial last line.
                    marker = next(index for index, line in enumerate(complete) if TARGET.fullmatch(line.strip()))
                    map_target, map_lines = observed["target"], [line.strip() for line in complete[marker + 1:]]
                    map_tail = _LogTail(log, raw.rfind(b"\n") + 1)
                    continue
                if now - start > ready_timeout:
                    raise TimeoutError("Forced map entry and soak readiness were not observed within the bounded startup interval.")
                time.sleep(0.25)
                continue
            if observed["menu"] and menu_started is None:
                if not observed["initial_image_bytes_verified"] or target_handle is None:
                    raise ValueError("Menu observation precedes authenticated image/process binding.")
                menu = observed["menu"]
                menu_pixels = menu["pixels"] or proxy_surface_buffer(
                    _read_log(run / "ddraw_surfdump_proxy.log"), menu["width"], menu["height"])
                if menu_pixels is not None:
                    menu_started = now
                    report["menu_surface"] = menu | dict(frame_pixels=menu_pixels, frame_source=(
                        "game_descriptor" if menu["pixels"] else "proxy_surface_buffer"))
                    print(json.dumps(dict(event="natural_menu_observed", identity=context["identity"], duration_sec=preflight["duration_sec"])), flush=True)
                    _menu_idle(native, target_handle, cdb_handle, _LogTail(log, raw.rfind(b"\n") + 1),
                               observed["target"], menu, menu_pixels, run, report, preflight)
                    break
            if not native.alive(cdb_handle) or (target_handle and not native.alive(target_handle)):
                raise ValueError("Debugger/candidate exited before the requested diagnostic completed.")
            if menu_started is None and now - start > ready_timeout:
                raise TimeoutError(("Native acquisition returns" if preflight.get("acquire_only") else "Natural menu readiness")
                    + " were not observed within the bounded startup interval.")
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
        # The debugger has exited, so the log is final: pin it for later replay.
        final_log = b""
        try:
            final_log = log.read_bytes() if log.exists() else b""
            report["retained_log"] = dict(path=log.name, sha256=_sha(final_log), bytes=len(final_log))
        except OSError as error:
            report["failures"].append("Retained CDB log could not be pinned: " + str(error))
        if extra and report.get("route_extra_files"):
            try:
                report["failures"].extend(_collect_route_extra(extra, asset_root, run, final_log, report))
            except (OSError, ValueError) as error:
                report["failures"].append("Route extra collection failed: " + str(error))
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
            preflight["smoke_only"] or report["natural_menu_idle_verified"] or report["acquisition_observation_completed"]
            or report["map_route_completed"])
        _json(run / "session-report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--route", choices=tuple(ROUTES), default="menu-idle")
    parser.add_argument("--duration", type=int, default=120)
    parser.add_argument("--smoke-only", action="store_true", help="stop after canonical initial bytes; supplies no menu/endurance pass")
    parser.add_argument("--acquire-only", action="store_true", help="observe genuine mouse/keyboard HRESULT returns; never force acquisition or input")
    parser.add_argument("--hidden-menu-entry", action="store_true",
                        help="menu-idle only: skip the intro sleeps and the hidden desktop's denied acquisition, both disclosed; never input, clicks or menu state")
    parser.add_argument("--route-extra", type=json.loads, default=None,
                        help='map-idle 120 only: one disclosed continuity extra as JSON, e.g. '
                             '{"name": "forced-save", "load_slot": 0, "save_slot": 7}')
    parser.add_argument("--output-root", type=Path, default=Path("C:/ClashTests/hd-multires-hidden"))
    parser.add_argument("--asset-root", type=Path, default=Path("C:/ClashTests/hd-multires-runtime-assets-20261025"))
    parser.add_argument("--ready-timeout", type=int, default=300)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not 30 <= args.ready_timeout <= 600:
        parser.error("--ready-timeout must be between 30 and 600 seconds")
    try:
        preflight, context, loaded, metadata, rows = plan(args.bundle, args.route, args.duration,
            smoke_only=args.smoke_only, acquire_only=args.acquire_only, hidden_menu_entry=args.hidden_menu_entry,
            route_extra=args.route_extra)
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
