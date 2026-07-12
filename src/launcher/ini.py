#!/usr/bin/env python3
"""Render the windowed DirectDraw wrapper config for launcher candidates.

Starts from the tracked ``dxcfg_windowed.ini`` template and substitutes only
the ``scaling=`` key. Only wrapper vocabulary that has been verified against a
real wrapper install is offered; unverified modes are rejected so the launcher
falls back to the template verbatim. Repo-only text rendering; starts no
process and opens no window.
"""

from __future__ import annotations

from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "dxcfg_windowed.ini"

# Maps launcher scaling-mode names to dxcfg `scaling=` values. Extend only
# after verifying the value against the user's actual wrapper in C:\Clash.
VERIFIED_SCALING_MODES: dict[str, str] = {
    "integer": "integer",
}
DEFAULT_SCALING_MODE = "integer"


class ScalingModeError(ValueError):
    """The requested scaling mode is not in the verified vocabulary."""


def render_dxcfg(
    scaling_mode: str = DEFAULT_SCALING_MODE, template_path: Path = TEMPLATE_PATH
) -> str:
    if scaling_mode not in VERIFIED_SCALING_MODES:
        known = ", ".join(sorted(VERIFIED_SCALING_MODES))
        raise ScalingModeError(
            f"Unverified scaling mode {scaling_mode!r}; verified modes: {known}"
        )
    value = VERIFIED_SCALING_MODES[scaling_mode]
    lines = template_path.read_text(encoding="utf-8").splitlines()
    rendered: list[str] = []
    replaced = False
    for line in lines:
        if line.strip().startswith("scaling="):
            rendered.append(f"scaling={value}")
            replaced = True
        else:
            rendered.append(line)
    if not replaced:
        raise ScalingModeError(f"Template has no scaling= line: {template_path}")
    return "\n".join(rendered) + "\n"
