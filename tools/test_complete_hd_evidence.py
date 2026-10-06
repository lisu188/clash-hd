#!/usr/bin/env python3
"""Offline complete-HD eligibility fixtures. Synthetic files are never runtime proof."""
from __future__ import annotations

import contextlib
import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import complete_hd_evidence as evidence
import complete_hd_promotion as promotion


def write(path: Path, value) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (json.dumps(value, indent=2) + "\n").encode()
    path.write_bytes(data)
    return {"path": str(path), "sha256": evidence.digest(data)}


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.original = b"fixture-only synthetic original; not game material"
        self.candidate = self.original + b"fixture-only complete-HD changes"
        self.probe = "fixture-only observation probe\n"
        producer = write(self.repo / "tools/fixture_validator.py", b"# fixture-only validator source\n")
        self.metadata = {
            "schema": 1, "stage": evidence.STAGE, "resolution": "1920x1080",
            "base_sha256": evidence.digest(self.original), "candidate_sha256": evidence.digest(self.candidate),
            "recipe_revision": evidence.RECIPE_REVISION,
            "source_hashes": {"tools/fixture_validator.py": producer["sha256"]},
            "patch_records": [{"offset": 0, "old": "00", "new": "01", "group": "fixture-only"}],
            "predecessor": {"fixture_only": True}, "probe_sha256": evidence.digest(self.probe.encode()),
        }
        refs = {
            "base_executable": write(root / "external/base.exe", self.original),
            "executable": write(root / "external/candidate.exe", self.candidate),
            "metadata": write(root / "evidence/builder.json", self.metadata),
            "probe": write(root / "evidence/probe.cdb", self.probe.encode()),
        }
        self.identity = {
            "stage": evidence.STAGE, "resolution": "1920x1080", "candidate_sha256": evidence.digest(self.candidate),
            "base_sha256": evidence.digest(self.original), "recipe_revision": evidence.RECIPE_REVISION,
            "metadata_sha256": refs["metadata"]["sha256"], "probe_sha256": evidence.digest(self.probe.encode()),
        }
        wrapper = write(root / "external/ddraw.dll", b"fixture-only wrapper identity")
        config = write(root / "external/dxcfg.ini", b"fixture-only config identity")
        self.now = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.start = self.now - timedelta(hours=10)
        self.reports = {}
        self.measured_checks = {}
        self.manifest = {"schema": evidence.RELEASE_SCHEMA, "candidate": refs, "lanes": {}}
        for name, (classes, checks) in evidence.LANES.items():
            hidden = name not in evidence.VISIBLE_LANES
            profile = {"environment": "hidden_cdb_host" if hidden else "host_visible",
                       "input_method": "not_applicable_hidden" if hidden else "manual_directinput",
                       "wrapper": wrapper, "wrapper_config": config}
            report = {
                "schema": evidence.LANE_SCHEMA, "lane": name, "identity": copy.deepcopy(self.identity),
                "passed": True, "failures": [], "evidence_class": classes[0], "stable_stage_should_change": False,
                "checks": {key: {"passed": True, "failures": []} for key in checks},
                "producer": producer,
                "source_artifacts": [write(root / f"evidence/{name}.log", b"fixture-only synthetic source trace")],
                "run_id": "fixture-only-" + name, "started_at": self.stamp(310), "finished_at": self.stamp(311),
                "generated_at": self.now.isoformat(), "runtime_profile": profile,
                "no_crash": True, "process_cleanup_verified": True,
                "input_injected": False, "input_or_callback_forced": False,
                "observed_result": "fixture-only expected observation; not real runtime evidence",
                "pass_fail_notes": "fixture-only passing outcome; not real runtime evidence",
                "live_save_mutated": False, "safe_test_save": True,
                "before_state_sha256": "a" * 64, "after_state_sha256": ("a" if name == "save_load_roundtrip" else "b") * 64,
                "release_resolutions": ["1920x1080"],
            }
            if name == "short_soak_ladder":
                rows, seconds = [], 0
                for tier, route, duration in evidence.SHORT_STEPS:
                    rows.append({"tier": tier, "route": route, "duration_sec": duration,
                                 "identity": copy.deepcopy(self.identity), "passed": True, "clean_stop": True,
                                 "started_at": self.stamp(seconds / 60), "finished_at": self.stamp((seconds + duration) / 60)})
                    seconds += duration
                report.update(steps=rows, started_at=rows[0]["started_at"], finished_at=rows[-1]["finished_at"],
                              input_responsiveness="not_applicable_hidden")
            elif name in ("long_map_idle", "long_map_pan"):
                minute = 60 if name == "long_map_idle" else 181
                report.update(tier="long2h", route="map-idle" if name == "long_map_idle" else "map-pan",
                              duration_sec=7200, clean_stop=True, started_at=self.stamp(minute), finished_at=self.stamp(minute + 120),
                              input_responsiveness="not_applicable_hidden")
            if name in evidence.VISIBLE_LANES:
                approval = {
                    "approved": True, "approval_record": "fixture-only simulated approval; not user/runtime consent",
                    "identity": copy.deepcopy(self.identity), "run_id": report["run_id"], "runtime_profile": profile,
                    "approved_at": self.stamp(309), "expires_at": self.stamp(312),
                }
                report["approval"] = write(root / f"evidence/{name}-approval.json", approval)
            self.reports[name] = report
            self.measured_checks[name] = copy.deepcopy(report["checks"])
            self.save_lane(name)
        self.path = root / "evidence/release.json"
        self.save()

    def stamp(self, minutes):
        return (self.start + timedelta(minutes=minutes)).isoformat()

    def builder(self, original, resolution):
        assert original == self.original and resolution == "1920x1080"
        return self.candidate, copy.deepcopy(self.metadata), self.probe

    def save_lane(self, name):
        self.manifest["lanes"][name] = write(self.root / f"evidence/{name}.json", self.reports[name])

    def save(self):
        write(self.path, self.manifest)

    def evaluate(self, *, fixture_verifiers=True):
        self.save()
        # Synthetic positive policy fixtures use explicitly injected verifier
        # code. Production never installs these or accepts a verifier from JSON.
        def replay(report, report_path, context, repo_root):
            return {"passed": True, "failures": [], "checks": copy.deepcopy(self.measured_checks[report["lane"]])}
        verifiers = {name: ("tools/fixture_validator.py", replay) for name in evidence.LANES}
        with patch.object(evidence, "BASE_SHA256", evidence.digest(self.original)), \
             patch.object(evidence, "CANDIDATE_ROOT", self.root / "external"), \
             (patch.object(evidence, "LANE_VERIFIERS", verifiers) if fixture_verifiers else contextlib.nullcontext()):
            return evidence.evaluate_release_manifest(self.path, builder=self.builder, repo_root=self.repo)


