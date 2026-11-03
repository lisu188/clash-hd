#!/usr/bin/env python3
"""Canonical hidden-soak CDB probe composition, a pure function of bytes.

run_hidden_soak.ps1 used to compose its probe inline. This module reproduces
that composition byte for byte from the two retained template byte strings
and the recorded run parameters, so the producer and the graders build the
same probe. Inputs the inline PowerShell would have treated differently from
plain text are rejected instead of reproduced: non-ASCII or control bytes, a
missing or repeated PlayGame anchor, .NET replacement tokens in the inserted
soak text, a standalone ``g`` command in that text and placeholders left after
substitution. A matching probe proves construction only, not that CDB ran it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROUTES = ("map-idle", "map-pan")
TICKS_PER_SECOND = 64
DURATION_SEC_RANGE = (60, 28800)
PAN_INTERVAL_SEC_RANGE = (1, 600)
LOAD_SLOT_RANGE = (0, 9)
REQUIRED_SOAK_PLACEHOLDERS = ("__SOAK_DURATION_TICKS__", "__SOAK_PAN__", "__PAN_INTERVAL_TICKS__")
MAX_TEMPLATE_BYTES = 1024 * 1024

PRE_ENTRY_LOAD_COORD_ACTION = (
    r'ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__; eb 005451c0 80; ed 00544d04 1; '
    r'.if (@$t1 < 0n16) { .printf \"SURFDUMP_LOAD_COORD seq=%d choice=%d entry=0x%08x ex=%d ey=%d '
    r'mouse=(%d,%d) selected=%d accept=%d\\n\", @$t1, poi(00543d7c), @eax, poi(@eax), poi(@eax+4), '
    r'poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c), poi(005441e0), poi(00544190); '
    r'r @$t1 = @$t1 + 1; };')
# The proven -FastForwardStartAnims block.
START_ANIMS_BREAKPOINTS = "\r\n".join((
    r'.echo SURFDUMP_START_ANIMS_SLEEP_FAST_FORWARD_ENABLED',
    r'bp 0044789a ".printf \"SURFDUMP_SKIP_START_SLEEP ret=004478a1\\n\"; r eip=004478a1; r esp=@esp+4; gc"',
    r'bp 0046e4d0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046e4d0 '
    r'next=0046e4d7\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046e4d7; r esp=@esp+4; gc } .else { gc }"',
    r'bp 0046e6df ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046e6df '
    r'next=0046e6e6\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046e6e6; r esp=@esp+4; gc } .else { gc }"',
    r'bp 0046fd01 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046fd01 '
    r'next=0046fd08\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046fd08; r esp=@esp+4; gc } .else { gc }"',
    r'bp 0047BFD0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_TIME_SLEEP ret=%p\\n\", '
    r'poi(@esp); r @$t12 = @$t12 + 1; }; r eax=0; r eip=poi(@esp); r esp=@esp+4; gc } .else { gc }"',
))
# Host ReadProcessMemory dumping only; the game continues after the base READY.
SURFACE_DUMP_ACTION = ".echo SURFDUMP_HOST_READY; gc"

# The old producer passed 1 to [regex]::Replace(input, pattern, replacement,
# options), which binds it to RegexOptions.IgnoreCase and replaces every
# match. Requiring exactly one anchor makes that a single insertion.
_PLAY_GAME_ANCHOR = re.compile(r"^bp 0040B660 ", re.MULTILINE | re.IGNORECASE)
_STANDALONE_G = re.compile(r"^\s*g\s*$", re.MULTILINE | re.IGNORECASE)  # PowerShell -match ignores case.
_LEFTOVER_PLACEHOLDER = re.compile(r"__[A-Z0-9_]+__")
# .NET replacement-pattern tokens [regex]::Replace would have expanded.
_DOTNET_SUBSTITUTION = re.compile(r"\$(?:[0-9$&`'+_]|\{)")
# Within printable ASCII plus tab/CR/LF, .NET Trim(), .NET \s and Python agree.
_PLAIN_TEXT = re.compile(r"[\t\r\n\x20-\x7e]*")
_TRIM = " \t\r\n"


class ProbeCompositionError(ValueError):
    """The inputs cannot be composed without guessing what the producer did."""


def _template_text(label: str, data: bytes) -> str:
    if type(data) is not bytes or not data or len(data) > MAX_TEMPLATE_BYTES:
        raise ProbeCompositionError(f"{label} must be nonempty retained bytes within {MAX_TEMPLATE_BYTES} bytes")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ProbeCompositionError(f"{label} is not plain ASCII") from exc
    if not _PLAIN_TEXT.fullmatch(text):
        raise ProbeCompositionError(f"{label} contains control characters other than tab, CR and LF")
    return text


def _bounded(label: str, value: object, bounds: tuple[int, int]) -> int:
    low, high = bounds
    if type(value) is not int or not low <= value <= high:
        raise ProbeCompositionError(f"{label} must be an integer in {low}..{high}")
    return value


def load_mouse_raw(load_slot: int) -> tuple[str, str]:
    """Native load-list point for one slot, in the game's raw <<6 mouse units."""
    return f"{320 << 6:08x}", f"{(166 + 22 * load_slot) << 6:08x}"


