"""Pure startup recipe/transport fixtures; no game, debugger or candidate IO."""
from __future__ import annotations

import copy
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import army_probe_startup as compiler
import render_cdb_surface_probe as renderer

# Independent frozen-compiler oracle: af8179ec tools/framed_modal_canvas_trace.py,
# SHA256 2f0ef571acdbc6892c775cc97698d535b56355c8086080713d3dfec040a6d3ba.
# Its authenticated legacy startup fragments were substituted without executing
# any command. These literal output hashes keep fresh-clone fixtures git-free.
EXPECTED = {
    "800x600": "a309f9c0bf2210d53635fefe2f4be687d72f2ff257823deb909c55128d0a60a4",
    "1024x768": "18954ffd249367b46730871ead526df06295d47cc31796a2be938d1bbe176005",
    "1280x720": "27cd8544586003b745a8b1d30c985f1adc398c7e94b208897c8e8ccb0cdc66fc",
    "1280x960": "854dced02527b4b2fcd46ee8f034eb916cc318e1ae4a72efb74c9d51033cef5f",
    "1920x1080": "5f2116ca6ed1e761cf35c9e95a9e96adbbc45eb96881f816571be38072df358b",
    "802x602": "da1c684441b973b521cd6aa3081ca7ab63d4efcb076466397fd575f765570a07",
}


def packet(resolution="1024x768"):
    template = renderer.render_probe(renderer.BASE_PROBE.read_text(encoding="utf-8-sig"),
                                     resolution, compiler.BASE_STAGE)["template"]
    return dict(resolution=resolution, map_probe_template=template,
                handoff_action=".echo ARMY_STARTUP_FIXTURE_HANDOFF;",
                byte_checks_before_first_breakpoint=".echo ARMY_STARTUP_FIXTURE_BYTES\n",
                startup_commands_before_final_g='bp80 00401234 ".echo ARMY_STARTUP_FIXTURE_OBSERVER; gc"\nbd 80\n')


