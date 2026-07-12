#!/usr/bin/env python3
"""Regression tests for repo_structure.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "repo_structure.py"
sys.path.insert(0, str(ROOT / "tools"))

import repo_structure  # noqa: E402


def write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_minimal_repo(root: Path) -> None:
    write(root / "README.md", "# fixture\n")
    write(root / "AGENTS.md", "# fixture\n")
    write(root / ".gitignore", "*.exe\n")
    write(root / "dxcfg_windowed.ini", "[window]\n")
    write(
        root / "patch_clash95_hd.py",
        "import runpy\nfrom pathlib import Path\nrunpy.run_path(str(Path('src') / 'patcher' / 'patch_clash95_hd.py'))\n",
    )
    write(
        root / "src/patcher/patch_clash95_hd.py",
        "EXPECTED_SHA256 = 'x'\nDEFAULT_STAGE = 'stage'\nPATCHES = ()\n",
    )
    write(root / "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp", "// cpp\n")
    write(root / "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.def", "EXPORTS\n")
    for rel_path in repo_structure.REQUIRED_DIRS:
        (root / rel_path).mkdir(parents=True, exist_ok=True)
    for rel_path in (
        "docs/hd/README.md",
        "scripts/README.md",
        "probes/README.md",
        "tools/README.md",
        "reports/README.md",
        "captures/README.md",
    ):
        write(root / rel_path, "# index\n")
    write(
        root / "captures/current/hd-map-evidence-current.md",
        "\n".join(
            [
                "captures/current/hd-map-smoke-current.md",
                "captures/current/post-owner-evidence-current.md",
                "captures/current/patch-manifest-compare-current-vs-partial12.md",
            ]
        ),
    )
    write(root / "captures/current/hd-map-smoke-current.md", "# smoke\n")
    write(root / "captures/current/post-owner-evidence-current.md", "# post owner\n")
    write(root / "captures/current/patch-manifest-compare-current-vs-partial12.md", "# compare\n")
    write(root / "captures/current/patch-stage-current-hd-map.json", "{}\n")


def assert_all_pass(checks: list[repo_structure.Check]) -> None:
    failures = [check for check in checks if not check.passed]
    assert not failures, failures


def main() -> int:
    output = repo_structure.build_output(ROOT)
    assert output.startswith("# Compact Repository Structure\n"), output
    assert "clash-hd/" in output, output
    assert "|-- src/" in output, output
    assert "|-- scripts/" in output, output
    assert "|-- tools/" in output, output
    assert "|-- raw/" in output, output
    assert "`-- meta/" in output, output
    assert "User-owned source material" in output, output
    assert "Agent-maintained Obsidian-compatible" in output, output

    counted = repo_structure.build_output(ROOT, include_counts=True)
    assert "tools/" in counted and " files)" in counted, counted

    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / "fixture"
        fixture.mkdir()
        make_minimal_repo(fixture)
        assert_all_pass(repo_structure.run_checks(fixture))

        write(fixture / ".agents/session.json", "{}\n")
        assert_all_pass(repo_structure.run_checks(fixture))

        write(fixture / "notes.txt", "not approved at root\n")
        checks = repo_structure.run_checks(fixture)
        assert any(check.name == "root_contents" and not check.passed for check in checks), checks
        (fixture / "notes.txt").unlink()

        write(fixture / "README.md", ".\\run_cdb_surface_dump.ps1\n")
        checks = repo_structure.run_checks(fixture)
        assert any(check.name == "stale_references" and not check.passed for check in checks), checks

    run = subprocess.run(
        [sys.executable, str(SCRIPT), "--counts", "--require-pass"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "# Compact Repository Structure" in run.stdout, run.stdout
    assert "Structure Checks" in run.stdout, run.stdout

    print("repo_structure tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
