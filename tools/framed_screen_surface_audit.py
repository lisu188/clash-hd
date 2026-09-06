#!/usr/bin/env python3
"""Authenticate a completed hidden modal capture and inspect its indexed pixels.

No process, debugger, input, image editing or candidate output. The entire
current producer packet/probe and ordered trace are reconstructed before pixel
claims. Four border bands and the tooltip footer have separate results. An
ordinary-map action bar is measured but is not a modal-controls requirement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re

import action_bar_surface_audit as action_bar
import frame_surface_audit as frame
import framed_screen_trace as trace
from src.patcher.framed_viewport import FramedViewport

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "scripts/cdb/run_framed_screen_capture.ps1"
SOURCE_PATHS = {
    "host_path": HOST,
    "trace": ROOT / "tools/framed_screen_trace.py",
    "converter": ROOT / "tools/cdb_surface_dump_to_png.py",
    "proxy_source": ROOT / "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp",
    "python": Path(os.environ.get("USERPROFILE", "")) / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe",
    "cdb": Path("C:/Program Files (x86)/Windows Kits/10/Debuggers/x86/cdb.exe"),
}
SOURCE_HASH_KEYS = {"host_path": "host_sha256", **{k: k + "_sha256" for k in SOURCE_PATHS if k != "host_path"}}
LIMITS = [
    "Indexed software-memory pixels only; primary-only layers and final visible wrapper composition remain separate.",
    "Controlled native dispatch and optional availability writes are retained; neither natural selection nor manual input is established.",
    "Ordinary-map bar matches are measurements only on these modal routes; no building controls, battle, interaction or complete modal composition is accepted.",
    "Frame and footer mismatches are retained. Footer text can replace background pixels; this audit applies no guessed exclusion mask.",
    "Source/hash/retained-handle records are cross-checked offline, not an independent live process observation or a digital signature of the capture.",
    "No runtime verdict, protected stage or promotion decision is changed.",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def equivalent(left, right):
    """JSON equality that does not confuse booleans with integer observations."""
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(right, sort_keys=True, separators=(",", ":"))


def same_path(value, expected) -> bool:
    return isinstance(value, str) and Path(value).resolve() == Path(expected).resolve()


def same_hash(value, expected) -> bool:
    # The existing proxy build manifest emits uppercase hashes; its host
    # validation is explicitly case-insensitive. Hex letter case is not an
    # identity change, while type/length/nonhex differences remain invalid.
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", value)) and value.lower() == expected


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def timestamp(value):
    require(isinstance(value, str), "missing observed timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "observed timestamps require a timezone")
    return result.astimezone(timezone.utc)


def check_isolation(plan, directory):
    """The same local directory/path policy as the producer; no file mutation."""
    for key, root in (("input_candidate", "C:/ClashTests"), ("candidate_dir", "C:/ClashTests"),
                      ("work_dir", "C:/ClashTests"), ("proxy_manifest", "C:/ClashTests"),
                      ("proxy_input", "C:/ClashTests"), ("out_dir", "C:/ClashCaptures")):
        value = plan[key]
        require(isinstance(value, str) and re.match(r"^[A-Za-z]:[\\/]", value)
                and not re.search(r'[":\r\n;\x00]', value[2:]), "unsafe producer path: " + key)
        path = Path(value).resolve()
        require(Path(root).resolve() in path.parents, "producer path escapes isolated root: " + key)
        for ancestor in (Path(value), *Path(value).parents):
            require(not ancestor.is_symlink() and not (hasattr(ancestor, "is_junction") and ancestor.is_junction()),
                    "reparse-point producer path: " + key)
    require(same_path(plan["out_dir"], directory), "plan belongs to another capture directory")
    candidate_dir = Path(plan["candidate_dir"])
    directory_digest = sha(str(candidate_dir).lower().encode("utf-8"))[:16]
    basename = f"framed-screen-{plan['route']}-{plan['resolution']}-{directory_digest}.exe"
    require(same_path(plan["candidate_path"], candidate_dir / basename), "copied candidate name differs from producer recipe")
    require(Path(plan["input_candidate"]).name.lower() != basename.lower(), "input candidate must have a distinct basename")
    require(same_path(plan["proxy_path"], candidate_dir / "ddraw.dll")
            and same_path(plan["palette_path"], candidate_dir / "ddraw_surfdump_palette.bin"),
            "proxy or palette is outside the copied candidate directory")


def check_processes(summary, plan):
    start, finish = timestamp(summary["started_at"]), timestamp(summary["finished_at"])
    require(finish >= start, "capture timestamps are reversed")
    cdb, candidates = summary["cdb"], summary["candidates"]
    require(isinstance(cdb, dict) and isinstance(candidates, list) and len(candidates) == 1,
            "snapshot lacks exactly one retained debugger and candidate identity")
    game = candidates[0]
    for identity, expected in ((cdb, plan["cdb"]), (game, plan["candidate_path"])):
        require(type(identity.get("process_id")) is int and identity["process_id"] > 0
                and identity.get("handle_retained") is True and same_path(identity.get("path"), expected),
                "retained process identity/path is invalid")
        ticks = identity.get("creation_filetime")
        require(type(ticks) is int and ticks > 0, "missing retained-handle creation time")
        observed = timestamp(identity["creation_utc"])
        derived = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=ticks // 10)
        require(abs((observed - derived).total_seconds()) <= 0.000001 and start <= observed <= finish,
                "retained process creation timestamp differs from its kernel time or run")
    require(game["process_id"] != cdb["process_id"] and game.get("parent_process_id") == cdb["process_id"]
            and timestamp(game["creation_utc"]) >= timestamp(cdb["creation_utc"])
            and game.get("candidate_sha256") == plan["candidate_sha256"], "candidate parent/time/SHA does not bind the launched debugger")
    require(re.fullmatch(r"ClashFramedScreen_[0-9a-f]{32}", summary.get("hidden_desktop", "")), "missing unique hidden desktop identity")
    directory = Path(plan["out_dir"])
    command = (f'"{plan["cdb"]}" -hd -logo "{directory / "cdb.log"}" '
               f'-c "$$><{directory / "framed-screen.cdb"}" "{plan["candidate_path"]}"')
    require(summary.get("command_line") == command, "debugger command is not the exact candidate/probe/log launch")
    cleanup = summary["cleanup"]
    require(isinstance(cleanup.get("candidates"), list) and len(cleanup["candidates"]) == 1,
            "cleanup lacks the one captured candidate receipt")
    for receipt, identity in ((cleanup.get("cdb"), cdb), (cleanup["candidates"][0], game)):
        require(isinstance(receipt, dict) and equivalent(receipt.get("identity"), identity), "cleanup receipt refers to a different process")
        require(all(type(receipt.get(k)) is bool for k in ("absent", "handle_closed", "termination_requested")),
                "cleanup receipt has invalid observations")
    require(type(cleanup.get("desktop_closed")) is bool, "missing hidden desktop close observation")
    verified = (cleanup["desktop_closed"] and all(r["absent"] and r["handle_closed"]
                for r in (cleanup["cdb"], *cleanup["candidates"])))
    require(not summary["passed"] or verified, "runtime PASS conflicts with incomplete owned-process cleanup")
    return dict(recorded_owned_process_cleanup_verified=verified, cdb=cdb, candidate=game,
                independent_live_query_performed=False)


def build_report(summary_path: Path, *, frame_resource: Path, command_resource: Path,
                 original_path: Path | None = None, plan_path: Path | None = None) -> dict:
    report = dict(schema="clash95_framed_screen_surface_audit_v1", generated_at=datetime.now(timezone.utc).isoformat(),
        source_authenticated=False, screenshot_binding_verified=False, frame_pixels_passed=False,
        structural_border_exact=False, footer_exact=False, input_runtime_passed=None, input_runtime_failures=None,
        runtime_verdict_changed=False, modal_controls_accepted=False, natural_availability_proven=False,
        manual_input_proof=False, visible_composition_proof=False, promotion_ready=False,
        sources={}, failures=[], frame=None, action_bar=None, limits=LIMITS)
    cache = {}
    def artifact(name, path, expected=None):
        path = Path(path).resolve()
        if path not in cache:
            cache[path] = path.read_bytes()
        data = cache[path]
        digest = sha(data)
        if expected is not None:
            require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected)
                    and digest == expected, name + " file hash differs from bound record")
        report["sources"][name] = dict(path=str(path), sha256=digest)
        return data
    def document(name, path):
        return json.loads(artifact(name, path).decode("utf-8-sig"))
    try:
        summary_path = Path(summary_path).resolve(); directory = summary_path.parent
        summary = document("summary", summary_path)
        report.update(input_runtime_passed=summary.get("passed"), input_runtime_failures=summary.get("failures"),
                      input_runtime_status=summary.get("status"), run_id=directory.name)
        require(summary.get("schema") == "clash95_framed_screen_capture_v1" and summary.get("executed") is True
                and summary.get("launch_attempted") is True and type(summary.get("passed")) is bool,
                "not an executed modal capture summary")
        require(isinstance(summary.get("failures"), list) and all(isinstance(x, str) for x in summary["failures"]),
                "invalid input runtime failures")
        require(all(summary.get(k) is False for k in ("manual_input_proof", "visible_composition_proof", "promotion_ready")),
                "summary contains unsupported proof/promotion claims")
        plan = document("plan", directory / "plan.json")
        require(equivalent(plan, summary.get("plan")), "summary and prelaunch plan differ")
        if plan_path is not None:
            require(equivalent(document("supplied_plan", plan_path), plan), "explicit supplied plan differs from capture plan")
        require(plan.get("schema") == "clash95_framed_screen_capture_plan_v1"
                and plan.get("stage") == trace.producer.STAGE and plan.get("environment") == "hidden_cdb_host"
                and plan.get("execute") is True and type(plan.get("deadline_seconds")) is int and plan["deadline_seconds"] == 120
                and equivalent(plan.get("child_environment"), dict(CLASH_PROXY_PRESENT="0", parent_environment_modified=False)),
                "plan stage/environment/launch boundary differs")
        require(all(plan.get(k) is False for k in ("manual_input_proof", "visible_composition_proof", "promotion_ready"))
                and type(plan.get("minimap_viewport")) is bool, "invalid plan proof/options")
        width, height = plan["width"], plan["height"]
        layout = FramedViewport(width, height)
        require(plan["resolution"] == layout.resolution and plan["route"] in trace.producer.ROUTES
                and plan["availability"] in ("existing_flags", "construct_all")
                and type(plan["castle_index"]) is int and 0 <= plan["castle_index"] <= 3,
                "unsupported plan geometry/route/availability")
        check_isolation(plan, directory)
        report.update(stage=plan["stage"], resolution=plan["resolution"], route=plan["route"],
                      availability=plan["availability"], castle_index=plan["castle_index"],
                      minimap_viewport=plan["minimap_viewport"], candidate_sha256=plan["candidate_sha256"])
        for key, path in SOURCE_PATHS.items():
            require(same_path(plan[key], path), "unexpected producer/runtime source path: " + key)
            artifact("producer_" + key, path, plan[SOURCE_HASH_KEYS[key]])
        if original_path is not None:
            require(same_path(plan["original"], original_path), "explicit original differs from planned original")
        original = artifact("original", plan["original"], plan["original_sha256"])
        candidate = artifact("candidate", plan["candidate_path"], plan["candidate_sha256"])
        require(artifact("input_candidate", plan["input_candidate"], plan["candidate_sha256"]) == candidate,
                "copied candidate differs from input")
        manifest = json.loads(artifact("proxy_manifest", plan["proxy_manifest"], plan["proxy_manifest_sha256"]).decode("utf-8-sig"))
        require(manifest.get("generated_by") == "clash-hd-surface-dump-proxy"
                and same_path(manifest.get("source"), plan["proxy_source"])
                and same_path(manifest.get("output"), plan["proxy_input"])
                and Path(plan["proxy_input"]).name.lower() == "ddraw.dll"
                and same_hash(manifest.get("source_sha256"), plan["proxy_source_sha256"])
                and same_hash(manifest.get("output_sha256"), plan["proxy_sha256"]), "proxy manifest/source/output differs")
        require(artifact("proxy_input", plan["proxy_input"], plan["proxy_sha256"])
                == artifact("proxy_copy", plan["proxy_path"], plan["proxy_sha256"]), "proxy copy differs")
        require(summary.get("postrun_identity") == dict(original_sha256=plan["original_sha256"],
            input_candidate_sha256=plan["candidate_sha256"], candidate_sha256=plan["candidate_sha256"],
            proxy_sha256=plan["proxy_sha256"]), "post-run original/candidate/proxy identity differs")
        report["process_observations"] = check_processes(summary, plan)
        packet = document("packet", directory / "packet.json")
        require(all(packet.get(k) == plan[k] for k in ("stage", "resolution", "candidate_sha256", "original_sha256",
                    "castle_index", "availability", "minimap_viewport")) and packet.get("route", {}).get("name") == plan["route"],
                "producer packet identity differs from plan")
        probe = artifact("probe", directory / "framed-screen.cdb", plan["probe_sha256"])
        log = artifact("log", directory / "cdb.log")
        saved_trace = document("trace", directory / "trace.json")
        require(equivalent(saved_trace, summary.get("trace")), "summary and stored trace differ")
        # The host validates while paused, before terminating owned processes.
        # Authenticate that exact prefix, then independently revalidate the whole
        # final log so added rejections/events cannot be hidden in a cleanup tail.
        prefix_hash = saved_trace.get("source", {}).get("log_raw_sha256")
        ends = {len(log), *(m.end() for m in re.finditer(b"\n", log))}
        prefixes = [log[:end] for end in sorted(ends) if sha(log[:end]) == prefix_hash]
        require(len(prefixes) == 1, "stored paused trace is not an exact prefix of the final log")
        result = trace.evaluate_trace(prefixes[0].decode("utf-8-sig"), original=original, candidate=candidate,
                                      packet=packet, generated_probe=probe)
        result["source"]["log_raw_sha256"] = sha(prefixes[0])
        require(equivalent(result, saved_trace), "stored trace differs from full current source/packet/probe/log reconstruction")
        final_trace = result if prefixes[0] == log else trace.evaluate_trace(log.decode("utf-8-sig"),
            original=original, candidate=candidate, packet=packet, generated_probe=probe)
        require(result.get("passed") is True and result.get("ready_for_host_capture") is True
                and final_trace.get("passed") is True, "ordered modal or initial-map trace failed")
        surface = result["surface"]
        require(all(equivalent(final_trace.get(k), result.get(k)) for k in ("surface", "modal_sequence", "initial_map_trace", "failures")),
                "final log changes the paused modal or initial trace")
        report["trace_binding"] = dict(paused_prefix_bytes=len(prefixes[0]), final_log_bytes=len(log),
            paused_prefix_sha256=prefix_hash, final_log_revalidated=True, source_packet_probe_reconstructed=True,
            surface=surface, forced_gate_original=result["modal_sequence"].get("forced_gate_original"))
        raw_path, png_path, metadata_path = (directory / name for name in ("surface.raw", "surface.png", "surface.png.json"))
        raw = artifact("raw", raw_path, summary["snapshot"]["sha256"])
        snapshot = summary["snapshot"]
        require(same_path(snapshot["path"], raw_path) and snapshot.get("paused") is True
                and type(snapshot.get("pixel_reads")) is int and snapshot["pixel_reads"] == 1
                and all(type(snapshot.get(k)) is int and snapshot[k] == v for k, v in
                        (("bytes", width * height), ("width", width), ("height", height), ("pitch", width)))
                and len(raw) == width * height and surface["width"] == width and surface["height"] == height
                and surface["bytes"] == len(raw), "snapshot does not bind the exact paused physical memory read")
        metadata = document("png_metadata", metadata_path)
        require(equivalent(metadata, summary.get("png")) and same_path(metadata.get("log_path"), directory / "cdb.log")
                and metadata.get("palette_mode") == "directdraw-palette"
                and same_path(metadata.get("palette_path"), plan["palette_path"]), "PNG metadata/log/palette differs")
        palette = summary["palette"]
        require(same_path(palette.get("path"), plan["palette_path"]) and type(palette.get("bytes")) is int
                and palette["bytes"] == 1024
                and len(artifact("palette", plan["palette_path"], palette["sha256"])) == 1024,
                "fresh proxy palette identity/size differs")
        artifact("png", png_path, metadata["png_sha256"])
        report["screenshot_binding"] = action_bar.bind_screenshot(dict(PngMetadata=str(metadata_path),
            PngSha256=metadata["png_sha256"], CandidatePath=plan["candidate_path"], CandidateSha256=plan["candidate_sha256"]),
            raw, raw_path, png_path, width, height)
        require(summary["passed"] == (not summary["failures"])
                and summary["status"] == ("bounded_hidden_modal_capture" if summary["passed"] else "failed"),
                "runtime outcome contradicts its retained failures/artifacts")
        report.update(source_authenticated=True, screenshot_binding_verified=True)
        native_frame = frame.load_native_frame(artifact("frame_resource", frame_resource))
        sprites, member_sha = action_bar.load_sprites(artifact("command_resource", command_resource))
        frame_result = frame.audit_surface(raw, layout, native_frame)
        cells = action_bar.compare_cells(raw, width, height, sprites, stage=plan["stage"])
        report.update(frame=frame_result, frame_pixels_passed=frame_result["passed"],
            structural_border_exact=frame_result["structural_border_exact"], footer_exact=frame_result["footer"]["exact"],
            action_bar=dict(applicability="ordinary_map_bar_not_required_for_this_modal", evaluated_as_gate=False,
                matching_cell_count=sum(c["exact_source_match"] for c in cells), cells=cells,
                source_member_sha256=member_sha, modal_controls_accepted=False))
        report["frame_source"] = dict(member_sha256=native_frame.member_sha256, member_offset=native_frame.member_offset,
                                     member_length=native_frame.member_length)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, OverflowError) as exc:
        report["failures"].append(str(exc))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("summary", "frame-resource", "command-resource", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--original", type=Path)
    parser.add_argument("--plan", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; use a new evidence path")
    report = build_report(args.summary, frame_resource=args.frame_resource, command_resource=args.command_resource,
                          original_path=args.original, plan_path=args.plan)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2); stream.write("\n")
    print(json.dumps({k: report[k] for k in ("source_authenticated", "screenshot_binding_verified", "frame_pixels_passed",
        "structural_border_exact", "footer_exact", "input_runtime_passed", "failures")}, indent=2))
    return 0 if report["frame_pixels_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
