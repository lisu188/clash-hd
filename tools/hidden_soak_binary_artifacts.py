"""Retained hidden-soak binary/build byte consistency, never loaded-image proof.

Only the fixed reader boundary performs I/O. The original executable is checked
by the harness pre/postflight, not reopened here: its report SHA is a label,
not original-file authentication. Candidate validation reconstructs selected
patch observations from the actual retained candidate bytes; it does not prove
that every unselected byte came from the retail executable or that it ran.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
from pathlib import Path, PureWindowsPath
from typing import Any

from hidden_soak_artifact_layout import _windows_path, validate_hidden_artifact_layout
from hidden_soak_probe_composition import ProbeCompositionError, compose_probe, composer_sha256
from hidden_soak_retained_files import read_retained_file as _read_retained_file
from patch_stage_report import build_report as _build_patch_report


PROTECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)
EXPECTED_BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_PINS = {
    "source": (_ROOT / "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp", "source_sha256"),
    "def_file": (_ROOT / "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.def", "def_sha256"),
    "build_script": (_ROOT / "scripts/build/build_ddraw_surfdump_proxy.ps1", "build_script_sha256"),
}
_PROBE_PINS = {
    "probe_template": _ROOT / "probes/cdb/render/clash95_surface_dump_probe.cdb",
    "soak_probe_template": _ROOT / "probes/cdb/soak/clash95_hidden_soak_route_extra.cdb",
}
_MAX_BINARY = 32 * 1024 * 1024
_MAX_LOG = 32 * 1024 * 1024
_MAX_JSON = 2 * 1024 * 1024
_MAX_SOURCE = 2 * 1024 * 1024
_COMPOSITION_PARAMETERS = ("route", "duration_sec", "pan_interval_sec", "load_slot", "raw_path")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_LOAD_ROW = re.compile(r"^ddraw_surfdump_proxy loaded present_enabled=([01])$")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _same_windows_path(value: Any, expected: str | PureWindowsPath) -> bool:
    errors: list[str] = []
    parsed = _windows_path(value, "artifact path", errors)
    return parsed is not None and parsed == PureWindowsPath(expected)


def _source_path_matches(value: Any, expected: Path) -> bool:
    # The producer pins these exact independently authored files. POSIX source
    # fixtures retain their actual native checkout paths, not invented C: paths.
    return _same_windows_path(value, str(expected)) if os.name == "nt" else type(value) is str and value == str(expected)


def _read(role: str, path: Any, maximum: int, artifacts: dict[str, Any], failures: list[str],
          *, expected_sha: Any = None, expected_size: Any = None, require_receipt: bool = False) -> bytes | None:
    if type(path) is not str or not path:
        failures.append(f"{role}: retained path is missing or invalid")
        return None
    try:
        data = _read_retained_file(path, maximum)
        if type(data) is not bytes or len(data) > maximum:
            raise ValueError("retained reader returned invalid or oversized bytes")
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        failures.append(f"{role}: retained read failed: {type(exc).__name__}: {exc}")
        return None
    actual_sha = _digest(data)
    artifacts[role] = {"path": path, "sha256": actual_sha, "size": len(data)}
    if require_receipt or expected_sha is not None:
        if type(expected_sha) is not str or not _SHA256.fullmatch(expected_sha):
            failures.append(f"{role}: collection SHA-256 receipt is missing or invalid")
        elif expected_sha.casefold() != actual_sha:
            failures.append(f"{role}: actual retained SHA-256 differs from its collection receipt")
    if require_receipt or expected_size is not None:
        if type(expected_size) is not int or expected_size < 0:
            failures.append(f"{role}: collection size receipt is missing or invalid")
        elif expected_size != len(data):
            failures.append(f"{role}: actual retained size differs from its collection receipt")
    return data


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_object(data: bytes | None, role: str, failures: list[str]) -> dict[str, Any] | None:
    if data is None:
        return None
    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=_unique_object,
                           parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {token}")))
        if not isinstance(value, dict):
            raise ValueError("JSON artifact is not an object")
        return value
    except (ValueError, TypeError, RecursionError, OverflowError) as exc:
        failures.append(f"{role}: invalid retained JSON: {type(exc).__name__}: {exc}")
        return None


def _patch_path(payload: dict[str, Any], failures: list[str]) -> str | None:
    errors: list[str] = []
    output = _windows_path(payload.get("output_directory"), "output_directory", errors)
    if output is None:
        failures.extend(errors)
        return None
    expected = output / "patch-stage.json"
    if not _same_windows_path(payload.get("patch_stage_report"), expected):
        failures.append("patch_stage_report must be the canonical output_directory/patch-stage.json")
        return None
    return payload["patch_stage_report"]


def _read_patch(payload: dict[str, Any], artifacts: dict[str, Any], failures: list[str]) -> dict[str, Any] | None:
    path = _patch_path(payload, failures)
    if path is None:
        return None
    data = _read("patch_stage_report", path, _MAX_JSON, artifacts, failures,
                 expected_sha=payload.get("patch_stage_report_sha256"),
                 expected_size=payload.get("patch_stage_report_size"), require_receipt=True)
    return _json_object(data, "patch_stage_report", failures)


def read_retained_patch(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Load the canonical receipt-bound patch JSON through the fixed reader."""
    if not isinstance(payload, dict):
        return None, "retained patch payload must be an object"
    if payload.get("environment") != "hidden_cdb_host":
        return None, "retained patch requires environment=hidden_cdb_host"
    failures: list[str] = []
    _, layout_errors = validate_hidden_artifact_layout(payload)
    if layout_errors:
        return None, "; ".join(layout_errors)
    patch = _read_patch(payload, {}, failures)
    return (None, "; ".join(failures)) if failures else (patch, None)


