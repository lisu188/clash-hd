"""Synthetic integrated callback fixtures; no runtime or actual approval."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from contextlib import redirect_stdout
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import complete_hd_evidence as evidence
import hd_layout_command_input_summary as summary
import hd_layout_observation_manifest as observer
import test_hd_layout_command_input_summary as legacy
import test_hd_layout_observation_manifest as producer_fixtures


def context_fixture(candidate: Path, resolution: str = "1920x1080") -> dict:
    inherited = "synthetic-inherited-validation"
    identity = {"stage": evidence.STAGE, "resolution": resolution, "candidate_sha256": summary.sha256(candidate.read_bytes()),
                "base_sha256": "a" * 64, "recipe_revision": evidence.RECIPE_REVISION}
    army = f"ARMY_CONTRACT_PASS stage={inherited} resolution={resolution} candidate_sha256={identity['candidate_sha256']} revision=fixture"
    complete = f"COMPLETEHD_CONTRACT_PASS stage={evidence.STAGE} resolution={resolution} candidate_sha256={identity['candidate_sha256']} revision={evidence.RECIPE_REVISION}"
    tile = f"PTILE_CONTRACT_PASS stage={inherited} resolution={resolution} candidate_sha256={identity['candidate_sha256']}"
    probe = "\n".join(".echo " + line for line in (army, complete, tile)) + "\n"
    metadata = {"schema": 1, **identity, "probe_sha256": summary.sha256(probe.encode()),
                "predecessor": {"stage": inherited, "army_revision": "fixture"},
                "probe_contract": {"complete_marker": complete, "inherited_marker": tile}}
    metadata_path, probe_path = candidate.with_suffix(".candidate.json"), candidate.with_suffix(".cdb")
    legacy.write_json(metadata_path, metadata)
    probe_path.write_bytes(probe.encode())
    identity.update(metadata_sha256=legacy.file_ref(metadata_path)["sha256"], probe_sha256=metadata["probe_sha256"])
    return {"identity": identity, "candidate_path": str(candidate.resolve()), "metadata_path": str(metadata_path.resolve()),
            "probe_path": str(probe_path.resolve()), "manifest": metadata, "probe": probe,
            "source_hashes": {"synthetic-fixture": "b" * 64}, "byte_rebuild_passed": True}


def bound_fixture(root: Path, *, input_method: str = "manual_directinput", resolution: str = "1920x1080") -> tuple[Path, dict]:
    path = legacy.write_fixture(root)
    manifest = summary.read_object(path)
    identity = manifest["identity"]
    context = context_fixture(Path(identity["candidate_path"]), resolution)
    identity.update(stage=evidence.STAGE, resolution=list(map(int, resolution.split("x"))),
                    candidate_identity=context["identity"], input_method=input_method,
                    input_plan=summary.release_input_plan(context, input_method))
    candidate_ref = legacy.file_ref(Path(context["metadata_path"]))
    manifest["candidate_manifest"] = candidate_ref
    receipt_path = Path(manifest["session_receipt"]["path"])
    receipt = summary.read_object(receipt_path)
    plan_path = Path(receipt["plan"]["path"])
    plan = summary.read_object(plan_path)
    plan["candidate_manifest"] = candidate_ref
    plan["identity"] = {key: identity[key] for key in summary.approval_bindings(identity) if key != "execution_plan_sha256"}
    plan["launch_environment"] = summary.launch_environment_policy("proxy-present", identity["resolution"])
    legacy.write_json(plan_path, plan)
    identity["execution_plan_sha256"] = legacy.file_ref(plan_path)["sha256"]
    approval_path = Path(manifest["approval"]["path"])
    approval = summary.read_object(approval_path)
    approval["identity"] = {key: identity[key] for key in summary.approval_bindings(identity)}
    legacy.write_json(approval_path, approval)
    manifest["approval"] = legacy.file_ref(approval_path)
    rendered = Path(manifest["probe"]["rendered_path"])
    probe = summary.render_probe(identity, context)
    rendered.write_bytes(probe.encode())
    manifest["probe"]["rendered_sha256"] = summary.sha256(rendered.read_bytes())
    startup = Path(receipt["startup_probe"]["path"])
    startup.write_bytes((probe + "\ng\n").encode())
    receipt.update(identity=copy.deepcopy(identity), approval=manifest["approval"], plan=legacy.file_ref(plan_path),
                   startup_probe=legacy.file_ref(startup), physical_client_size=identity["resolution"],
                   launch_environment={"policy": plan["launch_environment"], "effective_environment_sha256": "b" * 64})
    left, top, width, height = summary.panel_geometry(context)
    events = legacy.EVENTS
    for old, new in (("608", str(left)), ("528", str(top)), ("671", str(left + 63)), ("559", str(top + 31)),
                     ("640", str(left + 32)), ("544", str(top + 16)), ("width=800", f"width={width}"), ("height=600", f"height={height}")):
        events = events.replace(old, new)
    lines = [line.removeprefix(".echo ") for line in probe.splitlines() if line.startswith(".echo ")]
    log = Path(manifest["raw_log"]["path"])
    log.write_bytes(("\n".join(lines) + "\n" + events).encode())
    receipt["click_observation_start_line"] = len(lines)
    legacy.write_json(receipt_path, receipt)
    manifest.update(identity=identity, session_receipt=legacy.file_ref(receipt_path), raw_log=legacy.file_ref(log))
    legacy.write_json(path, manifest)
    return path, context


def evaluate(path: Path, context: dict) -> dict:
    # Production reconstruction is tested separately. This explicit test-only
    # loader installs synthetic bytes so no proprietary fixtures are needed.
    with patch.object(summary, "load_release_context", return_value=context):
        return summary.build_report(path, candidate_manifest=Path(context["metadata_path"]))


def test_manual_and_pulse_callback_pass_without_manual_release_proof(root):
    for method in ("manual_directinput", "win32_sendinput_relative"):
        path, context = bound_fixture(root / method, input_method=method)
        report = evaluate(path, context)
        assert report["passed"] and report["panel_click_callback_proof"], report
        assert report["manual_directinput_proof"] is False and report["promotion_ready"] is False


def test_mixed_identity_wrong_geometry_and_incomplete_native_sequence_fail(root):
    changes = (
        ("x=1696 y=1000", "x=608 y=528"), ("width=1920 height=1080", "width=800 height=600"),
        ("upper_exclusive=1759", "upper_exclusive=1760"),
        ("eax=1", "eax=0"), ("desc=00511d40", "desc=00514b78"), ("ret=00419c60", "ret=00419c61"),
        ("HDLAYOUT_INPUT_CALLBACK tid=1a2", "HDLAYOUT_INPUT_CALLBACK tid=1a3"),
        ("COMPLETEHD_CONTRACT_PASS", "COMPLETEHD_CONTRACT_FAIL"),
        ("candidate_sha256=", "candidate_sha256=0"),
    )
    for index, (old, new) in enumerate(changes):
        path, context = bound_fixture(root / str(index))
        legacy.replace_log(path, lambda text: text.replace(old, new))
        assert not evaluate(path, context)["passed"], (old, new)
    for name, transform in (
        ("missing_callback", lambda lines: lines[:-1]),
        ("missing_descriptor", lambda lines: [line for line in lines if not line.startswith("HDLAYOUT_INPUT_DESCRIPTOR")]),
        ("callback_order", lambda lines: lines[:-2] + lines[-2:][::-1]),
        ("forced_register", lambda lines: lines + ["0:000> r eax=1"]),
        ("forced_memory", lambda lines: lines + ["0:000> eb 00409d80 c3"]),
        ("forced_call", lambda lines: lines + ["0:000> .call 00409d80(00511d40)"]),
    ):
        path, context = bound_fixture(root / name)
        legacy.replace_log(path, lambda text: "\n".join(transform(text.splitlines())) + "\n")
        assert not evaluate(path, context)["passed"], name


def test_context_and_probe_rebinding_fail(root):
    for name in ("candidate", "resolution", "recipe", "metadata", "probe"):
        path, context = bound_fixture(root / name)
        changed = copy.deepcopy(context)
        field = {"candidate": "candidate_sha256", "resolution": "resolution", "recipe": "recipe_revision", "metadata": "metadata_sha256"}.get(name)
        if field:
            changed["identity"][field] = "1024x768" if name == "resolution" else "changed"
        else:
            rendered = Path(summary.read_object(path)["probe"]["rendered_path"])
            rendered.write_bytes(rendered.read_bytes() + b".call 00409d80()\n")
        assert not evaluate(path, changed)["passed"], name


def test_loaded_contracts_cannot_follow_the_input_identity_or_callback(root):
    for placement in ("after_identity", "after_callback"):
        path, context = bound_fixture(root / placement)
        def reorder(text):
            lines = text.splitlines()
            guards = [line for line in lines if line.startswith(
                ("ARMY_CONTRACT_PASS", "COMPLETEHD_CONTRACT_PASS", "PTILE_CONTRACT_PASS"))]
            # Keep blank lines at the original guard locations so the genuine
            # receipt's click boundary still precedes the native sequence.
            changed = ["" if line in guards else line for line in lines]
            index = (next(i for i, line in enumerate(changed) if line.startswith("HDLAYOUT_INPUT_IDENTITY")) + 1
                     if placement == "after_identity" else len(changed))
            changed[index:index] = guards
            return "\n".join(changed) + "\n"
        legacy.replace_log(path, reorder)
        report = evaluate(path, context)
        assert not report["passed"] and any("loaded-byte contracts must precede" in failure
                                            for failure in report["failures"]), report
        assert report["matched_sequence"] is not None, "fixture must retain a valid native callback sequence"


def test_producer_plan_binds_complete_context_without_runtime(root):
    with producer_fixtures.planned(root) as (args, old_plan, _, _, _):
        context = context_fixture(args.candidate)
        args.stage = evidence.STAGE
        args.candidate_manifest = Path(context["metadata_path"])
        args.input_method = "win32_sendinput_relative"
        with patch.object(summary, "load_release_context", return_value=context), \
             patch.object(observer.subprocess, "Popen", side_effect=AssertionError("no runtime in planning")), \
             patch.object(observer, "WindowsSession", side_effect=AssertionError("no Win32 in planning")):
            plan = observer.build_plan(args)
            assert observer.verify_plan(plan).candidate_manifest == args.candidate_manifest
        assert plan["identity"]["candidate_identity"] == context["identity"]
        assert plan["capture"]["native_client_size"] == [1920, 1080]
        assert plan["identity"]["input_plan"]["target_point"] == [1728, 1016]
        assert plan["inject_input"] is False and plan["executed"] is False
        assert not args.output_dir.exists()
        assert old_plan["identity"]["resolution"] == [800, 600]


def test_release_lane_replays_raw_callback_and_accepts_disclosed_pulse(root):
    path, context = bound_fixture(root / "input", input_method="win32_sendinput_relative")
    manifest = summary.read_object(path)
    identity = manifest["identity"]
    report_path = root / "lane.json"
    report = {"schema": evidence.LANE_SCHEMA, "lane": "panel_command", "identity": context["identity"],
              "passed": True, "failures": [], "stable_stage_should_change": False,
              "evidence_class": "observed_relocated_panel_native_callback", "producer": legacy.file_ref(Path(summary.__file__)),
              "command_manifest": legacy.file_ref(path), "source_artifacts": [legacy.file_ref(path)],
              "checks": {name: {"passed": True, "failures": []} for name in evidence.LANES["panel_command"][1]},
              "run_id": identity["run_id"], "started_at": identity["started_at"], "finished_at": identity["finished_at"],
              "generated_at": "2026-09-05T10:03:00+00:00", "no_crash": True, "process_cleanup_verified": True,
              "runtime_profile": {"environment": identity["environment"], "input_method": identity["input_method"],
                                  "wrapper": {key: identity["wrapper"][key] for key in ("path", "sha256")},
                                  "wrapper_config": identity["wrapper"]["config"]},
              "approval": manifest["approval"], "input_or_callback_forced": False, "input_injected": True}
    legacy.write_json(report_path, report)
    with patch.object(summary, "load_release_context", return_value=context):
        actual = evidence.evaluate_lane("panel_command", legacy.file_ref(report_path), context, root)
    assert actual["passed"], actual
    # Keep the caller-authored green flags and rehash all references, but remove
    # the native callback. Only source-artifact replay can reject this forgery.
    legacy.replace_log(path, lambda text: "\n".join(text.splitlines()[:-1]) + "\n")
    report["command_manifest"] = legacy.file_ref(path)
    report["source_artifacts"] = [legacy.file_ref(path)]
    legacy.write_json(report_path, report)
    with patch.object(summary, "load_release_context", return_value=context):
        actual = evidence.evaluate_lane("panel_command", legacy.file_ref(report_path), context, root)
    assert not actual["passed"] and any("no ordered" in failure for failure in actual["failures"]), actual


def test_complete_producer_execution_is_bound_and_passive_with_fake_apis(root):
    from PIL import Image
    with producer_fixtures.planned(root) as (args, _, plan_path, approval_path, _):
        context = context_fixture(args.candidate)
        args.stage = evidence.STAGE
        args.candidate_manifest = Path(context["metadata_path"])
        args.input_method = "win32_sendinput_relative"
        with patch.object(summary, "load_release_context", return_value=context):
            plan = observer.build_plan(args)
            observer.write_json(plan_path, plan)
            prelaunch = {**plan["identity"], "execution_plan_sha256": legacy.file_ref(plan_path)["sha256"]}
            now = datetime.now(timezone.utc)
            observer.write_json(approval_path, {"approved": True, "record_kind": "user_approval",
                "approval_text": "SYNTHETIC OFFLINE FIXTURE ONLY, not real approval",
                "approved_at": (now - timedelta(minutes=1)).isoformat(), "expires_at": (now + timedelta(minutes=10)).isoformat(),
                "identity": prelaunch})
            state = {"phase": "map", "clock": 0.0, "stopped": False, "captures": [], "closed": []}
            log = args.output_dir / "observation.log"
            base_path, _ = bound_fixture(root / "events", input_method=args.input_method)
            event_text = "\n".join(line for line in Path(summary.read_object(base_path)["raw_log"]["path"]).read_text().splitlines()
                                  if line.startswith("HDLAYOUT_INPUT_") and not line.startswith("HDLAYOUT_INPUT_IDENTITY")) + "\n"
            def append():
                if state["phase"] == "click":
                    text = event_text.replace("state=2", "state=6")
                else:
                    text = event_text.splitlines()[0] + "\n"
                    if state["phase"] == "map":
                        text = text.replace("mouse_x=1728 mouse_y=1016", "mouse_x=960 mouse_y=540")
                        text = text.replace("cursor_meta=005196a0 cursor_sprite=2 cursor_x=1728 cursor_y=1016",
                                            "cursor_meta=005196c8 cursor_sprite=3 cursor_x=960 cursor_y=540")
                    else:
                        text = text.replace("state=2", "state=6")
                with log.open("a", encoding="utf-8") as stream:
                    stream.write(text)
            class Process:
                pid = 122
                def poll(self): return 0 if state["stopped"] else None
                def terminate(self): state["stopped"] = True
                def wait(self, timeout): return 0
            class Session:
                kernel = SimpleNamespace(CloseHandle=lambda handle: state["closed"].append(handle))
                def candidate_child(self, parent, candidate, earliest):
                    return {"pid": 123, "parent_pid": parent, "path": str(candidate), "creation_filetime": earliest + 100, "handle": "owned"}
                def window(self, proc_id, dimensions):
                    assert proc_id == 123 and dimensions == (1920, 1080)
                    return 0x123456
                def process_dpi_awareness(self, owned): return 2
                def window_dpi_awareness(self, hwnd): return 2
                def capture(self, hwnd, proc_id, identity, target):
                    assert identity["candidate_identity"] == context["identity"]
                    assert identity["input_method"] == "win32_sendinput_relative"
                    state["captures"].append(target)
                    Image.new("RGB", tuple(identity["resolution"]), (7, 11, 13)).save(target)
                    sidecar = target.with_suffix(".json")
                    observer.write_json(sidecar, {"fixture_only": True})
                    return {**legacy.file_ref(target), "sidecar": legacy.file_ref(sidecar)}
                def stop_candidate(self, owned):
                    state["candidate_stopped"] = True
                    return True
            def launch(command, **kwargs):
                assert command[-1] == str(args.candidate)
                assert kwargs["env"]["CLASH_PROXY_PRESENT"] == "1"
                probe = summary.render_probe(prelaunch, context)
                log.write_text("\n".join(line.removeprefix(".echo ") for line in probe.splitlines() if line.startswith(".echo ")) + "\n")
                append()
                return Process()
            real_pair = observer.stable_pair
            def pair(*values):
                result = real_pair(*values)
                state["phase"] = "panel_hover" if state["phase"] == "map" else "click"
                return result
            def sleep(seconds):
                state["clock"] += seconds
                append()
            with patch.object(observer.subprocess, "Popen", side_effect=launch), \
                 patch.object(observer, "stable_pair", side_effect=pair), \
                 patch.object(observer.time, "sleep", side_effect=sleep), \
                 patch.object(observer.time, "monotonic", side_effect=lambda: state["clock"]), redirect_stdout(io.StringIO()):
                result = observer.execute(plan_path, approval_path, allow_visible_runtime=True, session_factory=Session)
            assert result["passed"], result
            assert len(state["captures"]) == 4 and state["closed"] == ["owned"] and state["candidate_stopped"] and state["stopped"]
            receipt = summary.read_object(args.output_dir / "session-receipt.json")
            assert receipt["physical_client_size"] == [1920, 1080]
            assert receipt["identity"]["candidate_identity"] == context["identity"]


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    with tempfile.TemporaryDirectory(prefix="complete-command-fixtures-") as directory:
        for index, test in enumerate(tests):
            path = Path(directory) / str(index)
            path.mkdir()
            test(path)
    print(f"complete_hd_command_input: PASS ({len(tests)} offline groups)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
