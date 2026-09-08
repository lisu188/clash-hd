"""Reconstruct the complete candidate before binding offline runtime consumers.

This authenticates producer inputs, never supplies runtime or promotion proof.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import complete_hd_candidate as complete


def verify_context(manifest: dict, original: bytes, *, resolution: str,
                   candidate: bytes | None = None, probe: str | None = None,
                   builder=None) -> dict:
    if manifest.get("stage") != complete.STAGE or manifest.get("resolution") != resolution:
        raise ValueError("complete candidate manifest stage or resolution differs")
    image, rebuilt, canonical_probe = (builder or complete.build_candidate)(original, resolution)
    # JSON is the interchange contract; predecessor tuples become JSON arrays.
    if manifest != json.loads(json.dumps(rebuilt)):
        raise ValueError("complete candidate manifest differs from exact source reconstruction")
    if candidate is not None and candidate != image:
        raise ValueError("complete candidate bytes differ from exact source reconstruction")
    if probe is not None and probe != canonical_probe:
        raise ValueError("complete candidate probe differs from exact source reconstruction")
    predecessor = rebuilt.get("predecessor", {})
    framed = predecessor.get("base_candidate", {}).get("base_candidate")
    return {"manifest": rebuilt, "candidate": image, "probe": canonical_probe,
            "framed": framed, "inherited_stage": predecessor.get("stage")}


def load_context(manifest_path: Path, original_path: Path, *, resolution: str,
                 candidate: bytes | None = None, probe: str | None = None) -> dict:
    from complete_hd_evidence import candidate_manifest_context
    verified = candidate_manifest_context(manifest_path, base_executable=original_path)
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if verified["identity"]["resolution"] != resolution:
        raise ValueError("complete candidate context resolution differs")
    image = Path(verified["candidate_path"]).read_bytes()
    probe_bytes = Path(verified["probe_path"]).read_bytes()
    for data, name in ((manifest_bytes, "metadata_sha256"), (image, "candidate_sha256"),
                       (probe_bytes, "probe_sha256")):
        if complete.sha256(data) != verified["identity"][name]:
            raise ValueError("complete candidate bundle changed while loading verified context")
    canonical_probe = probe_bytes.decode("utf-8")
    if candidate is not None and image != candidate:
        raise ValueError("complete candidate context bytes differ")
    if probe is not None and canonical_probe != probe:
        raise ValueError("complete candidate context probe differs")
    context = {"manifest": manifest, "candidate": image, "probe": canonical_probe,
               "framed": manifest["predecessor"]["base_candidate"]["base_candidate"],
               "inherited_stage": manifest["predecessor"]["stage"]}
    context["manifest_path"] = str(manifest_path.resolve())
    context["manifest_sha256"] = complete.sha256(manifest_bytes)
    return context


def loaded_contract_failures(log: str, probe: str, context: dict) -> list[str]:
    manifest = context["manifest"]
    identity = (f"resolution={manifest['resolution']} "
                f"candidate_sha256={manifest['candidate_sha256']}")
    contracts = (
        f"COMPLETEHD_CONTRACT_PASS stage={complete.STAGE} {identity} revision={manifest['recipe_revision']}",
        f"ARMY_CONTRACT_PASS stage={context['inherited_stage']} {identity} revision={manifest['predecessor']['army_revision']}",
        f"PTILE_CONTRACT_PASS stage={context['inherited_stage']} {identity}",
    )
    lines, probe_lines = log.splitlines(), probe.splitlines()
    failures, locations = [], []
    for contract in contracts:
        prefix = contract.split()[0]
        matching = [i for i, line in enumerate(lines) if line.startswith(prefix)]
        if len(matching) != 1 or lines[matching[0]] != contract:
            failures.append(f"missing, repeated or mismatched {prefix}")
        else:
            locations.append(matching[0])
        if probe_lines.count(".echo " + contract) != 1:
            failures.append(f"canonical probe lacks exact {prefix}")
    # Army loaded-byte checks precede complete identity and the PTILE observer.
    if len(locations) == 3 and not locations[1] < locations[0] < locations[2]:
        failures.append("complete loaded contracts are out of order")
    if any(line.startswith(("ARMY_CONTRACT_FAIL", "MCANVAS_CONTRACT_FAIL",
                            "COMPLETEHD_CONTRACT_FAIL", "PTILE_CONTRACT_FAIL", "PTILE_REJECT"))
           for line in lines):
        failures.append("loaded-byte contract rejected the complete candidate")
    return failures