def test_pinned_json_references_reject_duplicate_keys_and_invalid_numbers(root):
    invalid = (
        (b'{"approved":false,"approved":true}', "duplicate JSON key"),
        (b'{"identity":{"stage":"wrong","stage":"claimed"}}', "duplicate JSON key"),
        (b'{"rows":[{"passed":false,"passed":true}]}', "duplicate JSON key"),
        (b'{"measurement":NaN}', "invalid JSON numeric constant"),
        (b'{"measurement":Infinity}', "invalid JSON numeric constant"),
        (b'{"measurement":-Infinity}', "invalid JSON numeric constant"),
        (b'{"measurement":1e9999}', "non-finite JSON number"),
        (b'{"measurement":-1e9999}', "non-finite JSON number"),
        (b'{"nested":' + b'[' * 64 + b'0' + b']' * 64 + b'}', "container nesting exceeds 64"),
        (b'{"nested":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}', "parser capacity"),
    )
    for index, (data, reason) in enumerate(invalid):
        reference = write(root / f"invalid-{index}.json", data)
        # A correct digest cannot make ambiguous or non-JSON content valid.
        assert evidence.read_reference(reference, root)[1] == data
        for read in (
            lambda: evidence.read_reference(reference, root, json_object=True),
            lambda: evidence.verify_reference_graph({"retained": reference}, root),
        ):
            try:
                read()
            except ValueError as exc:
                assert reason in str(exc), (index, str(exc))
            else:
                raise AssertionError((index, "invalid pinned JSON was accepted"))

    valid = b'\xef\xbb\xbf{"rows":[{"name":"first","value":1.25},{"name":"second","value":-2e2}],"approved":false}'
    reference = write(root / "valid.json", valid)
    expected = {"rows": [{"name": "first", "value": 1.25}, {"name": "second", "value": -200.0}],
                "approved": False}
    assert evidence.read_reference(reference, root, json_object=True)[1] == expected
    evidence.verify_reference_graph({"retained": reference}, root)
    assert Path(reference["path"]).read_bytes() == valid
    deepest = b'{"nested":' + b'[' * 63 + b'0' + b']' * 63 + b'}'
    reference = write(root / "maximum-depth.json", deepest)
    evidence.read_reference(reference, root, json_object=True)
    evidence.verify_reference_graph({"retained": reference}, root)


def test_release_json_rejects_ambiguity_before_candidate_reconstruction(root):
    cases = (
        b'{"schema":"unsupported","schema":"' + evidence.RELEASE_SCHEMA.encode() + b'"}',
        b'{"candidate":{"identity":{"passed":false,"passed":true}}}',
        b'{"untrusted":NaN}',
        b'{"untrusted":1e9999}',
        b'{"untrusted":' + b'[' * 64 + b'0' + b']' * 64 + b'}',
        b'{"untrusted":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}',
    )
    for index, data in enumerate(cases):
        reference = write(root / f"release-{index}.json", data)
        with patch.object(evidence, "candidate_context", side_effect=AssertionError("must fail before candidate reads")):
            result = evidence.evaluate_release_manifest(Path(reference["path"]))
        assert result["passed"] is False and result["evidence_ready"] is False, result
        assert result["promotion_ready"] is False and result["candidate_context"] == {}, result
        assert result["failures"], result
        assert Path(reference["path"]).read_bytes() == data


def test_reference_graph_handles_long_chains_and_rechecks_shared_inputs(root):
    leaf = write(root / "leaf.json", b'{"leaf":true}')
    reference = leaf
    for index in range(40):
        # Every individual document stays below the 64-container bound; their
        # combined graph exceeds the old recursive walk's Python stack limit.
        nested = reference
        for _ in range(32):
            nested = [nested]
        data = json.dumps(nested, separators=(",", ":")).encode()
        reference = write(root / f"chain-{index}.json", data)
    seen = set()
    evidence.verify_reference_graph({"retained": reference, "shared": reference}, root, seen)
    assert len(seen) == 41, seen
    # Seen inputs still have their bytes rechecked, rather than trusting a prior
    # graph visit after the same correctly recorded input has changed.
    Path(leaf["path"]).write_bytes(b'{"leaf":false}')
    try:
        evidence.verify_reference_graph(leaf, root, seen)
    except ValueError as exc:
        assert "artifact SHA-256 mismatch" in str(exc), str(exc)
    else:
        raise AssertionError("changed shared input was accepted")