class _RetainedCandidate:
    def __init__(self, path: str, data: bytes) -> None:
        self._path, self._data = path, data

    def read_bytes(self) -> bytes:
        return self._data

    def __str__(self) -> str:
        return self._path


def _strict_json_equal(actual: Any, reported: Any) -> bool:
    try:
        return json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(reported, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError, OverflowError):
        return False


def _validate_candidate(payload: dict[str, Any], data: bytes | None, retained: dict[str, Any] | None,
                        summary: dict[str, Any], failures: list[str]) -> None:
    if data is None or retained is None:
        return
    try:
        actual = _build_patch_report(_RetainedCandidate(payload["candidate"], data), PROTECTED_STAGE, "800x600")
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, struct.error, SystemExit) as exc:
        failures.append(f"candidate: actual protected-stage byte regrade failed: {type(exc).__name__}: {exc}")
        return
    summary["candidate_patch_report"] = {
        "stage": actual.get("stage"), "resolution": actual.get("resolution"),
        "exe_sha256": actual.get("exe_sha256"), "patch_count": actual.get("patch_count"),
        "status_counts": actual.get("status_counts"), "current_hd_map_gate": actual.get("current_hd_map_gate"),
    }
    if not _same_windows_path(retained.get("exe"), payload["candidate"]):
        failures.append("patch_stage_report.exe does not bind the actual retained candidate path")
    for field in ("stage", "resolution", "exe_sha256", "expected_base_sha256", "image_base_hex", "sections",
                  "patch_count", "status_counts", "groups", "map", "patches", "current_hd_map_gate"):
        if not _strict_json_equal(actual.get(field), retained.get(field)):
            failures.append(f"patch_stage_report.{field} differs from the actual candidate byte regrade")
    if actual.get("patch_count", 0) <= 0 or actual.get("status_counts") != {"patched": actual.get("patch_count")}:
        failures.append("candidate: not every selected protected-stage patch is present in the actual bytes")
    if (actual.get("current_hd_map_gate") or {}).get("passed") is not True:
        failures.append("candidate: actual 800x600 current_hd_map_gate is not passing")


def _validate_proxy_pe(data: bytes, failures: list[str]) -> None:
    try:
        if len(data) < 64 or data[:2] != b"MZ":
            raise ValueError("missing DOS header")
        offset = struct.unpack_from("<I", data, 0x3C)[0]
        if offset < 64 or offset + 24 > len(data) or data[offset:offset + 4] != b"PE\0\0":
            raise ValueError("missing or truncated PE header")
        machine, sections = struct.unpack_from("<HH", data, offset + 4)
        optional_size, characteristics = struct.unpack_from("<HH", data, offset + 20)
        if machine != 0x014C or not characteristics & 0x2000:
            raise ValueError("proxy is not an x86 PE DLL")
        if optional_size < 96 or offset + 24 + optional_size + sections * 40 > len(data) or not 0 < sections <= 96:
            raise ValueError("truncated or invalid PE optional/section headers")
        if struct.unpack_from("<H", data, offset + 24)[0] != 0x10B:
            raise ValueError("proxy optional header is not PE32")
    except (ValueError, struct.error) as exc:
        failures.append(f"proxy: {exc}")


