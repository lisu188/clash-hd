#!/usr/bin/env python3
"""Synthetic, repo-only fixtures for additive HD-layout component eligibility."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hd_layout_completion_decision as decision
import hd_layout_summary
import patch_stage_report
from test_capture_tear_check import write_png
from test_hd_layout_summary import PASS_LOG
from test_hd_layout_visible_summary import fixture_images
import hd_layout_command_input_summary as command_parser
import test_hd_layout_command_input_summary as command_fixtures
from test_hd_layout_asset_composition import fixture_assets, fixture_resource, rejects


SHA = "A" * 64
STAGE = decision.STABLE_STAGE + "-combinedui-validation"
START = "2026-09-05T10:01:00Z"
FINISH = "2026-09-05T10:02:00Z"


def write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def ref(path: Path) -> dict:
    return {"path": str(path), "sha256": decision.sha256(path)}


def identity() -> dict:
    return {"run_id": "fixture-layout-run", "candidate_sha256": SHA,
            "candidate_path": r"C:\ClashTests\fixture\clash95_layout.exe",
            "stage": STAGE, "resolution": [800, 600], "environment": "host_visible",
            "input_method": "win32_sendinput_relative", "hwnd": "0x12345",
            "started_at": START, "finished_at": FINISH}


def synthetic_candidate(path: Path, stage: str) -> tuple[dict, bytes, bytes]:
    patcher = patch_stage_report.load_patcher()
    patches = patcher.select_patches(stage)
    base = bytearray(max(p.offset + len(p.old) for p in patcher.PATCHES) + 100)
    for patch in patcher.PATCHES:
        base[patch.offset:patch.offset + len(patch.old)] = patch.old
    patched = bytearray(base)
    for patch in patches:
        patched[patch.offset:patch.offset + len(patch.new)] = patch.new
    path.write_bytes(patched)
    return patch_stage_report.build_report(path, stage), bytes(base), bytes(patched)


def hidden_fixture(temp: Path) -> tuple[dict, dict]:
    log = temp / "geometry.log"
    log.write_text(PASS_LOG +
        "HDLAYOUT_PANEL_REDRAW_INVOKE desc=00511e49 x=736 y=560 helper=00419d60 return=0040a460\n"
        "HDLAYOUT_PANEL_REDRAW_ALLOWED desc=00511e49 x=736 y=560 clip=800 draw=004191f0 render=0a30eeb0 map_surface=0a30eeb0\n", encoding="utf-8")
    summary = hd_layout_summary.summarize(log)
    run = {"Passed": True, "Error": None, "HiddenDesktop": True, "AllowVisibleDesktop": False,
           "LaunchMode": "hidden-desktop", "Stage": STAGE, "CandidateSha256": SHA,
           "CandidatePath": r"C:\ClashTests\hidden-fixture\clash95_hidden.exe",
           "InputSha256": patch_stage_report.load_patcher().EXPECTED_SHA256, "RunDir": str(temp),
           "Surface": {"Width": 800, "Height": 600}, "Log": str(log)}
    return summary, run


def descriptor_prefix() -> str:
    selected = command_fixtures.EVENTS.splitlines()[0]
    for before, after in (("mouse_x=640", "mouse_x=320"), ("mouse_y=544", "mouse_y=300"),
                          ("cursor_meta=005196a0", "cursor_meta=005196c8"), ("cursor_sprite=2", "cursor_sprite=3"),
                          ("cursor_x=640", "cursor_x=320"), ("cursor_y=544", "cursor_y=300")):
        selected = selected.replace(before, after)
    hovered = command_fixtures.EVENTS.splitlines()[0].replace("state=2", "state=6")
    return "\n".join([selected] * 4 + [hovered] * 4) + "\n"


def prefix_ref(raw: bytes, line: int) -> dict:
    prefix = b"".join(raw.splitlines(keepends=True)[:line])
    return {"line": line, "prefix_bytes": len(prefix), "prefix_sha256": hashlib.sha256(prefix).hexdigest()}


def composition_fixture(temp: Path, *, native: bool = False, candidate_bytes: bytes | None = None) -> tuple[dict, dict]:
    temp.mkdir(parents=True, exist_ok=True)
    command_path = command_fixtures.write_fixture(temp, stage=STAGE, resource_bytes=fixture_resource(),
        candidate_bytes=candidate_bytes, descriptor_prefix=descriptor_prefix())
    command_fixtures.replace_log(command_path, lambda text: text.replace(command_fixtures.EVENTS,
        command_fixtures.EVENTS.replace("state=2", "state=6", 1)))
    command = command_parser.build_report(command_path)
    assert command["passed"], command
    ident = command["identity"]
    raw_log = Path(command["raw_log"]["path"]).read_bytes()
    rows, _, _ = command_parser.parse_events(raw_log.decode())
    assets = fixture_assets()
    composition = {"schema_version": 1, "identity": ident,
                   "evidence_class": "approved_visible_automated_layout_composition",
                   "command_manifest": ref(command_path), "approval": command["approval"], "frames": {}}
    base = fixture_images()[0]
    for index, name in enumerate(("map", "panel_hover")):
        pair = []
        state = next(row["values"] for row in rows if row["line"] == 2 + index * 4)
        pixels = decision.asset_composition.expected_panel(assets, state, (608, 528), 1, index == 1)
        pixels.update(decision.asset_composition.expected_panel(assets, state, (608, 560), 6))
        pixels.update(decision.asset_composition.sprite_pixels(assets["mouse"][state["cursor_sprite"]],
                                                              state["cursor_x"], state["cursor_y"]))
        for offset in range(2):
            width, height = (800, 600) if native else (1200, 900)
            def pixel_at(x, y):
                x, y = x * 800 // width, y * 600 // height
                return assets["palette"][pixels[x, y]] if (x, y) in pixels else base.rgb_at(x * 3 // 2, y * 3 // 2)
            path = write_png(temp / f"{name}-{offset}.png", width, height, pixel_at)
            sidecar = {"Hash": decision.sha256(path), "Width": width, "Height": height,
                       "CaptureMode": "screen", "CenterWindowMatchesTarget": True,
                       "TargetHwnd": ident["hwnd"], "CenterWindowHwnd": ident["hwnd"], "CenterRootHwnd": ident["hwnd"],
                       "CaptureId": f"fixture-{name}-{offset}", "RunId": ident["run_id"],
                       "CandidateSha256": ident["candidate_sha256"], "Stage": STAGE, "ClientSize": [800, 600],
                       "CapturedAt": f"2026-09-05T10:01:{10 + index * 20 + offset * 10}Z",
                       "InputObservationBefore": prefix_ref(raw_log, 2 + index * 4 + offset * 2),
                       "InputObservationAfter": prefix_ref(raw_log, 3 + index * 4 + offset * 2)}
            record = ref(path)
            record["sidecar"] = ref(write_json(path.with_suffix(".json"), sidecar))
            pair.append(record)
        composition["frames"][name] = pair
    return composition, command


def assert_contains(errors: list[str], fragment: str) -> None:
    assert any(fragment in value for value in errors), errors


def test_authoritative_bytes_and_original_reconstruction(temp: Path) -> None:
    for suffix in ("-hdlayout-framerestore", "-combinedui-validation"):
        stage = decision.STABLE_STAGE + suffix
        report, base, data = synthetic_candidate(temp / "candidate.fixture", stage)
        kwargs = {"candidate_sha": report["exe_sha256"], "stage": stage, "resolution": "800x600"}
        assert decision.validate_byte_report(report, **kwargs) == []
        patches = patch_stage_report.load_patcher().select_patches(stage)
        base_sha = hashlib.sha256(base).hexdigest()
        assert decision.validate_candidate_origin(data, patches, base_sha) == []
        unrelated = bytes([data[0] ^ 1]) + data[1:]
        assert_contains(decision.validate_candidate_origin(unrelated, patches, base_sha), "unrelated bytes")
        bad = copy.deepcopy(report)
        bad["patches"][0]["old"] = "00"
        assert_contains(decision.validate_byte_report(bad, **kwargs), "authoritative patch")
        bad = copy.deepcopy(report)
        bad["patches"] = bad["patches"][:-1]
        assert_contains(decision.validate_byte_report(bad, **kwargs), "every selected patch")
        bad = copy.deepcopy(report)
        bad["exe_sha256"] = "0" * 64
        assert_contains(decision.validate_byte_report(bad, **kwargs), "candidate SHA")
        assert_contains(decision.validate_byte_report(report, **dict(kwargs, resolution="1024x768")), "only 800x600")
    report, _, _ = synthetic_candidate(temp / "no-frame.fixture", decision.STABLE_STAGE + "-hdlayout")
    assert_contains(decision.validate_byte_report(report, candidate_sha=report["exe_sha256"],
                    stage=report["stage"], resolution="800x600"), "layout/frame groups")


def test_hidden_summary_cannot_be_pasted_or_rebound(temp: Path) -> None:
    summary, run = hidden_fixture(temp)
    kwargs = {"candidate_sha": SHA, "stage": STAGE}
    assert decision.validate_hidden(summary, run, **kwargs) == []
    wrong = dict(run, CandidateSha256="B" * 64)
    assert_contains(decision.validate_hidden(summary, wrong, **kwargs), "candidate/stage")
    assert_contains(decision.validate_hidden(summary, dict(run, InputSha256="B" * 64), **kwargs), "input SHA")
    Path(summary["log"]).write_text("unrelated battle callback log\n", encoding="utf-8")
    assert_contains(decision.validate_hidden(summary, run, **kwargs), "does not match its raw log")
    assert_contains(decision.validate_hidden(summary, run, **kwargs), "does not prove every anchor")


def test_composition_requires_same_run_raw_pixels(temp: Path) -> None:
    composition, command = composition_fixture(temp)
    assert decision.validate_composition(composition, command, START, FINISH) == []
    wrong = copy.deepcopy(composition)
    wrong["identity"]["run_id"] = "old-visible-layout-run"
    assert_contains(decision.validate_composition(wrong, command, START, FINISH), "identity differs")
    wrong = copy.deepcopy(composition)
    wrong["frames"]["map"][1] = wrong["frames"]["map"][0]
    errors = decision.validate_composition(wrong, command, START, FINISH)
    assert_contains(errors, "reuses one capture path")
    assert_contains(errors, "capture IDs must be present and distinct")
    sidecar_ref = composition["frames"]["map"][0]["sidecar"]
    sidecar_path = Path(sidecar_ref["path"])
    raw = decision.read_object(sidecar_path)
    raw["CandidateSha256"] = "B" * 64
    write_json(sidecar_path, raw)
    try:
        decision.validate_composition(composition, command, START, FINISH)
    except ValueError as exc:
        assert "SHA-256" in str(exc), exc
    else:
        raise AssertionError("tampered raw capture metadata was accepted")
    sidecar_ref.update(ref(sidecar_path))
    assert_contains(decision.validate_composition(composition, command, START, FINISH), "raw capture identity")
    raw["CandidateSha256"] = command["identity"]["candidate_sha256"]
    raw["CapturedAt"] = "2026-07-13T12:00:00Z"
    write_json(sidecar_path, raw)
    sidecar_ref.update(ref(sidecar_path))
    assert_contains(decision.validate_composition(composition, command, START, FINISH), "outside the command-input run")


def test_native_capture_numeric_mapping(temp: Path) -> None:
    composition, command = composition_fixture(temp, native=True)
    assert decision.validate_composition(composition, command, START, FINISH) == []
    raw_path = Path(composition["frames"]["map"][0]["path"])
    raw = decision.visible.read_png(raw_path)
    assert (raw.width, raw.height) == (800, 600)
    sidecar_path = Path(composition["frames"]["map"][0]["sidecar"]["path"])
    sidecar = decision.read_object(sidecar_path)
    sidecar["Width"] = 1200
    assert decision.authentic_screen_frame(raw_path, sidecar, identity()["hwnd"]) is False


def test_native_capture_states_and_source_content(temp: Path) -> None:
    composition, command = composition_fixture(temp, native=True)
    raw, rows, assets, boundary = decision.composition_sources(command)
    item = composition["frames"]["panel_hover"][0]
    sidecar = decision.read_object(Path(item["sidecar"]["path"]))
    state, first, last = decision.capture_state(sidecar, "panel_hover", raw, rows)
    assert (state["state"], state["state3"], state["selected_unit"]) == (6, 1, 2)
    assert last <= boundary
    manifest_path = Path(command["source_manifest"]["path"])
    manifest_bytes = manifest_path.read_bytes()
    raw_path = Path(command["raw_log"]["path"])
    # A later, independently proven click may move one pixel inside the same
    # icon; its own native hit-test rows must agree about that new position.
    command_fixtures.replace_log(manifest_path, lambda text: "\n".join(text.splitlines()[:boundary]) + "\n"
        + "\n".join(text.splitlines()[boundary:]).replace("640", "641") + "\n")
    moved_command = command_parser.build_report(manifest_path)
    assert moved_command["passed"], moved_command
    moved_composition = copy.deepcopy(composition)
    moved_composition["command_manifest"] = ref(manifest_path)
    assert decision.validate_composition(moved_composition, moved_command, START, FINISH) == []
    raw_path.write_bytes(raw)
    manifest_path.write_bytes(manifest_bytes)
    wrong = copy.deepcopy(sidecar)
    wrong["InputObservationBefore"]["prefix_sha256"] = "0" * 64
    rejects(lambda: decision.capture_state(wrong, "panel_hover", raw, rows), "prefix SHA")
    wrong = copy.deepcopy(sidecar)
    wrong["InputObservationAfter"] = wrong["InputObservationBefore"]
    rejects(lambda: decision.capture_state(wrong, "panel_hover", raw, rows), "fresh native")
    for old, new in (("state=6", "state=2"), ("cursor_sprite=2", "cursor_sprite=3"),
                     ("cursor_meta=005196a0", "cursor_meta=005196c8"), ("cursor_x=640", "cursor_x=641")):
        lines = raw.splitlines(keepends=True)
        for index in range(first - 1, last):
            lines[index] = lines[index].replace(old.encode(), new.encode())
        changed = b"".join(lines)
        changed_rows, _, _ = command_parser.parse_events(changed.decode())
        wrong = copy.deepcopy(sidecar)
        wrong["InputObservationBefore"] = prefix_ref(changed, first)
        wrong["InputObservationAfter"] = prefix_ref(changed, last)
        rejects(lambda: decision.capture_state(wrong, "panel_hover", changed, changed_rows), "source-defined")
    lines = raw.splitlines(keepends=True)
    lines.insert(first, lines[first - 1].replace(b"selected_unit=2", b"selected_unit=3"))
    changed = b"".join(lines)
    changed_rows, _, _ = command_parser.parse_events(changed.decode())
    wrong = copy.deepcopy(sidecar)
    wrong["InputObservationBefore"] = prefix_ref(changed, first)
    wrong["InputObservationAfter"] = prefix_ref(changed, last + 1)
    rejects(lambda: decision.capture_state(wrong, "panel_hover", changed, changed_rows), "changed across")
    # Change an entire later pair consistently: per-capture validation passes,
    # but the selected unit must remain identical across both protocol phases.
    lines = raw.splitlines(keepends=True)
    for index in range(5, 9):
        lines[index] = lines[index].replace(b"selected_unit=2", b"selected_unit=3")
    altered_raw = b"".join(lines)
    log_path = Path(command["raw_log"]["path"])
    log_path.write_bytes(altered_raw)
    altered_command = copy.deepcopy(command)
    altered_command["raw_log"] = ref(log_path)
    for pair in composition["frames"].values():
        for record in pair:
            metadata_path = Path(record["sidecar"]["path"])
            metadata = decision.read_object(metadata_path)
            for key in ("InputObservationBefore", "InputObservationAfter"):
                metadata[key] = prefix_ref(altered_raw, metadata[key]["line"])
            write_json(metadata_path, metadata)
            record["sidecar"] = ref(metadata_path)
    assert_contains(decision.validate_composition(composition, altered_command, START, FINISH), "changes the selected unit")
    image = decision.visible.read_png(Path(item["path"]))
    assert decision.asset_composition.check_frame(image, assets, state, "panel_hover") == []
    overlay = decision.asset_composition.sprite_pixels(assets["panel"][14], 608, 528)
    base = decision.asset_composition.expected_panel(assets, state, (608, 528), 1, False)
    # A complete stable frame without the source hover overlay must still fail.
    missing_hover = SimpleNamespace(width=800, height=600,
        rgb_at=lambda x, y: assets["palette"][base[x, y]] if (x, y) in overlay else image.rgb_at(x, y))
    assert_contains(decision.asset_composition.check_frame(missing_hover, assets, state, "panel_hover"), "hover/cursor composition")
    pointer = decision.asset_composition.sprite_pixels(assets["mouse"][state["cursor_sprite"]],
                                                        state["cursor_x"], state["cursor_y"])
    missing_pointer = SimpleNamespace(width=800, height=600,
        rgb_at=lambda x, y: (0, 0, 0) if (x, y) in pointer else image.rgb_at(x, y))
    assert_contains(decision.asset_composition.check_frame(missing_pointer, assets, state, "panel_hover"), "native cursor pixels")
    duplicate = decision.asset_composition.expected_panel(assets, state, (416, 400), 1)
    old_panel = SimpleNamespace(width=800, height=600,
        rgb_at=lambda x, y: assets["palette"][duplicate[x, y]] if (x, y) in duplicate else image.rgb_at(x, y))
    assert_contains(decision.asset_composition.check_frame(old_panel, assets, state, "panel_hover"), "legacy anchor")
    no_content = SimpleNamespace(width=800, height=600, rgb_at=lambda x, y: (30, 60, 90))
    assert_contains(decision.asset_composition.check_frame(no_content, assets, state, "panel_hover"), "source sprite")
    # Source identity remains required even when the supplied reference is rehashed.
    resource = temp / "DATA/minimum.res"
    resource.write_bytes(resource.read_bytes() + b"unapproved alteration")
    rejects(lambda: decision.composition_sources(command), "raw SHA-256")


def test_hygiene_cannot_predate_run() -> None:
    hygiene = {"passed": True, "matching_process_count": 0, "matching_processes": [],
               "inspection_returncode": 0, "inspection_error": "", "failures": [],
               "target_exact_names": ["cdb.exe"], "target_prefixes": ["clash95"],
               "generated_at": "2026-09-05T12:11:00Z"}
    assert decision.validate_hygiene(hygiene, FINISH) == []
    assert_contains(decision.validate_hygiene(dict(hygiene, generated_at=START), FINISH), "predates")
    assert_contains(decision.validate_hygiene(dict(hygiene, matching_process_count=1), FINISH), "not passing")


def test_manual_proof_requires_five_real_references(temp: Path) -> None:
    proof, expected_base = manual_fixture(temp)
    patcher = fixture_patcher(expected_base)
    with mock.patch.object(decision.manual, "EXPECTED_CANDIDATE_ROOT", str(temp)), \
            mock.patch.object(patch_stage_report, "load_patcher", return_value=patcher):
        assert decision.validate_manual_proof(proof) == []
        wrong = copy.deepcopy(proof)
        wrong["checked_items"][0]["artifacts"] = []
        assert_contains(decision.validate_manual_proof(wrong), "raw observation artifacts")
        wrong = copy.deepcopy(proof)
        wrong["checked_items"].append(wrong["checked_items"][0])
        assert_contains(decision.validate_manual_proof(wrong), "five unique")
        wrong = copy.deepcopy(proof)
        wrong["checked_items"][0]["executable_sha256"] = "B" * 64
        assert_contains(decision.validate_manual_proof(wrong), "actual candidate SHA")
        wrong = copy.deepcopy(proof)
        wrong["approved_visible_runtime"] = False
        assert_contains(decision.validate_manual_proof(wrong), "approved_visible_runtime")
        wrong = copy.deepcopy(proof)
        wrong["checked_items"] = wrong["checked_items"][:-1]
        assert_contains(decision.validate_manual_proof(wrong), "missing passing items")
        wrong = copy.deepcopy(proof)
        wrong["checked_items"][2]["candidate_path"] = wrong["checked_items"][0]["candidate_path"]
        wrong["checked_items"][2]["executable_sha256"] = wrong["checked_items"][0]["executable_sha256"]
        assert_contains(decision.validate_manual_proof(wrong), "declared stage bytes")


def manual_fixture(temp: Path) -> tuple[dict, bytes]:
    artifact = temp / "observation.txt"
    artifact.write_text("Synthetic test observation; not game evidence.", encoding="utf-8")
    items = []
    base = b""
    for item in decision.manual.CHECKLIST_ITEMS:
        candidate = temp / (item["id"] + ".exe")
        report, base, _ = synthetic_candidate(candidate, item["stage"])
        items.append({"id": item["id"], "stage": item["stage"], "status": "passed", "no_crash": True,
                      "observed_result": "Synthetic test observation", "evidence": str(artifact), "pass_fail_notes": "Fixture only",
                      "candidate_path": str(candidate), "executable_sha256": report["exe_sha256"], "artifacts": [str(artifact)]})
    proof = {"evidence_class": "manual_directinput", "approved_visible_runtime": True,
             "approval_record": "Synthetic fixture approval only", "candidate_path": items[0]["candidate_path"],
             "executable_sha256": items[0]["executable_sha256"], "no_stale_processes": True, "checked_items": items}
    return proof, base


def fixture_patcher(base: bytes) -> SimpleNamespace:
    # Only the known source hash is substituted for a synthetic byte fixture.
    # Every real patch definition, byte comparison and evidence parser remains active.
    fields = vars(patch_stage_report.load_patcher()).copy()
    fields["EXPECTED_SHA256"] = hashlib.sha256(base).hexdigest()
    return SimpleNamespace(**fields)


def test_full_raw_evidence_path_can_be_eligible_without_promotion(temp: Path) -> None:
    _, base, candidate_bytes = synthetic_candidate(temp / "candidate-template.fixture", STAGE)
    composition, command = composition_fixture(temp, native=True, candidate_bytes=candidate_bytes)
    manifest_path = Path(command["source_manifest"]["path"])
    manifest = command_parser.read_object(manifest_path)
    candidate = Path(manifest["identity"]["candidate_path"])
    ident = manifest["identity"]
    log = Path(manifest["raw_log"]["path"])
    approval = Path(manifest["approval"]["path"])
    hidden, hidden_run = hidden_fixture(temp)
    hidden_run["CandidateSha256"] = ident["candidate_sha256"]
    hidden_run["CandidatePath"] = str(candidate)
    hidden_run["InputSha256"] = hashlib.sha256(base).hexdigest()
    proof, manual_base = manual_fixture(temp)
    assert base == manual_base
    hygiene = {"passed": True, "matching_process_count": 0, "matching_processes": [],
               "inspection_returncode": 0, "inspection_error": "", "failures": [],
               "target_exact_names": ["cdb.exe"], "target_prefixes": ["clash95"], "generated_at": "2026-09-05T10:03:00Z"}
    args = decision.parse_args([])
    values = {"command_input_json": command, "composition_json": composition, "hidden_json": hidden,
              "hidden_run_json": hidden_run, "manual_proof": proof, "process_hygiene_json": hygiene}
    for name, value in values.items():
        setattr(args, name, write_json(temp / (name + ".json"), value))
    with mock.patch.object(decision.manual, "EXPECTED_CANDIDATE_ROOT", str(temp)), \
            mock.patch.object(patch_stage_report, "load_patcher", return_value=fixture_patcher(base)):
        args.patch_json = write_json(temp / "patch.json", patch_stage_report.build_report(candidate, STAGE))
        result = decision.build_decision(args)
        assert result["passed"] is True, result["failures"]
        assert result["component_promotion_ready"] is True
        assert result["decision"] == "eligible_for_hd_layout_component_review"
        assert result["promotion_ready"] is False and result["stable_stage_should_change"] is False
        assert result["full_game_complete"] is False
        receipt_path = Path(manifest["session_receipt"]["path"])
        original_receipt = receipt_path.read_bytes()
        original_manifest = manifest_path.read_bytes()
        wrong_receipt = decision.read_object(receipt_path)
        wrong_receipt["candidate_parent_pid"] = wrong_receipt["candidate_pid"]
        write_json(receipt_path, wrong_receipt)
        wrong_manifest = copy.deepcopy(manifest)
        wrong_manifest["session_receipt"] = command_fixtures.file_ref(receipt_path)
        write_json(manifest_path, wrong_manifest)
        optimistic = copy.deepcopy(command)
        optimistic["source_manifest"] = command_fixtures.file_ref(manifest_path)
        optimistic["session_receipt"] = command_fixtures.file_ref(receipt_path)
        write_json(args.command_input_json, optimistic)
        rejected = decision.build_decision(args)
        assert rejected["component_promotion_ready"] is False
        assert rejected["checks"]["command_input"]["passed"] is False
        assert_contains(rejected["failures"], "ownership")
        receipt_path.write_bytes(original_receipt)
        manifest_path.write_bytes(original_manifest)
        command_fixtures.replace_log(manifest_path, lambda text: text.replace("eax=1", "eax=0"))
        # Retain optimistic summary claims, update only references: reparsing must defeat them.
        command["source_manifest"] = ref(manifest_path)
        command["raw_log"] = ref(log)
        write_json(args.command_input_json, command)
        result = decision.build_decision(args)
        assert result["component_promotion_ready"] is False
        assert result["checks"]["command_input"]["passed"] is False
        assert_contains(result["failures"], "raw command evidence does not prove")


def test_missing_and_bool_only_inputs_fail_closed(temp: Path) -> None:
    missing = temp / "missing.json"
    args = decision.parse_args([])
    for field in ("command_input_json", "composition_json", "patch_json", "hidden_json", "hidden_run_json",
                  "manual_proof", "process_hygiene_json"):
        setattr(args, field, missing)
    outcome = decision.build_decision(args)
    assert outcome["passed"] is False and outcome["component_promotion_ready"] is False
    assert outcome["decision"] == "defer_hd_layout_completion"
    assert outcome["stable_stage_should_change"] is False and outcome["full_game_complete"] is False
    optimistic = write_json(temp / "optimistic.json", {"passed": True, "promotion_ready": True,
                                                      "command_click_alignment": True, "panel_click_callback_proof": True})
    args.command_input_json = optimistic
    assert decision.build_decision(args)["component_promotion_ready"] is False
    result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/hd_layout_completion_decision.py"),
        "--command-input-json", str(missing), "--manual-proof", str(missing), "--composition-json", str(missing),
        "--write-json", str(temp / "decision.json"), "--write-markdown", str(temp / "decision.md"), "--require-pass"],
        capture_output=True, text=True, check=False)
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads((temp / "decision.json").read_text())["component_promotion_ready"] is False


def run_tests() -> None:
    with tempfile.TemporaryDirectory(prefix="hd-layout-completion-fixtures-") as directory, \
            mock.patch.object(decision.asset_composition, "RESOURCE_SHA256", hashlib.sha256(fixture_resource()).hexdigest()):
        root = Path(directory)
        for index, test in enumerate((test_authoritative_bytes_and_original_reconstruction,
            test_hidden_summary_cannot_be_pasted_or_rebound, test_composition_requires_same_run_raw_pixels,
            test_manual_proof_requires_five_real_references, test_missing_and_bool_only_inputs_fail_closed,
            test_full_raw_evidence_path_can_be_eligible_without_promotion, test_native_capture_numeric_mapping,
            test_native_capture_states_and_source_content)):
            temp = root / str(index)
            temp.mkdir()
            test(temp)
        test_hygiene_cannot_predate_run()


if __name__ == "__main__":
    run_tests()
    print("HD layout completion decision tests passed")
