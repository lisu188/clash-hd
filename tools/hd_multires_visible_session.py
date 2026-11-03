#!/usr/bin/env python3
"""Prepare one exact visible acquisition/menu session; approval gates execution.

Default operation reads and authenticates only. No keyboard or mouse injection
is implemented. A fresh approval bound to the complete saved plan is mandatory
before default-desktop launch, owned-window activation or optional PrintWindow.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import struct
import threading
import time

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import hd_multires_hidden_session as hidden
from hd_multires_visible_win32 import DefaultDesktopJob, OwnedWindow

SCHEMA = "hd_multires_visible_session_plan_v1"
APPROVAL = "hd_multires_visible_session_approval_v1"
SCOPE = ["visible_launch", "owned_window_foreground_activation"]
PRODUCERS = (*hidden.PRODUCERS, "tools/hd_multires_visible_session.py", "tools/hd_multires_visible_win32.py")
WINDOW = re.compile(r"^HDSESSION_WINDOW_BEGIN\nHDSESSION_WINDOW_READY pid=([0-9a-fA-F]+) pc=([0-9a-fA-F`]+) hwnd=([0-9a-fA-F`]+)\nHDSESSION_WINDOW_END$", re.M)


class NativeDeadline:
    """Kill only the retained task job at the approved maximum, even in a GUI call."""
    def __init__(self, job, seconds):
        self.job, self.lock = job, threading.Lock()
        self.armed, self.expired, self.termination_requested = True, False, False
        self.timer = threading.Timer(seconds, self._expire)
        self.timer.daemon = True

    def _expire(self):
        with self.lock:
            if self.armed:
                self.expired = True
                self.termination_requested = bool(self.job.kernel.TerminateJobObject(self.job.job, 0x4844))

    def start(self):
        self.timer.start()
        return self

    def stop(self):
        self.timer.cancel()
        with self.lock:
            self.armed = False
            return dict(deadline_reached=self.expired, task_job_termination_requested=self.termination_requested)


def _stage_snapshot(root, rows):
    root = hidden._external(root)
    if not root.is_dir():
        raise ValueError("Visible plan requires the previously isolated asset directory; dry-run never copies it.")
    hidden.stage_assets(root, rows, create=False)
    names = {row["path"] for row in rows}
    names.update(p.relative_to(root).as_posix() for p in (root / "save").iterdir())
    return dict(manifest_sha256=hidden._file_sha(root / "asset-stage.json", 2 * 1024 * 1024),
        files=[dict(path=name, bytes=(root / name).stat().st_size, sha256=hidden._file_sha(root / name)) for name in sorted(names)])


def command_script(probe, identity, metadata):
    result = hidden.command_script(probe, identity, metadata)
    # The native CreateWindow return is observed before the HWND store. The
    # disclosed three-second debugger hold allows approved host activation;
    # no register, game state, acquisition HRESULT or input is changed.
    body = ('.printf "HDSESSION_CONTEXT_WARMUP pid=%x pc=%p hwnd=%p\\n", @$tpid, @eip, @eax; '
        '.echo HDSESSION_WINDOW_BEGIN; '
        '.printf "HDSESSION_WINDOW_READY pid=%x pc=%p hwnd=%p\\n", @$tpid, @eip, @eax; '
        '.echo HDSESSION_WINDOW_END; .sleep 0n3000; gc')
    line = 'bp /1 @$t19+0x61ace "' + body.replace('\\', '\\\\').replace('"', '\\"') + '"\r\n'
    if not result.endswith(b"g\r\n"):
        raise ValueError("Exact observation script lacks the expected final continue.")
    return result[:-3] + line.encode("ascii") + b"g\r\n"


def prepare(bundle, *, proxy, asset_root, session_dir, capture_owned_window=False):
    preflight, context, loaded, metadata, rows = hidden.plan(bundle)
    if context["identity"]["cell_id"] != "classic/1920x1080":
        raise ValueError("This reviewable visible protocol is limited to Classic1920x1080.")
    proxy = hidden.qualification.plain_path(proxy)
    if not proxy.is_relative_to(hidden.EXTERNAL):
        raise ValueError("The presenting proxy must be the retained source-built local artifact.")
    proxy_sha = hidden._pe_x86(proxy)
    build_manifest = proxy.parent / "ddraw_surfdump_proxy.build.json"
    built = hidden.qualification.read_json(build_manifest)
    cpp_sha = hidden._file_sha(hidden.ROOT / "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp", 4 * 1024 * 1024)
    if (built.get("generated_by") != "clash-hd-surface-dump-proxy" or
            str(built.get("source_sha256", "")).lower() != cpp_sha or
            str(built.get("output_sha256", "")).lower() != proxy_sha or
            Path(built.get("output", "")) != proxy):
        raise ValueError("Presenting proxy does not match its retained source/build manifest.")
    session_dir, asset_root = hidden._external(session_dir), hidden._external(asset_root)
    if session_dir.exists():
        raise ValueError("Visible session directory must be new, so an approval cannot replay a completed session.")
    script = command_script(loaded["probe"][1], context["identity"], metadata)
    plan = dict(schema=SCHEMA, executed=False, identity=context["identity"], bundle=str(bundle),
        bundle_sha256=preflight["bundle_sha256"], source_hashes=context["source_hashes"],
        canonical_probe_sha256=context["identity"]["probe_sha256"], session_script_sha256=hidden._sha(script),
        cdb=preflight["cdb"], proxy=dict(path=str(proxy), sha256=proxy_sha,
            build_manifest_path=str(build_manifest), build_manifest_sha256=hidden._file_sha(build_manifest, 2 * 1024 * 1024)),
        producer_source_hashes={name: hidden._file_sha(hidden.ROOT / name, 4 * 1024 * 1024) for name in PRODUCERS},
        python=dict(path=sys.executable, sha256=hidden._file_sha(Path(sys.executable), 32 * 1024 * 1024)),
        asset_root=str(asset_root), asset_snapshot=_stage_snapshot(asset_root, rows), session_dir=str(session_dir),
        environment="visible_cdb_host", desktop="winsta0\\default", wrapper_mode="source_proxy_present",
        child_environment=dict(CLASH_PROXY_PRESENT="1", _NT_SYMBOL_PATH=".", _NT_ALT_SYMBOL_PATH=""),
        maximum_session_sec=300, natural_menu_idle_sec=120, window_creation_debugger_hold_sec=3,
        scope=SCOPE + (["capture_owned_window"] if capture_owned_window else []),
        capture_owned_window=bool(capture_owned_window), keyboard_input_injected=False, mouse_input_injected=False,
        requires_fresh_user_approval=True, approval_record=None, runtime_evidence_verified=False,
        manual_input_proof=False, promotion_ready=False, short_ladder_completed=False, endurance_completed=False)
    plan["plan_sha256"] = hidden._sha(hidden.qualification.canonical(plan))
    return plan, context, loaded, metadata


def verify_approval(record, plan, *, now=None):
    now = now or datetime.now(timezone.utc)
    if (record.get("schema") != APPROVAL or record.get("approved") is not True or
            record.get("plan_sha256") != plan["plan_sha256"] or record.get("scope") != plan["scope"] or
            not isinstance(record.get("user_response"), str) or not record["user_response"].strip() or
            not isinstance(record.get("approval_question"), str) or not record["approval_question"].strip() or
            not isinstance(record.get("thread_id"), str) or not record["thread_id"].strip()):
        raise ValueError("Fresh real-user approval for the exact visible plan and scope is required.")
    try:
        recorded = datetime.fromisoformat(record["recorded_at_utc"])
        if recorded.tzinfo is None or not 0 <= (now - recorded).total_seconds() <= 12 * 3600:
            raise ValueError("Approval is future-dated, stale or lacks a timezone.")
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Approval timestamp must be fresh and timezone-aware.") from error
    return True


def reconstruct(saved):
    rebuilt = prepare(Path(saved["bundle"]), proxy=Path(saved["proxy"]["path"]),
        asset_root=Path(saved["asset_root"]), session_dir=Path(saved["session_dir"]),
        capture_owned_window=saved["capture_owned_window"])
    if saved != rebuilt[0]:
        raise ValueError("Saved visible plan differs from fresh artifact/source/asset reconstruction.")
    return rebuilt


def verify_plan_files(plan, *, before_launch):
    if hidden._file_sha(Path(plan["bundle"]), 2 * 1024 * 1024) != plan["bundle_sha256"]:
        raise ValueError("Candidate bundle index changed after plan verification.")
    for name, expected in (plan["source_hashes"] | plan["producer_source_hashes"]).items():
        if hidden._file_sha(hidden.ROOT / name, 4 * 1024 * 1024) != expected:
            raise ValueError("Planned source changed: " + name)
    if hidden._file_sha(Path(plan["proxy"]["build_manifest_path"]), 2 * 1024 * 1024) != plan["proxy"]["build_manifest_sha256"]:
        raise ValueError("Proxy build manifest changed after plan verification.")
    assets = Path(plan["asset_root"])
    if hidden._file_sha(assets / "asset-stage.json", 2 * 1024 * 1024) != plan["asset_snapshot"]["manifest_sha256"]:
        raise ValueError("Isolated asset manifest changed after plan verification.")
    if before_launch:
        current_save_names = {p.relative_to(assets).as_posix() for p in (assets / "save").iterdir()}
        planned_save_names = {r["path"] for r in plan["asset_snapshot"]["files"] if r["path"].startswith("save/")}
        if current_save_names != planned_save_names:
            raise ValueError("Isolated save inventory changed after approval.")
    for row in plan["asset_snapshot"]["files"]:
        path = hidden.qualification.plain_path(assets / row["path"])
        if before_launch or not (row["path"].startswith("save/") or row["path"] in ("CLASH.CFG", "options.cfg", "default.rec")):
            if hidden._file_sha(path) != row["sha256"]:
                raise ValueError("Planned isolated asset changed: " + row["path"])
    # Validate newly created state too, although changed content is allowed
    # after an approved game run in this isolated directory.
    for path in (assets / "save").iterdir():
        hidden.qualification.plain_path(path)
    return True


def execute(saved, approval_path):
    approval_path = hidden.qualification.plain_path(approval_path)
    approval_raw = hidden.qualification.read_file(approval_path, 1024 * 1024)
    approval = hidden.qualification.policy.parse_evidence_json(approval_raw, "visible approval")
    verify_approval(approval, saved)  # Before staging, files, desktop or process creation.
    plan, context, loaded, metadata = reconstruct(saved)
    run, assets = Path(plan["session_dir"]), Path(plan["asset_root"])
    hidden.qualification._reserve(run, 256 * 1024 * 1024)
    run.mkdir(parents=True, exist_ok=False)
    hidden._json(run / "approved-plan.json", plan)
    hidden._new(run / "user-approval.json", approval_raw)
    local_candidate, local_proxy, commands = run / "clash95_hd_session.exe", run / "ddraw.dll", run / "session.cdb"
    hidden._new(local_candidate, loaded["executable"][1])
    hidden._new(local_proxy, hidden.qualification.read_file(Path(plan["proxy"]["path"]), 32 * 1024 * 1024))
    hidden._new(commands, command_script(loaded["probe"][1], context["identity"], metadata))
    launch = dict(candidate=dict(path=str(local_candidate), sha256=context["identity"]["candidate_sha256"]),
        proxy=dict(path=str(local_proxy), sha256=plan["proxy"]["sha256"]),
        script=dict(path=str(commands), sha256=plan["session_script_sha256"]), debugger=plan["cdb"],
        approval=dict(path=str(run / "user-approval.json"), sha256=hidden._sha(approval_raw)))
    report = dict(schema="hd_multires_visible_session_report_v1", executed=True, plan_sha256=plan["plan_sha256"],
        identity=context["identity"], started_at=hidden._now(), failures=[], native_processes=[],
        initial_image_bytes_verified=False, acquisition_returns=[], window_activations=[], captures=[],
        natural_menu_idle_verified=False, runtime_evidence_verified=False, manual_input_proof=False,
        input_injected=False, input_acquisition_verified=False, promotion_ready=False, samples=[],
        short_ladder_completed=False, endurance_completed=False, launch_artifacts=launch)
    before_saves = hidden._live_save_hashes()
    job, target, target_identity, window, hwnd, deadline = None, None, None, None, None, None
    try:
        hidden.verify_launch_artifacts(launch)
        verify_plan_files(plan, before_launch=True)
        verify_approval(approval, plan)
        job = DefaultDesktopJob()
        job.open()
        debugger, debugger_identity = job.spawn(hidden.CDB,
            ["-y", ".", "-logo", str(run / "cdb.log"), "-cf", str(commands), str(local_candidate)],
            assets, dict(os.environ, **plan["child_environment"]))
        report["native_processes"].append(debugger_identity | {"role": "debugger"})
        deadline = NativeDeadline(job, plan["maximum_session_sec"]).start()
        start, menu_start, activation_at, captured_menu, next_sample, menu_controls = time.monotonic(), None, None, False, 0, None

        def retain_candidate():
            if (target is None or not job.alive(target) or
                    job.identify(target, target_identity["pid"]) != target_identity):
                raise ValueError("Retained candidate path, generation, liveness or job membership changed.")

        while True:
            log = hidden._read_log(run / "cdb.log")
            observed = hidden.parse_observations(log, context["identity"], metadata)
            report["initial_image_bytes_verified"] = observed["initial_image_bytes_verified"]
            report["acquisition_returns"] = observed["acquisition_returns"]
            if observed["target"] and target is None:
                target, target_identity = job.adopt(observed["target"]["pid"], local_candidate, debugger_identity["creation_filetime"])
                report["native_processes"].append(target_identity | {"role": "candidate"})
            if observed["failures"]:
                raise ValueError("; ".join(observed["failures"]))
            windows = WINDOW.findall(log)
            if len(windows) > 1:
                raise ValueError("Duplicate native CreateWindow return observation.")
            if windows and hwnd is None:
                pid, pc, address = (int(value.replace("`", ""), 16) for value in windows[0])
                if (target is None or not observed["initial_image_bytes_verified"] or
                        pid != target_identity["pid"] or pc != observed["target"]["base"] + 0x61ace):
                    raise ValueError("Window observation lacks authenticated candidate/return-PC binding.")
                hwnd, window = address, OwnedWindow(retain_candidate)
                activation = window.activate(hwnd, target_identity["pid"])
                report["window_activations"].append(activation)
                activation_at = time.monotonic()
            if observed["acquisition_returns"]:
                if hwnd is None or any(row["hwnd"] != hwnd for row in observed["acquisition_returns"]):
                    raise ValueError("Acquire HWND differs from the approved owned native window.")
                if any(row["failed_hresult"] for row in observed["acquisition_returns"]):
                    raise ValueError("Native Acquire returned a failed genuine HRESULT; no bypass was attempted.")
            now = time.monotonic()
            if hwnd and activation_at and now - activation_at > 0.25 and not any(row["foreground_verified"] for row in report["window_activations"]):
                # One bounded retry of the same retained owned window, no input.
                activation = window.activate(hwnd, target_identity["pid"])
                report["window_activations"].append(activation)
                activation_at = None
                if not activation["foreground_verified"]:
                    raise ValueError("Windows refused owned-window foreground activation.")
            if observed["menu"] and menu_start is None:
                if hwnd is None or not any(row["foreground_verified"] for row in report["window_activations"]):
                    raise ValueError("Natural menu preceded verified approved owned-window activation.")
                menu_start = now
                report["menu_surface"] = observed["menu"]
            if menu_start is not None and now >= next_sample:
                retain_candidate()
                controls = job.read(target, observed["target"]["base"] + 0x143d78, 8)
                if menu_controls is None:
                    menu_controls = controls
                if controls != menu_controls or struct.unpack_from("<I", controls)[0] != 0:
                    raise ValueError("Native menu control/exit state changed during approved idle observation.")
                menu = observed["menu"]
                descriptor = job.read(target, menu["surface"], 8)
                if struct.unpack("<HHI", descriptor) != (menu["width"], menu["height"], menu["pixels"]):
                    raise ValueError("Native menu surface descriptor changed during visible sampling.")
                report["samples"].append(dict(elapsed_sec=now - menu_start,
                    menu_exit=struct.unpack_from("<I", controls)[0], menu_choice=struct.unpack_from("<I", controls, 4)[0],
                    **job.telemetry(target)))
                next_sample = now + 1
            if menu_start is not None and plan["capture_owned_window"] and not captured_menu:
                hidden.qualification._reserve(run, 64 * 1024 * 1024)
                payload, capture = window.capture(hwnd, target_identity["pid"])
                hidden._new(run / "owned-menu.bmp", payload)
                report["captures"].append(capture | dict(path="owned-menu.bmp", sha256=hidden._sha(payload), hwnd=hwnd))
                captured_menu = True
            if menu_start is not None and now - menu_start >= plan["natural_menu_idle_sec"]:
                report["natural_menu_idle_verified"] = True
                report["measured_menu_idle_sec"] = now - menu_start
                break
            if not job.alive(debugger) or (target is not None and not job.alive(target)):
                raise ValueError("Owned debugger/candidate exited before the diagnostic completed.")
            if now - start >= plan["maximum_session_sec"]:
                raise TimeoutError("The exact visible session reached its five-minute maximum.")
            time.sleep(0.1)
        proxy_log = hidden._read_log(run / "ddraw_surfdump_proxy.log")
        if "loaded present_enabled=1" not in proxy_log or "present_enabled=0" in proxy_log:
            raise ValueError("The approved presenting proxy mode was not observed.")
    except Exception as error:
        report["failures"].append(type(error).__name__ + ": " + str(error))
    finally:
        if deadline:
            report["native_deadline"] = deadline.stop()
            if report["native_deadline"]["deadline_reached"]:
                report["failures"].append("The independent five-minute task-job deadline was reached.")
        report["cleanup"] = job.close() if job else dict(cleanup_verified=True, reason="no native job created")
        if not report["cleanup"]["cleanup_verified"]:
            report["failures"].append("Owned native cleanup was not verified.")
        try:
            report["live_saves_unchanged"] = hidden._live_save_hashes() == before_saves
            report["launch_artifacts_unchanged"] = hidden.verify_launch_artifacts(launch)
            report["plan_files_unchanged"] = verify_plan_files(plan, before_launch=False)
            if not report["live_saves_unchanged"]:
                raise ValueError("Live source-save hashes changed during isolated session.")
        except (OSError, ValueError) as error:
            report["failures"].append(str(error))
        report["finished_at"] = hidden._now()
        report["diagnostic_passed"] = (not report["failures"] and report["initial_image_bytes_verified"] and
            report["natural_menu_idle_verified"] and len(report["acquisition_returns"]) == 2 and
            any(row["foreground_verified"] for row in report["window_activations"]))
        hidden._json(run / "session-report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--proxy", type=Path)
    parser.add_argument("--asset-root", type=Path, default=Path("C:/ClashTests/hd-multires-runtime-assets-20261025"))
    parser.add_argument("--session-dir", type=Path, default=Path("C:/ClashTests/hd-multires-visible/classic1080-20261025"))
    parser.add_argument("--capture-owned-window", action="store_true")
    parser.add_argument("--write-plan", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.plan:
            if args.bundle or args.proxy or args.write_plan or args.capture_owned_window:
                raise ValueError("A saved exact plan cannot be combined with preparation overrides.")
            saved = hidden.qualification.read_json(args.plan)
            if args.execute:
                if not args.approval:
                    raise ValueError("Execution requires a fresh real-user --approval record bound to the plan.")
                result = execute(saved, args.approval)
            else:
                result = reconstruct(saved)[0]
        else:
            if args.execute or args.approval or not args.bundle or not args.proxy:
                raise ValueError("Prepare with --bundle and --proxy; execute only from a saved plan and approval.")
            result = prepare(args.bundle, proxy=args.proxy, asset_root=args.asset_root,
                session_dir=args.session_dir, capture_owned_window=args.capture_owned_window)[0]
            if args.write_plan:
                target = hidden._external(args.write_plan)
                target.parent.mkdir(parents=True, exist_ok=True)
                hidden._json(target, result)
        print(json.dumps(result, indent=2), flush=True)
        return 0 if not args.execute or result.get("diagnostic_passed") else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        print(json.dumps(dict(schema=SCHEMA, executed=False, failure=str(error), requires_fresh_user_approval=True)), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
