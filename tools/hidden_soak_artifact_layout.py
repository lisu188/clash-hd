"""Hidden-soak Windows artifact layout checks, without filesystem access.

This gate binds declared paths to one canonical hidden run. It authenticates no
physical file, retained bytes, loaded image, or process. Patch-report paths are
deliberately outside this bounded lexical check; their existing JSON byte
binding and future physical-artifact authentication remain separate checks.
"""

from __future__ import annotations

import re
from pathlib import PureWindowsPath
from typing import Any


HIDDEN_CANDIDATE_ROOT = PureWindowsPath(r"C:\ClashTests\hd-soak\hidden")
HIDDEN_OUTPUT_ROOT = PureWindowsPath(r"C:\ClashCaptures\hd-soak\hidden")
EXPECTED_INPUT = PureWindowsPath(r"C:\Clash\clash95.exe")
EXPECTED_WORKDIR = PureWindowsPath(r"C:\Clash")
_DEVICE_NAME = re.compile(
    r"^(?:con|prn|aux|nul|clock\$|conin\$|conout\$|com[0-9\u00b9\u00b2\u00b3]|lpt[0-9\u00b9\u00b2\u00b3])$",
    re.IGNORECASE,
)


def _windows_path(value: Any, field: str, failures: list[str]) -> PureWindowsPath | None:
    if type(value) is not str or not value or value != value.strip():
        failures.append(f"{field} must be a nonempty absolute Windows path without surrounding whitespace")
        return None
    text = value.replace("/", "\\")
    if not re.match(r"^[A-Za-z]:\\", text):
        failures.append(f"{field} must use an absolute drive path, not a relative, UNC, or device path")
        return None
    if field not in {"workdir", "output_directory"} and text.endswith("\\"):
        failures.append(f"{field} must name a file, not a path ending in a directory separator")
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        failures.append(f"{field} contains a forbidden control character")
        return None
    # Inspect the original components before PureWindowsPath can discard '.'.
    for component in text[3:].split("\\"):
        if not component:
            continue
        if component in {".", ".."}:
            failures.append(f"{field} contains a forbidden dot/traversal component")
            return None
        if component.endswith((".", " ")) or any(character in '<>:"|?*' for character in component):
            failures.append(f"{field} contains an ambiguous or invalid Windows path component")
            return None
        if _DEVICE_NAME.fullmatch(component.split(".", 1)[0].rstrip(" ")):
            failures.append(f"{field} contains a reserved Windows device name")
            return None
    return PureWindowsPath(text)


def _strictly_under(path: PureWindowsPath, root: PureWindowsPath) -> bool:
    return path != root and root in path.parents


def validate_hidden_artifact_layout(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return deterministic lexical layout evidence and all path diagnostics.

    Only case and slash spelling are normalized. No existence, realpath,
    symlink/reparse, digest, or native observation is established here.
    """
    failures: list[str] = []
    proxy = payload.get("proxy")
    if not isinstance(proxy, dict):
        failures.append("proxy must be an object for hidden artifact layout binding")
        proxy = {}
    values = {
        "input_exe": payload.get("input_exe"),
        "workdir": payload.get("workdir"),
        "candidate": payload.get("candidate"),
        "output_directory": payload.get("output_directory"),
        "proxy.path": proxy.get("path"),
        "proxy.build_manifest": proxy.get("build_manifest"),
        "proxy.log": proxy.get("log"),
        "proxy.build_log": proxy.get("build_log"),
        "cdb_log": payload.get("cdb_log"),
        "generated_probe": payload.get("generated_probe"),
    }
    paths = {field: _windows_path(value, field, failures) for field, value in values.items()}
    for field, expected in (("input_exe", EXPECTED_INPUT), ("workdir", EXPECTED_WORKDIR)):
        if paths[field] is not None and paths[field] != expected:
            failures.append(f"{field} must be {expected}")

    candidate = paths["candidate"]
    output = paths["output_directory"]
    candidate_run: PureWindowsPath | None = None
    if candidate is not None:
        if candidate.suffix.casefold() != ".exe":
            failures.append("candidate must name an .exe file")
        if candidate.parent.parent != HIDDEN_CANDIDATE_ROOT:
            failures.append(f"candidate must be in one per-run directory immediately under {HIDDEN_CANDIDATE_ROOT}")
        else:
            candidate_run = candidate.parent
    output_run: PureWindowsPath | None = None
    if output is not None:
        if output.parent != HIDDEN_OUTPUT_ROOT:
            failures.append(f"output_directory must be one per-run directory immediately under {HIDDEN_OUTPUT_ROOT}")
        else:
            output_run = output
    if candidate_run is not None and output_run is not None and candidate_run.name.casefold() != output_run.name.casefold():
        failures.append("candidate and output_directory must name the same hidden run")

    if candidate_run is not None:
        for field, name in (
            ("proxy.path", "ddraw.dll"),
            ("proxy.build_manifest", "ddraw_surfdump_proxy.build.json"),
            ("proxy.log", "ddraw_surfdump_proxy.log"),
        ):
            if paths[field] is not None and paths[field] != candidate_run / name:
                failures.append(f"{field} must be the candidate-local {name}")
    if output_run is not None:
        for field in ("proxy.build_log", "cdb_log", "generated_probe"):
            if paths[field] is not None and not _strictly_under(paths[field], output_run):
                failures.append(f"{field} must be a file path under the same output_directory run")

    summary = {
        "scope": "hidden_windows_lexical_artifact_layout_only",
        "physical_artifacts_authenticated": False,
        "patch_manifest_layout_checked": False,
        "expected_candidate_root": str(HIDDEN_CANDIDATE_ROOT),
        "expected_output_root": str(HIDDEN_OUTPUT_ROOT),
        "candidate_run": str(candidate_run) if candidate_run is not None else None,
        "output_run": str(output_run) if output_run is not None else None,
        "paths": {field: str(path) if path is not None else None for field, path in paths.items()},
    }
    return summary, failures