def prepare_soak_text(soak_template: bytes, *, route: str, duration_sec: int, pan_interval_sec: int,
                      load_slot: int) -> str:
    """Return the stripped soak extra with one run's parameters substituted.

    compose_probe inserts exactly this text; other hidden producers can reuse
    it without the legacy base template.
    """
    if route not in ROUTES:
        raise ProbeCompositionError("route must be map-idle or map-pan")
    duration_ticks = _bounded("duration_sec", duration_sec, DURATION_SEC_RANGE) * TICKS_PER_SECOND
    pan_interval_ticks = _bounded("pan_interval_sec", pan_interval_sec, PAN_INTERVAL_SEC_RANGE) * TICKS_PER_SECOND
    _bounded("load_slot", load_slot, LOAD_SLOT_RANGE)
    mouse_x, mouse_y = load_mouse_raw(load_slot)
    soak = _template_text("soak probe template", soak_template).strip(_TRIM)
    missing = [name for name in REQUIRED_SOAK_PLACEHOLDERS if name not in soak]
    if missing:
        raise ProbeCompositionError("soak probe template is missing required placeholders: " + ", ".join(missing))
    if _STANDALONE_G.search(soak):
        raise ProbeCompositionError("soak probe template must not contain a standalone g command")
    for placeholder, value in (("__SOAK_DURATION_TICKS__", f"0n{duration_ticks}"),
                               ("__PAN_INTERVAL_TICKS__", f"0n{pan_interval_ticks}"),
                               ("__SOAK_PAN__", "1" if route == "map-pan" else "0"),
                               ("__LOAD_SLOT__", str(load_slot)),
                               ("__LOAD_MOUSE_RAW_X__", mouse_x),
                               ("__LOAD_MOUSE_RAW_Y__", mouse_y)):
        soak = soak.replace(placeholder, value)
    return soak


