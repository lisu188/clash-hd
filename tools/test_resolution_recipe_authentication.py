"""Source/RAM recipe-authentication tests; no executable outputs or runtime.

The default suite needs tracked source only. --original-backed reads the supplied
original once and reconstructs one representative of each supported recipe in
RAM. It never launches, installs, compiles or saves a candidate or probe.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import ExitStack
import copy
import dis
import hashlib
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

import resolution_recipe_authentication as auth

ORIGINAL = None
NAMESPACE_PREFIXES = ("_clash_recipe_authenticator_", "_clash_complete_recipe_")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def namespaces():
    return {name: module for name, module in sys.modules.items()
            if name.startswith(NAMESPACE_PREFIXES)}


def selection(revision="complete_hd_v1", resolution="1920x1080"):
    return dict(profile="completehd", resolution=resolution, recipe_revision=revision,
                stage=auth.RECIPES[revision][1])


def imports(code):
    for instruction in dis.get_instructions(code):
        if instruction.opname == "IMPORT_NAME":
            yield instruction.argval
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            yield from imports(constant)


class SourceTests(unittest.TestCase):
    def test_exact_two_recipe_scope_and_unsupported_matrix_cells(self):
        self.assertEqual(set(auth.RECIPES), {"complete_hd_v1", "complete_hd_all_presets_v1"})
        self.assertEqual(auth.RECIPES["complete_hd_all_presets_v1"][2], auth.PRESETS)
        self.assertNotIn("802x602", auth.RECIPES["complete_hd_v1"][2])
        for changed in (dict(profile="classic"), dict(profile="modalwidgets"),
                        dict(recipe_revision="caller_recipe"), dict(resolution="802x602"),
                        dict(resolution="1366x768"), dict(stage=auth.STABLE_STAGE)):
            values = selection(); values.update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                auth.rebuild_recipe(b"not original", **values)

    def test_original_identity_has_no_override_or_coercion(self):
        for original in (b"wrong", bytearray(b"wrong"), memoryview(b"wrong"), "wrong", True, b""):
            with self.subTest(type=type(original).__name__), self.assertRaises(ValueError):
                auth.rebuild_recipe(original, **selection())
        with self.assertRaises(TypeError):
            auth.rebuild_recipe(b"wrong", expected_base_sha256=sha(b"wrong"), **selection())

    def test_public_predicates_paths_builders_and_factories_cannot_execute(self):
        trap = Mock(side_effect=AssertionError("mutable public helper executed"))
        with ExitStack() as stack:
            for name in ("_sha", "_require", "_snapshot", "_unchanged", "_modules", "_build_api"):
                stack.enter_context(patch.object(auth, name, trap))
            for name, value in (("MODULE", Path("relative.py")), ("ROOT", Path("relative")),
                                ("BASE_SHA256", sha(b"wrong")), ("RECIPES", {}),
                                ("ast", types.SimpleNamespace()), ("sys", types.SimpleNamespace()),
                                ("uuid", types.SimpleNamespace()), ("types", types.SimpleNamespace())):
                stack.enter_context(patch.object(auth, name, value))
            rebuild, authenticate = auth._factory()
            with self.assertRaisesRegex(ValueError, "exact original executable"):
                rebuild(b"wrong", **selection_values())
            with self.assertRaisesRegex(ValueError, "exact original executable"):
                authenticate(b"wrong", candidate=b"wrong", metadata={}, probe="wrong", **selection_values())
        trap.assert_not_called()

    def test_factory_accepts_no_alternate_source_or_execution_arguments(self):
        for argument in ("_path", "_raw", "_exec", "_modules", "_parse"):
            with self.subTest(argument=argument), self.assertRaises(TypeError):
                auth._factory(**{argument: object()})

    def test_complete_fixed_source_graph_and_bare_import_rewriting(self):
        snapshot = auth._snapshot()
        self.assertEqual(len(snapshot), 27)
        self.assertEqual(sha(snapshot[auth.LEDGER][0]), auth.LEDGER_SHA256)
        self.assertEqual(sha(snapshot[auth.LEGACY][0]), auth.LEGACY_SHA256)
        self.assertEqual(snapshot[auth.SOURCE][0], auth.MODULE.read_bytes())
        public = types.ModuleType("build_framed_army_candidate")
        public.__getattr__ = Mock(side_effect=AssertionError("bare public module accessed"))
        with patch.dict(sys.modules, {"build_framed_army_candidate": public}):
            with auth._modules(snapshot) as constructors:
                legacy = constructors[auth.LEGACY]
                names = tuple(imports(legacy.build_candidate.__code__))
                self.assertTrue(any(name.endswith(".tools.build_framed_army_candidate") for name in names))
                self.assertNotIn("build_framed_army_candidate", names)
                self.assertTrue(all(not name.startswith(("src.", "tools.")) for name in names))
                for entry, module in constructors.items():
                    self.assertEqual(module.__file__, str(auth.ROOT / entry))
                    self.assertEqual(module.ROOT, auth.ROOT)
                    self.assertTrue(module.__name__.startswith("_clash_complete_recipe_"))
        public.__getattr__.assert_not_called()

    def test_absolute_and_bare_imports_preserve_python_bindings(self):
        snapshot = auth._snapshot()
        with auth._modules(snapshot) as constructors:
            prefix = constructors[auth.LEGACY].__name__.split(".")[0]
            raw = ("import src.patcher.pe_extension\n"
                   "import build_framed_army_candidate as army\n"
                   "from src.patcher import pe_extension as pe\n"
                   "from build_framed_army_candidate import STAGE as army_stage\n")
            tree = auth._ProjectImports(prefix, snapshot).visit(ast.parse(raw))
            ast.fix_missing_locations(tree); values = {}
            exec(compile(tree, "<pure import fixture>", "exec"), values)
            self.assertIs(values["src"], sys.modules[prefix + ".src"])
            self.assertIs(values["army"], sys.modules[prefix + ".tools.build_framed_army_candidate"])
            self.assertIs(values["pe"], sys.modules[prefix + ".src.patcher.pe_extension"])
            self.assertEqual(values["army_stage"], values["army"].STAGE)

    def test_unknown_absolute_and_relative_project_imports_fail_closed(self):
        snapshot = auth._snapshot()
        with self.assertRaisesRegex(ValueError, "absent from the canonical ledger"):
            auth._ProjectImports("private", snapshot).visit(ast.parse("import src.patcher.caller_fake"))
        with auth._modules(snapshot) as constructors:
            prefix = constructors[auth.LEGACY].__name__.split(".")[0]
            for raw in ("from src.patcher import caller_fake", "from . import caller_fake"):
                tree = auth._ProjectImports(prefix, snapshot).visit(ast.parse(raw)); ast.fix_missing_locations(tree)
                with self.subTest(raw=raw), self.assertRaises(ImportError):
                    exec(compile(tree, "<missing import fixture>", "exec"),
                         {"__package__": prefix + ".src.patcher"})

    def test_private_namespaces_and_path_restore_on_success_and_failure(self):
        snapshot = auth._snapshot(); before = namespaces(); paths = list(sys.path)
        with auth._modules(snapshot):
            self.assertNotEqual(namespaces(), before)
        self.assertEqual(namespaces(), before); self.assertEqual(sys.path, paths)
        with self.assertRaisesRegex(RuntimeError, "intentional consumer failure"):
            with auth._modules(snapshot):
                sys.path.insert(0, "pure temporary alias")
                raise RuntimeError("intentional consumer failure")
        self.assertEqual(namespaces(), before); self.assertEqual(sys.path, paths)

    def test_namespace_cleanup_removes_only_owned_module_identities(self):
        foreign = types.ModuleType("foreign_fixture")
        replaced = None
        try:
            with auth._modules(auth._snapshot()) as constructors:
                replaced = constructors[auth.LEGACY].__name__
                sys.modules[replaced] = foreign
            self.assertIs(sys.modules[replaced], foreign)
        finally:
            if replaced and sys.modules.get(replaced) is foreign:
                del sys.modules[replaced]

    def test_changed_dependency_bytes_fail_without_filesystem_writes(self):
        read = Path.read_bytes; target = auth.ROOT / "src/patcher/framed_viewport.py"
        def changed(path):
            raw = read(path)
            return raw + b"\n# modeled source drift\n" if path == target else raw
        with patch.object(Path, "read_bytes", changed), self.assertRaisesRegex(ValueError, "source pin differs"):
            auth._snapshot()

    def test_post_snapshot_change_rejects_original_raw_source(self):
        snapshot = auth._snapshot(); read = Path.read_bytes; target = auth.ROOT / auth.LEGACY
        def changed(path):
            raw = read(path)
            return raw[:-1] + bytes([raw[-1] ^ 1]) if path == target else raw
        with patch.object(Path, "read_bytes", changed), self.assertRaisesRegex(ValueError, "source pin differs"):
            auth._unchanged(snapshot)

    def test_own_source_change_rejects_before_any_candidate_reconstruction(self):
        read = Path.read_bytes
        def changed(path):
            raw = read(path)
            return raw + b"\n# modeled drift\n" if path == auth.MODULE else raw
        with patch.object(Path, "read_bytes", changed):
            with self.assertRaisesRegex(ValueError, "authenticator source changed"):
                auth.rebuild_recipe(b"wrong", **selection())
            with self.assertRaisesRegex(ValueError, "source changed before private execution"):
                auth._factory()

    def test_factory_requires_one_exact_terminal_call_before_execution(self):
        canonical = ast.parse(auth.MODULE.read_bytes())
        calls = [n for n in ast.walk(canonical) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "_factory"]
        self.assertEqual(len(calls), 1)
        # This is a parser model only; no altered source is written or admitted.
        for extra in ("if False:\n    _factory()\n", "_factory()\n"):
            tree = copy.deepcopy(canonical)
            tree.body[0:0] = ast.parse(extra).body
            with patch.object(ast, "parse", return_value=tree):
                modeled_factory = auth._make_factory()
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, "sole exact source-owned factory"):
                modeled_factory()


def selection_values():
    # Literal independent values remain valid while public RECIPES is poisoned.
    return dict(profile="completehd", resolution="1920x1080", recipe_revision="complete_hd_v1",
        stage="gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-validation")


class OriginalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if ORIGINAL is None:
            raise unittest.SkipTest("explicit --original-backed read-only RAM audit not requested")
        cls.original = ORIGINAL.read_bytes()
        if sha(cls.original) != auth.BASE_SHA256:
            raise ValueError("original fixture SHA differs")
        cls.original_digest = sha(cls.original)
        cls.saved_path = list(sys.path)
        sys.path.insert(0, str(auth.ROOT))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "saved_path"):
            sys.path[:] = cls.saved_path

    def verify_recipe(self, revision, resolution):
        values = selection(revision, resolution)
        module = importlib.import_module(auth.RECIPES[revision][0].removesuffix(".py").replace("/", "."))
        baseline = module.build_candidate(self.original, resolution)
        trap = Mock(side_effect=AssertionError("public producer alias executed"))
        fake = {}
        for name in auth._snapshot():
            if name == auth.SOURCE:
                continue
            key = name.removesuffix(".py").replace("/", ".")
            alias = types.ModuleType(key); alias.__file__ = str(auth.ROOT / name)
            alias.__getattr__ = trap; alias.build_candidate = trap
            fake[key] = alias
            if name.startswith("tools/"):
                fake[Path(name).stem] = alias
        with patch.dict(sys.modules, fake), patch.object(module, "build_candidate", trap), \
                patch.object(auth, "_sha", trap), patch.object(auth, "_snapshot", trap):
            rebuilt = auth.rebuild_recipe(self.original, **values)
            self.assertEqual((rebuilt["image"], rebuilt["metadata"], rebuilt["probe"]), baseline)
            accepted = auth.authenticate_recipe(self.original, candidate=rebuilt["image"],
                metadata=rebuilt["metadata"], probe=rebuilt["probe"], **values)
            self.assertEqual(accepted, rebuilt)
        trap.assert_not_called()
        self.assertEqual(rebuilt["source_hashes"][auth.SOURCE], sha(auth.MODULE.read_bytes()))
        self.assertEqual(len(rebuilt["source_hashes"]), 27)
        self.assertFalse(rebuilt["projection"])
        for name in ("runtime_executed", "manual_input_proof", "promotion_ready"):
            self.assertIs(rebuilt["metadata"][name], False)
        # Reapply authored old/new records independently; old bytes must match.
        output = bytearray(self.original)
        for record in rebuilt["metadata"]["patch_records"]:
            offset = record["file_offset"]; old = bytes.fromhex(record["old_hex"]); new = bytes.fromhex(record["new_hex"])
            self.assertEqual(bytes(output[offset:offset + len(old)]), old)
            output[offset:offset + len(old)] = new
        self.assertEqual(bytes(output), rebuilt["image"])
        for changed in (dict(candidate=b"substituted"), dict(probe=rebuilt["probe"] + ".echo invented\n"),
                        dict(metadata={**rebuilt["metadata"], "promotion_ready": True})):
            supplied = dict(candidate=rebuilt["image"], metadata=rebuilt["metadata"], probe=rebuilt["probe"])
            supplied.update(changed)
            with self.subTest(changed=next(iter(changed))), self.assertRaisesRegex(ValueError, "private reconstruction"):
                auth.authenticate_recipe(self.original, **supplied, **values)
        self.assertEqual(sha(self.original), self.original_digest)
        self.assertEqual(sha(ORIGINAL.read_bytes()), self.original_digest)

    def test_legacy_1920_private_rebuild_with_hostile_public_aliases(self):
        self.verify_recipe("complete_hd_v1", "1920x1080")

    def test_successor_1366_private_rebuild_with_hostile_public_aliases(self):
        self.verify_recipe("complete_hd_all_presets_v1", "1366x768")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", type=Path)
    arguments, remaining = parser.parse_known_args()
    ORIGINAL = arguments.original_backed
    unittest.main(argv=[sys.argv[0], *remaining])
