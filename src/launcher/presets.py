#!/usr/bin/env python3
"""Resolution preset manifest access for the Clash95 HD launcher.

Reads the committed ``src/launcher/resolutions.json`` status manifest. This is
a repo-only data module; it starts no process and opens no window.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MANIFEST_PATH = Path(__file__).resolve().parent / "resolutions.json"
RESOLUTION_KEY_RE = re.compile(r"^([1-9]\d{2,3})x([1-9]\d{2,3})$")
VALID_STATUSES = ("stable", "validated", "experimental")


class ManifestError(ValueError):
    """The resolutions manifest is missing, malformed, or inconsistent."""


@dataclass(frozen=True)
class ResolutionOption:
    key: str
    width: int
    height: int
    status: str
    tiles: tuple[int, int] | None
    evidence: dict[str, str] | None

    @property
    def is_experimental(self) -> bool:
        return self.status == "experimental"


def parse_resolution_key(key: str) -> tuple[int, int]:
    match = RESOLUTION_KEY_RE.match(key or "")
    if not match:
        raise ManifestError(f"Resolution key must look like 800x600, got: {key!r}")
    return int(match.group(1)), int(match.group(2))


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise ManifestError(f"Resolutions manifest not found: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Resolutions manifest is not valid JSON: {path}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise ManifestError(f"Resolutions manifest must have schema 1: {path}")
    if not isinstance(manifest.get("resolutions"), dict) or not manifest["resolutions"]:
        raise ManifestError(f"Resolutions manifest lists no resolutions: {path}")
    return manifest


def load_options(manifest: dict[str, Any] | None = None) -> list[ResolutionOption]:
    manifest = manifest if manifest is not None else load_manifest()
    options: list[ResolutionOption] = []
    for key, entry in manifest["resolutions"].items():
        width, height = parse_resolution_key(key)
        status = entry.get("status")
        if status not in VALID_STATUSES:
            raise ManifestError(f"Resolution {key} has unknown status: {status!r}")
        tiles = entry.get("tiles")
        tiles_tuple = (int(tiles[0]), int(tiles[1])) if tiles else None
        options.append(
            ResolutionOption(
                key=key,
                width=width,
                height=height,
                status=status,
                tiles=tiles_tuple,
                evidence=entry.get("evidence"),
            )
        )
    return options


def default_key(manifest: dict[str, Any] | None = None) -> str:
    manifest = manifest if manifest is not None else load_manifest()
    return str(manifest.get("default"))


def stable_stage(manifest: dict[str, Any] | None = None) -> str:
    manifest = manifest if manifest is not None else load_manifest()
    return str(manifest.get("stable_stage"))


def custom_bounds(manifest: dict[str, Any] | None = None) -> tuple[tuple[int, int], tuple[int, int]]:
    manifest = manifest if manifest is not None else load_manifest()
    bounds = manifest.get("custom_bounds") or {}
    minimum = bounds.get("min") or [800, 600]
    maximum = bounds.get("max") or [3840, 2160]
    return (int(minimum[0]), int(minimum[1])), (int(maximum[0]), int(maximum[1]))


def validate_custom_resolution(
    width: int, height: int, manifest: dict[str, Any] | None = None
) -> list[str]:
    manifest = manifest if manifest is not None else load_manifest()
    errors: list[str] = []
    if not manifest.get("custom_allowed"):
        errors.append("Custom resolutions are disabled by the manifest.")
        return errors
    (min_w, min_h), (max_w, max_h) = custom_bounds(manifest)
    if width < min_w or height < min_h:
        errors.append(f"Custom resolution must be at least {min_w}x{min_h}.")
    if width > max_w or height > max_h:
        errors.append(f"Custom resolution must be at most {max_w}x{max_h}.")
    if width % 2 or height % 2:
        errors.append("Custom resolution width and height must both be even.")
    return errors


def patcher_supports_resolutions(patcher: Any) -> bool:
    """True once the patcher exposes the multi-resolution generator API."""
    return hasattr(patcher, "generate_patches")
