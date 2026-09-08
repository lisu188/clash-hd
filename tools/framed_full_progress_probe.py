"""Bind separate full-paint entry/store/return observers; never execute CDB.

The canonical PTILE events remain unchanged, including every duplicate. These
extra observations distinguish instruction progress and native present flags;
they do not by themselves validate a trace or explain a debugger retrap.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from complete_hd_runtime_context import complete, verify_context
from framed_noop_progress_probe import inspect_breakpoints
from src.patcher import pe_extension as pe

ENTRY_VA = 0x418700
STATUS_STORE = bytes.fromhex("89442424619d833d9069520000")
RETURN_PREFIX = bytes.fromhex("8b45fc8b55f88990b8000000")
MARKERS = ("FRAMED_FULL_ENTRY", "FRAMED_FULL_POST_STORE", "FRAMED_FULL_RETURN")
LIMITS = [
    "Diagnostic only; unchanged PTILE traces and their failures remain authoritative.",
    "Startup armed and unfiltered. Compare only matching native calls in the observed MAP_READY..TRACE_CLOSED interval.",
    "Entry/stack addresses can be reused. Thread, entry/return order and caller must match before interpreting saved EBP.",
    "Saved EBP is the actual native present flag; zero alone is not proof of a completed omitted-present call.",
    "The post-store observer is before POPAD/POPFD. It proves this instruction boundary, not final presentation or return.",
    "A duplicated observer can itself be a debugger observation defect; no duplicates are removed or declared harmless.",
    "No input, visible composition, endurance or promotion acceptance is established.",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def analyze_progress(log: str, sites: dict) -> dict:
    """Keep every observation and report bounded completed native-call facts.

    This never changes the PTILE evaluator or turns diagnostics into a pass.
    Reused stacks require an observed return before the next matching entry.
    """
    lines = log.splitlines()
    ready = [i for i, line in enumerate(lines) if line.startswith("PTILE_MAP_READY ")]
    close = [i for i, line in enumerate(lines) if line.startswith("PTILE_TRACE_CLOSED ")]
    if len(ready) != 1 or len(close) != 1 or ready[0] >= close[0]:
        raise ValueError("full progress analysis needs one ordered ready/closure interval")
    pattern = re.compile(r"(?P<marker>FRAMED_FULL_ENTRY|FRAMED_FULL_POST_STORE|FRAMED_FULL_RETURN) "
        r"tid=(?P<tid>[0-9a-fA-F]{1,8}) eip=(?P<eip>[0-9a-fA-F]{8}) esp=(?P<esp>[0-9a-fA-F]{8}) "
        r"entry_esp=(?P<entry_esp>[0-9a-fA-F]{8}) caller=(?P<caller>[0-9a-fA-F]{8}) "
        r"saved_ebp=(?P<saved_ebp>[0-9a-fA-F]{8}) value=(?P<value>[0-9a-fA-F]{1,8}) trace_seq=(?P<trace_seq>[0-9]+)")
    records, calls, pending, failures = [], [], {}, []
    for index, line in enumerate(lines):
        if not any(line.startswith(marker) for marker in MARKERS):
            continue
        match = pattern.fullmatch(line)
        if not match:
            failures.append(f"line{index+1}: malformed full progress record")
            continue
        row = {name: value if name == "marker" else int(value, 10 if name == "trace_seq" else 16)
               for name, value in match.groupdict().items()}
        row.update(line=index+1, in_interval=ready[0] < index < close[0])
        records.append(row)
        if not row["in_interval"]:
            continue
        key = row["tid"], row["entry_esp"]
        if not row["tid"] or not row["entry_esp"] or row["entry_esp"] % 4:
            failures.append(f"line{index+1}: invalid thread/entry stack")
        marker = row["marker"]
        if marker == MARKERS[0]:
            if key in pending:
                failures.append(f"line{index+1}: entry repeats before observed return")
            call = dict(entry=row, posts=[], returns=[])
            calls.append(call)
            pending.setdefault(key, call)
            if row["eip"] != sites["entry"] or row["esp"] != row["entry_esp"]:
                failures.append(f"line{index+1}: entry site/stack differs")
            continue
        call = pending.get(key)
        if call is None:
            failures.append(f"line{index+1}: progress lacks matching native entry")
            continue
        entry = call["entry"]
        if row["caller"] != entry["caller"]:
            failures.append(f"line{index+1}: caller changed during native call")
        if marker == MARKERS[1]:
            call["posts"].append(row)
            if (row["eip"] != sites["post_store"] or row["esp"]+144 != row["entry_esp"] or
                    row["saved_ebp"] != entry["value"]):
                failures.append(f"line{index+1}: post-store site/stack/native present flag differs")
            if len(call["posts"]) != 1:
                failures.append(f"line{index+1}: post-store boundary repeats")
        else:
            call["returns"].append(row)
            if (row["eip"] != sites["returning"] or row["esp"]+52 != row["entry_esp"] or
                    row["saved_ebp"] != entry["saved_ebp"] or len(call["posts"]) != 1):
                failures.append(f"line{index+1}: return site/stack/caller EBP or progress differs")
            del pending[key]
    if pending:
        failures.append("native full calls remain without observed returns")
    return dict(records=records, calls=calls, failures=failures,
                observation_sequence_complete=bool(calls) and not failures,
                acceptance=False, promotion_ready=False, manual_input_proof=False,
                limits=LIMITS)


def observation_sites(image: bytes, framed: dict) -> dict:
    """Check exact emitted instruction spans before deriving stack expressions."""
    view = pe.inspect_pe(image)
    if view.image_base != 0x400000:
        raise ValueError("full progress diagnostic requires the reviewed fixed image base")
    layout = framed["layout_contract"]
    if (layout["full_entry_extra_stack_bytes"] != 60 or
            layout["full_status_to_caller_before_call"] != 148):
        raise ValueError("full progress wrapper stack contract differs")
    status = framed["status_vas"]["full_converge"]
    returning = layout["full_return_observer_va"]
    hook = framed["entry_vas"]["hook_framed_full_entry"]
    entry_jump = b"\xe9" + (hook - (ENTRY_VA + 5)).to_bytes(4, "little", signed=True) + b"\x90" * 4
    expected = ((ENTRY_VA, entry_jump, "installed full entry"),
                (ENTRY_VA+9, bytes.fromhex("89c5"), "native MOV EBP,EAX selects presentation"),
                (status, STATUS_STORE, "saved-status MOV followed by POPAD/POPFD and native CMP"),
                (returning, RETURN_PREFIX, "wrapper restores the saved map vtable after native return"))
    spans = []
    for va, data, purpose in expected:
        offset = view.file_offset(va - view.image_base, len(data))
        if image[offset:offset + len(data)] != data:
            raise ValueError(f"full progress observation bytes differ at {va:08x}")
        spans.append(dict(va=va, rva=va-view.image_base, offset=offset, bytes=data.hex(), purpose=purpose))
    return dict(entry=ENTRY_VA, status=status, post_store=status+4, returning=returning,
                spans=spans, status_stack_to_entry=144, return_stack_to_entry=52,
                return_ebp_to_entry=36, saved_native_ebp_offset=8, stored_status_offset=36)


def build_diagnostic(original: bytes, candidate: bytes, *, candidate_sha256: str,
                     stage: str, resolution: str, rendered_probe: str,
                     candidate_manifest: dict, first_breakpoint_id: int = 83) -> dict:
    if stage != complete.STAGE or not re.fullmatch(r"[0-9a-f]{64}", candidate_sha256 or ""):
        raise ValueError("full progress requires the exact complete stage and lowercase candidate SHA")
    if sha(candidate) != candidate_sha256:
        raise ValueError("full progress candidate SHA differs")
    if type(first_breakpoint_id) is not int or not 83 <= first_breakpoint_id <= 97:
        raise ValueError("three free diagnostic IDs are required within83..99")
    context = verify_context(candidate_manifest, original, resolution=resolution, candidate=candidate)
    text = rendered_probe.replace("\r\n", "\n")
    if "\r" in text or any(marker in text for marker in MARKERS):
        raise ValueError("full progress requires a new, unmodified main probe")
    if text.count(context["probe"].replace("\r\n", "\n").strip()) != 1:
        raise ValueError("full progress main lacks one unchanged canonical PTILE probe")
    inventories = [inspect_breakpoints(rendered_probe, breakpoint_id=value)
                   for value in range(first_breakpoint_id, first_breakpoint_id+3)]
    sites = observation_sites(candidate, context["framed"])
    declarations = inventories[0]["declarations"]
    existing = {int(row["va"], 16) for row in declarations}
    if any(sites[key] in existing for key in ("entry", "post_store", "returning")):
        raise ValueError("full progress observation instruction is already occupied")
    if not any(row["id"] == 70 and int(row["va"], 16) == sites["status"] for row in declarations):
        raise ValueError("canonical full-convergence observer70 is missing or moved")
    conditions, excluded = [], []
    for span in sites["spans"]:
        for index, expected in enumerate(bytes.fromhex(span["bytes"])):
            va = span["va"] + index
            if va in existing:
                excluded.append(va)
            else:
                conditions.append(f"(by({va:08x}) != {expected:02x})")
    rows = [".if (" + " | ".join(conditions) + ") { .echo FRAMED_FULL_PROGRESS_BYTE_REJECT; q }",
            f".echo FRAMED_FULL_PROGRESS_BOUND stage={stage} resolution={resolution} candidate_sha256={candidate_sha256} acceptance=false",
            ".echo FRAMED_FULL_PROGRESS_SCOPE observe_only startup_armed unfiltered manual_input_proof=false promotion_ready=false"]
    # No assignment to target/debugger registers, caller memory or trace counter.
    # At native entry E: return address[E], EAX selects presentation. The
    # verified native body copies EAX to EBP after saving the caller's EBP.
    # Hook status after CALL and PUSHFD/PUSHAD is E-144; saved native EBP[ESP+8].
    # Native return restores wrapper EBP=E-36 and ESP=E-52 before map-table restore.
    expressions = (
        (sites["entry"], "@$tid, @eip, @esp, @esp, poi(@esp), @ebp, @eax, @$t9"),
        (sites["post_store"], "@$tid, @eip, @esp, @esp+0n144, poi(@esp+0n144), poi(@esp+8), poi(@esp+0n36), @$t9"),
        (sites["returning"], "@$tid, @eip, @esp, @ebp+0n36, poi(@ebp+0n36), poi(@ebp+8), poi(@ebp-0n12), @$t9"),
    )
    for bp, marker, (va, arguments) in zip(range(first_breakpoint_id, first_breakpoint_id+3), MARKERS, expressions):
        rows.append(f'bp{bp} {va:08x} ".printf \\"{marker} tid=%x eip=%p esp=%p '
                    r'entry_esp=%p caller=%p saved_ebp=%p value=%x trace_seq=%u\\n\", '
                    + arguments + '; gc"')
    snippet = "\n".join(rows) + "\n"
    if any(len(line) >= 4096 for line in rows) or "PTILE_" in snippet:
        raise ValueError("full progress snippet exceeds command bounds or changes trace namespace")
    return dict(schema="clash95_framed_full_progress_v1", prepared=True, stage=stage,
                resolution=resolution, candidate_sha256=candidate_sha256, original_sha256=sha(original),
                candidate_manifest_sha256=sha((json.dumps(candidate_manifest, indent=2)+"\n").encode()),
                observation_sites=sites, breakpoint_ids=list(range(first_breakpoint_id, first_breakpoint_id+3)),
                value_semantics={MARKERS[0]: "native EAX presentation argument; saved_ebp is caller EBP",
                                 MARKERS[1]: "stored convergence result; saved_ebp is native presentation flag",
                                 MARKERS[2]: "uninterpreted native return EAX; saved_ebp is caller EBP"},
                excluded_existing_breakpoint_bytes=excluded, inventory=inventories[0],
                snippet_sha256=sha(snippet.encode("ascii")), snippet=snippet,
                acceptance=False, manual_input_proof=False, promotion_ready=False, limits=LIMITS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "candidate", "rendered-probe", "candidate-manifest"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("candidate-sha256", "stage", "resolution"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--first-breakpoint-id", type=int, default=83)
    args = parser.parse_args()
    try:
        report = build_diagnostic(args.original.read_bytes(), args.candidate.read_bytes(),
            candidate_sha256=args.candidate_sha256, stage=args.stage, resolution=args.resolution,
            rendered_probe=args.rendered_probe.read_bytes().decode("ascii"),
            candidate_manifest=json.loads(args.candidate_manifest.read_text(encoding="utf-8")),
            first_breakpoint_id=args.first_breakpoint_id)
        report["candidate_manifest_path"] = str(args.candidate_manifest.resolve())
        report["candidate_manifest_sha256"] = sha(args.candidate_manifest.read_bytes())
        report["producer_source_sha256"] = sha(Path(__file__).read_bytes())
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"full progress preparation failed: {error}\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
