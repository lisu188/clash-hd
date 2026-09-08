"""Rebuild the normal complete-HD hidden map command file without executing it.

The caller must first authenticate the candidate with complete_hd_runtime_context.
This deliberately supports only the normal slot-0, hidden-proxy, fast-forward,
paused initial-paint route. The existing PowerShell producer is left unchanged.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PureWindowsPath
import re

import render_cdb_surface_probe as renderer
from complete_hd_runtime_context import complete

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/cdb/run_cdb_surface_dump.ps1"
RECIPE = "complete_hd_normal_main_v1"

# Literal values of the supported producer branches, including CDB escaping.
# A change to any producer action needs an explicit recipe review; recorded
# source_main hashes alone never authorize an alternative debugger program.
LOAD_ACTION = r'ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__; eb 005451c0 80; ed 00544d04 1; .if (@$t1 < 0n16) { .printf \"SURFDUMP_LOAD_COORD seq=%d choice=%d entry=0x%08x ex=%d ey=%d mouse=(%d,%d) selected=%d accept=%d\\n\", @$t1, poi(00543d7c), @eax, poi(@eax), poi(@eax+4), poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c), poi(005441e0), poi(00544190); r @$t1 = @$t1 + 1; };'
START_ACTION = "\r\n".join((
    '.echo SURFDUMP_START_ANIMS_SLEEP_FAST_FORWARD_ENABLED',
    r'bp 0044789a ".printf \"SURFDUMP_SKIP_START_SLEEP ret=004478a1\\n\"; r eip=004478a1; r esp=@esp+4; gc"',
    r'bp 0046e4d0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046e4d0 next=0046e4d7\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046e4d7; r esp=@esp+4; gc } .else { gc }"',
    r'bp 0046e6df ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046e6df next=0046e6e6\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046e6e6; r esp=@esp+4; gc } .else { gc }"',
    r'bp 0046fd01 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046fd01 next=0046fd08\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046fd08; r esp=@esp+4; gc } .else { gc }"',
    r'bp 0047BFD0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_TIME_SLEEP ret=%p\\n\", poi(@esp); r @$t12 = @$t12 + 1; }; r eax=0; r eip=poi(@esp); r esp=@esp+4; gc } .else { gc }"',
))
MINIMAP_ACTION = r'.if (poi(005202e4) == 0) { .echo FRAMED_CAPTURE_REJECT missing_game_data; q } .else { .if ((poi(poi(005202e4)+23ec7) != 0) & (poi(poi(005202e4)+23ec7) != 1) & (poi(poi(005202e4)+23ec7) != 2) & (poi(poi(005202e4)+23ec7) != 3) & (poi(poi(005202e4)+23ec7) != 4)) { .echo FRAMED_CAPTURE_REJECT minimap_selector; q } .else { .printf \"FRAMED_MINIMAP enabled=%d origin=(%d,%d) size=(%d,%d)\\n\", (poi(poi(005202e4)+2230f+poi(poi(005202e4)+23ec7)*58f) != 0), wo(00523344), wo(00523346), wo(00523348), wo(0052334a); }; };'
PAUSE_ACTION = r'.printf \"PTILE_TRACE_CLOSED tid=%x eip=%p esp=%p\\n\", @$tid, @eip, @esp; .echo SURFDUMP_HOST_READY;'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_token(raw_path: Path | str) -> str:
    """Match GetFullPath + slash normalization; do not accept command text."""
    value = str(raw_path)
    if not value.isascii() or any(c in value for c in '\x00\r\n";'):
        raise ValueError("raw capture path must be a literal ASCII absolute path")
    windows = PureWindowsPath(value)
    if windows.drive:
        if not windows.is_absolute() or ".." in windows.parts:
            raise ValueError("raw capture path must be absolute and normalized")
        return windows.as_posix()
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("raw capture path must be absolute and normalized")
    return path.as_posix()


def rebuild_normal_main(context: dict, raw_path: Path | str) -> dict:
    """Reconstruct the already authenticated candidate's supported main recipe.

    This helper is not a substitute for deterministic candidate reconstruction:
    its context comes from load_context/verify_context, and only the owning
    evaluator authenticates run mode, artifacts, source hashes and log records.
    """
    manifest, extra = context["manifest"], context["probe"]
    if (manifest.get("stage") != complete.STAGE or
            manifest.get("recipe_revision") != complete.REVISION or
            context.get("framed", {}).get("stage") != renderer.FRAMED_STAGE):
        raise ValueError("normal complete main requires the exact complete/framed recipe")
    if (not isinstance(extra, str) or not extra.isascii() or "\r" in extra or
            sha(extra.encode("ascii")) != manifest.get("probe_sha256") or
            sha(context["candidate"]) != manifest.get("candidate_sha256")):
        raise ValueError("normal complete main context bytes or canonical probe differ")
    if re.search(r"(?m)^\s*g\s*$", extra) or "__" in extra:
        raise ValueError("normal complete extra has unsupported continuation or placeholders")
    raw_token = file_token(raw_path)
    template_bytes = renderer.BASE_PROBE.read_bytes()
    recipe = renderer.render_probe(template_bytes.decode("utf-8-sig"),
                                   manifest["resolution"], renderer.FRAMED_STAGE,
                                   canonical_template=True, load_slot=0)
    text = recipe["template"]
    text = renderer.replace_exact(text, "__PRE_ENTRY_LOAD_COORD_ACTION__", LOAD_ACTION)
    x, y = recipe["geometry"]["load_mouse"]
    replacements = {"__LOAD_SLOT__": "0", "__LOAD_MOUSE_RAW_X__": f"{x << 6:08x}",
                    "__LOAD_MOUSE_RAW_Y__": f"{y << 6:08x}"}
    for old, new in replacements.items():
        if old not in text:
            raise ValueError(f"normal complete main missing producer placeholder {old}")
        text = text.replace(old, new)
    insertion = "bp 0040B660 "
    if len(re.findall(r"(?m)^bp 0040B660 ", text)) != 1:
        raise ValueError("normal complete main needs one PlayGame insertion point")
    # A callable avoids interpreting CDB dollar registers as regex replacements.
    text = re.sub(r"(?m)^bp 0040B660 ", lambda _: extra.strip() + "\r\n\r\n" + insertion, text)
    for old, new in (("__START_ANIMS_BP__", START_ACTION),
                     ("__VISIBILITY_PLAYGAME_ACTION__", ""),
                     ("__VISIBILITY_PATCH_ACTION__", ""),
                     ("__SURFACE_DUMP_ACTION__", MINIMAP_ACTION + PAUSE_ACTION)):
        text = renderer.replace_exact(text, old, new)
    # Host ReadProcessMemory currently uses no raw-path token in CDB. Keep the
    # producer's literal substitution; the evaluator separately binds raw files.
    text = text.replace("__RAW_PATH__", raw_token)
    if "__" in text or not text.isascii():
        raise ValueError("normal complete main has unresolved or non-ASCII commands")
    # Windows Set-Content -Encoding ASCII appends one CRLF to its string value.
    text += "\r\n"
    normalized = text.replace("\r\n", "\n")
    if "\r" in normalized:
        raise ValueError("normal complete template contains unsupported line endings")
    return {"recipe": RECIPE, "text": text, "lf_text": normalized,
            "geometry": recipe["geometry"], "raw_path": raw_token,
            "source_hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path.read_bytes())
                              for path in (Path(__file__), Path(renderer.__file__), renderer.BASE_PROBE, HARNESS)}}


def verify_normal_main(main_text: str, context: dict, raw_path: Path | str) -> dict:
    """Reject any command difference, even with self-consistent artifact hashes."""
    rebuilt = rebuild_normal_main(context, raw_path)
    if not isinstance(main_text, str) or not main_text.isascii():
        raise ValueError("complete source main must be ASCII text")
    permitted = (rebuilt["text"], rebuilt["lf_text"], rebuilt["lf_text"].replace("\n", "\r\n"))
    if main_text not in permitted:
        raise ValueError("complete source main differs from the exact normal hidden recipe")
    return {"recipe": RECIPE, "exact_recipe_verified": True,
            "stage": context["manifest"]["stage"], "resolution": context["manifest"]["resolution"],
            "candidate_sha256": context["manifest"]["candidate_sha256"],
            "canonical_probe_sha256": context["manifest"]["probe_sha256"],
            "source_main_sha256": sha(main_text.encode("ascii")),
            "source_main_lf_sha256": sha(rebuilt["lf_text"].encode("ascii")),
            "raw_path": rebuilt["raw_path"], "source_hashes": rebuilt["source_hashes"],
            "runtime_executed": False, "acceptance": False}
