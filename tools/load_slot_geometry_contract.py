"""Read-only load-coordinate source contract shared by historical route guards.

This checks the reviewed direct assignment path, not arbitrary PowerShell
program equivalence. The renderer is replayed as a pure Python function; no
game, debugger, shell, or input command is run.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any


def active_lines(text: str) -> list[str]:
    """Exclude comments and multiline strings before matching source statements."""
    output, block, quote, here = [], 0, None, None
    for line in text.splitlines():
        if here is not None:
            if line.strip() == here + "@":
                here = None
            continue
        started_in_string = quote is not None
        clean, index = [], 0
        while index < len(line):
            char, pair = line[index], line[index:index + 2]
            if block:
                if pair == "<#":
                    block += 1
                    index += 2
                elif pair == "#>":
                    block -= 1
                    index += 2
                else:
                    index += 1
                continue
            if quote:
                clean.append(char)
                if (quote == '"' and char == "`") or (char == quote and pair == quote * 2):
                    if index + 1 < len(line):
                        clean.append(line[index + 1])
                    index += 2
                    continue
                if char == quote:
                    quote = None
            elif pair == "<#":
                block = 1
                index += 2
                continue
            elif char == "#":
                break
            elif pair in ("@'", '@"') and not line[index + 2:].strip():
                here = pair[1]
                break
            elif char in ("'", '"'):
                quote = char
                clean.append(char)
            else:
                clean.append(char)
            index += 1
        if not started_in_string and clean:
            output.append("".join(clean).strip())
    if block or quote or here:
        raise ValueError("unterminated PowerShell comment/string in geometry source")
    return output


def check_harness(path: Path, *, extra_probe: bool = False, require_slot_range: bool = False) -> dict[str, Any]:
    failures, observations = [], []
    result: dict[str, Any] = {"path": str(path), "exists": path.is_file(), "passed": False,
                              "source_mode": None, "markers": {}, "row_geometry": observations, "failures": failures}
    try:
        raw = path.read_bytes()
        lines = active_lines(raw.decode("utf-8-sig"))
        result["sha256"] = hashlib.sha256(raw).hexdigest()
        common = ["$loadMouseRawX = $loadMouseX -shl 6", "$loadMouseRawY = $loadMouseY -shl 6"]
        target = "$extraProbeText" if extra_probe else "$probeText"
        replacements = [f"{target} = {target}.Replace('__LOAD_SLOT__', [string]$LoadSlot)"]
        if extra_probe:
            replacements += [f"{target} = {target}.Replace('__LOAD_MOUSE_RAW_{axis}__', ('{{0:x8}}' -f $loadMouseRaw{axis}))" for axis in ("X", "Y")]
        modern = "$loadMouseX = $surfaceGeometry.load_mouse[0]" in lines
        if modern:
            result["source_mode"] = "shared_python_recipe"
            expected = [
                "$probeRenderer = Join-Path $RepoRoot 'tools\\render_cdb_surface_probe.py'",
                "$renderArgs = @('-B', $probeRenderer, '--template', $ProbeTemplate, '--resolution', $Resolution, '--stage', $recipeStage, '--load-slot', $LoadSlot)",
                "$probeRecipeJson = & $pythonExe @renderArgs",
                "$probeRecipe = $probeRecipeJson | ConvertFrom-Json",
                "$surfaceGeometry = $probeRecipe.geometry",
                "$loadMouseX = $surfaceGeometry.load_mouse[0]",
                "$loadMouseY = $surfaceGeometry.load_mouse[1]",
            ] + common + replacements
            import render_cdb_surface_probe as renderer
            renderer_path = path.resolve().parents[2] / "tools/render_cdb_surface_probe.py"
            expected_source = Path(renderer.__file__).read_bytes()
            actual_source = renderer_path.read_bytes()
            result["renderer"] = {"path": str(renderer_path), "sha256": hashlib.sha256(actual_source).hexdigest(),
                                  "expected_sha256": hashlib.sha256(expected_source).hexdigest()}
            if actual_source != expected_source:
                raise ValueError("selected renderer differs from the inspected pure recipe")
            template = renderer.BASE_PROBE.read_text(encoding="utf-8-sig")
            for slot in range(10):
                recipe = renderer.render_probe(template, "800x600", renderer.patcher.DEFAULT_STAGE, load_slot=slot, extra_probe=extra_probe)
                geometry = recipe["geometry"]
                point = geometry["load_mouse"]
                if point != [320, 166 + 22 * slot] or geometry["load_input_space"] != "native_slot_list":
                    failures.append(f"renderer row {slot} changed native load-list coordinates: {point}")
                observations.append({"slot": slot, "logical": point, "raw": [value << 6 for value in point]})
            for slot in (-1, 10):
                try:
                    renderer.render_probe(template, "800x600", renderer.patcher.DEFAULT_STAGE, load_slot=slot)
                except ValueError:
                    continue
                failures.append(f"renderer accepted out-of-range load slot {slot}")
        else:
            result["source_mode"] = "legacy_inline_formula"
            expected = ["$loadMouseX = 320", "$loadMouseY = 166 + (22 * $LoadSlot)"] + common + replacements
        if require_slot_range:
            expected = ["[ValidateRange(0,9)]", "[int]$LoadSlot = 0"] + expected
        positions = []
        for statement in expected:
            hits = [index for index, line in enumerate(lines) if line == statement]
            result["markers"][statement] = len(hits) == 1
            if len(hits) != 1:
                failures.append(f"expected one active source statement: {statement}")
            else:
                positions.append(hits[0])
        if positions != sorted(positions):
            failures.append("load geometry data flow is out of order")
        # Comments/string copies cannot substitute for an assignment, and an
        # additional assignment cannot silently replace the checked value.
        protected = {"loadMouseX", "loadMouseY", "loadMouseRawX", "loadMouseRawY"}
        if modern:
            protected |= {"probeRenderer", "probeRecipeJson", "probeRecipe", "surfaceGeometry"}
        for line in lines:
            assignment = re.match(r"^\$(\w+)\s*=", line)
            if assignment and assignment[1] in protected and line not in expected:
                failures.append(f"unexpected geometry assignment: {line}")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, IndexError) as exc:
        failures.append(str(exc))
    result["passed"] = not failures
    return result