def _validate_proxy(payload: dict[str, Any], artifacts: dict[str, Any], summary: dict[str, Any], failures: list[str]) -> None:
    proxy = payload["proxy"]
    if proxy.get("used") is not True:
        failures.append("proxy.used must be true for the retained hidden proxy")
    if not (proxy.get("present_enabled") is False or type(proxy.get("present_enabled")) is int and proxy["present_enabled"] == 0):
        failures.append("proxy.present_enabled must be false or integer zero")
    data = _read("proxy", proxy["path"], _MAX_BINARY, artifacts, failures, expected_sha=proxy.get("sha256"))
    if type(proxy.get("sha256")) is not str or not _SHA256.fullmatch(proxy["sha256"]):
        failures.append("proxy: declared binary SHA-256 is missing or invalid")
    if data is not None:
        _validate_proxy_pe(data, failures)
    records: dict[str, bytes | None] = {}
    for role in ("build_manifest", "log", "build_log"):
        records[role] = _read(f"proxy.{role}", proxy[role], _MAX_JSON if role == "build_manifest" else _MAX_LOG,
                              artifacts, failures, expected_sha=proxy.get(f"{role}_sha256"),
                              expected_size=proxy.get(f"{role}_size"), require_receipt=True)
        if records[role] == b"":
            failures.append(f"proxy.{role}: retained artifact is empty")
    manifest = _json_object(records["build_manifest"], "proxy.build_manifest", failures)
    if manifest is not None:
        if manifest.get("generated_by") != "clash-hd-surface-dump-proxy":
            failures.append("proxy.build_manifest.generated_by is not the fixed proxy builder")
        if not _same_windows_path(manifest.get("output"), proxy["path"]):
            failures.append("proxy.build_manifest.output does not bind the candidate-local DLL")
        if data is not None and (type(manifest.get("output_sha256")) is not str or manifest["output_sha256"].casefold() != _digest(data)):
            failures.append("proxy.build_manifest.output_sha256 differs from the actual proxy DLL")
        if not _same_windows_path(manifest.get("build_log"), proxy["build_log"]):
            failures.append("proxy.build_manifest.build_log does not bind the retained build log")
        for field, (expected, sha_field) in _SOURCE_PINS.items():
            if not _source_path_matches(manifest.get(field), expected):
                failures.append(f"proxy.build_manifest.{field} is not the fixed repository producer input")
                continue
            _read(f"proxy.{field}", str(expected), _MAX_SOURCE, artifacts, failures, expected_sha=manifest.get(sha_field),
                  require_receipt=False)
            if type(manifest.get(sha_field)) is not str or not _SHA256.fullmatch(manifest[sha_field]):
                failures.append(f"proxy.build_manifest.{sha_field} is missing or invalid")
    if records["log"] is not None:
        try:
            # Only real LF/CRLF record boundaries count; Unicode separators
            # and vertical whitespace embedded in prose cannot create rows.
            lines = [line.removesuffix("\r") for line in records["log"].decode("utf-8-sig").split("\n")]
            rows = [(index + 1, match.group(1)) for index, line in enumerate(lines) if (match := _LOAD_ROW.fullmatch(line))]
            summary["proxy_load_rows"] = [{"line_number": line, "present_enabled": int(enabled)} for line, enabled in rows]
            if len(rows) != 1 or rows[0][1] != "0":
                failures.append("proxy.log must retain exactly one anchored loaded present_enabled=0 row")
            if any(line.startswith("ddraw_surfdump_proxy loaded") and not _LOAD_ROW.fullmatch(line) for line in lines):
                failures.append("proxy.log retains a malformed proxy-loaded observation")
            if any(line.startswith("PROXY_PRESENT_WINDOW") for line in lines):
                failures.append("proxy.log retains a contradictory PROXY_PRESENT_WINDOW observation")
        except UnicodeError as exc:
            failures.append(f"proxy.log: invalid retained text: {type(exc).__name__}: {exc}")


