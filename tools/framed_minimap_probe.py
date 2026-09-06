#!/usr/bin/env python3
"""Bind read-only minimap observers to an exact framed validation candidate.

Reconstructs candidate bytes in memory. Writes only new probe/report files;
never starts a debugger, changes the game, or grants runtime acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import build_framed_candidate as builder
from framed_noop_progress_probe import inspect_breakpoints


def sha(data):
    return hashlib.sha256(data).hexdigest()


GD = "poi(005202e4)"
STATE_ARGUMENTS = (f"by(00523f54), poi({GD}+222e0), poi({GD}+222e4), "
                   f"poi({GD}+222e8), poi({GD}+222ec)")
CAPTURE_ACTION = (r'.printf \"FRAMED_MINIMAP_VIEWPORT scale=%d world=(%d,%d) scroll=(%d,%d)\\n\", '
                  + STATE_ARGUMENTS + "; ")
INSERTION = r'.printf \"FRAMED_MINIMAP enabled='


def build_observed_probe(original: bytes, candidate: bytes, *, resolution: str,
                         rendered_probe: str) -> dict:
    image, metadata, canonical_extra = builder.build_candidate(
        original, resolution, minimap_viewport=True)
    if candidate != image:
        raise ValueError("candidate differs from exact minimap-enabled framed reconstruction")
    # The existing reader checks unique startup bc*, static declarations and
    # controls, bounded lines, a final g, and free explicit IDs independently.
    inventory = [inspect_breakpoints(rendered_probe, breakpoint_id=value) for value in (80, 81)]
    text = rendered_probe.replace("\r\n", "\n")
    if "\r" in text or text.count(canonical_extra.strip()) != 1:
        raise ValueError("rendered main lacks one unchanged canonical loaded-byte extra")
    if text.count(INSERTION) != 1 or "FRAMED_MINIMAP_VIEWPORT" in text or "FRAMED_MINIMAP_DRAW" in text:
        raise ValueError("missing, repeated or already observed minimap capture action")
    # The existing minimap statement is inside the producer's gameData/selector
    # checks. Do not append gameData reads to an arbitrary standalone printf.
    capture_lines = [line for line in text.splitlines() if INSERTION in line]
    if (len(capture_lines) != 1 or not capture_lines[0].startswith('bp 00406FA0 "') or
            '.if (poi(005202e4) == 0)' not in capture_lines[0] or
            'FRAMED_CAPTURE_REJECT missing_game_data' not in capture_lines[0] or
            'PTILE_TRACE_CLOSED' not in capture_lines[0] or
            'SURFDUMP_HOST_READY' not in capture_lines[0]):
        raise ValueError("minimap state reads require the guarded paused update capture")
    observers = metadata["minimap_viewport_contract"]["observers"]
    if set(observers) != {"memory", "primary"} or len(set(observers.values())) != 2:
        raise ValueError("invalid emitted minimap observation contract")
    existing_sites = {int(row["va"], 16) for row in inventory[0]["declarations"]}
    rows = [f".echo FRAMED_MINIMAP_OBSERVER_BOUND stage={builder.STAGE} resolution={resolution} "
            f"candidate_sha256={sha(candidate)}"]
    bindings = []
    for bp, name in zip((80, 81), ("memory", "primary")):
        va = observers[name]
        if type(va) is not int or va in existing_sites:
            raise ValueError("emitted observer overlaps an existing breakpoint")
        offset = builder.clip.file_offset(candidate, va, 5)
        if candidate[offset] != 0xE8:
            raise ValueError("minimap observation must precede its direct native CALL")
        row = (f'bp{bp} {va:08x} ".printf \\"FRAMED_MINIMAP_DRAW target=%p rect=(%d,%d,%d,%d) '
               r'color=%x tid=%x scale=%d world=(%d,%d) scroll=(%d,%d)\\n\", '
               '@eax, @edx, @ebx, @ecx, poi(@esp), poi(@esp+4), @$tid, '
               + STATE_ARGUMENTS + '; gc"')
        rows.append(row)
        bindings.append(dict(name=name, breakpoint=bp, va=va, native_call_hex=candidate[offset:offset+5].hex()))
    snippet = "\n".join(rows) + "\n"
    lines = text.rstrip("\n").splitlines()
    if not lines or lines[-1].strip() != "g":
        raise ValueError("main probe must end in its single standalone g")
    observed = "\n".join(lines[:-1]) + "\n" + snippet + "g\n"
    observed = observed.replace(INSERTION, CAPTURE_ACTION + INSERTION)
    if any(len(line) >= 4096 for line in observed.splitlines()):
        raise ValueError("observed probe exceeds bounded CDB line length")
    return dict(schema="clash95_framed_minimap_observer_v1", stage=builder.STAGE,
                resolution=resolution, candidate_sha256=sha(candidate),
                original_sha256=sha(original), canonical_extra_sha256=sha(canonical_extra.encode("ascii")),
                source_main_sha256=sha(rendered_probe.encode("ascii")),
                source_main_lf_sha256=sha(text.encode("ascii")),
                observed_main_sha256=sha(observed.encode("ascii")),
                observer_bindings=bindings, snippet=snippet, capture_action=CAPTURE_ACTION,
                probe=observed, runtime_executed=False, acceptance=False,
                manual_input_proof=False, promotion_ready=False,
                limits="Read-only drawn coordinates and paused state. The surrounding main probe remains a bound producer input; this does not independently reconstruct every original harness command.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "candidate", "rendered-probe", "output", "report"):
        parser.add_argument("--"+name, required=True, type=Path)
    parser.add_argument("--resolution", required=True)
    args = parser.parse_args()
    outputs = [args.output.resolve(), args.report.resolve()]
    inputs = {p.resolve() for p in (args.original, args.candidate, args.rendered_probe)}
    if len(set(outputs)) != 2 or any(p in inputs or p.exists() for p in outputs):
        parser.error("distinct new output files required; existing artifacts are preserved")
    packet = build_observed_probe(args.original.read_bytes(), args.candidate.read_bytes(),
                                  resolution=args.resolution,
                                  rendered_probe=args.rendered_probe.read_bytes().decode("ascii"))
    packet["producer_source_sha256"] = sha(Path(__file__).read_bytes())
    packet["source_main_path"] = str(args.rendered_probe.resolve())
    packet["observed_main_path"] = str(args.output.resolve())
    with args.output.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(packet["probe"])
    with args.report.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump({k: v for k, v in packet.items() if k != "probe"}, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"observed_main_sha256": packet["observed_main_sha256"],
                      "candidate_sha256": packet["candidate_sha256"], "runtime_executed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
