"""Observed hidden report/source byte binding, not native producer proof.

There is no caller-selected reader or skip policy. The embedded external
report_json remains unchanged; an explicitly selected canonical copy must
contain exactly the same bytes. A successful check authenticates neither file
immutability nor native execution, capture coherence, running time or input.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from hidden_soak_artifact_layout import _windows_path
from hidden_soak_retained_files import read_retained_file as _read_retained_file


MAX_REPORT_BYTES = 32 * 1024 * 1024


def _source_path(value: Any, label: str, failures: list[str], *, selected: bool = False) -> str | None:
    if not isinstance(value, (str, Path)):
        failures.append(f"{label} must name a nonempty native file path")
        return None
    text = str(value)
    if not text or text != text.strip() or any(ord(character) < 32 or ord(character) == 127 for character in text):
        failures.append(f"{label} must name an unambiguous native file path")
        return None
    path = Path(text)
    if not path.is_absolute():
        if not selected:
            failures.append(f"{label} must name an absolute retained external report")
            return None
        # absolute(), unlike resolve(), must not follow a selected symlink.
        path = Path.cwd() / path
    if os.name == "nt":
        if _windows_path(text if Path(text).is_absolute() else str(path), label, failures) is None:
            return None
    elif ".." in path.parts or any(part in {".", ".."} for part in text.split("/")):
        failures.append(f"{label} contains a forbidden dot/traversal component")
        return None
    return str(path)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON constant: {value}")


def _strict_object(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object,
                       parse_constant=_reject_constant)
    if type(value) is not dict:
        raise ValueError("retained report JSON must be an object")
    return value


def _typed_content(value: Any) -> str:
    # JSON spellings distinguish true/1 and 1/1.0, unlike Python dict equality.
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


def _read(path: str, role: str, summary: dict[str, Any], failures: list[str]) -> bytes | None:
    try:
        raw = _read_retained_file(path, MAX_REPORT_BYTES)
        if type(raw) is not bytes or not raw or len(raw) > MAX_REPORT_BYTES:
            raise ValueError("retained report must contain bounded nonempty original bytes")
        summary[role] = {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
        return raw
    except (OSError, ValueError, TypeError, OverflowError) as error:
        failures.append(f"{role}: retained report read failed: {type(error).__name__}: {error}")
        return None


def validate_hidden_report_binding(
    payload: dict[str, Any], *, selected_path: str | Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Bind the supplied object and optional selected alias to retained bytes.

    The same-path case performs one bounded held read. Distinct selected paths
    require exact byte equality, followed by a fresh external read to reject
    observed drift across the copy comparison. No files are written or resolved
    through links. The reader rejects observed reparse/identity/read/close loss.
    """
    summary: dict[str, Any] = {
        "scope": "observed_hidden_report_and_selected_source_byte_consistency_only",
        "external_source": {}, "selected_source": {},
        "payload_matches": False, "selected_bytes_match": False,
        "immutable_files_authenticated": False, "native_producer_authenticated": False,
        "native_execution_authenticated": False, "coherent_capture_authenticated": False,
        "running_time_authenticated": False,
    }
    failures: list[str] = []
    if type(payload) is not dict:
        return summary, ["source_report binding requires an object"]
    if payload.get("environment") != "hidden_cdb_host":
        failures.append("source_report binding requires environment=hidden_cdb_host")
    external = _source_path(payload.get("report_json"), "report_json", failures)
    selected = external if selected_path is None else _source_path(
        selected_path, "source_report_path", failures, selected=True,
    )
    if external is None or selected is None:
        return summary, failures
    raw = _read(external, "external_source", summary, failures)
    if raw is None:
        return summary, failures
    try:
        actual = _strict_object(raw)
        summary["payload_matches"] = _typed_content(actual) == _typed_content(payload)
        if not summary["payload_matches"]:
            failures.append("source_report content does not match the supplied typed JSON object")
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        failures.append(f"external_source: invalid retained JSON: {type(error).__name__}: {error}")
    if os.path.normcase(external) == os.path.normcase(selected):
        summary["selected_source"] = dict(summary["external_source"])
        summary["selected_bytes_match"] = True
    else:
        selected_raw = _read(selected, "selected_source", summary, failures)
        summary["selected_bytes_match"] = selected_raw == raw
        if not summary["selected_bytes_match"]:
            failures.append("source_report_path selected copy bytes differ from the retained external report_json")
        try:
            reread = _read_retained_file(external, MAX_REPORT_BYTES)
            if type(reread) is not bytes or reread != raw:
                raise ValueError("external report changed during selected-copy comparison")
        except (OSError, ValueError, TypeError, OverflowError) as error:
            failures.append(f"external_source: retained comparison recheck failed: {type(error).__name__}: {error}")
    return summary, failures
