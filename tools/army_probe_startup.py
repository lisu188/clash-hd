"""Pure army probe transport from the explicit reviewed startup recipe.

The literals preserve the original six startup lines and ordinary slot-0 load
substitution. This module never reads the changing runtime harness or starts
anything. The caller must authenticate its candidate and command packet;
compilation supplies neither runtime acceptance nor manual/promotion proof.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REVISION = "army_probe_startup_v1"
BASE_STAGE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation"
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602")
DUMP_TOKEN = "__SURFACE_DUMP_ACTION__"
RECIPE_SHA256 = "f0f72a09aec7db61193889984a00e3b195ad71bc8f9567ed2d149d07d8c8edac"
HISTORICAL_SOURCE = {
    "revision": "af8179ec",
    "path": "scripts/cdb/run_cdb_surface_dump.ps1",
    "sha256": "ae90b6930a287d4fdc12dc5506780b82af3fbbe1c6cbc49dcc2bc08d5e64e43b",
    "extraction": "six FastForwardStartAnims literals and ordinary pre-entry load literal; LF, doubled apostrophes decoded",
}
PINNED_SOURCES = {
    "tools/render_cdb_surface_probe.py": "12685fdfde4972e0f5f9c3d5678fd159fff965bd9ddd7642cb3718c8530296cf",
    "patch_clash95_hd.py": "b2d8af4caf3fef1de0e3902b638be3c6bfba731bca7cd8d10c85c93e12424093",
    "src/patcher/patch_clash95_hd.py": "05f31359f93a0eb0b319679ee524b21c05cd3e86e485b7ebb92afc8e6da29f31",
    "src/patcher/framed_recipe.py": "aaf7f0ec724f89e0e48add0f5a608b4e4b7fae90b79be1dcd30effd91174001a",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "probes/cdb/render/clash95_surface_dump_probe.cdb": "6346ca89d5c3e8b63fbb6c96839c48920aa9eb039523f49b442f7fc47fef7df8",
}
STARTUP_LINES = (
    '.echo SURFDUMP_START_ANIMS_SLEEP_FAST_FORWARD_ENABLED',
    'bp 0044789a ".printf \\"SURFDUMP_SKIP_START_SLEEP ret=004478a1\\\\n\\"; r eip=004478a1; r esp=@esp+4; gc"',
    'bp 0046e4d0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \\"SURFDUMP_SKIP_AVI_SLEEP call=0046e4d0 next=0046e4d7\\\\n\\"; r @$t12 = @$t12 + 1; }; r eip=0046e4d7; r esp=@esp+4; gc } .else { gc }"',
    'bp 0046e6df ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \\"SURFDUMP_SKIP_AVI_SLEEP call=0046e6df next=0046e6e6\\\\n\\"; r @$t12 = @$t12 + 1; }; r eip=0046e6e6; r esp=@esp+4; gc } .else { gc }"',
    'bp 0046fd01 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \\"SURFDUMP_SKIP_AVI_SLEEP call=0046fd01 next=0046fd08\\\\n\\"; r @$t12 = @$t12 + 1; }; r eip=0046fd08; r esp=@esp+4; gc } .else { gc }"',
    'bp 0047BFD0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \\"SURFDUMP_SKIP_TIME_SLEEP ret=%p\\\\n\\", poi(@esp); r @$t12 = @$t12 + 1; }; r eax=0; r eip=poi(@esp); r esp=@esp+4; gc } .else { gc }"',
)
PRE_ENTRY = 'ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__; eb 005451c0 80; ed 00544d04 1; .if (@$t1 < 0n16) { .printf \\"SURFDUMP_LOAD_COORD seq=%d choice=%d entry=0x%08x ex=%d ey=%d mouse=(%d,%d) selected=%d accept=%d\\\\n\\", @$t1, poi(00543d7c), @eax, poi(@eax), poi(@eax+4), poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c), poi(005441e0), poi(00544190); r @$t1 = @$t1 + 1; };'
REQUIRED_TOKENS = (
    "__START_ANIMS_BP__", "__PRE_ENTRY_LOAD_COORD_ACTION__", "__LOAD_SLOT__",
    "__LOAD_MOUSE_RAW_X__", "__LOAD_MOUSE_RAW_Y__",
    "__VISIBILITY_PLAYGAME_ACTION__", "__VISIBILITY_PATCH_ACTION__", DUMP_TOKEN,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_sources() -> dict[str, str]:
    recipe = ("\n".join(STARTUP_LINES) + "\n" + PRE_ENTRY + "\n").encode("ascii")
    if len(STARTUP_LINES) != 6 or sha(recipe) != RECIPE_SHA256:
        raise ValueError("reviewed literal startup recipe differs")
    for name, expected in PINNED_SOURCES.items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise ValueError("reviewed startup geometry source differs: " + name)
    return dict(PINNED_SOURCES)


def provenance() -> dict:
    sources = verify_sources()
    sources["tools/army_probe_startup.py"] = sha(Path(__file__).read_bytes())
    return dict(revision=REVISION, recipe_sha256=RECIPE_SHA256,
                historical_source=dict(HISTORICAL_SOURCE), source_sha256=sources,
                runtime_executed=False, manual_input_proof=False, promotion_ready=False)


def _text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(name + " must be text")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError(name + " must be ASCII command text") from error
    text = value.replace("\r\n", "\n")
    if "\r" in text or any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise ValueError(name + " contains unsupported control characters")
    return text


def _transport(text: str) -> None:
    resets = re.findall(r"(?m)^\s*bc[ \t]+\*[ \t]*$", text)
    continues = re.findall(r"(?m)^[ \t]*g[ \t]*$", text)
    if resets != ["bc *"] or continues != ["g"] or not text.endswith("g\n"):
        raise ValueError("exactly one canonical bc * and final standalone g required")
    first_breakpoint = re.search(r"(?m)^bp", text)
    if first_breakpoint and text.index("bc *\n") >= first_breakpoint.start():
        raise ValueError("breakpoint declarations precede the initial reset")


def compile_probe(packet: dict) -> str:
    """Compile caller-authenticated fields; writes nothing and launches nothing."""
    sources = verify_sources()
    if not isinstance(packet, dict) or packet.get("resolution") not in RESOLUTIONS:
        raise ValueError("one of the six exact army fixture resolutions is required")
    text = _text(packet.get("map_probe_template"), "map_probe_template")
    _transport(text)
    for token in REQUIRED_TOKENS:
        if text.count(token) != 1:
            raise ValueError("expected exactly one canonical token: " + token)
    fragments = {}
    for name in ("handoff_action", "byte_checks_before_first_breakpoint", "startup_commands_before_final_g"):
        value = _text(packet.get(name), name)
        if not value or re.search(r"__[A-Za-z0-9_]+__", value):
            raise ValueError(name + " must be a nonempty resolved command fragment")
        if name != "handoff_action" and not value.endswith("\n"):
            raise ValueError(name + " requires its final line boundary")
        fragments[name] = value

    # Import only after checking the exact renderer and its geometry sources.
    from render_cdb_surface_probe import BASE_PROBE, render_probe
    geometry = render_probe(BASE_PROBE.read_text(encoding="utf-8-sig"),
                            packet["resolution"], BASE_STAGE, load_slot=0)["geometry"]
    replacements = {
        "__START_ANIMS_BP__": "\n".join(STARTUP_LINES),
        "__PRE_ENTRY_LOAD_COORD_ACTION__": PRE_ENTRY,
        "__LOAD_SLOT__": "0",
        "__LOAD_MOUSE_RAW_X__": f"{geometry['load_mouse'][0] << 6:08x}",
        "__LOAD_MOUSE_RAW_Y__": f"{geometry['load_mouse'][1] << 6:08x}",
        "__VISIBILITY_PLAYGAME_ACTION__": "", "__VISIBILITY_PATCH_ACTION__": "",
        DUMP_TOKEN: fragments["handoff_action"],
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    text = text.replace("bc *\n", "bc *\n" + fragments["byte_checks_before_first_breakpoint"])
    text = re.sub(r"(?m)^g$", lambda _: fragments["startup_commands_before_final_g"] + "g", text)
    if re.search(r"__[A-Za-z0-9_]+__", text):
        raise ValueError("unresolved command-file substitution")
    _transport(text)
    if any(len(line.encode("ascii")) >= 4096 for line in text.splitlines()):
        raise ValueError("compiled command file exceeds the 4095-byte line limit")
    occupied, sites = set(), set()
    for line in text.splitlines():
        if not re.match(r"^bp", line):
            continue
        match = re.fullmatch(r'bp\s*(?:(\d+)\s+)?([0-9a-fA-F]{8})\s+".*"', line)
        if not match:
            raise ValueError("unrecognized breakpoint declaration")
        number = int(match[1]) if match[1] else next(i for i in range(1000) if i not in occupied)
        site = int(match[2], 16)
        if number in occupied or site in sites or not 0 <= number < 1000:
            raise ValueError("compiled command-file breakpoint collision or unsupported id")
        occupied.add(number)
        sites.add(site)
    if verify_sources() != sources:
        raise ValueError("startup sources changed during compilation")
    return text