def test_complete_evidence_only_grants_eligibility(root):
    fixture = Fixture(root)
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    result = fixture.evaluate()
    assert result["passed"] and result["evidence_ready"] and result["eligible_for_stable_promotion"], result
    assert len(result["lanes"]) == len(evidence.LANES) == 16
    assert result["promotion_approved"] is False and result["promotion_ready"] is False
    assert result["stable_stage_should_change"] is False and result["checklist_updated"] is None
    assert result["full_game_complete"] is False
    assert before == {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_candidate_rebuild_is_required(root):
    cases = ("candidate", "metadata", "probe", "source", "original", "resolution")
    for case in cases:
        fixture = Fixture(root / case)
        if case == "candidate":
            fixture.manifest["candidate"]["executable"] = write(fixture.root / "external/other.exe", b"different bytes with matching claimed artifact hash")
        elif case == "metadata":
            changed = copy.deepcopy(fixture.metadata)
            changed["patch_records"] = []
            fixture.manifest["candidate"]["metadata"] = write(fixture.root / "evidence/other-builder.json", changed)
        elif case == "probe":
            fixture.manifest["candidate"]["probe"] = write(fixture.root / "evidence/other.cdb", b"wrong probe")
        elif case == "source":
            (fixture.repo / "tools/fixture_validator.py").write_bytes(b"changed source")
        elif case == "original":
            fixture.manifest["candidate"]["base_executable"] = write(fixture.root / "external/other-base.exe", b"unknown original")
        else:
            changed = copy.deepcopy(fixture.metadata)
            changed["resolution"] = "800x600"
            fixture.manifest["candidate"]["metadata"] = write(fixture.root / "evidence/other-builder.json", changed)
            fixture.builder = lambda original, resolution: (fixture.candidate, changed, fixture.probe)
        result = fixture.evaluate()
        assert not result["passed"] and not result["promotion_ready"], (case, result)


def test_missing_failed_and_mismatched_lanes(root):
    for name in evidence.LANES:
        fixture = Fixture(root / name)
        fixture.reports[name]["identity"]["candidate_sha256"] = "0" * 64
        fixture.save_lane(name)
        result = fixture.evaluate()
        assert not result["passed"] and any(name in item for item in result["failures"]), (name, result)
    fixture = Fixture(root / "missing")
    del fixture.manifest["lanes"]["battle_entry_return"]
    assert not fixture.evaluate()["passed"]
    fixture = Fixture(root / "exit-zero-defer")
    fixture.reports["panel_command"].update(passed=True, decision="defer_stable_promotion")
    fixture.reports["panel_command"]["checks"]["panel_click_callback_proof"]["passed"] = False
    fixture.save_lane("panel_command")
    assert not fixture.evaluate()["passed"]


def test_archived_component_and_evidence_rebinding_fail(root):
    fixture = Fixture(root / "legacy")
    fixture.reports["geometry"] = {"passed": True, "candidate_sha256": "a" * 64, "stage": "castlecenter-all", "failures": []}
    fixture.save_lane("geometry")
    assert not fixture.evaluate()["passed"]
    for case in ("artifact", "producer", "approval", "future", "profile"):
        fixture = Fixture(root / case)
        row = fixture.reports["stable_menu_load"]
        if case == "artifact":
            Path(row["source_artifacts"][0]["path"]).write_bytes(b"changed raw evidence")
        elif case == "producer":
            row["producer"] = row["source_artifacts"][0]
        elif case == "approval":
            approval = json.loads(Path(row["approval"]["path"]).read_text())
            approval["identity"]["resolution"] = "800x600"
            row["approval"] = write(Path(row["approval"]["path"]), approval)
        elif case == "future":
            row["generated_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        else:
            row["runtime_profile"]["environment"] = "guest_win98"
        fixture.save_lane("stable_menu_load")
        assert not fixture.evaluate()["passed"], case


def test_manual_input_and_callback_remain_separate(root):
    for lane, field, value in (
        ("stable_menu_load", "evidence_class", "approved_hidden_cdb_host_soak"),
        ("stable_hd_map_input", "input_injected", True),
        ("right_bottom_validation_input", "input_or_callback_forced", True),
        ("castle_overview_centered_input", "observed_result", ""),
        ("panel_command", "input_or_callback_forced", True),
    ):
        fixture = Fixture(root / (lane + field))
        fixture.reports[lane][field] = value
        fixture.save_lane(lane)
        assert not fixture.evaluate()["passed"]


def test_soak_ladder_and_long_routes_fail_closed(root):
    for case in ("empty", "order", "short", "overlap", "identity", "cleanup", "hidden-input", "premature-long"):
        fixture = Fixture(root / case)
        lane = "short_soak_ladder"
        row = fixture.reports[lane]
        if case == "empty":
            row["steps"] = []
        elif case == "order":
            row["steps"][1], row["steps"][2] = row["steps"][2], row["steps"][1]
        elif case == "short":
            row["steps"][-1]["duration_sec"] = 1799
        elif case == "overlap":
            row["steps"][-1]["started_at"] = row["steps"][0]["started_at"]
        elif case == "identity":
            row["steps"][-1]["identity"]["resolution"] = "800x600"
        elif case == "cleanup":
            row["steps"][-1]["clean_stop"] = False
        elif case == "hidden-input":
            row["input_responsiveness"] = "passed"
        else:
            lane = "long_map_idle"
            fixture.reports[lane].update(started_at=fixture.stamp(0), finished_at=fixture.stamp(120))
        fixture.save_lane(lane)
        assert not fixture.evaluate()["passed"], case


def test_promotion_is_explicit_and_bound_to_exact_acceptance(root):
    fixture = Fixture(root)
    result = fixture.evaluate()
    decision = {"schema": "complete_hd_promotion_decision_v1", "decision": "approve_complete_hd_promotion",
                "approved": True, "approval_record": "fixture-only simulated promotion decision, not actual user consent",
                "approved_at": fixture.now.isoformat(), "current_stable_stage": evidence.STABLE_STAGE,
                "identity": fixture.identity, "acceptance_sha256": result["acceptance_sha256"]}
    fixture.manifest["promotion_decision"] = write(root / "evidence/promotion.json", decision)
    result = fixture.evaluate()
    assert result["passed"] and result["promotion_ready"] and result["promotion_approved"], result
    assert result["stable_stage_should_change"] is False and result["checklist_updated"] is None
    # Even another honest report requires a new decision binding the new set.
    fixture.reports["geometry"]["observed_result"] = "additional fixture-only observation"
    fixture.save_lane("geometry")
    result = fixture.evaluate()
    assert result["evidence_ready"] and not result["promotion_ready"] and result["promotion_failures"], result


def test_complete_cli_does_not_run_component_subprocesses(root):
    fixture = Fixture(root)
    output = root / "summary.json"
    before_checklist = (promotion.ROOT / "reports/final_hd_release_checklist.md").read_bytes()
    with patch.object(promotion, "run_step", side_effect=AssertionError("no child process may launch")), \
         patch.object(evidence, "evaluate_release_manifest", return_value=fixture.evaluate()), contextlib.redirect_stdout(io.StringIO()):
        result = promotion.main(["--release-manifest", str(fixture.path), "--candidate-manifest", str(root / "evidence/builder.json"), "--write-json", str(output), "--require-pass"])
        assert result == 0
        result = promotion.main(["--release-manifest", str(fixture.path), "--candidate-manifest", str(root / "evidence/builder.json"), "--write-json", str(output), "--update-checklist"])
        assert result == 2
    assert (promotion.ROOT / "reports/final_hd_release_checklist.md").read_bytes() == before_checklist


def test_self_authored_green_envelopes_cannot_establish_release(root):
    fixture = Fixture(root)
    result = fixture.evaluate(fixture_verifiers=False)
    assert not result["evidence_ready"] and not result["eligible_for_stable_promotion"] and not result["promotion_ready"], result
    assert "geometry" in result["unimplemented_lane_verifiers"]
    assert any("source-artifact verifier is not implemented" in row for row in result["failures"]), result
    # A zero-exit reporting command must not disguise incomplete release proof,
    # even when the caller forgot --require-pass.
    with patch.object(evidence, "evaluate_release_manifest", return_value=result), contextlib.redirect_stdout(io.StringIO()):
        status = promotion.main(["--release-manifest", str(fixture.path), "--candidate-manifest", str(root / "evidence/builder.json"),
                                 "--write-json", str(root / "incomplete-summary.json")])
    assert status == 2


def test_claimed_pass_must_match_independently_replayed_checks(root):
    fixture = Fixture(root)
    fixture.measured_checks["geometry"]["partial_tiles"] = {"passed": False, "failures": ["unexplained blank visible cell"]}
    result = fixture.evaluate()
    assert not result["evidence_ready"]
    assert any("source-artifact check is missing or failed: partial_tiles" in row for row in result["failures"]), result


def test_actual_resolution_manifest_is_replayed(root):
    fixture = Fixture(root)
    report = fixture.reports["resolution_coverage"]
    source = write(fixture.repo / "tools/complete_hd_evidence.py", b"fixture-only validator source")
    manifest = json.loads((evidence.ROOT / "src/launcher/resolutions.json").read_text(encoding="utf-8"))
    report["producer"] = source
    manifest_path = fixture.repo / "src/launcher/resolutions.json"
    context = {"identity": fixture.identity, "byte_rebuild_passed": True}

    def evaluate(current):
        report["resolution_manifest"] = write(manifest_path, current)
        fixture.save_lane("resolution_coverage")
        return evidence.evaluate_lane("resolution_coverage", fixture.manifest["lanes"]["resolution_coverage"], context,
                                      fixture.path.parent, repo_root=fixture.repo)

    # The supported Complete-HD profile establishes metadata coverage only;
    # the other fifteen production lane verifiers remain incomplete.
    result = evaluate(manifest)
    assert result["passed"], result
    missing = copy.deepcopy(manifest)
    missing["profiles"].pop("completehd")
    result = evaluate(missing)
    assert not result["passed"] and any("advertised_resolution_matches" in row for row in result["failures"]), result
    unsupported = copy.deepcopy(manifest)
    unsupported["profiles"]["unknown"] = copy.deepcopy(manifest["profiles"]["completehd"])
    result = evaluate(unsupported)
    assert not result["passed"] and any("Schema 2 requires" in row for row in result["failures"]), result
    for mutation in ("malformed-profile", "projection", "recipe", "features", "complete-stage", "complete-recipe",
                     "complete-features", "complete-default", "complete-resolutions", "complete-stable", "complete-validated"):
        invalid = copy.deepcopy(manifest)
        if mutation == "malformed-profile": invalid["profiles"]["framed"] = []
        elif mutation == "projection": invalid["resolutions"]["800x600"]["status"] = "experimental"
        elif mutation == "recipe": invalid["profiles"]["framed"]["recipe_revision"] = "unsupported-recipe"
        elif mutation == "features": invalid["profiles"]["framed"]["features"]["minimap_viewport"] = 1
        elif mutation == "complete-stage": invalid["profiles"]["completehd"]["stage"] = evidence.STABLE_STAGE
        elif mutation == "complete-recipe": invalid["profiles"]["completehd"]["recipe_revision"] = "unsupported-recipe"
        elif mutation == "complete-features": invalid["profiles"]["completehd"]["features"]["minimap_viewport"] = False
        elif mutation == "complete-default": invalid["profiles"]["completehd"]["default"] = "1920x1080"
        elif mutation == "complete-resolutions": invalid["profiles"]["completehd"]["resolutions"] = None
        else: invalid["profiles"]["completehd"]["resolutions"]["1920x1080"]["status"] = mutation.removeprefix("complete-")
        result = evaluate(invalid)
        assert not result["passed"], (mutation, result)

    # Unit-test the remaining metadata predicates using a supported profile.
    # This assumed context is not a reconstructed complete-HD candidate and
    # cannot be used to claim whole-release or runtime acceptance.
    framed = manifest["profiles"]["framed"]
    supported_context = {"identity": {**fixture.identity, "stage": framed["stage"],
                                      "recipe_revision": framed["recipe_revision"]}, "byte_rebuild_passed": True}
    report["resolution_manifest"] = write(manifest_path, manifest)
    result = evidence._resolution_verifier(report, fixture.path, supported_context, fixture.repo)
    assert result["passed"], result
    wrong_recipe = copy.deepcopy(supported_context)
    wrong_recipe["identity"]["recipe_revision"] = "different-recipe"
    result = evidence._resolution_verifier(report, fixture.path, wrong_recipe, fixture.repo)
    assert not result["passed"] and "advertised_resolution_matches" in result["failures"], result
    framed["resolutions"]["1920x1080"].update(
        status="validated", evidence={"fixture": "fixture-only-not-runtime-proof.json"},
        evidence_scope={key: copy.deepcopy(framed[key]) for key in ("stage", "recipe_revision", "features")})
    report["resolution_manifest"] = write(manifest_path, manifest)
    result = evidence._resolution_verifier(report, fixture.path, supported_context, fixture.repo)
    assert not result["passed"] and "other_resolutions_not_promoted" in result["failures"], result


def test_shared_candidate_manifest_argument_cannot_rebind_index(root):
    fixture = Fixture(root)
    with patch.object(evidence, "BASE_SHA256", evidence.digest(fixture.original)), \
         patch.object(evidence, "CANDIDATE_ROOT", fixture.root / "external"):
        result = evidence.evaluate_release_manifest(fixture.path, candidate_manifest=root / "other.candidate.json",
                                                    builder=fixture.builder, repo_root=fixture.repo)
    assert not result["evidence_ready"] and any("--candidate-manifest differs" in row for row in result["failures"]), result


def test_release_summary_never_replaces_immutable_input(root):
    fixture = Fixture(root)
    before = fixture.path.read_bytes()
    with patch.object(evidence, "evaluate_release_manifest", return_value=fixture.evaluate()), \
         contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        status = promotion.main(["--release-manifest", str(fixture.path), "--candidate-manifest", str(root / "evidence/builder.json"),
                                 "--write-json", str(fixture.path)])
    assert status == 2 and fixture.path.read_bytes() == before


def raw_soak_fixture(route="map-idle"):
    """Tiny invented bytes/observations in the existing format, never runtime proof."""
    identity = {"stage": evidence.STABLE_STAGE, "resolution": "4x4", "base_sha256": evidence.BASE_SHA256,
                "candidate_sha256": evidence.digest(b"synthetic raw-soak fixture, not an executable")}
    pan = int(route == "map-pan")
    ready = {"source": "SOAK_SURFDUMP_READY", "redraw_seq": 4, "surface": "00100000", "base": "00110000",
             "width": 4, "height": 4, "bytes": 16}
    start = {"route_ticks": 7680, "pan": pan, "player": 0, "tick": 10000, "game_data": "00200000", "scroll_x": 4, "scroll_y": 4}
    end = {"route_ticks": 7680, "pan": pan, "hits": 8192, "tick_delta": 7680, "player": 0, "scroll_x": 4, "scroll_y": 5 if pan else 4}
    events = [{"phase": phase, "x": x, "y": y, "hits": hits, "tick_delta": ticks, "delta_x": 1, "delta_y": 1}
              for phase, x, y, hits, ticks in ((0, 4, 4, 1, 1280), (1, 5, 4, 2, 2560),
                                              (2, 5, 5, 2049, 3840), (3, 4, 5, 3000, 5120))] if pan else []
    lines = [f"SOAK_ROUTE_START route_ticks=7680 pan={pan} player=0 tick=10000 gd=00200000 scroll=(4,4)",
             "SOAK_SURFDUMP_READY redraw_seq=4 surface=00100000 size=(4,4) base=00110000 bytes=16"]
    heartbeat = f"SOAK_HEARTBEAT hits=2048 tickdelta=3840 player=0 scroll=({5 if pan else 4},4)"
    if pan:
        lines.append("SOAK_PAN_PLAN base=(4,4) delta=(1,1) max=(10,10) safe=1")
        for event in events:
            if event["phase"] == 2:
                lines.append(heartbeat)
            lines.append(f"SOAK_PAN_SET phase={event['phase']} x={event['x']} y={event['y']} hits={event['hits']} tickdelta={event['tick_delta']} delta=(1,1)")
    else:
        lines.append(heartbeat)
    lines += [f"SOAK_ROUTE_END route_ticks=7680 pan={pan} hits=8192 tickdelta=7680 player=0 scroll=(4,{5 if pan else 4})",
              "SURFDUMP_READY redraw_seq=4 surface=00100000 size=(4,4) base=00110000 bytes=16"]
    raw = {f"frame-{index + 1:04d}": bytes(range(index, index + 16)) for index in range(3)}
    begin = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    frames, processes = [], []
    for index, (name, data) in enumerate(raw.items()):
        timestamp = (begin + timedelta(seconds=index * 60)).isoformat()
        frames.append({"Name": name, "Timestamp": timestamp, "Width": 4, "Height": 4,
                       "Hash": evidence.digest(data), "NonblackPercent": round(100 * (16 - data.count(0)) / 16, 3),
                       "UniqueSampleColors": len(set(data)), "CaptureMode": "hidden-cdb-host-readprocessmemory", "RenderEvidence": True})
        processes.append({"Timestamp": timestamp, "HasExited": False, "ExitCode": None,
                          "WorkingSet64": 8 * 1024 * 1024, "PrivateMemorySize64": 16 * 1024 * 1024, "HandleCount": 20})
    samples = {"schema": "hidden_cdb_host_soak_samples_v1", "executed": True, "environment": "hidden_cdb_host",
               "launch_mode": "hidden-desktop", "frame_read_method": "host_readprocessmemory", "route": route,
               "duration_sec": 120, "duration_ticks": 7680, "frame_interval_sec": 60, "pan_interval_sec": 20 if pan else None,
               "stage": identity["stage"], "candidate_sha256": identity["candidate_sha256"], "input_sha256": identity["base_sha256"],
               "input_responsiveness": "not_applicable_hidden", "ready_marker": ready, "route_start_marker": start,
               "route_end_marker": end, "heartbeat_count": 1, "pan_event_count": len(events), "pan_events": events,
               "surface": {"Base": "00110000", "Width": 4, "Height": 4, "Bytes": 16, "Source": "SOAK_SURFDUMP_READY"},
               "runner_failures": [], "capture_errors": [], "frame_samples": frames, "process_samples": processes,
               "cleanup": {"game_stopped": True, "cdb_stopped": True, "errors": [], "stopped_process_ids": [123, 456]},
               "clean_stop": True, "elapsed_coverage": {"passed": True}}
    for field in ("av_observed", "surface_invalid_observed", "app_request_quit_observed", "cdb_exit_before_duration",
                  "game_exit_before_duration", "process_exited_unexpectedly"):
        samples[field] = False
    return samples, "\n".join(lines), raw, identity


def audit_raw_fixture(parts):
    return evidence.audit_hidden_soak_raw(*parts, minimum_duration_sec=120)


def assert_raw_rejected(parts, expected):
    result = audit_raw_fixture(parts)
    assert not result["raw_validation_passed"] and not result["passed"] and not result["release_evidence_verified"], result
    assert any(expected in failure for failure in result["raw_failures"]), (expected, result)


def test_consistent_raw_diagnostics_never_become_release_proof(root):
    for route in ("map-idle", "map-pan"):
        result = audit_raw_fixture(raw_soak_fixture(route))
        assert result["raw_validation_passed"] and result["raw_failures"] == [], result
        assert not any(result[key] for key in ("passed", "release_evidence_verified", "candidate_authenticated",
                                               "clean_stop_verified", "input_evidence_verified")), result
        assert result["failures"] == result["producer_gaps"] == list(evidence.HIDDEN_SOAK_PRODUCER_GAPS)
        assert result["observations"]["frame_span_sec"] == result["observations"]["process_span_sec"] == 120
        assert result["observations"]["frame_metrics"][0]["unique_colors"] == 16
        assert result["observations"]["process_growth"] == {"WorkingSet64": 0, "PrivateMemorySize64": 0, "HandleCount": 0}
    assert len(set(evidence.LANES) - set(evidence.LANE_VERIFIERS)) == 14
    assert all(name not in evidence.LANE_VERIFIERS for name in ("short_soak_ladder", "long_map_idle", "long_map_pan"))


def test_raw_frame_inventory_requires_every_middle_buffer(root):
    for case in ("missing-middle", "truncated", "orphan", "duplicate-name", "omitted-row"):
        samples, log, raw, identity = raw_soak_fixture()
        if case == "missing-middle": raw.pop("frame-0002")
        elif case == "truncated": raw["frame-0002"] = raw["frame-0002"][:-1]
        elif case == "orphan": raw["frame-0004"] = bytes(range(16))
        elif case == "duplicate-name": samples["frame_samples"][1]["Name"] = "frame-0001"
        else: samples["frame_samples"].pop(1)
        assert_raw_rejected((samples, log, raw, identity), "raw")


def test_raw_bytes_recompute_hash_histogram_and_render_thresholds(root):
    for case in ("hash", "percent", "colors", "black-bytes", "uniform-bytes"):
        samples, log, raw, identity = raw_soak_fixture()
        row = samples["frame_samples"][1]
        if case == "hash": row["Hash"] = "f" * 64
        elif case == "percent": row["NonblackPercent"] = 99.0
        elif case == "colors": row["UniqueSampleColors"] = 8
        else:
            data = (b"\x00" if case == "black-bytes" else b"\x01") * 16
            raw["frame-0002"] = data
            row.update(Hash=evidence.digest(data), NonblackPercent=0 if case == "black-bytes" else 100, UniqueSampleColors=1)
        assert_raw_rejected((samples, log, raw, identity), "raw frame")


def test_raw_candidate_binding_cannot_reuse_stable_evidence_for_complete(root):
    for field, value in (("stage", evidence.STAGE), ("candidate_sha256", "f" * 64),
                         ("base_sha256", "0" * 64), ("resolution", "8x4")):
        samples, log, raw, identity = raw_soak_fixture()
        identity[field] = value
        assert_raw_rejected((samples, log, raw, identity), "candidate")
    samples, log, raw, identity = raw_soak_fixture()
    assert_raw_rejected((samples, log, raw, {}), "candidate identity")


def test_raw_metadata_comparison_rejects_bool_int_aliases_and_nonfinite_values(root):
    for case in ("marker-bool", "marker-float", "dimension-bool", "process-bool", "count-bool", "nan", "infinity"):
        samples, log, raw, identity = raw_soak_fixture()
        if case == "marker-bool": samples["route_start_marker"]["pan"] = False
        elif case == "marker-float": samples["ready_marker"]["redraw_seq"] = 4.0
        elif case == "dimension-bool": samples["frame_samples"][1]["Width"] = True
        elif case == "process-bool": samples["process_samples"][1]["HasExited"] = 0
        elif case == "count-bool": samples["heartbeat_count"] = True
        else: samples["untrusted_nested_metrics"] = {"value": float("nan") if case == "nan" else float("inf")}
        result = audit_raw_fixture((samples, log, raw, identity))
        assert not result["raw_validation_passed"] and not result["passed"], (case, result)


def test_raw_markers_require_anchoring_unique_inventory_and_probe_order(root):
    for case in ("missing-log", "duplicate-end", "malformed", "unanchored-start", "missing-heartbeat", "ready-before-start", "short-end"):
        samples, log, raw, identity = raw_soak_fixture()
        lines = log.splitlines()
        if case == "missing-log": log = ""
        elif case == "duplicate-end": log += "\n" + lines[-2]
        elif case == "malformed": log += "\nSOAK_ROUTE_END route_ticks=not-a-number"
        elif case == "unanchored-start": log = log.replace("SOAK_ROUTE_START", "0:000> SOAK_ROUTE_START", 1)
        elif case == "missing-heartbeat": log = "\n".join(line for line in lines if not line.startswith("SOAK_HEARTBEAT"))
        elif case == "ready-before-start": log = "\n".join([lines[1], lines[0], *lines[2:]])
        else:
            log = log.replace("tickdelta=7680", "tickdelta=7679")
            samples["route_end_marker"]["tick_delta"] = 7679
        result = audit_raw_fixture((samples, log, raw, identity))
        assert not result["raw_validation_passed"], (case, result)


def test_raw_policy_duration_and_measured_sample_coverage_cannot_be_shortened(root):
    parts = raw_soak_fixture()
    assert not evidence.audit_hidden_soak_raw(*parts)["raw_validation_passed"]  # default is two hours
    for case in ("short-duration", "short-span", "large-gap", "duplicate-time", "no-timezone", "missing-time", "bool-interval", "oversized-interval"):
        samples, log, raw, identity = raw_soak_fixture()
        if case == "short-duration": samples["duration_sec"] = 119
        elif case in ("short-span", "large-gap"):
            begin = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
            for index, row in enumerate(samples["frame_samples"]):
                row["Timestamp"] = (begin + timedelta(seconds=index * (1 if case == "short-span" else 120))).isoformat()
        elif case == "duplicate-time": samples["frame_samples"][1]["Timestamp"] = samples["frame_samples"][0]["Timestamp"]
        elif case == "no-timezone": samples["process_samples"][1]["Timestamp"] = "2026-10-01T12:01:00"
        elif case == "missing-time": samples["process_samples"][1].pop("Timestamp")
        else: samples["frame_interval_sec"] = True if case == "bool-interval" else 120
        result = audit_raw_fixture((samples, log, raw, identity))
        assert not result["raw_validation_passed"], (case, result)


def test_raw_process_measurements_and_fixed_growth_limits_ignore_green_summaries(root):
    for case in ("missing-metric", "bool-metric", "negative-metric", "exited", "exit-code", "error", "missing-row",
                 "working-growth", "private-growth", "handle-growth"):
        samples, log, raw, identity = raw_soak_fixture()
        row = samples["process_samples"][1]
        samples.update(passed=True, process_growth_passed=True, max_working_set_growth_mb=999999,
                       max_private_memory_growth_mb=999999, max_handle_growth=999999)
        if case == "missing-metric": row.pop("WorkingSet64")
        elif case == "bool-metric": row["HandleCount"] = True
        elif case == "negative-metric": row["PrivateMemorySize64"] = -1
        elif case == "exited": row["HasExited"] = True
        elif case == "exit-code": row["ExitCode"] = 0
        elif case == "error": row["Error"] = "process query failed"
        elif case == "missing-row": samples["process_samples"] = samples["process_samples"][:1]
        elif case == "working-growth": row["WorkingSet64"] += 64 * 1024 * 1024 + 1
        elif case == "private-growth": row["PrivateMemorySize64"] += 64 * 1024 * 1024 + 1
        else: row["HandleCount"] += 129
        assert_raw_rejected((samples, log, raw, identity), "process")


def test_raw_hidden_evidence_never_accepts_manual_input_claims(root):
    for field, value in (("input_responsiveness", "passed"), ("input_max_abs_error", 0),
                         ("input_max_sample_abs_error", False), ("route_results", {"native_click": True})):
        samples, log, raw, identity = raw_soak_fixture("map-pan")
        samples[field] = value
        assert_raw_rejected((samples, log, raw, identity), "input")


def test_raw_forced_pan_replays_bounds_phase_order_and_frame_progression(root):
    for case in ("unsafe", "wrong-phase", "wrong-inward-delta", "out-of-order", "heartbeat-position", "cross-stream-order", "no-progression"):
        samples, log, raw, identity = raw_soak_fixture("map-pan")
        if case == "unsafe": log += "\nSOAK_PAN_UNSAFE base=(4,4) max=(10,10) reason=no_inward_direction"
        elif case == "wrong-phase":
            log = log.replace("SOAK_PAN_SET phase=1", "SOAK_PAN_SET phase=0")
            samples["pan_events"][1]["phase"] = 0
        elif case == "wrong-inward-delta":
            log = log.replace("delta=(1,1)", "delta=(-1,-1)")
            for row in samples["pan_events"]: row.update(delta_x=-1, delta_y=-1)
        elif case == "out-of-order":
            log = log.replace("hits=2 tickdelta=2560", "hits=1 tickdelta=1280")
            samples["pan_events"][1].update(hits=1, tick_delta=1280)
        elif case == "heartbeat-position": log = log.replace("player=0 scroll=(5,4)", "player=0 scroll=(4,4)")
        elif case == "cross-stream-order":
            log = log.replace("SOAK_HEARTBEAT hits=2048 tickdelta=3840", "SOAK_HEARTBEAT hits=4096 tickdelta=5000")
        else:
            data = raw["frame-0001"]
            for name in raw: raw[name] = data
            for row in samples["frame_samples"]:
                row.update(Hash=evidence.digest(data), NonblackPercent=93.75, UniqueSampleColors=16)
        result = audit_raw_fixture((samples, log, raw, identity))
        assert not result["raw_validation_passed"], (case, result)


def test_raw_runtime_failure_markers_override_claimed_green_report_flags(root):
    for marker in ("AV_SURFDUMP", "SURFDUMP_INVALID", "SURFDUMP_APP_REQUEST_QUIT text_ptr=00100000 caption_ptr=00110000"):
        samples, log, raw, identity = raw_soak_fixture()
        samples.update(passed=True, no_crash=True, render_integrity=True, clean_stop=True)
        assert_raw_rejected((samples, log + "\n" + marker, raw, identity), "runtime failure")


def test_raw_malformed_containers_fail_without_a_completed_adapter(root):
    for index, value in ((0, None), (1, None), (2, []), (3, [])):
        parts = list(raw_soak_fixture())
        parts[index] = value
        result = audit_raw_fixture(parts)
        assert not result["raw_validation_passed"] and not result["passed"], result
    for field, value in (("frame_samples", {}), ("process_samples", [True]), ("frame_samples", [None])):
        samples, log, raw, identity = raw_soak_fixture()
        samples[field] = value
        result = audit_raw_fixture((samples, log, raw, identity))
        assert not result["raw_validation_passed"], result
    for minimum in (0, True, "120"):
        result = evidence.audit_hidden_soak_raw(*raw_soak_fixture(), minimum_duration_sec=minimum)
        assert not result["raw_validation_passed"] and not result["release_evidence_verified"], result


def test_raw_bounded_tokens_and_metadata_fail_without_conversion_errors(root):
    for case in ("surface-backticks", "base-backticks", "game-data-backticks", "long-decimal", "long-hex",
                 "out-of-range-address", "long-resolution", "oversized-resolution", "huge-duration", "huge-interval", "huge-telemetry"):
        samples, log, raw, identity = raw_soak_fixture()
        if case == "surface-backticks": log = log.replace("surface=00100000", "surface=``")
        elif case == "base-backticks": log = log.replace("base=00110000", "base=`")
        elif case == "game-data-backticks": log = log.replace("gd=00200000", "gd=``")
        elif case == "long-decimal": log = log.replace("route_ticks=7680", "route_ticks=" + "9" * 5000)
        elif case == "long-hex": log = log.replace("gd=00200000", "gd=" + "f" * 2048)
        elif case == "out-of-range-address":
            log = log.replace("gd=00200000", "gd=ffffffffffffffff")
            samples["route_start_marker"]["game_data"] = "ffffffffffffffff"
        elif case == "long-resolution": identity["resolution"] = "9" * 5000 + "x4"
        elif case == "oversized-resolution": identity["resolution"] = "99999x99999"
        elif case == "huge-duration": samples["duration_sec"] = 2 ** 2048
        elif case == "huge-interval": samples["frame_interval_sec"] = 2 ** 2048
        else: samples["process_samples"][1]["PrivateMemorySize64"] = 2 ** 2048
        result = audit_raw_fixture((samples, log, raw, identity))
        assert not result["raw_validation_passed"] and not result["passed"], (case, result)
    result = evidence.audit_hidden_soak_raw(*raw_soak_fixture(), minimum_duration_sec=2 ** 2048)
    assert not result["raw_validation_passed"], result
    # CDB can pad x86 pointers or print the normal 8+8 backtick notation.
    samples, log, raw, identity = raw_soak_fixture()
    log = log.replace("00100000", "0000000000100000").replace("00110000", "00000000`00110000").replace("00200000", "00000000`00200000")
    samples["ready_marker"].update(surface="0000000000100000", base="00000000`00110000")
    samples["surface"]["Base"] = "00000000`00110000"
    samples["route_start_marker"]["game_data"] = "00000000`00200000"
    result = audit_raw_fixture((samples, log, raw, identity))
    assert result["raw_validation_passed"] and not result["release_evidence_verified"], result


def test_raw_deep_metadata_is_rejected_without_recursion_error(root):
    samples, log, raw, identity = raw_soak_fixture()
    deep = []
    for _ in range(10000):
        deep = [deep]
    samples["untrusted_nested_metadata"] = deep
    result = audit_raw_fixture((samples, log, raw, identity))
    assert not result["raw_validation_passed"] and not result["passed"], result
    assert any("finite JSON" in failure for failure in result["raw_failures"]), result


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    with tempfile.TemporaryDirectory(prefix="complete-hd-evidence-fixtures-") as directory:
        for index, test in enumerate(tests):
            test(Path(directory) / str(index))
    print(f"complete_hd_evidence: PASS ({len(tests)} offline test groups)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
