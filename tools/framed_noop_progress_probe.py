#!/usr/bin/env python3
"""Prepare a separate read-only native post-ADD diagnostic; never run CDB.

Supply the COMPLETE rendered surface probe to check breakpoint availability.
The returned snippet belongs after its declarations and before its final g.
Do not append it to the canonical numbered extra probe passed to the strict
trace validator: that file and every existing breakpoint command stay intact.

Native418A90 pushes five registers and reserves8 bytes. At418AFA the stack is
entryESP-28; ADD ESP,8 reaches418AFD with entryESP-20, before the five POPs and
RET. The read-only marker records that site, not proof of RET or acceptance.
It is armed from startup and keeps pre-readiness observations. Compare only
the actual MAP_READY..TRACE_CLOSED interval for the current initial-paint lane.
Repeated pre-ADD records still fail the existing gate; never deduplicate them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import build_framed_candidate as builder

STAGE = builder.STAGE
PRE_ADD_VA = 0x418AFA
POST_ADD_VA = 0x418AFD
NATIVE_ENTRY_VA = 0x418A90
EPILOGUE = bytes.fromhex("83c4085d5f5e595bc3")
PROLOGUE = bytes.fromhex("535156575583ec08")
MARKER = "FRAMED_NOOP_POST_ADD"
_BP = re.compile(r'bp\s*(?:(?P<id>[0-9]{1,3})\s+)?(?P<va>[0-9a-f]{8})\s+"(?P<body>(?:\\.|[^"\\])*)"', re.I)
_CONTROL = re.compile(r'(?:^|[;{}])\s*(?P<op>b[dec])\s+(?P<ids>[^;{}]+)', re.I)
LIMITS = [
    "Diagnostic only: no runtime, rendering, return, input, endurance or promotion acceptance.",
    "Keep the original numbered extra probe and all raw records unchanged; repeated pre-ADD observations remain failures.",
    "Armed from startup with no filtering; pre-readiness observations remain outside the initial-paint comparison interval.",
    "A post-ADD stop observes EIP/ESP before POPs, not completion of the native RET or an explanation of debugger retraps.",
    "The current fixed image-base lane and separate full loaded-image gate remain required; this snippet rechecks only its native span and installed entry hook.",
    "Already-declared breakpoint bytes are explicitly excluded from the second live byte read; exact reconstruction and the unchanged earlier canonical byte gate still bind them.",
    "The read-only trace_seq is shared debugger provenance, not a new native invocation identifier or per-thread counter.",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_breakpoints(rendered_probe: str, *, breakpoint_id: int = 80) -> dict:
    """Fail closed on collisions or dynamic declarations in this bounded lane.

    This inventories a generated, single command-file startup; it is not a
    general CDB program analyzer or authorization of its existing commands.
    Explicit IDs and lowest-free implicit IDs are both retained. No existing
    breakpoint is cleared, disabled, rewritten or hidden by this helper.
    """
    if type(breakpoint_id) is not int or not 80 <= breakpoint_id <= 99:
        raise ValueError("diagnostic breakpoint ID must be an integer in80..99")
    if (not isinstance(rendered_probe, str) or not rendered_probe.isascii()
            or "\x00" in rendered_probe or MARKER in rendered_probe.upper()):
        raise ValueError("rendered probe must be new non-NUL ASCII text")
    lines = rendered_probe.splitlines()
    substantive = [line for line in lines if line.strip()]
    if not substantive or substantive[-1].strip() != "g":
        raise ValueError("complete rendered probe must end in its standalone startup g")
    if sum(line.strip() == "g" for line in lines) != 1:
        raise ValueError("unsupported early startup continuation")
    if sum(line.strip().lower() == "bc *" for line in lines) != 1:
        raise ValueError("rendered startup must have one initial bc *")
    occupied, sites, declarations = set(), set(), []
    cleared = False
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if len(raw) >= 4096:
            raise ValueError(f"line{number}: exceeds bounded command length")
        if line.lower() == "bc *":
            if declarations:
                raise ValueError("breakpoint clearing must precede all declarations")
            cleared = True
            continue
        if "$$><" in line or re.search(r'\.(?:script\w*|cmdtree|foreach|for)\b', line, re.I):
            raise ValueError("dynamic command files/loops cannot establish breakpoint availability")
        match = _BP.fullmatch(line)
        if match:
            if not cleared:
                raise ValueError("breakpoint declaration precedes initial clear")
            selected = (int(match["id"]) if match["id"] is not None
                        else next(index for index in range(1000) if index not in occupied))
            va = int(match["va"], 16)
            if selected in occupied or not va or va in sites:
                raise ValueError("duplicate breakpoint ID or site")
            if selected == breakpoint_id or POST_ADD_VA <= va < PRE_ADD_VA + len(EPILOGUE):
                raise ValueError("diagnostic breakpoint ID or post-ADD site already occupied")
            occupied.add(selected)
            sites.add(va)
            declarations.append(dict(line=number, id=selected, va=f"{va:08x}"))
            commands = match["body"]
            if re.search(r'(?:^|[;{}])\s*(?:bp|bu|bm|ba)(?:\s|[0-9])', commands, re.I):
                raise ValueError("nested breakpoint declarations are unsupported")
        else:
            commands = line
            if re.match(r'(?:bp|bu|bm|ba)(?:\s|[0-9])', line, re.I):
                raise ValueError("unsupported breakpoint declaration")
        for control in _CONTROL.finditer(commands):
            ids = control["ids"].strip().split()
            if control["op"].lower() == "bc" or any(not token.isdecimal() for token in ids):
                raise ValueError("dynamic/wildcard/clearing breakpoint controls are unsupported")
            if breakpoint_id in map(int, ids):
                raise ValueError("existing command controls the proposed diagnostic breakpoint")
    if not declarations:
        raise ValueError("complete rendered probe lacks breakpoint declarations")
    return dict(breakpoint_id=breakpoint_id, occupied_ids=sorted(occupied), declarations=declarations,
                rendered_probe_sha256=sha(rendered_probe.encode("ascii")),
                insertion="after all existing declarations and immediately before the final standalone g")


def _span(image: bytes, va: int, size: int) -> tuple[int, bytes]:
    pe = builder.pe.inspect_pe(image)
    if pe.image_base != 0x400000:
        raise ValueError("only the reviewed fixed image-base diagnostic lane is supported")
    offset = pe.file_offset(va - pe.image_base, size)
    return offset, image[offset:offset + size]


def build_diagnostic(original: bytes, candidate: bytes, *, candidate_sha256: str,
                     stage: str, resolution: str, rendered_probe: str,
                     breakpoint_id: int = 80) -> dict:
    if stage != STAGE:
        raise ValueError("stage must equal the exact reviewed framed validation stage")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", candidate_sha256 or ""):
        raise ValueError("candidate SHA-256 must contain exactly64 hexadecimal digits")
    if sha(candidate) != candidate_sha256.lower():
        raise ValueError("candidate SHA-256 mismatch")
    # The builder verifies the known original, every source pin, and all hooks,
    # scalars, payload and relocation bytes; no candidate file is written here.
    reconstructed, _, canonical_extra = builder.build_candidate(original, resolution)
    if reconstructed != candidate:
        raise ValueError("candidate differs from exact framed reconstruction")
    inventory = inspect_breakpoints(rendered_probe, breakpoint_id=breakpoint_id)
    normalized = rendered_probe.replace("\r\n", "\n")
    if normalized.count(canonical_extra.replace("\r\n", "\n").strip()) != 1:
        raise ValueError("rendered probe must contain exactly one unchanged canonical extra probe")
    if _span(original, NATIVE_ENTRY_VA, len(PROLOGUE))[1] != PROLOGUE:
        raise ValueError("native five-push/local-stack prologue differs")
    for image in (original, candidate):
        if _span(image, PRE_ADD_VA, len(EPILOGUE))[1] != EPILOGUE:
            raise ValueError("native ADD/POP/RET observation bytes differ")
    # Cover the patched entry jump and complete early-return decision block.
    # Candidate reconstruction authenticates scalar differences in this block.
    spans = []
    for va, size, purpose in ((NATIVE_ENTRY_VA, len(PROLOGUE), "installed incremental entry"),
                              (NATIVE_ENTRY_VA + len(PROLOGUE), 0x418B03 - 0x418A98,
                               "native decision block and ADD/POP/RET")):
        offset, data = _span(candidate, va, size)
        spans.append(dict(va=f"{va:08x}", rva=f"{va - 0x400000:08x}",
                          offset=offset, bytes=data.hex(), purpose=purpose))
    rows = []
    # Existing software breakpoints may have replaced their first opcode with
    # INT3. Do not clear them or assume by() synthesizes original instruction
    # bytes. The unchanged canonical extra already checked these bytes before
    # declaring its numbered observers. The unoccupied post-ADD span is always
    # rechecked in full here, and candidate reconstruction covers every byte.
    declared_sites = {int(row["va"], 16) for row in inventory["declarations"]}
    conditions, existing_breakpoint_bytes = [], []
    for span in spans:
        for index, value in enumerate(bytes.fromhex(span["bytes"])):
            va = int(span["va"], 16) + index
            if va in declared_sites:
                existing_breakpoint_bytes.append(dict(va=f"{va:08x}", expected_byte=f"{value:02x}",
                                                     reason="existing breakpoint; prior canonical gate retained"))
            else:
                conditions.append(f"(by({va:08x}) != {value:02x})")
    for index in range(0, len(conditions), 64):
        rows.append(".if (" + " | ".join(conditions[index:index + 64])
                    + ") { .echo FRAMED_NOOP_DIAGNOSTIC_BYTE_REJECT; q }")
    rows.append(f".echo FRAMED_NOOP_DIAGNOSTIC_BOUND stage={stage} resolution={resolution} "
                f"candidate_sha256={candidate_sha256.lower()} breakpoint={breakpoint_id} acceptance=false")
    rows.append(".echo FRAMED_NOOP_DIAGNOSTIC_SCOPE observe_only startup_armed unfiltered manual_input_proof=false promotion_ready=false")
    rows.append(f'bp{breakpoint_id} {POST_ADD_VA:08x} ".printf \\"{MARKER} tid=%x eip=%p esp=%p '
                'world=(%d,%d) caller=%p entry_esp=%p trace_seq=%u\\\\n\\", '
                '@$tid, @eip, @esp, @eax, @edx, poi(@esp+0n20), @esp+0n20, @$t9; gc"')
    snippet = "\n".join(rows) + "\n"
    if any(len(row) >= 4096 for row in rows) or "PTILE_" in snippet.upper():
        raise ValueError("invalid diagnostic command size or trace namespace")
    return dict(schema="clash95_framed_noop_progress_diagnostic_v1", prepared=True,
                acceptance=False, manual_input_proof=False, promotion_ready=False,
                original_sha256=sha(original), candidate_sha256=candidate_sha256.lower(),
                stage=stage, resolution=resolution, image_base="00400000",
                observation=dict(va=f"{POST_ADD_VA:08x}", marker=MARKER,
                                 pre_add_stack_to_entry=28, post_add_stack_to_entry=20,
                                 instruction="POP EBP, after ADD ESP,8 and before any POP"),
                byte_spans=spans, already_declared_breakpoint_bytes=existing_breakpoint_bytes,
                inventory=inventory, snippet_sha256=sha(snippet.encode("ascii")),
                snippet=snippet, limits=LIMITS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--rendered-probe", type=Path, required=True)
    parser.add_argument("--breakpoint-id", type=int, default=80)
    parser.add_argument("--json", action="store_true", help="emit binding metadata and snippet as JSON")
    args = parser.parse_args()
    try:
        report = build_diagnostic(args.original.read_bytes(), args.candidate.read_bytes(),
                                  candidate_sha256=args.candidate_sha256, stage=args.stage,
                                  resolution=args.resolution,
                                  rendered_probe=args.rendered_probe.read_bytes().decode("ascii"),
                                  breakpoint_id=args.breakpoint_id)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"diagnostic preparation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2) if args.json else report["snippet"], end="\n" if args.json else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
