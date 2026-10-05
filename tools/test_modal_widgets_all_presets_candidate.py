#!/usr/bin/env python3
"""Portable source/PE/geometry fixtures; optional one-preset original in memory.

Synthetic instruction fixtures extract only the pinned assembler region. They
cannot satisfy production identity/admission and execute no x86, native loader,
compiler, game or debugger. No candidate, probe or evidence bundle is written.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import modal_widgets_all_presets_candidate as tool
from src.patcher import owned_modal_all_presets_emit as adapters
from src.patcher import pe_extension as pe


def synthetic_complete(resolution="1366x768"):
    """Independent eleven-section format fixture with mapped native addresses."""
    text_size = 0x150000
    data = bytearray(0x400 + text_size + 9 * 512 + 4096)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 0x70)
    data[0x70:0x74] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x74, 0x14C, 11, 0, 0, 0, 224, 0x182)
    opt, raw = 0x88, 0x400
    struct.pack_into("<H", data, opt, 0x10B)
    struct.pack_into("<III", data, opt + 28, 0x400000, 4096, 512)
    struct.pack_into("<II", data, opt + 56, 0x199000, 1024)
    struct.pack_into("<I", data, opt + 92, 16)
    struct.pack_into("<II", data, opt + 136, 0x156000, 12)
    rows = [(b".text", 0x1000, text_size, text_size, 0x400, pe.RX_CODE),
            (b".bss", 0x151000, 4096, 4096, 0, 0xC0000080)]
    raw += text_size
    for name, rva, flags in ((b".rdata", 0x152000, 0x40000040), (b".data", 0x153000, 0xC0000040),
                             (b".idata", 0x154000, 0xC0000040), (b".debug", 0x155000, 0x40000040),
                             (b".reloc", 0x156000, 0x42000040), (b".hdcode", 0x157000, pe.RX_CODE),
                             (b".hdmodal", 0x158000, pe.RX_CODE)):
        rows.append((name, rva, 0x20000 if name == b".hdmodal" else 512, 512, raw, flags))
        raw += 512
    rows.append((b".hdstate", 0x178000, 4096, 4096, raw, tool.parent.RW))
    raw += 4096
    rows.append((b".hdarmy", 0x179000, 0x20000, 512, raw, pe.RX_CODE))
    raw += 512
    data = data[:raw]
    struct.pack_into("<I", data, opt + 4, text_size + 3 * 512)
    for index, row in enumerate(rows):
        name, rva, virtual, size, start, flags = row
        struct.pack_into("<8sIIIIIIHHI", data, opt + 224 + 40 * index,
                         name, virtual, rva, size, start, 0, 0, 0, 0, flags)
    data[0x400:0x400 + text_size] = b"\x90" * text_size
    struct.pack_into("<I", data, 0x401, 0x551008)
    view = pe.inspect_pe(bytes(data))
    struct.pack_into("<IIHH", data, view.file_offset(0x156000, 12), 0x1000, 12, 0x3001, 0)
    def put(va, value):
        off = view.file_offset(va - view.image_base, len(value))
        data[off:off + len(value)] = value
    for va, old in ((0x432C0B, bytes.fromhex("e8d0f8fcff")),
                    (0x401E30, b"\xe9" + struct.pack("<i", 0x558000 - 0x401E30 - 5)),
                    (0x432F94, bytes.fromhex("b921010000bbdc000000")),
                    (0x432F5C, bytes.fromhex("e84fdc0200")), (0x4331D5, bytes.fromhex("e8d6d90200")),
                    (0x433273, bytes.fromhex("e868f2fcff")), (0x432C66, bytes.fromhex("e8e594fdff")),
                    (0x419D63, b"\x81\x38" + struct.pack("<I", int(resolution.split("x")[0]))),
                    (0x419D8C, b"\x81\x39" + struct.pack("<I", int(resolution.split("x")[0])))):
        put(va, old)
    put(0x545158, bytes(12))
    put(0x4EFC3A, b"%d\0")
    image = bytes(data)
    hooks = []
    for va in (0x401E30, 0x4224B2):
        off = view.file_offset(va - view.image_base, 5)
        hooks.append(dict(va=va, new_hex=image[off:off + 5].hex()))
    owner = dict(state_va=0x578000, state_bytes=4096, modal_state_offsets={},
                 modal_entry_vas={"is_active": 0x558000, "full_blit": 0x558010}, code_sha256="synthetic", hooks=hooks)
    context = dict(stage=tool.parent.STAGE, recipe_revision=tool.parent.REVISION, resolution=resolution,
                   candidate_sha256=tool.sha256(image), predecessor={"base_candidate": owner, "hooks": []},
                   source_hashes={}, fixture_count=1, **{key: False for key in tool.parent.FALSE_CLAIMS})
    return image, context


def instruction_fixture(modules, kind, *, code_va, width, height):
    """Exact frozen instruction region, without pretending synthetic ABI admission."""
    if kind == "widgets":
        module = modules["src/patcher/framed_modal_widget_bounds.py"]
        return module._emit_guards(base_va=code_va, state_va=0x578000, owner_va=0x558000,
            width=width, height=height, comparisons={"single": b"\x81\x38" + struct.pack("<I", width),
                                                  "list": b"\x81\x39" + struct.pack("<I", width)})
    name, fn_name, _ = adapters.ADAPTERS[kind]
    module = modules[name]
    tree = ast.parse((ROOT / name).read_bytes())
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == fn_name)
    start = next(i for i, node in enumerate(fn.body) if isinstance(node, ast.Assign)
                 and ast.unparse(node).startswith("a = clip._Assembler(base_va)"))
    end = next(i for i, node in enumerate(fn.body) if isinstance(node, ast.Assign)
               and ast.unparse(node) == "code = a.finish()")
    scope = dict(module.__dict__, base_va=code_va, width=width, height=height,
                 state=0x578000, active=0x558000,
                 entries={"is_active": 0x558000, "full_blit": 0x558010, "mirror": 0x558020},
                 descriptor_prefixes={va: (0, 0, 0) for va in module.CURSOR_DESCRIPTORS}
                 if kind == "primary" else {})
    exec(compile(ast.fix_missing_locations(ast.Module(body=fn.body[start:end + 1], type_ignores=[])),
                 "synthetic-frozen-instruction-region", "exec"), scope)
    return types.SimpleNamespace(code=scope["code"], relocations=tuple(scope["a"].relocations),
                                 entries={name: code_va + off for name, off in scope["a"].labels.items()})


def synthetic_emit(modules, kind, original, current, context, *, base_va, width, height):
    """Explicit private-format replacement; never used by public build_candidate."""
    private_pe = tool._extension(modules, kind).pe
    view = pe.inspect_pe(current)
    bundle = instruction_fixture(modules, kind, code_va=base_va, width=width, height=height)
    hooks = []
    names = {"slots": ("slot_blit",), "primary": ("full_blit", "placeholder", "cursor_rect", "cursor_rect", "panel_copy"),
             "text": ("quantity",), "widgets": ("single", "list")}[kind]
    sites = next(row[2] for row in tool.LAYERS if row[0] == kind)
    for va, name in zip(sites, names):
        size = 10 if va == 0x432F94 else 6 if kind == "widgets" else 5
        off = view.file_offset(va - view.image_base, size)
        old = current[off:off + size]
        target = bundle.entries[name]
        op = b"\xe9" if va in (0x401E30, 0x432F94) else b"\xe8"
        new = op + struct.pack("<i", target - va - 5) + b"\x90" * (size - 5)
        hooks.append(private_pe.HookPatch(off, va - view.image_base, va, old, new, "synthetic." + name,
                     (private_pe.CodeRelocation(1, "rel32", target, "synthetic exact instruction-region entry"),)))
    return types.SimpleNamespace(code=bundle.code, relocations=bundle.relocations, entries=bundle.entries,
        base_va=base_va, hook_sites=tuple(hooks), modal_state_va=0x578000,
        candidate_sha256=tool.sha256(current), source_contract=dict(predecessor_stage=context["stage"],
            predecessor_revision=context["recipe_revision"], native_spans=[]))


def synthetic_layers(modules, resolution="1366x768"):
    complete, context = synthetic_complete(resolution)
    current, layers = complete, []
    with patch.object(adapters, "_emit", side_effect=synthetic_emit):
        for kind, _, _, _ in tool.LAYERS:
            current, context, _ = tool._build_layer(b"synthetic-format-only", current, context, kind, modules, pe, {})
            layers.append(context)
    return complete, current, layers


class SourceTests(unittest.TestCase):
    def test_exact_nine_presets_and_private_frozen_adapters(self):
        sources = tool._sources()
        self.assertEqual(tool.RESOLUTIONS, tool.parent.RESOLUTIONS)
        self.assertEqual(len(tool.RESOLUTIONS), 9)
        for kind, (name, fn, admissions) in adapters.ADAPTERS.items():
            tree = adapters._adapter_tree(sources[name], ROOT / name, fn, admissions)
            self.assertEqual(tree.body[0].name, "_emit_from_context")
            self.assertEqual(tree.body[0].args.kwonlyargs[-1].arg, "context")
            damaged = ast.parse(sources[name])
            frozen = next(node for node in damaged.body if isinstance(node, ast.FunctionDef) and node.name == fn)
            expected = ast.dump(ast.parse(admissions[-1]).body[0], include_attributes=False)
            frozen.body = [node for node in frozen.body if ast.dump(node, include_attributes=False) != expected]
            bad = ast.unparse(damaged)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                adapters._adapter_tree(bad, ROOT / name, fn, admissions)
        with adapters._producer(sources) as (modules, _, _):
            self.assertEqual(modules["src/patcher/complete_hd_candidate.py"].REVISION, "complete_hd_v1")
            self.assertEqual(modules["src/patcher/complete_hd_all_presets_candidate.py"].RESOLUTIONS, tool.RESOLUTIONS)

    def test_forged_original_and_selector_fail_before_construction(self):
        for value in (b"fixture", bytearray(b"fixture"), None):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                tool.build_candidate(value, "1366x768")
        with patch.object(tool, "sha256", return_value=tool.BASE_SHA256), patch.object(tool, "_sources", side_effect=AssertionError):
            for resolution in ("802x602", "1366X768", "01366x768", None, True):
                with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                    tool.build_candidate(b"fixture", resolution)

    def test_private_imports_do_not_use_public_producer_aliases(self):
        alias = types.ModuleType("tools.build_framed_modal_primary_candidate")
        alias.build_candidate = lambda *args: self.fail("public frozen producer called")
        before = list(sys.path)
        with patch.dict(sys.modules, {alias.__name__: alias}):
            with adapters._producer(tool._sources()) as (modules, _, _):
                self.assertIsNot(modules["tools/build_framed_modal_primary_candidate.py"], alias)
                self.assertTrue(modules["src/patcher/framed_modal_primary.py"]._emit_from_context.__module__.startswith("_clash95_all_presets_"))
            self.assertIs(sys.modules[alias.__name__], alias)
        self.assertEqual(sys.path, before)
        self.assertFalse(any(name.startswith("_clash95_all_presets_") for name in sys.modules))

    def test_source_pin_tamper_rejected(self):
        name = "src/patcher/framed_modal_primary.py"
        read = Path.read_bytes
        def tamper(path):
            result = read(path)
            return result + b"\n# synthetic change\n" if path == ROOT / name else result
        with patch.object(Path, "read_bytes", tamper), self.assertRaisesRegex(ValueError, "producer source differs"):
            tool._sources()


class GeometryAndImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = adapters._producer(tool._sources())
        cls.modules, _, _ = cls.scope.__enter__()
    @classmethod
    def tearDownClass(cls):
        cls.scope.__exit__(None, None, None)

    def test_all_nine_exact_instruction_strides_geometry_allocation_and_replay(self):
        for resolution in tool.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                base, image, layers = synthetic_layers(self.modules, resolution)
                current = image
                for layer in reversed(layers):
                    current, audit = tool._audit_layer(current, layer, layer["layer_kind"], pe)
                    self.assertEqual(audit["new_state_bytes"], 0)
                self.assertEqual(current, base)
                view = pe.inspect_pe(image)
                self.assertEqual(len(view.sections), 15)
                self.assertEqual(tuple(s.name.rstrip(b"\0") for s in view.sections[-4:]),
                                 (b".hdslots", b".hdprim", b".hdptxt", b".hdwgt"))
                records = tool.byte_records(base, image, view)
                self.assertEqual(tool.apply_records(base, records, expected_base_sha256=tool.sha256(base), view=view), image)
                width, height = map(int, resolution.split("x"))
                dx, dy = (width - 640) // 2, (height - 480) // 2
                slot_code = image[view.sections[-4].raw_offset:view.sections[-4].raw_offset + layers[0]["code_bytes"]]
                self.assertIn(b"\x69\xd1" + struct.pack("<I", width), slot_code)
                self.assertIn(b"\x81\xc7" + struct.pack("<I", dy * width + dx), slot_code)
                self.assertIn(b"\x81\xc7" + struct.pack("<I", width - 33), slot_code)
                text_code = image[view.sections[-2].raw_offset:view.sections[-2].raw_offset + layers[2]["code_bytes"]]
                for stack_offset, amount in ((40, dx), (44, dx), (48, dy)):
                    self.assertIn(b"\x81\x44\x24" + bytes([stack_offset]) + struct.pack("<I", amount), text_code)
                self.assertTrue(0 <= dx and 0 <= dy and dx + 640 <= width and dy + 480 <= height)
                self.assertTrue(all(va >= view.image_base + section.rva and va < view.image_base + section.rva + layer["code_bytes"]
                                    for section, layer in zip(view.sections[-4:], layers) for va in layer["layer_entries"].values()))

    def test_tampered_metadata_operands_hooks_sources_state_and_parent_fail(self):
        _, image, layers = synthetic_layers(self.modules)
        context = layers[-1]
        for key, value in (("stage", "stable"), ("recipe_revision", "frozen"), ("resolution", "802x602"),
                           ("code_characteristics", tool.parent.RW), ("input_sha256", "0" * 64),
                           ("old_relocation_sha256", "0" * 64), ("merged_relocation_sha256", "0" * 64),
                           ("state_bytes", 4096), ("hooks", context["hooks"][:-1]),
                           ("relocations", [row for row in context["relocations"] if row["kind"] != "abs32"])):
            bad = deepcopy(context)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool._audit_layer(image, bad, "widgets", pe)
        for key in tool.FALSE_CLAIMS:
            bad = deepcopy(context)
            bad[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool._audit_layer(image, bad, "widgets", pe)
        bad = deepcopy(context)
        bad["hook_relocations"][0]["target"] += 1
        with self.assertRaisesRegex(ValueError, "operand differs"):
            tool._audit_layer(image, bad, "widgets", pe)
        bad = deepcopy(context)
        bad["relocations"].append(deepcopy(bad["relocations"][0]))
        with self.assertRaisesRegex(ValueError, "overlap"):
            tool._audit_layer(image, bad, "widgets", pe)

    def test_payload_directory_header_padding_and_replay_tamper_rejected(self):
        base, image, layers = synthetic_layers(self.modules)
        context, view = layers[-1], pe.inspect_pe(image)
        section = view.sections[-1]
        for offset in (section.raw_offset, section.raw_offset + context["code_bytes"], section.header_offset + 36):
            data, bad = bytearray(image), deepcopy(context)
            data[offset] ^= 1
            bad["candidate_sha256"] = bad["output_sha256"] = tool.sha256(bytes(data))
            for row in bad["edits"]:
                start, length = row["offset"], len(bytes.fromhex(row["new_hex"]))
                if start <= offset < start + length:
                    row["new_hex"] = bytes(data[start:start + length]).hex()
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                tool._audit_layer(bytes(data), bad, "widgets", pe)
        rows = tool.byte_records(base, image, view)
        index = next(i for i, row in enumerate(rows) if row["old_hex"])
        for key, value in (("stage", "stable"), ("old_hex", "00"), ("rva", 0), ("appended", True), ("file_offset", True)):
            bad = deepcopy(rows)
            bad[index][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool.apply_records(base, bad, expected_base_sha256=tool.sha256(base), view=view)
        with self.assertRaises(ValueError):
            tool.apply_records(base, rows, expected_base_sha256="0" * 64, view=view)

    def test_reverse_reemit_admission_rejects_parent_source_type_order_and_omitted_operand(self):
        base, image, layers = synthetic_layers(self.modules)
        complete_context = layers[0]["base_candidate"]
        def authenticate(context, expected_parent=complete_context):
            return tool._authenticate_context(b"synthetic-format-only", image, context, base,
                                               expected_parent, self.modules, pe, {})
        with patch.object(adapters, "_emit", side_effect=synthetic_emit):
            self.assertEqual(len(authenticate(layers[-1])), 4)
            for key, value in (("source_hashes", {"unreviewed.py": "0" * 64}),
                               ("layer_kind", "primary"), ("layer_entries", {"single": 0x1234})):
                bad = deepcopy(layers[-1])
                bad[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    authenticate(bad)
            bad = deepcopy(layers[-1])
            bad["relocations"] = [row for row in bad["relocations"] if row["kind"] != "rel32"]
            # HIGHLOW alone cannot discover a missing declared relative operand;
            # exact source re-emission supplies the separate rejection.
            tool._audit_layer(image, bad, "widgets", pe)
            with self.assertRaisesRegex(ValueError, "source-emitted"):
                authenticate(bad)
            bad = deepcopy(layers[-1])
            ancestor = bad
            for _ in tool.LAYERS:
                ancestor = ancestor["base_candidate"]
            ancestor["fixture_count"] = True  # Python equality would consider this 1.
            with self.assertRaisesRegex(ValueError, "exact all-preset"):
                authenticate(bad)
            ancestor["fixture_count"] = 1.0
            with self.assertRaisesRegex(ValueError, "exact all-preset"):
                authenticate(bad)
            wrong = deepcopy(complete_context)
            wrong["candidate_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                authenticate(layers[-1], wrong)
        with self.assertRaises(ValueError):
            tool._canonical({"nonfinite": float("nan")})

    def test_only_full_blit_overlap_and_root_restore_survive(self):
        base, image, layers = synthetic_layers(self.modules)
        context = layers[0]["base_candidate"]
        audit = tool._audit_hook_chain(base, image, context, layers, pe)
        self.assertTrue(audit["root_restore_preserved"])
        self.assertEqual(audit["permitted_overlap_va"], 0x401E30)
        bad = deepcopy(layers)
        bad[1]["hooks"].append(deepcopy(bad[0]["hooks"][0]))
        with self.assertRaisesRegex(ValueError, "unsupported native hook overlap"):
            tool._audit_hook_chain(base, image, context, bad, pe)
        bad = bytearray(image)
        bad[pe.inspect_pe(image).file_offset(0x224B2, 1)] ^= 1
        with self.assertRaisesRegex(ValueError, "hook differs"):
            tool._audit_hook_chain(base, bytes(bad), context, layers, pe)

    def test_final_probe_rebinds_all_loaded_predicates_and_binds_text_format(self):
        for resolution in tool.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                base, image, layers = synthetic_layers(self.modules, resolution)
                context = layers[0]["base_candidate"]
                view = pe.inspect_pe(base)
                va = 0x401E30
                old = base[view.file_offset(va - view.image_base, 2):view.file_offset(va - view.image_base, 2) + 2]
                marker = "COMPLETEHD_ALL_PRESETS_CONTRACT_PASS stage=" + context["stage"]
                inherited = (f".if ((wo({va:08x}) != {int.from_bytes(old, 'little'):x})) {{ .echo ARMY_CONTRACT_FAIL; q }}\n"
                    ".echo ARMY_CONTRACT_PASS old-image\n.echo " + marker + "\n.echo PTILE_CONTRACT_PASS old-image\n"
                    ".echo PTILE_OBSERVER_RETAINED\n")
                context["probe_sha256"] = tool.sha256(inherited.encode())
                context["probe_contract"] = {"complete_marker": marker}
                probe, contract = tool._probe(base, image, context, inherited, layers, self.modules, pe, "b" * 64)
                self.assertEqual(probe.count("_CONTRACT_PASS"), 1)
                self.assertEqual(contract["inherited_predicate_count"], 1)
                self.assertIn("producer_sha256=" + "b" * 64, probe)
                self.assertIn(".echo PTILE_OBSERVER_RETAINED", probe)
                self.assertIn("(wo(004efc3a) != 6425)", probe)
                self.assertIn("(by(004efc3c) != 0)", probe)
                text = self.modules["tools/build_framed_modal_primary_text_candidate.py"]
                after = pe.inspect_pe(image)
                for match in tool.PREDICATE.finditer(probe):
                    kind, address, expected = match.groups()
                    self.assertEqual(int.from_bytes(text.loaded_bytes(image, after, int(address, 16), 2 if kind == "wo" else 1), "little"),
                                     int(expected, 16))
                bad = bytearray(image)
                bad[after.file_offset(0xEFC3A, 1)] ^= 1
                format_match = next(match for match in tool.PREDICATE.finditer(probe) if match.group(2) == "004efc3a")
                self.assertNotEqual(int.from_bytes(text.loaded_bytes(bytes(bad), after, 0x4EFC3A, 2), "little"),
                                    int(format_match.group(3), 16))
                for variant in (inherited.replace(marker, "FOREIGN_MARKER"), inherited.replace("wo(00401e30)", "wo(00401e31)"),
                                inherited.replace("wo(00401e30)", "poi(00401e30)")):
                    altered = dict(context, probe_sha256=tool.sha256(variant.encode()))
                    with self.assertRaises(ValueError):
                        tool._probe(base, image, altered, variant, layers, self.modules, pe, "b" * 64)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", action="store_true", help="one 1366x768 candidate in memory; no files or runtime")
    args = parser.parse_args(argv)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not result.wasSuccessful():
        return 1
    if args.original_backed:
        original = Path("C:/Clash/clash95.exe").read_bytes()
        image, metadata, probe = tool.build_candidate(original, "1366x768")
        assert metadata["candidate_sha256"] == tool.sha256(image)
        assert metadata["probe_sha256"] == tool.sha256(probe.encode())
        assert all(metadata[key] is False for key in tool.FALSE_CLAIMS)
        assert metadata["structural_gate"]["section_count"] == 15
        assert probe.count("_CONTRACT_PASS") == 1
        print("ORIGINAL_BACKED_CONSTRUCTION_PASS resolution=1366x768 candidate_sha256=" + tool.sha256(image)
              + " bytes=" + str(len(image)) + " runtime_executed=false primary_composition_proven=false promotion_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
