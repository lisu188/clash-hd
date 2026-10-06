"""Privately reconstruct two Complete HD recipes without writing candidates.

This is a byte/source authentication boundary, not runtime or release evidence.
The frozen Complete all-preset source ledger supplies the complete legacy
dependency graph. Public builder modules, matrix helpers and pyc files cannot
choose an implementation. Unsupported profiles and revisions fail explicitly.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[1]
MODULE = Path(__file__).resolve()
SOURCE = "tools/resolution_recipe_authentication.py"
LEDGER = "src/patcher/complete_hd_all_presets_candidate.py"
LEDGER_SHA256 = "856de49937c5d66b83a3dc7d5d22c94503fd2890147781580635eeabb7a91043"
LEGACY = "src/patcher/complete_hd_candidate.py"
LEGACY_SHA256 = "e406149480e9cdf1ba0314f5e9ae735d7b587f61772afac4b0b9e7ce9fd3bd06"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
STABLE_STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
                "presentbounds-minimapright-dynvswitch")
PRESETS = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
           "1920x1080", "2560x1440", "3440x1440", "3840x2160")
RECIPES = {
    "complete_hd_v1": (LEGACY, STABLE_STAGE + "-completehd-validation",
                       ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080")),
    "complete_hd_all_presets_v1": (LEDGER, STABLE_STAGE + "-completehd-allpresets-validation", PRESETS),
}
MAX_ORIGINAL_BYTES = 64 * 1024**2
MAX_SOURCE_BYTES = 2 * 1024**2
MAX_GRAPH_BYTES = 16 * 1024**2
_IMPORTED_SOURCE = MODULE.read_bytes()


def _require(value, message):
    if not value:
        raise ValueError(message)


def _sha(raw):
    _require(type(raw) is bytes, "exact immutable bytes required")
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _stamp(value):
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def _read_source(name, expected=None):
    _require(type(name) is str and name.endswith(".py") and not name.startswith(("/", "\\"))
             and ":" not in name and "\\" not in name and ".." not in name.split("/"),
             "fixed canonical source path required")
    path = ROOT / name
    _require(path.resolve(strict=True) == path and path.is_relative_to(ROOT), "source path escapes canonical checkout")
    for entry in (path, *path.parents):
        _require(not entry.is_symlink() and not getattr(entry, "is_junction", lambda: False)()
                 and not getattr(entry.stat(), "st_file_attributes", 0) & 0x400, "reparsed source path")
    before = path.stat()
    _require(0 < before.st_size <= MAX_SOURCE_BYTES, "bounded canonical source required")
    raw = path.read_bytes()
    after = path.stat()
    _require(_stamp(before) == _stamp(after), "source changed while reading: " + name)
    _require(expected is None or _sha(raw) == expected, "frozen source pin differs: " + name)
    return raw, _stamp(after)


def _literal(raw, name):
    rows = [node.value for node in ast.parse(raw).body if isinstance(node, ast.Assign)
            and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name]
    _require(len(rows) == 1, "one fixed literal source declaration required: " + name)
    return ast.literal_eval(rows[0])


def _snapshot():
    _require(MODULE == ROOT / SOURCE, "authenticator loaded from another checkout")
    ledger = _read_source(LEDGER, LEDGER_SHA256)
    pins = _literal(ledger[0], "PINNED_SOURCES")
    # MODULE_ORDER uses a source expression rather than a literal. Its exact
    # source is pinned; recover the order only after private source execution.
    _require(type(pins) is dict and pins.get(LEGACY) == LEGACY_SHA256
             and all(type(name) is type(digest) is str and len(digest) == 64
                     and all(c in "0123456789abcdef" for c in digest) for name, digest in pins.items()),
             "exact frozen Complete dependency ledger required")
    result = {LEDGER: ledger, SOURCE: _read_source(SOURCE)}
    for name, digest in pins.items():
        result[name] = _read_source(name, digest)
    _require(sum(len(raw) for raw, _ in result.values()) <= MAX_GRAPH_BYTES, "bounded complete source graph required")
    return result


def _unchanged(snapshot):
    for name, (raw, stamp) in snapshot.items():
        current, current_stamp = _read_source(name, _sha(raw))
        _require(current == raw and current_stamp == stamp, "source changed during reconstruction: " + name)


class _ProjectImports(ast.NodeTransformer):
    """Route every known project import to an empty-path private package."""
    def __init__(self, prefix, sources):
        self.prefix = prefix
        self.names = {name.removesuffix(".py").replace("/", ".") for name in sources}
        self.bare = {Path(name).stem: name.removesuffix(".py").replace("/", ".")
                     for name in sources if name.startswith("tools/")}

    def _mapped(self, name):
        if name in self.bare:
            return self.prefix + "." + self.bare[name]
        if name == "src" or name == "tools" or name.startswith(("src.", "tools.")):
            _require(name in self.names or name in ("src", "src.patcher", "tools"),
                     "project import is absent from the canonical ledger: " + name)
            return self.prefix + "." + name
        return None

    def visit_ImportFrom(self, node):
        if node.level:
            # Empty __path__ and the privately registered canonical modules
            # resolve relative imports; an undeclared dependency cannot load.
            return node
        if node.module:
            mapped = self._mapped(node.module)
            if mapped is not None:
                node.module = mapped
        return node

    def visit_Import(self, node):
        output = []
        for alias in node.names:
            mapped = self._mapped(alias.name)
            if mapped is None:
                output.append(ast.Import(names=[alias]))
            elif alias.asname or "." not in alias.name:
                output.append(ast.Import(names=[ast.alias(name=mapped, asname=alias.asname or alias.name)]))
            else:
                # Preserve `import src.patcher.x`'s local binding to src, not x.
                output.append(ast.Import(names=[ast.alias(name=mapped, asname="_canonical_imported_module")]))
                root = alias.name.split(".")[0]
                output.append(ast.ImportFrom(module=self.prefix, names=[ast.alias(name=root, asname=root)], level=0))
        return [ast.copy_location(item, node) for item in output]


@contextmanager
def _modules(snapshot):
    prefix = "_clash_complete_recipe_" + uuid.uuid4().hex
    owned = {}
    original_path = list(sys.path)
    def add(name, module):
        _require(name not in sys.modules, "private namespace collision")
        sys.modules[name] = module
        owned[name] = module
    try:
        for suffix in ("", ".src", ".src.patcher", ".tools"):
            name = prefix + suffix
            package = types.ModuleType(name)
            package.__path__ = []
            add(name, package)
            if suffix:
                parent, _, leaf = name.rpartition(".")
                setattr(owned[parent], leaf, package)
        def execute(name):
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__, module.__package__ = str(ROOT / name), full.rpartition(".")[0]
            add(full, module)
            setattr(owned[module.__package__], full.rpartition(".")[2], module)
            tree = _ProjectImports(prefix, snapshot).visit(ast.parse(snapshot[name][0], module.__file__))
            ast.fix_missing_locations(tree)
            exec(compile(tree, module.__file__, "exec"), module.__dict__)
            _require(module.__file__ == str(ROOT / name) and module.__name__ == full,
                     "private source module identity changed")
            return module
        # This source imports only standard-library modules at top level.
        # Its pinned order supplies the exact dependencies for both recipes.
        ledger = execute(LEDGER)
        order = ledger.MODULE_ORDER
        _require(type(order) is tuple and len(set(order)) == len(order)
                 and set(order) == set(snapshot) - {SOURCE, LEDGER, LEGACY},
                 "source-owned Complete dependency order differs from ledger")
        for name in order:
            execute(name)
        legacy = execute(LEGACY)
        yield {LEDGER: ledger, LEGACY: legacy}
    finally:
        for name, module in reversed(tuple(owned.items())):
            if sys.modules.get(name) is module:
                del sys.modules[name]
        sys.path[:] = original_path


def _build_api(imported):
    source_path, imported_raw = MODULE, imported
    snapshotter, unchanged, modules, sha, require = _snapshot, _unchanged, _modules, _sha, _require
    recipes, presets, base_sha = dict(RECIPES), PRESETS, BASE_SHA256
    def guard():
        require(source_path.read_bytes() == imported_raw, "authenticator source changed since private compilation")
    def rebuild_recipe(original, *, profile, resolution, recipe_revision, stage):
        guard()
        require(type(profile) is str and profile == "completehd" and type(recipe_revision) is str
                and recipe_revision in recipes, "only the two fixed Complete HD recipes are supported")
        entry, expected_stage, resolutions = recipes[recipe_revision]
        require(type(resolution) is str and resolution in resolutions and resolution in presets
                and type(stage) is str and stage == expected_stage, "exact supported preset and recipe stage required")
        require(type(original) is bytes and 0 < len(original) <= MAX_ORIGINAL_BYTES
                and sha(original) == base_sha, "exact original executable required; no override")
        sources = snapshotter()
        require(sources[SOURCE][0] == imported_raw, "authenticator snapshot differs from privately compiled bytes")
        with modules(sources) as loaded:
            constructor = loaded[entry]
            require(constructor.ROOT == ROOT and constructor.BASE_SHA256 == base_sha
                    and constructor.REVISION == recipe_revision and constructor.STAGE == expected_stage,
                    "canonical recipe identity differs")
            result = constructor.build_candidate(original, resolution)
        require(type(result) is tuple and len(result) == 3 and type(result[0]) is bytes
                and type(result[1]) is dict and type(result[2]) is str, "exact canonical bundle types required")
        image, metadata, probe = result
        require(metadata.get("stage") == expected_stage and metadata.get("resolution") == resolution
                and metadata.get("recipe_revision") == recipe_revision and metadata.get("base_sha256") == base_sha
                and metadata.get("candidate_sha256") == sha(image)
                and metadata.get("probe_sha256") == sha(probe.encode("utf-8")), "canonical bundle identity differs")
        pins = metadata.get("source_hashes")
        require(type(pins) is dict and pins and all(name in sources and value == sha(sources[name][0])
                for name, value in pins.items()), "canonical producer source pins differ")
        unchanged(sources)
        guard()
        return dict(image=image, metadata=metadata, probe=probe, projection=False,
                    source_hashes={name: sha(raw) for name, (raw, _) in sources.items()})
    def authenticate_recipe(original, *, candidate, metadata, probe, **selection):
        require(type(candidate) is bytes and type(metadata) is dict and type(probe) is str,
                "exact supplied bundle types required")
        result = rebuild_recipe(original, **selection)
        require(candidate == result["image"] and _canonical(metadata) == _canonical(result["metadata"])
                and probe == result["probe"], "supplied bytes, metadata or canonical probe differ from private reconstruction")
        guard()
        return result
    return rebuild_recipe, authenticate_recipe


def _make_factory():
    # A zero-argument closure captures canonical issuance inputs. No caller can
    # supply a different source path, bytes, compiler, importer or source hash.
    path, raw = MODULE, _IMPORTED_SOURCE
    registered, module_type, fresh = sys.modules, types.ModuleType, uuid.uuid4
    parse, walk, compiler, execute, require = ast.parse, ast.walk, compile, exec, _require
    call_type, name_type, assign_type, tuple_type = ast.Call, ast.Name, ast.Assign, ast.Tuple
    def factory():
        """Execute canonical own source before any mutable public helper alias."""
        require(path.read_bytes() == raw, "authenticator source changed before private execution")
        tree = parse(raw, filename=str(path))
        calls = [node for node in walk(tree) if isinstance(node, call_type)
                 and isinstance(node.func, name_type) and node.func.id == "_factory"]
        terminal = tree.body[-1]
        require(len(calls) == 1 and isinstance(terminal, assign_type) and len(terminal.targets) == 1
              and isinstance(terminal.targets[0], tuple_type)
              and tuple(getattr(node, "id", None) for node in terminal.targets[0].elts) == ("rebuild_recipe", "authenticate_recipe")
              and isinstance(terminal.value, call_type) and isinstance(terminal.value.func, name_type)
              and terminal.value.func.id == "_factory" and not terminal.value.args and not terminal.value.keywords,
              "sole exact source-owned factory required")
        tree.body.pop()
        name = "_clash_recipe_authenticator_" + fresh().hex
        require(name not in registered, "private authenticator namespace collision")
        module = module_type(name)
        module.__file__ = str(path)
        registered[name] = module
        try:
            execute(compiler(tree, str(path), "exec"), module.__dict__)
            result = module._build_api(raw)
            require(path.read_bytes() == raw, "authenticator source changed during private execution")
            return result
        finally:
            if registered.get(name) is module:
                del registered[name]
    return factory


_factory = _make_factory()


rebuild_recipe, authenticate_recipe = _factory()
