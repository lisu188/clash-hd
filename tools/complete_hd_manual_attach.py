"""Prepare or capture one freshly approved existing complete-HD process.

Default preparation reads files only. Execution attaches an observation handle;
it never launches, injects input, focuses, moves, or stops a process. Successful
capture is diagnostic material, never accepted human input or release evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

import complete_hd_evidence as evidence
from complete_hd_manual_attach_win32 import image_contract, verify_image

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_ROOT = Path("C:/ClashCaptures")
SCHEMA = "complete_hd_manual_attachment_plan_v1"
SOURCES = ("tools/complete_hd_manual_attach.py", "tools/complete_hd_manual_attach_win32.py",
           "tools/complete_hd_evidence.py", "tools/complete_hd_runtime_context.py",
           "tools/hd_layout_observation_manifest.py", "tools/menu_pulse_click.py",
           "tools/hd_layout_command_input_summary.py", "tools/capture_tear_check.py",
           "tools/capture_geometry.py")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reference(path: Path) -> dict:
    path = path.resolve()
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return {"path": str(path), "sha256": hasher.hexdigest()}


def read_object(path: Path, maximum: int = 256 * 1024) -> dict:
    if path.stat().st_size > maximum:
        raise ValueError("oversized structured input")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate structured input key")
            result[key] = value
        return result
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("structured input must be an object")
    return value


def external(path: Path) -> Path:
    path = path.resolve()
    if (not path.is_relative_to(CAPTURE_ROOT.resolve()) or path == CAPTURE_ROOT.resolve()
            or path.is_relative_to(ROOT.resolve())):
        raise ValueError("observation material must remain external under C:/ClashCaptures")
    return path


def integer(value, low: int, high: int, description: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"invalid {description}")
    return value


def target_bindings(path: Path, identity: dict, dimensions: list[int]) -> dict:
    path = external(path)
    before = reference(path)
    value = read_object(path, 64 * 1024)
    if set(value) != {"schema", "candidate_identity", "target_id", "points"} or value["schema"] != "complete_hd_attachment_targets_v1":
        raise ValueError("unsupported bounded observation targets")
    if value["candidate_identity"] != identity or value["target_id"] not in evidence.MANUAL_IDS:
        raise ValueError("target candidate or manual checklist identity differs")
    if not isinstance(value["points"], list) or not 1 <= len(value["points"]) <= 32:
        raise ValueError("one through 32 measured target points required")
    names = set()
    for row in value["points"]:
        if not isinstance(row, dict) or set(row) != {"id", "logical", "basis"}:
            raise ValueError("invalid target record")
        name = row["id"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", name) or name in names:
            raise ValueError("invalid or repeated target name")
        names.add(name)
        if not isinstance(row["logical"], list) or len(row["logical"]) != 2:
            raise ValueError("target needs an exact logical point")
        for coordinate, maximum in zip(row["logical"], dimensions):
            integer(coordinate, 0, maximum - 1, "target coordinate")
        basis = row["basis"]
        if not isinstance(basis, dict) or set(basis) != {"path", "sha256"}:
            raise ValueError("target needs its original external observation or source-analysis basis")
        basis_path = external(Path(basis["path"]))
        if reference(basis_path) != basis:
            raise ValueError("target basis artifact changed")
    if reference(path) != before:
        raise ValueError("target bindings changed during preparation")
    return {"artifact": before, **value, "native_hitbox_accepted": False,
            "scope": "approved observation points only; source content does not establish native hit testing"}


def build_plan(*, candidate_manifest: Path, wrapper: Path, configuration: Path,
               target_file: Path, pid: int, creation_filetime: int, hwnd: int,
               client_origin: list[int], output_dir: Path, run_id: str,
               checkpoints: int = 1, interval_ms: int = 1000, duration_seconds: int = 60,
               context_loader=None) -> dict:
    integer(pid, 1, 0xffffffff, "positive existing PID")
    integer(creation_filetime, 1, 0x7fffffffffffffff, "process creation FILETIME")
    integer(hwnd, 1, 0xffffffffffffffff, "existing HWND")
    integer(checkpoints, 1, 12, "checkpoint count")
    integer(interval_ms, 250, 10000, "checkpoint interval")
    integer(duration_seconds, 1, 300, "bounded runtime interval")
    if not isinstance(client_origin, list) or len(client_origin) != 2:
        raise ValueError("explicit measured client origin required")
    for value in client_origin:
        integer(value, -131072, 131072, "client origin")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_id) or run_id in (".", ".."):
        raise ValueError("invalid run identifier")
    output_dir = external(output_dir)
    if output_dir.exists():
        raise ValueError("observation output directory already exists")
    context = (context_loader or evidence.candidate_manifest_context)(candidate_manifest.resolve())
    identity = context["identity"]
    if identity["stage"] != evidence.STAGE or identity["recipe_revision"] != evidence.RECIPE_REVISION or context.get("byte_rebuild_passed") is not True:
        raise ValueError("exact complete candidate reconstruction required")
    dimensions = list(map(int, identity["resolution"].split("x")))
    candidate = Path(context["candidate_path"])
    wrapper, configuration = wrapper.resolve(), configuration.resolve()
    if wrapper != candidate.parent / "ddraw.dll" or configuration.parent != candidate.parent or configuration == wrapper or configuration == candidate:
        raise ValueError("wrapper and configuration must be exact local candidate files")
    artifacts = {"candidate": reference(candidate), "candidate_manifest": reference(candidate_manifest),
                 "canonical_probe": reference(Path(context["probe_path"])),
                 "wrapper": reference(wrapper), "configuration": reference(configuration)}
    for name, key in (("candidate", "candidate_sha256"), ("candidate_manifest", "metadata_sha256"), ("canonical_probe", "probe_sha256")):
        if artifacts[name]["sha256"] != identity[key]:
            raise ValueError("candidate bundle changed while planning")
    # Ensure the selected wrapper is bounded PE32 before an approval is sought.
    wrapper_data = wrapper.read_bytes()
    pe = int.from_bytes(wrapper_data[60:64], "little")
    preferred = int.from_bytes(wrapper_data[pe + 24 + 28:pe + 24 + 32], "little")
    image_contract(wrapper_data, preferred)
    targets = target_bindings(target_file, identity, dimensions)
    return {"schema": SCHEMA, "run_id": run_id, "candidate_identity": identity,
            "artifacts": artifacts, "candidate_source_hashes": context["source_hashes"],
            "producer_sources": {name: reference(ROOT / name) for name in SOURCES},
            "attachment": {"pid": pid, "creation_filetime": creation_filetime, "hwnd": hwnd,
                           "client_origin": client_origin, "process_path": str(candidate.resolve())},
            "client_size": dimensions, "targets": targets, "output_directory": str(output_dir),
            "schedule": {"checkpoints": checkpoints, "captures_per_checkpoint": 3,
                         "interval_ms": interval_ms, "duration_seconds": duration_seconds},
            "input_method": "manual_directinput", "operator": "human",
            "executed": False, "planning_valid": True, "runtime_ready": False,
            "manual_input_accepted": False, "release_ready": False,
            "approval_requirement": "Existing fresh explicit user approval must bind the exact saved plan SHA and attachment identity before any Win32 initialization.",
            "ownership": {"process_owned_by_adapter": False, "process_termination_permitted": False,
                          "cleanup_owner": "user or separately approved process owner",
                          "external_process_cleanup_verified": False},
            "limitations": ["Observation points are not proven control hitboxes.",
                            "This adapter supplies captures and identity checks, not native callback or human-input acceptance.",
                            "Configuration bytes are pinned; the adapter cannot infer whether the wrapper consumed that file.",
                            "Window recreation, movement, resize, candidate exit or occlusion stops capture; no reacquisition or focus.",
                            "Owner launch approval and eventual process cleanup remain separate from this attachment approval."]}


def verify_plan(plan: dict, *, context_loader=None) -> None:
    if plan.get("schema") != SCHEMA:
        raise ValueError("unsupported attachment plan")
    artifacts, attachment, schedule = plan["artifacts"], plan["attachment"], plan["schedule"]
    expected = build_plan(candidate_manifest=Path(artifacts["candidate_manifest"]["path"]),
        wrapper=Path(artifacts["wrapper"]["path"]), configuration=Path(artifacts["configuration"]["path"]),
        target_file=Path(plan["targets"]["artifact"]["path"]), pid=attachment["pid"],
        creation_filetime=attachment["creation_filetime"], hwnd=attachment["hwnd"],
        client_origin=attachment["client_origin"], output_dir=Path(plan["output_directory"]), run_id=plan["run_id"],
        checkpoints=schedule["checkpoints"], interval_ms=schedule["interval_ms"],
        duration_seconds=schedule["duration_seconds"], context_loader=context_loader)
    if plan != expected:
        raise ValueError("saved attachment plan differs from exact files, sources or contract")


def approval_identity(plan: dict, plan_sha: str) -> dict:
    return {"execution_plan_sha256": plan_sha, "candidate_identity": plan["candidate_identity"],
            "attachment": plan["attachment"], "input_method": "manual_directinput", "scope": "capture_existing_process_only"}


def timestamp(value) -> datetime:
    if not isinstance(value, str):
        raise ValueError("approval timestamps must be explicit timezone-aware strings")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("approval timestamp lacks timezone")
    return result.astimezone(timezone.utc)


def validate_approval(path: Path, plan: dict, plan_sha: str, *, now=None) -> dict:
    path = external(path)
    record = read_object(path, 64 * 1024)
    if (record.get("record_kind") != "user_approval" or record.get("approved") is not True
            or not isinstance(record.get("approval_text"), str) or not record["approval_text"].strip()
            or record.get("identity") != approval_identity(plan, plan_sha)):
        raise ValueError("existing explicit user approval does not bind the exact attachment plan")
    current = now or datetime.now(timezone.utc)
    issued, expires = timestamp(record.get("approved_at")), timestamp(record.get("expires_at"))
    if not issued <= current < expires or expires - issued > timedelta(hours=12):
        raise ValueError("approval is stale or outside its fresh 12-hour interval")
    if current + timedelta(seconds=plan["schedule"]["duration_seconds"] + 30) > expires:
        raise ValueError("approval does not cover the bounded attachment and handle cleanup")
    return record


def assert_files(plan: dict) -> None:
    refs = [*plan["artifacts"].values(), *plan["producer_sources"].values(), plan["targets"]["artifact"]]
    refs += [row["basis"] for row in plan["targets"]["points"]]
    for expected in refs:
        if reference(Path(expected["path"])) != expected:
            raise ValueError("approved attachment artifact changed: " + expected["path"])
    for name, expected in plan["candidate_source_hashes"].items():
        source = (ROOT / name).resolve()
        if not source.is_relative_to(ROOT.resolve()) or digest(source.read_bytes()) != expected:
            raise ValueError("approved candidate source changed")


def measured_identity(plan: dict, session) -> dict:
    selected = plan["attachment"]
    identity = session.identity()
    expected = {"pid": selected["pid"], "creation_filetime": selected["creation_filetime"], "path": selected["process_path"]}
    if identity != expected:
        raise ValueError("retained process identity differs; stale/reused PID or wrong executable")
    modules = session.modules()
    loaded = {}
    for name in ("candidate", "wrapper"):
        artifact = plan["artifacts"][name]
        matching = [row for row in modules if row["path"] == artifact["path"]]
        if len(matching) != 1:
            raise ValueError("exact approved loaded module missing or ambiguous: " + name)
        module = matching[0]
        data = Path(artifact["path"]).read_bytes()
        if digest(data) != artifact["sha256"]:
            raise ValueError("loaded module's on-disk bytes changed: " + name)
        probe = Path(plan["artifacts"]["canonical_probe"]["path"]).read_text(encoding="utf-8") if name == "candidate" else None
        contract = image_contract(data, module["base"], probe)
        if module["size"] != contract["image_size"]:
            raise ValueError("loaded module allocation differs")
        loaded[name] = {"path": module["path"], "on_disk_sha256": digest(data), **verify_image(contract, session.read)}
    # A different loaded ddraw.dll cannot be hidden alongside the selected one.
    wrappers = [row for row in modules if Path(row["path"]).name.lower() == "ddraw.dll"]
    if len(wrappers) != 1 or wrappers[0]["path"] != plan["artifacts"]["wrapper"]["path"]:
        raise ValueError("loaded DirectDraw wrapper identity is ambiguous")
    if session.identity() != identity:
        raise ValueError("retained process changed during loaded-image verification")
    return {"process": identity, "loaded_modules": loaded}


def measured_placement(plan: dict, session) -> dict:
    width, height = plan["client_size"]
    points = [[0, 0], [width - 1, 0], [0, height - 1], [width - 1, height - 1], [width // 2, height // 2]]
    points += [row["logical"] for row in plan["targets"]["points"]]
    actual = session.placement(points)
    expected_client = [*plan["attachment"]["client_origin"], width, height]
    if actual.get("hwnd") != plan["attachment"]["hwnd"] or actual.get("client") != expected_client or actual.get("dpi_awareness") not in (1, 2):
        raise ValueError("measured HWND/client geometry differs from approved placement")
    records = actual.get("targets")
    if not isinstance(records, list) or len(records) != len(points):
        raise ValueError("required target accessibility measurements missing")
    for point, row in zip(points, records):
        if (row.get("accessible") is not True or row.get("client") != expected_client
                or row.get("logical_size") != [width, height]
                or row.get("screen_target") != [point[0] + expected_client[0], point[1] + expected_client[1]]
                or row.get("target_hwnd") != plan["attachment"]["hwnd"]):
            raise ValueError("required observation target is inaccessible or its placement changed")
    return actual


def write_new(path: Path, value: dict) -> None:
    path = external(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def execute(plan_path: Path, approval_path: Path, *, allow_visible_runtime: bool,
            context_loader=None, session_factory=None, now=None, monotonic=time.monotonic, sleep=time.sleep,
            tear_analyzer=None) -> dict:
    if allow_visible_runtime is not True:
        raise ValueError("execution also requires explicit allow-visible-runtime")
    plan_path, approval_path = external(plan_path), external(approval_path)
    plan_ref, approval_ref = reference(plan_path), reference(approval_path)
    plan = read_object(plan_path, 4 * 1024 * 1024)
    verify_plan(plan, context_loader=context_loader)
    approval = validate_approval(approval_path, plan, plan_ref["sha256"], now=now)
    if reference(plan_path) != plan_ref or reference(approval_path) != approval_ref:
        raise ValueError("plan or approval changed during verification")
    assert_files(plan)
    output = Path(plan["output_directory"])
    output.mkdir(parents=True, exist_ok=False)
    def utc_now():
        return (now or datetime.now(timezone.utc)).isoformat()
    result = {"schema": "complete_hd_manual_attachment_receipt_v1", "executed": False,
              "plan": plan_ref, "approval": approval_ref, "candidate_identity": plan["candidate_identity"],
              "run_id": plan["run_id"], "started_at": utc_now(), "finished_at": None,
              "environment": "host_visible", "launch_mode": "attach_existing_process_read_only",
              "input_method": "manual_directinput", "input_mechanism": "none_observation_only",
              "capture_complete": False, "manual_input_accepted": False, "release_ready": False,
              "runtime_ready": False, "process_owned_by_adapter": False,
              "external_process_cleanup_verified": False, "observation_handle_closed": False,
              "captures": [], "failures": [], "proof_class": "approved_existing_process_capture_diagnostic"}
    session, deadline = None, monotonic() + plan["schedule"]["duration_seconds"]
    def active():
        if reference(plan_path) != plan_ref or reference(approval_path) != approval_ref:
            raise ValueError("plan or approval changed during observation")
        # Check time after file I/O so a slow integrity check cannot authorize
        # a new capture beyond the permitted interval.
        if monotonic() >= deadline or (now or datetime.now(timezone.utc)) >= timestamp(approval["expires_at"]):
            raise ValueError("approved attachment capture interval expired")
    try:
        active()
        if session_factory is None:
            from complete_hd_manual_attach_win32 import WindowsAttachment
            session_factory = WindowsAttachment
        session = session_factory(plan)
        result["executed"] = True
        for index in range(plan["schedule"]["checkpoints"]):
            active(); assert_files(plan)
            checkpoint = {"index": index, "frames": [], "operator_result": "pending", "native_callback_accepted": False}
            result["captures"].append(checkpoint)
            checkpoint["identity_before"] = measured_identity(plan, session)
            checkpoint["placement_before"] = measured_placement(plan, session)
            for frame_index in range(3):
                active(); assert_files(plan)
                # Retained identity and every actual target bracket each capture;
                # no automatic HWND reacquisition, scaling, movement or focus.
                if session.identity() != checkpoint["identity_before"]["process"]:
                    raise ValueError("retained process changed before capture")
                before = measured_placement(plan, session)
                capture_started_at = utc_now()
                active()
                frame = session.capture(before_attempt=active)
                if frame is None or list(frame.size) != plan["client_size"]:
                    raise ValueError("original-size client capture failed")
                path = output / f"checkpoint-{index + 1}-frame-{frame_index + 1}.png"
                frame.save(path)
                record = {**reference(path), "placement_before": before, "stage": plan["candidate_identity"]["stage"],
                          "capture_started_at": capture_started_at, "capture_finished_at": utc_now(),
                          "resolution": plan["candidate_identity"]["resolution"], "capture_method": "visible_original_client_pixels",
                          "target": plan["targets"]["target_id"], "result": "pending_postcapture_validation"}
                checkpoint["frames"].append(record)
                after = measured_placement(plan, session)
                record["placement_after"] = after
                if before != after or session.identity() != checkpoint["identity_before"]["process"]:
                    raise ValueError("process/window/target placement changed during capture")
                active()
                record["result"] = "captured_geometry_bound_pending_tear_analysis"
            checkpoint["identity_after"] = measured_identity(plan, session)
            if checkpoint["identity_before"] != checkpoint["identity_after"]:
                raise ValueError("loaded identity changed between capture boundaries")
            if index + 1 < plan["schedule"]["checkpoints"]:
                sleep(min(plan["schedule"]["interval_ms"] / 1000, max(0, deadline - monotonic())))
        active(); assert_files(plan)
        result["capture_complete"] = True
    except (Exception, KeyboardInterrupt) as exc:
        result["failures"].append(str(exc) or "observation interrupted")
    finally:
        if session is not None:
            try:
                result["observation_handle_closed"] = session.close() is True
                if result["observation_handle_closed"] is not True:
                    result["failures"].append("retained observation handle did not close")
            except (Exception, KeyboardInterrupt) as exc:
                result["failures"].append("observation handle cleanup failed: " + str(exc))
        result["finished_at"] = utc_now()
        # Publish the original runtime failure/partial files before offline tear
        # analysis, which may be slow or fail. Never overwrite this receipt.
        write_new(output / "capture-receipt.json", result)
    if tear_analyzer is None:
        from capture_tear_check import build_report
        tear_analyzer = build_report
    for checkpoint in result["captures"]:
        if checkpoint["frames"]:
            try:
                for frame in checkpoint["frames"]:
                    if reference(Path(frame["path"]))["sha256"] != frame["sha256"]:
                        raise ValueError("original capture bytes changed before tear analysis")
                checkpoint["tear_check"] = tear_analyzer([Path(row["path"]) for row in checkpoint["frames"]], None)
                for frame in checkpoint["frames"]:
                    if reference(Path(frame["path"]))["sha256"] != frame["sha256"]:
                        raise ValueError("original capture bytes changed during tear analysis")
                if checkpoint["tear_check"].get("clean") is not True:
                    result["failures"].append(f"checkpoint {checkpoint['index']} has suspected capture tearing")
            except (Exception, KeyboardInterrupt) as exc:
                result["failures"].append("tear analysis failed: " + str(exc))
    result["passed"] = result["capture_complete"] and result["observation_handle_closed"] and not result["failures"]
    write_new(output / "summary.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path)
    parser.add_argument("--wrapper", type=Path)
    parser.add_argument("--configuration", type=Path)
    parser.add_argument("--target-file", type=Path)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--creation-filetime", type=int)
    parser.add_argument("--hwnd", type=lambda value: int(value, 0))
    parser.add_argument("--client-origin", type=int, nargs=2)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--checkpoints", type=int, default=1)
    parser.add_argument("--interval-ms", type=int, default=1000)
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--write-plan", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-visible-runtime", action="store_true")
    args = parser.parse_args()
    try:
        if args.execute:
            if not args.plan or not args.approval:
                raise ValueError("execution requires a saved plan and existing external user approval")
            result = execute(args.plan, args.approval, allow_visible_runtime=args.allow_visible_runtime)
            print(json.dumps(result, indent=2)); return 0 if result["passed"] else 2
        if args.approval or args.allow_visible_runtime:
            raise ValueError("approval and runtime switches are accepted only with --execute")
        if args.plan:
            plan = read_object(external(args.plan), 4 * 1024 * 1024); verify_plan(plan)
        else:
            keys = ("candidate_manifest", "wrapper", "configuration", "target_file", "pid", "creation_filetime", "hwnd",
                    "client_origin", "output_dir", "run_id", "checkpoints", "interval_ms", "duration_seconds")
            if any(getattr(args, key) is None for key in keys):
                raise ValueError("planning requires exact candidate, wrapper/configuration, targets, existing process identity and placement")
            plan = build_plan(**{key: getattr(args, key) for key in keys})
        if args.write_plan:
            write_new(args.write_plan, plan)
        print(json.dumps({"plan": plan, "executed": False,
                          "saved_plan": reference(args.write_plan or args.plan) if args.write_plan or args.plan else None,
                          "approval_record_created": False}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"manual attachment: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