class StartupTests(unittest.TestCase):
    def test_six_resolutions_match_independent_historical_output_and_slot_zero_geometry(self):
        self.assertEqual(set(compiler.RESOLUTIONS), set(EXPECTED))
        for size, expected in EXPECTED.items():
            with self.subTest(resolution=size):
                values = packet(size); before = copy.deepcopy(values)
                output = compiler.compile_probe(values)
                self.assertEqual(compiler.sha(output.encode("ascii")), expected)
                self.assertEqual(values, before)
                width, height = map(int, size.split("x"))
                self.assertIn(f"(@$t12 != 0n{width}) | (@$t15 != 0n{height})", output)
                self.assertEqual(output.count("ed 00544cfc 00005000; ed 00544d00 00002980;"), 2)
                self.assertIn(".echo ARMY_STARTUP_FIXTURE_HANDOFF;", output)
                self.assertNotRegex(output, r"__[A-Za-z0-9_]+__")
                self.assertEqual(len(compiler.STARTUP_LINES), 6)
                self.assertEqual(sum(line.startswith("bp ") for line in compiler.STARTUP_LINES), 5)

    def test_crlf_is_canonicalized_without_changing_packet(self):
        values = packet()
        for name, value in list(values.items()):
            if name != "resolution": values[name] = value.replace("\n", "\r\n")
        before = copy.deepcopy(values)
        self.assertEqual(compiler.compile_probe(values), compiler.compile_probe(packet()))
        self.assertEqual(values, before)

    def test_every_required_token_must_occur_exactly_once(self):
        values = packet()
        for token in compiler.REQUIRED_TOKENS:
            for replacement in ("", token + token):
                with self.subTest(token=token, replacement=replacement):
                    bad = dict(values, map_probe_template=values["map_probe_template"].replace(token, replacement))
                    with self.assertRaisesRegex(ValueError, "exactly one canonical token"):
                        compiler.compile_probe(bad)

    def test_missing_duplicate_moved_or_nonfinal_transport_commands_fail(self):
        values = packet(); template = values["map_probe_template"]
        variants = [template.replace("bc *\n", ""), template.replace("bc *\n", "bc *\nbc *\n"),
                    template.replace("bc *\n", "BC *\n"), template[:-2], template + "g\n",
                    template + ".echo AFTER_FINAL_GO\n", template.replace("bc *\n", "")[:-2] + "bc *\ng\n"]
        for text in variants:
            with self.subTest(text=text[-45:]), self.assertRaises(ValueError):
                compiler.compile_probe(dict(values, map_probe_template=text))
        for name in ("byte_checks_before_first_breakpoint", "startup_commands_before_final_g"):
            for command in ("bc *\n", "g\n"):
                with self.subTest(fragment=name, command=command), self.assertRaises(ValueError):
                    compiler.compile_probe(dict(values, **{name: values[name] + command}))

    def test_unresolved_tokens_bad_text_and_fragment_boundaries_fail(self):
        values = packet()
        for name in ("map_probe_template", "handoff_action", "byte_checks_before_first_breakpoint", "startup_commands_before_final_g"):
            for suffix in ("__UNRESOLVED__", "__unresolved__", "\x00", "\r", "\u0105"):
                with self.subTest(fragment=name, suffix=suffix), self.assertRaises(ValueError):
                    compiler.compile_probe(dict(values, **{name: values[name] + suffix}))
            for invalid in (None, 1, True, b"bytes"):
                with self.subTest(fragment=name, value=invalid), self.assertRaises(ValueError):
                    compiler.compile_probe(dict(values, **{name: invalid}))
        for name in ("byte_checks_before_first_breakpoint", "startup_commands_before_final_g"):
            with self.subTest(fragment=name), self.assertRaisesRegex(ValueError, "line boundary"):
                compiler.compile_probe(dict(values, **{name: values[name].rstrip("\n")}))

    def test_4095_byte_lines_pass_but_4096_and_oversized_expansion_fail(self):
        values = packet(); name = "startup_commands_before_final_g"
        good = dict(values, **{name: values[name] + "$$" + "x" * 4093 + "\n"})
        self.assertEqual(max(map(len, compiler.compile_probe(good).splitlines())), 4095)
        for bad in (dict(values, **{name: values[name] + "$$" + "x" * 4094 + "\n"}),
                    dict(values, handoff_action="x" * 4095)):
            with self.assertRaisesRegex(ValueError, "4095-byte"):
                compiler.compile_probe(bad)

    def test_implicit_and_explicit_breakpoint_collisions_and_unknown_syntax_fail(self):
        values = packet(); name = "startup_commands_before_final_g"
        for declaration in ('bp80 00405678 "gc"', 'bp 80 00405678 "gc"',
                            'bp81 00401234 "gc"', 'bp81 0044789a "gc"',
                            'bp0 00405678 "gc"', 'bp1000 00405678 "gc"', 'bp module!name "gc"'):
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                compiler.compile_probe(dict(values, **{name: values[name] + declaration + "\n"}))

    def test_source_recipe_and_resolution_fail_closed_without_reading_live_harness(self):
        values = packet()
        original_read = Path.read_bytes
        def read(path):
            if path.name == "run_cdb_surface_dump.ps1":
                raise AssertionError("the versioned recipe must not read the mutable runtime harness")
            return original_read(path)
        with patch.object(Path, "read_bytes", read):
            self.assertEqual(compiler.sha(compiler.compile_probe(values).encode()), EXPECTED[values["resolution"]])
        for size in ("1280x800", "0800x600", "800X600", None, 800):
            with self.subTest(size=size), self.assertRaises(ValueError):
                compiler.compile_probe(dict(values, resolution=size))
        with patch.dict(compiler.PINNED_SOURCES, {"tools/render_cdb_surface_probe.py": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "geometry source differs"):
                compiler.compile_probe(values)
        with patch.object(compiler, "STARTUP_LINES", compiler.STARTUP_LINES[:-1] + (".echo CHANGED",)):
            with self.assertRaisesRegex(ValueError, "literal startup recipe differs"):
                compiler.compile_probe(values)
        result = compiler.provenance()
        self.assertEqual(result["recipe_sha256"], "f0f72a09aec7db61193889984a00e3b195ad71bc8f9567ed2d149d07d8c8edac")
        self.assertEqual(result["source_sha256"]["tools/army_probe_startup.py"], compiler.sha(Path(compiler.__file__).read_bytes()))
        for name in ("runtime_executed", "manual_input_proof", "promotion_ready"):
            self.assertIs(result[name], False)


if __name__ == "__main__":
    unittest.main()