def compose_probe(probe_template: bytes, soak_template: bytes, *, route: str, duration_sec: int,
                  pan_interval_sec: int, load_slot: int, raw_path: str) -> bytes:
    """Return the exact generated probe bytes for one hidden soak run."""
    if route not in ROUTES:
        raise ProbeCompositionError("route must be map-idle or map-pan")
    _bounded("duration_sec", duration_sec, DURATION_SEC_RANGE)
    _bounded("pan_interval_sec", pan_interval_sec, PAN_INTERVAL_SEC_RANGE)
    _bounded("load_slot", load_slot, LOAD_SLOT_RANGE)
    if (type(raw_path) is not str or not raw_path or not _PLAIN_TEXT.fullmatch(raw_path)
            or any(character in raw_path for character in '\t\r\n"')):
        raise ProbeCompositionError("raw_path must be one line of plain ASCII without quotes")
    mouse_x, mouse_y = load_mouse_raw(load_slot)
    soak = prepare_soak_text(soak_template, route=route, duration_sec=duration_sec,
                             pan_interval_sec=pan_interval_sec, load_slot=load_slot)

    probe = _template_text("probe template", probe_template)
    # Order matters: the load-coordinate action carries the mouse placeholders.
    for placeholder, value in (("__PRE_ENTRY_LOAD_COORD_ACTION__", PRE_ENTRY_LOAD_COORD_ACTION),
                               ("__LOAD_SLOT__", str(load_slot)),
                               ("__LOAD_MOUSE_RAW_X__", mouse_x),
                               ("__LOAD_MOUSE_RAW_Y__", mouse_y)):
        probe = probe.replace(placeholder, value)
    if len(_PLAY_GAME_ANCHOR.findall(probe)) != 1:
        raise ProbeCompositionError("probe template must contain exactly one PlayGame breakpoint anchor")
    insertion = soak + "\r\n\r\n" + "bp 0040B660 "
    if _DOTNET_SUBSTITUTION.search(insertion):
        raise ProbeCompositionError("soak probe text contains a .NET replacement token the old producer expanded")
    probe = _PLAY_GAME_ANCHOR.sub(lambda _match: insertion, probe)  # A function keeps backslashes literal.
    for placeholder, value in (("__START_ANIMS_BP__", START_ANIMS_BREAKPOINTS),
                               ("__VISIBILITY_PLAYGAME_ACTION__", ""),
                               ("__VISIBILITY_PATCH_ACTION__", ""),
                               ("__SURFACE_DUMP_ACTION__", SURFACE_DUMP_ACTION),
                               ("__RAW_PATH__", raw_path.replace("\\", "/"))):
        probe = probe.replace(placeholder, value)
    leftover = sorted(set(_LEFTOVER_PLACEHOLDER.findall(probe)))
    if leftover:
        raise ProbeCompositionError("probe composition left unsubstituted placeholders: " + ", ".join(leftover))
    return (probe + "\r\n").encode("ascii")  # Set-Content -Encoding ASCII appended one CRLF.


def composer_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _read_template(path: Path) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(MAX_TEMPLATE_BYTES + 1)
    if len(data) > MAX_TEMPLATE_BYTES:
        raise ProbeCompositionError(f"{path} exceeds {MAX_TEMPLATE_BYTES} bytes")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--soak-template", type=Path, required=True)
    parser.add_argument("--route", choices=ROUTES, required=True)
    parser.add_argument("--duration-sec", type=int, required=True)
    parser.add_argument("--pan-interval-sec", type=int, required=True)
    parser.add_argument("--load-slot", type=int, required=True)
    parser.add_argument("--raw-path", required=True)
    parser.add_argument("--output", type=Path, required=True, help="new file; an existing one is never replaced")
    args = parser.parse_args(argv)
    try:
        templates = {"probe_template": _read_template(args.probe_template),
                     "soak_probe_template": _read_template(args.soak_template)}
        parameters = {"route": args.route, "duration_sec": args.duration_sec, "pan_interval_sec": args.pan_interval_sec,
                      "load_slot": args.load_slot, "raw_path": args.raw_path}
        probe = compose_probe(templates["probe_template"], templates["soak_probe_template"], **parameters)
        with args.output.open("xb") as stream:
            stream.write(probe)
            stream.flush()
            os.fsync(stream.fileno())
        if args.output.read_bytes() != probe:
            raise ProbeCompositionError("generated probe changed after its exclusive write")
    except (OSError, ProbeCompositionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    receipt = {"schema": "hidden_soak_probe_composition_v1", "composer_sha256": composer_sha256(),
               "parameters": parameters, "generated_probe_sha256": hashlib.sha256(probe).hexdigest(),
               "generated_probe_size": len(probe),
               **{f"{role}_sha256": hashlib.sha256(data).hexdigest() for role, data in templates.items()},
               **{f"{role}_size": len(data) for role, data in templates.items()}}
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
