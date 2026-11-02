#!/usr/bin/env python3
"""Prove the canonical probe composer against the legacy inline PowerShell.

Windows-only and repo-only: extracts the composition block verbatim from
run_hidden_soak.ps1 at the last commit that composed inline, swaps only its
frames-directory raw-path call for a parameter, and runs it under Windows
PowerShell as string composition (no game, CDB, proxy, wrapper or capture).
Every parameter set in tools/test_hidden_soak_probe_composition.py is composed
from the repository templates and the test's synthetic templates, and each
legacy output must equal compose_probe() byte for byte. Rerun this after any
probe template change and commit the new receipt.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hidden_soak_probe_composition as composition

LEGACY_COMMIT = "b800d45df96be224fb02af67fa42e3f80fbfee3a"
LEGACY_SCRIPT = "scripts/cdb/run_hidden_soak.ps1"
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
RAW_PATH_CALL = "(Get-FullPath -Path (Join-Path $framesDir 'surface.raw'))"
TEMPLATES = {"probe_template": "probes/cdb/render/clash95_surface_dump_probe.cdb",
             "soak_probe_template": "probes/cdb/soak/clash95_hidden_soak_route_extra.cdb"}


def legacy_harness(script: bytes) -> tuple[str, list[int]]:
    """Return a parameterised harness holding the legacy block verbatim."""
    lines = script.decode("ascii").splitlines(keepends=True)
    start = [i for i, line in enumerate(lines) if line.startswith("$durationTicks = [int64]$DurationSec * 64")]
    write = [i for i, line in enumerate(lines)
             if line.rstrip("\r\n") == "Set-Content -LiteralPath $generatedProbe -Value $probeText -Encoding ASCII"]
    if (len(start) != 1 or len(write) != 1 or not start[0] < write[0] - 1
            or not lines[write[0] - 1].startswith("Assert-SoakDiskReserve -Paths $diskPaths")):
        raise ValueError("legacy composition block markers are not where the harness expects them")
    block = "".join(lines[start[0]:write[0] - 1])
    if block.count(RAW_PATH_CALL) != 1 or "$framesDir" in block.replace(RAW_PATH_CALL, ""):
        raise ValueError("legacy raw-path expression is not the single expected call")
    harness = ("param([string]$ProbeTemplate, [string]$SoakProbeTemplate, [string]$Route, [int]$DurationSec,\r\n"
               "      [int]$PanIntervalSec, [int]$LoadSlot, [string]$RawPath, [string]$Output)\r\n"
               "$ErrorActionPreference = 'Stop'\r\n" + block.replace(RAW_PATH_CALL, "$RawPath")
               + "Set-Content -LiteralPath $Output -Value $probeText -Encoding ASCII\r\n")
    return harness, [start[0] + 1, write[0] + 1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True, help="new directory outside the checkout")
    parser.add_argument("--receipt", type=Path, required=True, help="new receipt JSON path")
    args = parser.parse_args(argv)
    work = args.work_dir.resolve()
    if sys.platform != "win32" or not POWERSHELL.is_file():
        raise SystemExit("the legacy composition runs only under Windows PowerShell")
    if work.is_relative_to(ROOT):
        raise SystemExit("the parity work directory must be outside the checkout")
    work.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("probe_composition_cases", ROOT / "tools/test_hidden_soak_probe_composition.py")
    cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cases)

    legacy = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{LEGACY_COMMIT}:{LEGACY_SCRIPT}"])
    harness, lines = legacy_harness(legacy)
    harness_path = work / "legacy_composition_harness.ps1"
    harness_path.write_bytes(harness.encode("ascii"))
    (work / "synthetic_probe.cdb").write_bytes(cases.SYNTHETIC_PROBE_TEMPLATE)
    (work / "synthetic_soak.cdb").write_bytes(cases.SYNTHETIC_SOAK_TEMPLATE)
    template_sets = {"real": {role: ROOT / path for role, path in TEMPLATES.items()},
                     "synthetic": {"probe_template": work / "synthetic_probe.cdb", "soak_probe_template": work / "synthetic_soak.cdb"}}
    version = subprocess.check_output([str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command",
                                       "$PSVersionTable.PSVersion.ToString()"], text=True).strip()
    results, failures = [], []
    for kind, paths in template_sets.items():
        data = {role: path.read_bytes() for role, path in paths.items()}
        for case, (route, duration, pan_interval, slot) in cases.CASES.items():
            target = work / f"{kind}-{case}.legacy.cdb"
            run = subprocess.run([str(POWERSHELL), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                  "-File", str(harness_path), "-ProbeTemplate", str(paths["probe_template"]),
                                  "-SoakProbeTemplate", str(paths["soak_probe_template"]), "-Route", route,
                                  "-DurationSec", str(duration), "-PanIntervalSec", str(pan_interval),
                                  "-LoadSlot", str(slot), "-RawPath", cases.RAW_PATH, "-Output", str(target)],
                                 capture_output=True, text=True, timeout=120)
            legacy_bytes = target.read_bytes() if run.returncode == 0 and target.is_file() else None
            probe = composition.compose_probe(data["probe_template"], data["soak_probe_template"], route=route,
                                              duration_sec=duration, pan_interval_sec=pan_interval, load_slot=slot,
                                              raw_path=cases.RAW_PATH)
            if legacy_bytes != probe:
                failures.append(f"{kind}/{case}: legacy rc={run.returncode} differs from compose_probe: {run.stderr.strip()[:300]}")
            results.append({"templates": kind, "case": case, "route": route, "duration_sec": duration,
                            "pan_interval_sec": pan_interval, "load_slot": slot,
                            "generated_probe_sha256": hashlib.sha256(probe).hexdigest(),
                            "generated_probe_size": len(probe), "byte_equal": legacy_bytes == probe})
    receipt = {
        "schema": "hidden_soak_probe_composition_parity_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "legacy_source": {"path": LEGACY_SCRIPT, "commit": LEGACY_COMMIT, "sha256": hashlib.sha256(legacy).hexdigest(),
                          "lines": lines, "raw_path_call_replaced_by_parameter": RAW_PATH_CALL},
        "legacy_runtime": f"Windows PowerShell {version}",
        "composer": {"path": "tools/hidden_soak_probe_composition.py", "sha256": composition.composer_sha256()},
        "templates": {
            "real": {role: {"path": TEMPLATES[role], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "size": path.stat().st_size} for role, path in template_sets["real"].items()},
            "synthetic": {role: {"path": "tools/test_hidden_soak_probe_composition.py",
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": path.stat().st_size}
                          for role, path in template_sets["synthetic"].items()}},
        "raw_path": cases.RAW_PATH,
        "cases": results,
        "failures": failures,
        "passed": not failures,
        "scope": "String composition only; no game, CDB, proxy, wrapper, capture or runtime claim.",
    }
    with args.receipt.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": receipt["passed"], "cases": len(results), "failures": failures}, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
