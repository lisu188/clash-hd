#!/usr/bin/env python3
"""Static sanity checks for battle UI CDB probe templates."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE_DIR = ROOT / "probes" / "cdb" / "battle"
REGISTER_RE = re.compile(r"@\$t(?P<index>\d+)")


def battle_probe_paths() -> list[Path]:
    return sorted(PROBE_DIR.glob("*.cdb"))


def test_battle_probe_registers_are_valid(paths: list[Path]) -> None:
    invalid: list[str] = []
    for path in paths:
        text = path.read_text(encoding="ascii")
        for match in REGISTER_RE.finditer(text):
            index = int(match.group("index"))
            if index > 19:
                invalid.append(f"{path.relative_to(ROOT)} uses @$t{index}")
    assert not invalid, "\n".join(invalid)


def test_battle_probes_are_extra_probe_safe(paths: list[Path]) -> None:
    failures: list[str] = []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="ascii").splitlines(), start=1):
            stripped = line.strip()
            if stripped == "g":
                failures.append(f"{path.relative_to(ROOT)}:{line_number} has standalone g")
            if stripped.startswith(".echo") and ";" in stripped:
                failures.append(f"{path.relative_to(ROOT)}:{line_number} has semicolon in .echo")
    assert not failures, "\n".join(failures)


def test_battle_probes_emit_battle_rows(paths: list[Path]) -> None:
    failures = [
        str(path.relative_to(ROOT))
        for path in paths
        if "BATTLE_" not in path.read_text(encoding="ascii")
    ]
    assert not failures, "\n".join(failures)


def run_tests() -> None:
    paths = battle_probe_paths()
    assert paths, f"no battle probes found under {PROBE_DIR}"
    test_battle_probe_registers_are_valid(paths)
    test_battle_probes_are_extra_probe_safe(paths)
    test_battle_probes_emit_battle_rows(paths)


def main() -> int:
    run_tests()
    print("battle UI probe tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
