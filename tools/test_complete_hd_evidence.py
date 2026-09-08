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

    # The real launcher has no complete-HD profile yet; that remains an honest
    # missing requirement even though the existing Classic/Framed schema is valid.
    result = evaluate(manifest)
    assert not result["passed"] and any("advertised_resolution_matches" in row for row in result["failures"]), result
    unsupported = copy.deepcopy(manifest)
    unsupported["profiles"]["complete"] = {
        "default": "800x600", "stage": evidence.STAGE, "recipe_revision": evidence.RECIPE_REVISION,
        "features": {"minimap_viewport": True},
        "resolutions": {"800x600": {"status": "experimental"}, "1920x1080": {"status": "experimental"}},
    }
    result = evaluate(unsupported)
    assert not result["passed"] and any("separate Classic and Framed profiles" in row for row in result["failures"]), result
    for mutation in ("malformed-profile", "projection", "recipe", "features"):
        invalid = copy.deepcopy(manifest)
        if mutation == "malformed-profile": invalid["profiles"]["framed"] = []
        elif mutation == "projection": invalid["resolutions"]["800x600"]["status"] = "experimental"
        elif mutation == "recipe": invalid["profiles"]["framed"]["recipe_revision"] = "unsupported-recipe"
        else: invalid["profiles"]["framed"]["features"]["minimap_viewport"] = 1
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


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    with tempfile.TemporaryDirectory(prefix="complete-hd-evidence-fixtures-") as directory:
        for index, test in enumerate(tests):
            test(Path(directory) / str(index))
    print(f"complete_hd_evidence: PASS ({len(tests)} offline test groups)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
