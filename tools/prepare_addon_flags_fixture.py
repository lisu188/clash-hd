#!/usr/bin/env python3
"""Prepare an isolated save fixture that sets a building's addon_flags bit 0x02.

Gate 1 of the HD completion sequence (``reports/hd_completion_certainty.md``)
needs the right-bottom building action menu to draw through the *natural* game
path. The panel only renders when the clicked building's ``addon_flags`` byte at
``building_record + 416`` has bit ``0x02`` set (``clash95.c:49999``). Because a
save load is a verbatim binary image restore (``SaveSlot_LoadGame`` bulk-reads
the game data block), the natural route is reachable by a single isolated
save-byte edit -- no new binary patch, exactly as the disassembly cross-check
prescribes ("Do not patch the binary to force the right-bottom panel").

This tool copies a source save into an isolated fixture directory and sets bit
``0x02`` at::

    file_offset = header_size + records_base + building_index * record_stride + addon_flags_offset

with the disassembly-verified defaults ``header_size=0x10``,
``records_base=509674``, ``record_stride=467``, ``addon_flags_offset=416``. The
edit is pure bytes so it is fully unit-testable off Windows; correctness against
the live game is confirmed when the fixture is loaded during the approved VM
run.

It never mutates the live ``C:\\Clash\\save`` tree or the source save, and by
default refuses to write inside the repository (mirroring the guards in
``scripts/smoke/prepare_right_bottom_slot_fixture.ps1``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


# Disassembly-verified save-layout constants (reports/hd_completion_certainty.md,
# clash-disassembly docs/SAVE_DAT_FORMAT.md row 509674). Exposed as CLI flags so
# a corrected layout can be supplied without editing code.
DEFAULT_HEADER_SIZE = 0x10
DEFAULT_RECORDS_BASE = 509674
DEFAULT_RECORD_STRIDE = 467
DEFAULT_ADDON_FLAGS_OFFSET = 416
DEFAULT_OWNER_OFFSET = 3
DEFAULT_FLAG_BIT = 0x02

LIVE_SAVE_ROOT = "C:\\Clash\\save"
LIVE_ORIGINAL_WORKDIR = "C:\\Clash"
RUNTIME_POLICY = (
    "repo-only byte editor; copies a save and flips one addon_flags bit; does "
    "not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
)
PROOF_CLASS = "non_natural_isolated_fixture"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def addon_flags_offset(
    building_index: int,
    *,
    header_size: int,
    records_base: int,
    record_stride: int,
    addon_flags_offset_in_record: int,
) -> int:
    """File offset of the addon_flags byte for ``building_index``."""
    if building_index < 0:
        raise ValueError(f"building_index must be >= 0, got {building_index}")
    return (
        header_size
        + records_base
        + building_index * record_stride
        + addon_flags_offset_in_record
    )


def _normalize_windows_path(value: str) -> str:
    """Casefolded, separator-normalized form for Windows-style guard checks."""
    return str(value or "").replace("/", "\\").rstrip("\\").casefold()


def _is_same_or_under(path_text: str, root_text: str) -> bool:
    path = _normalize_windows_path(path_text)
    root = _normalize_windows_path(root_text)
    return bool(path and (path == root or path.startswith(root + "\\")))


def guard_failures(
    *,
    source_save: Path,
    out_save: Path,
    repo_root: Path,
    allow_repo_output: bool,
) -> list[str]:
    """Return reasons the requested output is unsafe (empty list == safe)."""
    failures: list[str] = []
    src = source_save.resolve()
    dst = out_save.resolve()

    if src == dst:
        failures.append(f"refusing to overwrite the source save: {src}")

    try:
        dst.relative_to(repo_root.resolve())
        under_repo = True
    except ValueError:
        under_repo = False
    if under_repo and not allow_repo_output:
        failures.append(
            f"refusing fixture output inside the repository by default: {dst} "
            "(pass --allow-repo-output for a deliberate local handoff)"
        )

    # Windows-path guards: on a Windows/wine host these keep the edit away from
    # the live game tree even though the paths do not exist on Linux.
    dst_win = str(out_save)
    if _is_same_or_under(dst_win, LIVE_SAVE_ROOT):
        failures.append(f"refusing to write into the live Clash save directory: {dst_win}")
    if _is_same_or_under(dst_win, LIVE_ORIGINAL_WORKDIR) and not _is_same_or_under(
        dst_win, "C:\\ClashTests"
    ):
        # Anything directly under C:\Clash that is not the sanctioned test root.
        failures.append(f"refusing fixture output inside the live Clash workdir: {dst_win}")
    return failures


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    source_save = Path(args.source_save)
    out_dir = Path(args.out_dir)
    out_save = out_dir / args.save_basename

    offset = addon_flags_offset(
        args.building_index,
        header_size=args.header_size,
        records_base=args.records_base,
        record_stride=args.record_stride,
        addon_flags_offset_in_record=args.addon_flags_offset,
    )
    owner_offset = (
        args.header_size
        + args.records_base
        + args.building_index * args.record_stride
        + args.owner_offset
    )

    failures = guard_failures(
        source_save=source_save,
        out_save=out_save,
        repo_root=repo_root,
        allow_repo_output=args.allow_repo_output,
    )

    source_exists = source_save.is_file()
    source_sha256: str | None = None
    source_size: int | None = None
    observed_addon_byte: int | None = None
    observed_owner_byte: int | None = None
    if source_exists:
        data = source_save.read_bytes()
        source_size = len(data)
        source_sha256 = hashlib.sha256(data).hexdigest()
        if offset >= source_size:
            failures.append(
                f"addon_flags offset {offset} (0x{offset:X}) is beyond the save size "
                f"{source_size} for building_index {args.building_index}"
            )
        else:
            observed_addon_byte = data[offset]
        if 0 <= owner_offset < source_size:
            observed_owner_byte = data[owner_offset]
    else:
        failures.append(f"source save does not exist: {source_save}")

    if (
        args.require_owner is not None
        and observed_owner_byte is not None
        and observed_owner_byte != args.require_owner
    ):
        failures.append(
            f"building_index {args.building_index} owner byte was "
            f"{observed_owner_byte} (0x{observed_owner_byte:02X}), expected "
            f"{args.require_owner} (0x{args.require_owner:02X}); pick a building "
            "the player owns"
        )

    new_addon_byte = (
        observed_addon_byte | args.flag_bit if observed_addon_byte is not None else None
    )

    return {
        "runtime_policy": RUNTIME_POLICY,
        "proof_class": PROOF_CLASS,
        "promotion_ready": False,
        "dry_run": not args.execute,
        "repo_root": str(repo_root),
        "source_save": str(source_save),
        "source_exists": source_exists,
        "source_size": source_size,
        "source_sha256": source_sha256,
        "out_dir": str(out_dir),
        "out_save": str(out_save),
        "save_basename": args.save_basename,
        "building_index": args.building_index,
        "layout": {
            "header_size": args.header_size,
            "records_base": args.records_base,
            "record_stride": args.record_stride,
            "addon_flags_offset": args.addon_flags_offset,
            "owner_offset": args.owner_offset,
            "flag_bit": args.flag_bit,
        },
        "addon_flags_file_offset": offset,
        "addon_flags_file_offset_hex": f"0x{offset:X}",
        "owner_file_offset": owner_offset,
        "observed_addon_flags_byte": observed_addon_byte,
        "observed_owner_byte": observed_owner_byte,
        "new_addon_flags_byte": new_addon_byte,
        "must_not_mutate": [LIVE_SAVE_ROOT, LIVE_ORIGINAL_WORKDIR + "\\clash95.exe", str(repo_root)],
        "passed": not failures,
        "failures": failures,
    }


def apply_fixture(plan: dict[str, Any], *, source_save: Path, out_save: Path, flag_bit: int) -> dict[str, Any]:
    offset = int(plan["addon_flags_file_offset"])
    out_save.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_save, out_save)
    data = bytearray(out_save.read_bytes())
    before = data[offset]
    data[offset] = before | flag_bit
    out_save.write_bytes(data)
    result = dict(plan)
    result["applied"] = True
    result["dry_run"] = False
    result["written_offset"] = offset
    result["byte_before"] = before
    result["byte_after"] = data[offset]
    result["output_sha256"] = sha256_of(out_save)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-save", required=True, help="Path to the source save (never mutated)")
    parser.add_argument(
        "--out-dir",
        required=True,
        help=r"Isolated fixture directory, e.g. C:\ClashTests\right-bottom-addon-fixture\save",
    )
    parser.add_argument("--save-basename", default="0.dat", help="Fixture save filename (load slot), default 0.dat")
    parser.add_argument("--building-index", type=int, required=True, help="Building record index (0-99) to flag")
    parser.add_argument("--header-size", type=int, default=DEFAULT_HEADER_SIZE)
    parser.add_argument("--records-base", type=int, default=DEFAULT_RECORDS_BASE)
    parser.add_argument("--record-stride", type=int, default=DEFAULT_RECORD_STRIDE)
    parser.add_argument("--addon-flags-offset", type=int, default=DEFAULT_ADDON_FLAGS_OFFSET)
    parser.add_argument("--owner-offset", type=int, default=DEFAULT_OWNER_OFFSET)
    parser.add_argument("--flag-bit", type=lambda v: int(v, 0), default=DEFAULT_FLAG_BIT)
    parser.add_argument(
        "--require-owner",
        type=lambda v: int(v, 0),
        default=None,
        help="If set, fail unless the record owner byte equals this player index",
    )
    parser.add_argument("--allow-repo-output", action="store_true", help="Permit fixture output inside the repo")
    parser.add_argument("--execute", action="store_true", help="Actually write the fixture (default is dry-run)")
    parser.add_argument("--json", action="store_true", help="Emit the plan/result as JSON")
    parser.add_argument("--write-json", type=Path, help="Also write the plan/result JSON to this path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plan = build_plan(args)

    result = plan
    if args.execute and plan["passed"]:
        result = apply_fixture(
            plan,
            source_save=Path(args.source_save),
            out_save=Path(args.out_dir) / args.save_basename,
            flag_bit=args.flag_bit,
        )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"runtime-policy: {result['runtime_policy']}")
        print(f"proof-class: {result['proof_class']}")
        print(f"dry-run: {result['dry_run']}")
        print(f"building-index: {result['building_index']}")
        print(f"addon-flags-offset: {result['addon_flags_file_offset']} ({result['addon_flags_file_offset_hex']})")
        print(f"observed-addon-flags-byte: {result['observed_addon_flags_byte']}")
        print(f"new-addon-flags-byte: {result['new_addon_flags_byte']}")
        print(f"out-save: {result['out_save']}")
        print(f"passed: {result['passed']}")
        if result.get("applied"):
            print(f"byte-before: {result['byte_before']}")
            print(f"byte-after: {result['byte_after']}")
            print(f"output-sha256: {result['output_sha256']}")
        if result["failures"]:
            print("failures:")
            for failure in result["failures"]:
                print(f"  - {failure}")

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