def _validate_probes(payload: dict[str, Any], artifacts: dict[str, Any], summary: dict[str, Any], failures: list[str]) -> None:
    # Pins authenticate the bytes currently retained at these fixed source
    # paths; the rebuild below authenticates canonical construction from them.
    summary["canonical_probe_regeneration_authenticated"] = False
    slot = payload.get("load_slot")
    if type(slot) is not int or not 0 <= slot <= 9:
        failures.append("load_slot must be an integer in the normalized range 0..9")
    summary["load_slot"] = slot
    retained: dict[str, bytes | None] = {}
    for role in ("generated_probe", *_PROBE_PINS):
        path = payload.get(role)
        if role in _PROBE_PINS and not _source_path_matches(path, _PROBE_PINS[role]):
            failures.append(f"{role} is not the fixed repository probe template")
            continue
        data = _read(role, path, _MAX_SOURCE, artifacts, failures,
                     expected_sha=payload.get(f"{role}_sha256"),
                     expected_size=payload.get(f"{role}_size"), require_receipt=True)
        if data == b"":
            failures.append(f"{role}: retained artifact is empty")
        retained[role] = data
    _validate_probe_composition(payload, retained, summary, failures)


def _validate_probe_composition(payload: dict[str, Any], retained: dict[str, bytes | None],
                                summary: dict[str, Any], failures: list[str]) -> None:
    """Rebuild the generated probe from the retained templates and recorded parameters."""
    record = payload.get("probe_composition")
    parameters = record.get("parameters") if isinstance(record, dict) else None
    if (not isinstance(record, dict) or record.get("schema") != "hidden_soak_probe_composition_v1"
            or not isinstance(parameters, dict) or set(parameters) != set(_COMPOSITION_PARAMETERS)):
        failures.append("probe_composition must record the canonical composer parameters")
        return
    errors: list[str] = []
    for field in ("route", "duration_sec", "load_slot"):
        if type(parameters[field]) is not type(payload.get(field)) or parameters[field] != payload.get(field):
            errors.append(f"probe_composition {field} differs from the report")
    if payload.get("route") == "map-pan" and parameters["pan_interval_sec"] != payload.get("pan_interval_sec"):
        errors.append("probe_composition pan_interval_sec differs from the report")
    recorded = record.get("composer_sha256")
    summary["probe_composition"] = {
        "parameters": dict(parameters), "recorded_composer_sha256": recorded, "grader_composer_sha256": composer_sha256(),
        "same_composer_source": type(recorded) is str and recorded.casefold() == composer_sha256()}
    if all(type(retained.get(role)) is bytes and retained[role] for role in ("generated_probe", *_PROBE_PINS)):
        try:
            rebuilt = compose_probe(retained["probe_template"], retained["soak_probe_template"], **parameters)
        except ProbeCompositionError as exc:
            errors.append(f"probe_composition: {exc}")
        else:
            if rebuilt != retained["generated_probe"]:
                errors.append("generated_probe differs from the canonical composition of the retained templates")
    else:
        errors.append("probe_composition: the generated probe and both templates must be retained to rebuild it")
    failures.extend(errors)
    summary["canonical_probe_regeneration_authenticated"] = not errors


def validate_retained_binaries(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Verify canonical retained files and actual selected-patch observations."""
    summary: dict[str, Any] = {
        "scope": "hidden_retained_binary_and_build_byte_consistency_only",
        "original_file_authenticated": False, "loaded_image_authenticated": False,
        "native_execution_authenticated": False, "candidate_patch_only": True, "artifacts": {},
        "retained_bytes_consistent": False,
    }
    if not isinstance(payload, dict):
        return summary, ["retained binary payload must be an object"]
    failures: list[str] = []
    if payload.get("environment") != "hidden_cdb_host":
        failures.append("retained binaries require environment=hidden_cdb_host")
    if payload.get("stage") != PROTECTED_STAGE:
        failures.append("retained binaries require the protected stable stage")
    if type(payload.get("input_sha256")) is not str or payload["input_sha256"].casefold() != EXPECTED_BASE_SHA256:
        failures.append("input_sha256 label does not match the expected original; original file is not authenticated here")
    layout, layout_errors = validate_hidden_artifact_layout(payload)
    summary["layout"] = layout
    failures.extend(layout_errors)
    if layout_errors:
        return summary, failures
    artifacts = summary["artifacts"]
    candidate = _read("candidate", payload["candidate"], _MAX_BINARY, artifacts, failures,
                      expected_sha=payload.get("candidate_sha256"))
    if type(payload.get("candidate_sha256")) is not str or not _SHA256.fullmatch(payload["candidate_sha256"]):
        failures.append("candidate: declared SHA-256 is missing or invalid")
    patch = _read_patch(payload, artifacts, failures)
    _validate_candidate(payload, candidate, patch, summary, failures)
    _validate_proxy(payload, artifacts, summary, failures)
    _validate_probes(payload, artifacts, summary, failures)
    summary["retained_bytes_consistent"] = not failures
    return summary, failures
