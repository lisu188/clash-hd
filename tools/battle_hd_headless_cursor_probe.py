"""Build an additive, read-only cursor observer for the fixed 0EDEF candidate.

No process is launched. The output is an ExtraProbeTemplate for the existing
headless surface-dump harness, including its unchanged forced lifecycle fixture.
That fixture and the base harness mutate state and bypass initial acquisition;
the separately delimited observer only reads registers, code, stack and data.
It cannot establish authentic input, visible rendering, or acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
CANDIDATE_SHA = "0edef38dac3c5036c6012adde248bc57736273cc1bbcbb9fd05e5867a1946ca0"
PROTOCOL = "expanded_battle_headless_cursor_v2"
STAGE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd"
LIFECYCLE = ROOT / "probes/cdb/battle/clash95_battle_hd_lifecycle_extra.cdb"
BASE = ROOT / "probes/cdb/render/clash95_surface_dump_probe.cdb"
HARNESS = ROOT / "scripts/cdb/run_cdb_surface_dump.ps1"
DEPENDENCIES = (
    # Enumerate the reviewed Windows checkout and Git LF blob separately.
    # Hash raw bytes and record the observed form; never normalize before checking.
    (LIFECYCLE, ("1a17fe974d955f4ed75ea2af1c6768c2cfc0911dacbe954df14bf684425e6843",
                 "11874021279d5bd19902bced8f7563cdfdddbff835a15e510f3f71fda2b85a17")),
    (BASE, ("6346ca89d5c3e8b63fbb6c96839c48920aa9eb039523f49b442f7fc47fef7df8",)),
    (HARNESS, ("01fbee7aeacceb6237fcf42fae84aa7d0c1912aba85fadc2fbab030c2b1475a8",)),
)
CALLERS = (0x42DA46, 0x42DE6E, 0x566533)
# Full source hook spans are checked independently of the candidate identity.
SOURCE_HOOKS = (
    (0x460A61, "a1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28"),
    (0x460E11, "68e0010000c7402000000000b9800200008b463c31db31d2c7401c0000000089f0e8e9fcffff"),
)
# Original-backed native ABI, callback and relative DIDATAFORMAT contracts.
NATIVE = (
    (0x42E8B0, "5351525657b8c0d45100"),
    (0x460AF0, "5181e2ffff00008b8854040000d3e289502431d28b88540400006689dad3e2895028"),
    (0x460B12, "31d2e8b7faffff59c3"),
    (0x4605D0, "535156575583ec08"),
    (0x46060E, "ff5114"),
    (0x460A50, "535152565789c2b898515400e86fb50100"),
    (0x460A87, "f605c0515400807544f605c851540080740483422c028b42248b4a1039c87d03894a24"),
    (0x47BFD0, "53515283ec6089c3"),
    (0x47C01C, "8d542450528b40086a108b0850ff51243d1e00078075098b4308508b10ff521c"),
    (0x47C03C, "8b4424508943108b442454894314"),
    (0x4612E0, "53515256575589c683b868040000000f84e3010000"),
    (0x4614D8, "e873f5ffff5d5f5e5a595bc3"),
    (0x50F218, "e0124600"),
    (0x4E80F0, "180000001000000002000000100000000700000080804e00"),
)
PATCHED = (
    (0x460A61, "e99a2a1000" + "90" * 33),
    (0x460E11, "e9ea251000" + "90" * 33),
    (0x563400, "813dd8995100b0e842007415813dd8995100a01746007518833d4820530000740f68d0020000b900050000e9ae65f8ffe98b65f8ff"),
    (0x563500, "813dd8995100b0e842007415813dd8995100a01746007534833d4820530000742ba1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28e93bd5efffe9bf62f8ff"),
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_va(raw: bytes, va: int, size: int) -> bytes:
    """Read file-backed PE32 bytes through the section table, never VA-offset guesses."""
    if len(raw) < 0x40 or raw[:2] != b"MZ":
        raise ValueError("not an MZ image")
    pe = struct.unpack_from("<I", raw, 0x3C)[0]
    if pe + 84 > len(raw) or raw[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE image")
    count, optional = struct.unpack_from("<H", raw, pe + 6)[0], struct.unpack_from("<H", raw, pe + 20)[0]
    if struct.unpack_from("<H", raw, pe + 24)[0] != 0x10B:
        raise ValueError("not PE32")
    rva = va - struct.unpack_from("<I", raw, pe + 52)[0]
    table = pe + 24 + optional
    if table + count * 40 > len(raw) or size <= 0:
        raise ValueError("invalid PE sections or read size")
    for index in range(count):
        section_rva, raw_size, offset = struct.unpack_from("<III", raw, table + 40 * index + 12)
        if section_rva <= rva and rva + size <= section_rva + raw_size:
            start = offset + rva - section_rva
            if start + size <= len(raw):
                return raw[start:start + size]
    raise ValueError(f"VA {va:08x} is not file-backed")


def verify_bytes(raw: bytes, contracts, label: str) -> None:
    for va, expected in contracts:
        data = bytes.fromhex(expected)
        if read_va(raw, va, len(data)) != data:
            raise ValueError(f"{label} byte mismatch at {va:08x}")


def guard(va: int, expected: str) -> str:
    data = bytes.fromhex(expected)
    terms = []
    for offset in range(0, len(data), 2):
        part = data[offset:offset + 2]
        accessor = "wo" if len(part) == 2 else "by"
        terms.append(f"({accessor}({va + offset:08x}) != 0x{int.from_bytes(part, 'little'):04x})")
    # Word/byte comparisons avoid MASM's high-bit DWORD sign extension.
    return f".if ({' | '.join(terms)}) {{ .echo BHDH_CURSOR_FAIL bytes_{va:08x}; q }}"


def caller_filter(offset: int) -> str:
    return "(" + " | ".join(f"(poi(@esp+0x{offset:x}) == {caller:08X})" for caller in CALLERS) + ")"


def chain(offsets) -> str:
    return " & ".join(f"(poi(@esp+0x{offset:x}) == {value:08X})" for offset, value in offsets)


def observer_breakpoints() -> list[str]:
    rows = []

    def add(va, name, offset, condition, fields, args):
        body = (f".if ({condition} & {caller_filter(offset)}) {{ .printf "
                f'\\"BHDH_CURSOR_{name} caller=%p tid=%x cursor_sp=%p eip=%p esp=%p owner=%p battle=%p {fields}\\\\n\\", '
                f"poi(@esp+0x{offset:x}), @$tid, @esp+0x{offset:x}, @eip, @esp, poi(005199d8), poi(00532048), {args}; }}; gc")
        rows.append(f'bp{100 + len(rows)} {va:08X} "{body}"')

    logical = "poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c)"
    values = "poi(005451a8), poi(005451ac), poi(00544cfc), poi(00544d00), poi(00544cf8), by(0054512c), poi(00544ce8), poi(00544cec), poi(00544cf0), poi(00544cf4)"
    fields = "raw=(%p,%p) shifted=(%p,%p) sensitivity=%p shift=%d bounds=(%p,%p,%p,%p)"
    add(0x460AF0, "ENTRY", 0, "(@eax == 00544CD8)", "requested=(%d,%d) prior=(%d,%d)", f"(@edx & 0xffff), (@ebx & 0xffff), {logical}")
    add(0x47C029, "DEVICE_CALL", 0xD4,
        "(@ebx == 00545198) & (poi(@esp+4) == 0n16) & (poi(@esp+8) == (@esp+0x5c)) & " + chain(((0x78, 0x460A61), (0x90, 0x4614DD), (0xAC, 0x460611), (0xCC, 0x460B19))),
        "device=%p length=%d buffer=%p before=(%p,%p,%p,%p)", "poi(@esp), poi(@esp+4), poi(@esp+8), poi(@esp+0x5c), poi(@esp+0x60), poi(@esp+0x64), poi(@esp+0x68)")
    add(0x47C02C, "DEVICE_RETURN", 0xC8,
        "(@ebx == 00545198) & " + chain(((0x6C, 0x460A61), (0x84, 0x4614DD), (0xA0, 0x460611), (0xC0, 0x460B19))),
        "hresult=%p buffer=%p after=(%p,%p,%p,%p)", "@eax, @esp+0x50, poi(@esp+0x50), poi(@esp+0x54), poi(@esp+0x58), poi(@esp+0x5c)")
    helper_condition = "(@edx == 00544CD8) & " + chain(((0x14, 0x4614DD), (0x30, 0x460611), (0x50, 0x460B19)))
    for va, name in ((0x563500, "HELPER_ENTRY"), (0x563547, "RELATIVE_APPLIED"), (0x56354C, "LEGACY_BRANCH"), (0x460A87, "PRE_CLAMP")):
        add(va, name, 0x58, helper_condition, fields, values)
    add(0x460B1A, "RETURN", 0, "1", "logical=(%d,%d) " + fields, f"{logical}, {values}")
    return rows


def verify_sources() -> dict:
    records = {}
    for path, accepted in DEPENDENCIES:
        raw = path.read_bytes()
        actual = sha256(raw)
        if actual not in accepted:
            raise ValueError(f"dependency SHA mismatch: {path.relative_to(ROOT)}")
        records[str(path.relative_to(ROOT))] = {"sha256": actual, "bytes": len(raw)}
    return records


def verify_inventory(observer: list[str], lifecycle: str, base: str, harness: str) -> dict:
    pattern = r"\bbp(\d*) ([0-9a-fA-F]{8}) "
    old = re.findall(pattern, base + "\n" + lifecycle)
    # The pinned harness inserts at most five startup breakpoints. Scan their
    # literal definitions too, including the alternative one-BP skip mode.
    start = harness.index("$startAnimsBreakpoint =")
    end = harness.index("$probeText = $probeText.Replace('__START_ANIMS_BP__'", start)
    startup = re.findall(pattern, harness[start:end])
    new = re.findall(pattern, "\n".join(observer))
    new_addresses = [int(va, 16) for _, va in new]
    if len(new_addresses) != len(set(new_addresses)):
        raise ValueError("duplicate observer address")
    if set(new_addresses) & {int(va, 16) for _, va in old + startup}:
        raise ValueError("observer collides with inherited breakpoint")
    if len(old) + len(startup) >= 100 or any(int(i) >= 100 for i, _ in old + startup if i):
        raise ValueError("inherited breakpoint IDs reach observer reservation")
    if len(new) != 8 or [int(i) for i, _ in new] != list(range(100, 108)):
        raise ValueError("unexpected observer ID reservation")
    return {"observer_ids": list(range(100, 108)), "observer_addresses": [f"{x:08x}" for x in new_addresses], "inherited_bp_upper_bound": len(old) + len(startup)}


def build(original: bytes, candidate: bytes) -> tuple[str, dict]:
    if sha256(original) != ORIGINAL_SHA:
        raise ValueError("original SHA mismatch")
    if sha256(candidate) != CANDIDATE_SHA:
        raise ValueError("candidate SHA mismatch")
    verify_bytes(original, NATIVE + SOURCE_HOOKS, "original")
    verify_bytes(candidate, NATIVE + PATCHED, "candidate")
    dependencies = verify_sources()
    lifecycle, base, harness = (path.read_text(encoding="utf-8") for path in (LIFECYCLE, BASE, HARNESS))
    observer = observer_breakpoints()
    inventory = verify_inventory(observer, lifecycle, base, harness)
    header = [
        ".echo === BHDH cursor diagnostic for exact candidate 0EDEF ===",
        f".echo BHDH_CURSOR_CANDIDATE sha256={CANDIDATE_SHA}",
        ".echo BHDH_CURSOR_CLASS hidden_forced_lifecycle_acquisition_bypassed_not_authentic_input",
        ".echo BHDH_CURSOR_OBSERVER read_only_no_shared_scratch_state",
    ]
    # Check loaded code before installing lifecycle breakpoints within these
    # spans. Preserve the inherited lifecycle text and its implicit BP order.
    probe = "\n".join(header + [guard(va, raw) for va, raw in NATIVE + PATCHED]) + "\n"
    probe += lifecycle.rstrip() + "\n.echo === BHDH read-only observer begin ===\n"
    probe += "\n".join(observer) + "\n.echo === BHDH read-only observer end ===\n"
    if max(map(len, probe.splitlines())) >= 4095:
        raise ValueError("CDB command line exceeds bound")
    manifest = {
        "schema": 1, "protocol": PROTOCOL, "status": "prepared_not_run", "candidate_sha256": CANDIDATE_SHA,
        "original_sha256": ORIGINAL_SHA, "stage": STAGE, "resolution": [1280, 720],
        "environment": "hidden_cdb_host", "route_class": "forced_lifecycle_fixture",
        "observer_class": "read_only_native_device_result_and_cursor_helper",
        "initial_acquisition": "bypassed_by_inherited_base_harness",
        "input_responsiveness": "not_applicable_hidden", "visible_acceptance": False,
        "manual_input_proof": False, "promotion_ready": False,
        "runtime_result": None, "dependencies": dependencies,
        "inventory": inventory, "loaded_guard_spans": len(NATIVE + PATCHED),
        "source_hook_spans": len(SOURCE_HOOKS),
        "record_identity": ["caller", "tid", "cursor_sp"],
        "expected_callers": {"banner": "0042da46", "modal": "0042de6e", "results": "00566533"},
        "observation_limit": "Exact three cursor call sites and native stack chains within finite lifecycle fixture; host deadline remains required.",
        "interpretation": "A failing HRESULT does not establish valid relative deltas. RELATIVE_APPLIED observes helper execution, PRE_CLAMP precedes native clamping, RETURN follows native polling. Missing records remain missing evidence.",
    }
    return probe, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-exe", type=Path, required=True)
    parser.add_argument("--candidate-exe", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="new directory outside the repository")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.is_relative_to(ROOT):
        parser.error("generated probe packets belong outside the repository")
    probe, manifest = build(args.source_exe.read_bytes(), args.candidate_exe.read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    probe_path = output / "battle-hd-headless-cursor-extra.cdb"
    probe_bytes = probe.encode("ascii")
    probe_path.write_bytes(probe_bytes)
    manifest.update({"probe": {"path": str(probe_path), "sha256": sha256(probe_bytes)}, "producer": {"path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__).read_bytes())}, "original_path": str(args.source_exe.resolve()), "candidate_path": str(args.candidate_exe.resolve())})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "extra_probe_template": str(probe_path), "manifest": str(output / "manifest.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
