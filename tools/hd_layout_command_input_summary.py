#!/usr/bin/env python3
"""Validate existing relocated command-panel input observations without runtime.

The manifest binds a raw log, exact rendered observation probe, and real user
approval record to one candidate/run. No template or diagnostic invocation is
proof. Callback observation alone never grants manual proof or promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "probes/cdb/ui/clash95_hd_layout_command_input_extra.cdb"
STABLE_STAGE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch"
SUPPORTED_STAGES = tuple(STABLE_STAGE + suffix for suffix in ("-hdlayout", "-hdlayout-framerestore", "-combinedui-validation"))
INPUT_METHODS = ("manual_directinput", "win32_sendinput_relative", "win32_mouse_event")
EXPECTED_DESCRIPTOR = 0x00511D40
EXPECTED_CALLBACK = 0x00409D80
EXPECTED_DISPATCH = 0x00419C5D
EXPECTED_RETURN = 0x00419C60
MARKER_PREFIX = "HDLAYOUT_INPUT_"
SEQUENCE = ("DESCRIPTOR", "HIT_X", "HIT_Y", "GATE_BEFORE", "GATE_OBSERVED", "DISPATCH", "CALLBACK")
EVENT_FIELDS = {
    "DESCRIPTOR": "tid desc x y state state3 callback mouse_x mouse_y selected_unit width height cursor_meta cursor_sprite cursor_x cursor_y",
    "HIT_X": "tid desc cursor lower upper_exclusive",
    "HIT_Y": "tid desc cursor lower upper_exclusive",
    "GATE_BEFORE": "tid desc callback mouse_x mouse_y click_flag button0",
    "GATE_OBSERVED": "tid desc eax callback mouse_x mouse_y",
    "DISPATCH": "tid desc argument eip callback mouse_x mouse_y",
    "CALLBACK": "tid desc eip ret mouse_x mouse_y selected_unit",
}
HEX_FIELDS = {"tid", "desc", "state", "state3", "callback", "click_flag", "button0", "argument", "eip", "ret", "cursor_meta"}
APPROVAL_BINDINGS = ("run_id", "candidate_path", "candidate_sha256", "stage", "resolution", "environment", "input_method", "wrapper", "input_plan", "execution_plan_sha256")
INPUT_PLAN = {"method": "manual_directinput", "steps": [
    "User loads a map and selects a unit, then holds the normal selected-unit cursor over empty traversable central terrain until selected-map captures finish (native descriptor state 2).",
    "User hovers the first relocated command icon at logical (640,544), without changing selection, until hover captures finish (native descriptor state 6).",
    "User clicks that icon once; the observer records the native input gate and callback."],
    "inject_input": False, "force_route_or_callback": False}
SESSION_PRODUCER = REPO_ROOT / "tools/hd_layout_observation_manifest.py"
MAX_APPROVAL_AGE = timedelta(hours=12)
RUNTIME_POLICY = "repo-only existing evidence parsing; no game, debugger, input, window, or capture execution"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def native_selected_descriptor_state(value: Any) -> bool:
    """Selected-unit sprite state, optionally with the native hover overlay.

    sub_40A360 writes 1 when no unit is selected, 2 when selected. Bit 4
    controls the hover overlay. sub_419B80 calls the callback BEFORE testing
    bits 1/2 for visual feedback; bit 1 is not an input-enable requirement.
    """
    return type(value) is int and value in (2, 6)


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO string with a timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def reference(base: Path, data: dict[str, Any], *, path_key: str = "path", hash_key: str = "sha256") -> tuple[Path, bytes]:
    if not isinstance(data, dict) or not isinstance(data.get(path_key), str) or not data[path_key]:
        raise ValueError(f"missing reference field {path_key}")
    path = Path(data[path_key])
    path = (path if path.is_absolute() else base.parent / path).resolve()
    content = path.read_bytes()
    if not is_sha256(data.get(hash_key)) or sha256(content) != data[hash_key].lower():
        raise ValueError(f"SHA-256 mismatch for {path}")
    return path, content


def render_probe(identity: dict[str, Any]) -> str:
    """Render the observation-only template; writing/running it is a harness duty."""
    text = PROBE.read_text(encoding="utf-8")
    for name in ("run_id", "candidate_sha256", "stage", "environment", "input_method"):
        value = identity.get(name)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
            raise ValueError(f"unsafe or missing probe identity {name}")
        text = text.replace(f"__HDLAYOUT_{name.upper()}__", value)
    return text


def validate_identity(identity: dict[str, Any]) -> list[str]:
    failures = []
    if not isinstance(identity.get("run_id"), str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", identity["run_id"]):
        failures.append("run_id is missing or malformed")
    if not is_sha256(identity.get("candidate_sha256")):
        failures.append("candidate SHA-256 is missing or malformed")
    candidate = identity.get("candidate_path")
    if not isinstance(candidate, str) or not Path(candidate).is_absolute():
        failures.append("candidate_path must identify an absolute isolated candidate")
    else:
        path = Path(candidate).resolve()
        if path == Path(r"C:\Clash\clash95.exe").resolve() or path.is_relative_to(REPO_ROOT):
            failures.append("candidate_path identifies the original executable or repository")
    if identity.get("stage") not in SUPPORTED_STAGES or identity.get("resolution") != [800, 600]:
        failures.append("candidate is not a supported 800x600 validation layout")
    if identity.get("environment") != "host_visible" or identity.get("input_method") not in INPUT_METHODS:
        failures.append("input observation needs a declared visible-host input method")
    if identity.get("input_method") != "manual_directinput" or identity.get("input_plan") != INPUT_PLAN:
        failures.append("input plan differs from the supported manual observation session")
    if not isinstance(identity.get("wrapper"), dict) or not is_sha256(identity.get("execution_plan_sha256")):
        failures.append("wrapper and exact execution-plan binding are required")
    hwnd = identity.get("hwnd")
    if not isinstance(hwnd, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", hwnd) or int(hwnd, 16) == 0:
        failures.append("target HWND is missing or invalid")
    try:
        started, finished = timestamp(identity.get("started_at")), timestamp(identity.get("finished_at"))
        if finished <= started:
            failures.append("run finish must follow start")
    except ValueError as exc:
        failures.append(str(exc))
    return failures


def parse_events(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    rows, identities, failures = [], [], []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line.startswith(MARKER_PREFIX):
            continue  # Debugger command echoes and printf templates are not observations.
        marker, _, tail = line.partition(" ")
        kind = marker.removeprefix(MARKER_PREFIX)
        fields = {}
        try:
            for token in tail.split():
                key, separator, value = token.partition("=")
                if not separator or not value or key in fields:
                    raise ValueError("duplicate or malformed fields")
                fields[key] = value
            if kind == "IDENTITY":
                identities.append({"line": number, "values": fields})
                continue
            if kind not in EVENT_FIELDS or set(fields) != set(EVENT_FIELDS[kind].split()):
                raise ValueError("unknown marker or mismatched fields")
            values = {}
            for key, value in fields.items():
                if not re.fullmatch(r"(?:0x)?[0-9a-fA-F]+" if key in HEX_FIELDS else r"-?\d+", value):
                    raise ValueError(f"invalid {key}")
                values[key] = int(value, 16 if key in HEX_FIELDS else 10)
            rows.append({"line": number, "marker": kind, "values": values})
        except ValueError as exc:
            failures.append(f"malformed observation at line {number}: {exc}")
    return rows, identities, failures


def sequence_failures(rows: list[dict[str, Any]]) -> list[str]:
    values = [row["values"] for row in rows]
    descriptor, hit_x, hit_y, before, gate, dispatch, callback = values
    failures = []
    if any(row["desc"] != EXPECTED_DESCRIPTOR or row["tid"] != descriptor["tid"] or row["tid"] <= 0 for row in values):
        failures.append("sequence descriptor/thread differs")
    if (descriptor["x"], descriptor["y"], descriptor["width"], descriptor["height"]) != (608, 528, 800, 600):
        failures.append("descriptor is not at its relocated 800x600 anchor")
    if (not native_selected_descriptor_state(descriptor["state"]) or descriptor["state3"] not in (1, 2) or descriptor["selected_unit"] < 0
            or callback["selected_unit"] != descriptor["selected_unit"]):
        failures.append("descriptor state or selected-unit identity differs from the native selected command state")
    if any(row["callback"] != EXPECTED_CALLBACK for row in (descriptor, before, gate, dispatch)):
        failures.append("descriptor callback does not match native map-mode callback")
    mouse = (descriptor["mouse_x"], descriptor["mouse_y"])
    for row in (before, gate, dispatch, callback):
        if (row["mouse_x"], row["mouse_y"]) != mouse:
            failures.append("cursor changed during the native click sequence")
            break
    for hit, axis, lower, upper in ((hit_x, 0, 608, 671), (hit_y, 1, 528, 559)):
        if (hit["lower"], hit["upper_exclusive"]) != (lower, upper) or hit["cursor"] != mouse[axis] or not lower <= hit["cursor"] < upper:
            failures.append(f"native {'XY'[axis]} hitbox/cursor does not match relocated bounds")
    if before["click_flag"] & 1 == 0 or before["button0"] & 0x80 == 0 or gate["eax"] != 1:
        failures.append("native click gate did not observe a pressed input")
    if dispatch["argument"] != EXPECTED_DESCRIPTOR or dispatch["eip"] != EXPECTED_DISPATCH:
        failures.append("indirect callback dispatch does not match the native instruction")
    if callback["eip"] != EXPECTED_CALLBACK or callback["ret"] != EXPECTED_RETURN:
        failures.append("callback entry/return does not match native descriptor dispatch")
    return failures


def match_sequence(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]] | None, list[str]]:
    pending: dict[int, list[dict[str, Any]]] = {}
    rejections = []
    for row in rows:
        tid = row["values"]["tid"]
        if row["marker"] == SEQUENCE[0]:
            pending[tid] = [row]
            continue
        attempt = pending.get(tid)
        if not attempt or row["marker"] != SEQUENCE[len(attempt)]:
            pending.pop(tid, None)
            continue
        attempt.append(row)
        if len(attempt) == len(SEQUENCE):
            failures = sequence_failures(attempt)
            if not failures:
                return attempt, rejections
            rejections.extend(failures)
            pending.pop(tid)
    return None, rejections


def launch_environment_policy(wrapper_mode: str) -> dict:
    """Exact per-child policy; inherited host values are never published."""
    if wrapper_mode not in ("proxy-present", "gog"):
        raise ValueError("unsupported visible wrapper mode")
    overrides = {"__COMPAT_LAYER": "HIGHDPIAWARE"}
    if wrapper_mode == "proxy-present":
        overrides["CLASH_PROXY_PRESENT"] = "1"
    return {"inherit": "host environment except case-insensitive removals",
            "remove_names": ["__COMPAT_LAYER"], "remove_prefixes": ["CLASH_PROXY_"],
            "set": overrides, "scope": "owned CDB process and inherited candidate child only",
            "required_candidate_dpi_awareness": [1, 2], "required_window_dpi_awareness": [1, 2],
            "required_physical_client_size": [800, 600]}


def build_report(manifest_path: Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    report: dict[str, Any] = {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_policy": RUNTIME_POLICY, "passed": False, "status": "missing_evidence",
        "source_manifest": {"path": str(manifest_path), "sha256": None}, "identity": {},
        "raw_log": {}, "probe": {}, "approval": {}, "session_receipt": {}, "matched_sequence": None,
        "command_click_alignment": False, "panel_click_callback_proof": False,
        "native_click_gate_observed": False,
        "manual_directinput_proof": False, "promotion_ready": False,
        "proof_class": "observed_relocated_panel_native_callback",
        "limitations": ["Native callback observation is separate from manual-input release proof and visible composition."],
        "failures": [],
    }
    failures = report["failures"]
    try:
        content = manifest_path.read_bytes()
        report["source_manifest"]["sha256"] = sha256(content)
        manifest = read_object(manifest_path)
        if type(manifest.get("schema_version")) is not int or manifest.get("schema_version") != 1 or manifest.get("executed") is not True:
            failures.append("manifest must describe an executed version-1 observation run")
        identity = manifest.get("identity")
        if not isinstance(identity, dict):
            raise ValueError("manifest identity must be an object")
        report["identity"] = identity
        failures.extend(validate_identity(identity))
        raw_path, raw = reference(manifest_path, manifest.get("raw_log"))
        report["raw_log"] = {"path": str(raw_path), "sha256": sha256(raw)}
        probe = manifest.get("probe")
        template_path, template = reference(manifest_path, probe, path_key="template_path", hash_key="template_sha256")
        rendered_path, rendered = reference(manifest_path, probe, path_key="rendered_path", hash_key="rendered_sha256")
        report["probe"] = {"template_path": str(template_path), "template_sha256": sha256(template),
                           "rendered_path": str(rendered_path), "rendered_sha256": sha256(rendered)}
        if template_path != PROBE.resolve() or rendered.decode("utf-8-sig").replace("\r\n", "\n") != render_probe(identity).replace("\r\n", "\n"):
            failures.append("rendered probe differs from the exact observation-only template and run identity")
        approval_path, approval_bytes = reference(manifest_path, manifest.get("approval"))
        approval = read_object(approval_path)
        approval_failures = []
        if not isinstance(approval.get("identity"), dict):
            raise ValueError("approval identity must be an object")
        if approval.get("approved") is not True or approval.get("record_kind") != "user_approval" or not str(approval.get("approval_text") or "").strip():
            approval_failures.append("record is not explicit user approval")
        for key in APPROVAL_BINDINGS:
            if (approval.get("identity") or {}).get(key) != identity.get(key):
                approval_failures.append(f"approval does not bind run {key}")
        if set(approval["identity"]) != set(APPROVAL_BINDINGS):
            approval_failures.append("approval must bind the prelaunch identity without a predicted HWND")
        approved_at, expires_at = timestamp(approval.get("approved_at")), timestamp(approval.get("expires_at"))
        started_at, finished_at = timestamp(identity.get("started_at")), timestamp(identity.get("finished_at"))
        if not approved_at <= started_at < finished_at <= expires_at:
            approval_failures.append("run is outside the approval interval")
        if started_at - approved_at > MAX_APPROVAL_AGE or expires_at - approved_at > MAX_APPROVAL_AGE:
            approval_failures.append("approval interval exceeds the fresh 12-hour boundary")
        report["approval"] = {"path": str(approval_path), "sha256": sha256(approval_bytes), "passed": not approval_failures}
        failures.extend(approval_failures)
        receipt_path, receipt_bytes = reference(manifest_path, manifest.get("session_receipt"))
        receipt = read_object(receipt_path)
        report["session_receipt"] = {"path": str(receipt_path), "sha256": sha256(receipt_bytes)}
        producer_path, _ = reference(receipt_path, receipt.get("producer_source"))
        plan_path, plan_bytes = reference(receipt_path, receipt.get("plan"))
        plan = read_object(plan_path)
        if producer_path != SESSION_PRODUCER.resolve() or receipt.get("schema_version") != 1 or receipt.get("executed") is not True:
            failures.append("session receipt is not from the observation producer")
        if receipt.get("identity") != identity or receipt.get("approval") != manifest.get("approval"):
            failures.append("measured session identity/approval differs from manifest")
        if sha256(plan_bytes) != identity.get("execution_plan_sha256"):
            failures.append("measured session does not bind the approved execution plan")
        if plan.get("identity") != {key: identity[key] for key in APPROVAL_BINDINGS if key != "execution_plan_sha256"}:
            failures.append("execution plan differs from the approved candidate and input plan")
        expected_environment = launch_environment_policy(identity["wrapper"]["mode"])
        environment = receipt.get("launch_environment")
        if (plan.get("launch_environment") != expected_environment or not isinstance(environment, dict)
                or set(environment) != {"policy", "effective_environment_sha256"}
                or environment.get("policy") != expected_environment
                or not isinstance(environment.get("effective_environment_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", environment.get("effective_environment_sha256", ""))):
            failures.append("measured child environment does not bind the approved native-DPI launch policy")
        if (type(receipt.get("candidate_dpi_awareness")) is not int or receipt.get("candidate_dpi_awareness") not in (1, 2)
                or type(receipt.get("window_dpi_awareness")) is not int or receipt.get("window_dpi_awareness") not in (1, 2)
                or receipt.get("physical_client_size") != [800, 600]):
            failures.append("owned process/window did not establish DPI-aware native 800x600 capture")
        candidate_pid, cdb_pid = receipt.get("candidate_pid"), receipt.get("cdb_pid")
        if (type(candidate_pid) is not int or candidate_pid <= 0 or type(cdb_pid) is not int or cdb_pid <= 0
                or candidate_pid == cdb_pid or receipt.get("candidate_parent_pid") != cdb_pid
                or receipt.get("hwnd_pid") != candidate_pid or type(receipt.get("candidate_creation_filetime")) is not int
                or receipt.get("candidate_creation_filetime", 0) <= 0
                or receipt.get("process_image_path") != identity.get("candidate_path")
                or receipt.get("process_image_sha256") != identity.get("candidate_sha256")):
            failures.append("measured candidate/window ownership is invalid")
        if receipt.get("cleanup") != {"candidate_stopped": True, "cdb_stopped": True}:
            failures.append("owned session process cleanup was not verified")
        creation = receipt.get("candidate_creation_filetime")
        if type(creation) is int:
            created_at = datetime.fromtimestamp(creation / 10000000 - 11644473600, timezone.utc)
            if not started_at <= created_at <= finished_at:
                failures.append("candidate creation is outside the approved measured session")
        if receipt.get("failures") != []:
            failures.append("session producer reported incomplete or failed observations")
        startup_path, startup = reference(receipt_path, receipt.get("startup_probe"))
        if startup.decode("utf-8-sig").replace("\r\n", "\n") != render_probe(identity).replace("\r\n", "\n") + "\ng\n":
            failures.append("startup probe is not the exact observation template followed by go")
        cdb_path, _ = reference(plan_path, plan.get("cdb"))
        expected_command = [str(cdb_path), "-hd", "-logo", str(raw_path), "-cf", str(startup_path), identity["candidate_path"]]
        if receipt.get("launch_command") != expected_command:
            failures.append("actual launch command differs from the approved observation command")
        for key, expected_path in (("producer_source", SESSION_PRODUCER),
                                   ("wrapper_script", REPO_ROOT / "scripts/smoke/run_hd_layout_input_probe.ps1"),
                                   ("observation_template", PROBE), ("summary_source", Path(__file__))):
            path, _ = reference(plan_path, plan.get(key))
            if path != expected_path.resolve():
                failures.append(f"execution plan {key} is not the canonical source")
        for ref in (identity["wrapper"], identity["wrapper"].get("config")):
            reference(manifest_path, ref)
        text = raw.decode("utf-8-sig")
        if re.search(r"(?:_FORCE(?:D)?(?:\b|_)|_SYNTHETIC|HDLAYOUT_PANEL_REDRAW_INVOKE)", text, re.IGNORECASE):
            failures.append("raw log contains forced or synthetic diagnostic observations")
        if re.search(r"(?:^|[;{}>])\s*(?:r\s+e(?:ax|bx|cx|dx|ip|sp|bp|si|di)\s*=|e[bwdq]\s+(?:0x)?(?:00544(?:cfc|d00|d04)|005451c0|00511d(?:40|60))\b|\.call\b)", text, re.IGNORECASE | re.MULTILINE):
            failures.append("raw debugger commands mutate target input, registers, or callbacks")
        if re.search(r"access violation|c0000005|Unable to (?:insert|remove) breakpoint|Syntax error|Memory access error", text, re.IGNORECASE):
            failures.append("raw log contains debugger/runtime errors")
        rows, identities, malformed = parse_events(text)
        failures.extend(malformed)
        expected_header = {key: str(identity.get(key)) for key in ("run_id", "candidate_sha256", "stage", "environment", "input_method")}
        expected_header.update(schema_version="1", width="800", height="600")
        if len(identities) != 1 or identities[0]["values"] != expected_header:
            failures.append("raw log identity does not match exactly one manifest-bound run")
        elif rows and identities[0]["line"] >= rows[0]["line"]:
            failures.append("run identity must precede input observations")
        click_start_line = receipt.get("click_observation_start_line")
        if type(click_start_line) is not int or click_start_line < 1:
            failures.append("session lacks the measured post-capture click observation boundary")
            click_start_line = 0
        matched, rejected = match_sequence([row for row in rows if row["line"] > click_start_line])
        report.update(observation_count=len(rows), rejected_sequence_reasons=rejected, matched_sequence=matched)
        if failures:
            report["status"] = "invalid_evidence"
        elif matched is None:
            report["status"] = "incomplete_evidence"
            failures.append("no ordered relocated descriptor/hitbox/native-gate/matching-callback sequence")
        else:
            report.update(passed=True, status="observed", command_click_alignment=True,
                          panel_click_callback_proof=True, native_click_gate_observed=True)
    except FileNotFoundError as exc:
        failures.append(f"missing evidence: {exc.filename}")
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        report["status"] = "invalid_evidence"
        failures.append(f"invalid evidence: {exc}")
    return report


def to_markdown(report: dict[str, Any]) -> str:
    lines = ["# HD Layout Command Input Observation", "", f"- Status: {report['status']}",
             f"- Passing: {report['passed']}", f"- Policy: {report['runtime_policy']}",
             "- Manual DirectInput proof: False", "- Promotion ready: False", ""]
    lines.extend(f"- {key}: {value}" for key, value in report["identity"].items())
    if report["failures"]:
        lines.extend(["", "## Failures", ""] + [f"- {failure}" for failure in report["failures"]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    report = build_report(args.manifest)
    for path, content in ((args.write_json, json.dumps(report, indent=2) + "\n"),
                          (args.write_markdown, to_markdown(report))):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(f"hd-layout-command-input: {report['status']}")
    return 2 if args.require_pass and not report["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
