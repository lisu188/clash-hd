"""Private source issuer for the versioned HD launcher constructors.

Public module aliases do not select code. Each call rereads exact source,
compiles a fresh isolated namespace, and rechecks every source before returning.
The frozen constructors retain their own deeper source/byte authentication.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import importlib
from pathlib import Path
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/patcher/hd_multires_issuer.py"
FROZEN_SOURCE_PINS = {
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/four_sided_frame.py": "433fd27fb8afda4a12f5539604f722f18bf8d37885125e30ee9cfb948926c2a9",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/framed_camera.py": "f8caea185f3714a6924a4e4cb40aa049866fc7864afa41a66da1b56a93059ef8",
    "src/patcher/framed_bounded_paint.py": "981d946007b0438051dba033dce9e8e442cb7863ee49c547fbaad1e35d66cf1f",
    "src/patcher/framed_bounded_input.py": "8117232bb875b1a0f9fb179b7a77ec7325e633ce283574b7f9b8cc3d37589258",
    "src/patcher/classic_all_presets_candidate.py": "29a4e16cbe649d1801317f61b0a85d968a0a8e6f37032dfe4552203f64110f26",
    "src/patcher/framed_all_presets_candidate.py": "19aff1e4ed6ab34fe2ab209921ae1f5e950805a7b553965df0faa805939451a2",
    "src/patcher/complete_hd_all_presets_candidate.py": "856de49937c5d66b83a3dc7d5d22c94503fd2890147781580635eeabb7a91043",
    "src/patcher/owned_modal_all_presets_emit.py": "6089243ccd79a8b312ca39dcdbdfaa2aad631637898cf8063b393db119a05f3c",
    "src/patcher/modal_widgets_all_presets_candidate.py": "9c7abbcbb137b75ece5d45d2b13496f04a72b90bf13654af1c3c11f1015cf2fe",
}
MODULE_ORDER = (*FROZEN_SOURCE_PINS, "src/patcher/hd_multires_classic_bounded.py",
                "src/patcher/hd_multires_bounded.py",
                "src/patcher/hd_multires_candidate.py")
MAX_SOURCE_BYTES = 4 * 1024 * 1024


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _read(relative):
    _require(type(relative) is str and "\\" not in relative and ":" not in relative
             and all(part not in ("", ".", "..") for part in relative.split("/")),
             "issuer source path must be canonical")
    path = ROOT / relative
    _require(path.resolve() == path, "issuer source path is aliased: " + relative)
    for node in (path, *path.parents):
        if node == ROOT:
            break
        _require(not node.is_symlink() and not (getattr(node.lstat(), "st_file_attributes", 0) & 0x400),
                 "issuer source path must not use links: " + relative)
    _require(path.is_file() and path.stat().st_size <= MAX_SOURCE_BYTES,
             "issuer source is missing or oversized: " + relative)
    data = path.read_bytes()
    _require(len(data) <= MAX_SOURCE_BYTES, "issuer source exceeds its read bound")
    return data


def _snapshot(issuer_bytes):
    sources = {name: _read(name) for name in (*MODULE_ORDER, SOURCE)}
    _require(sources[SOURCE] == issuer_bytes, "canonical issuer source changed after binding")
    for name, digest in FROZEN_SOURCE_PINS.items():
        _require(_sha(sources[name]) == digest, "frozen issuer source pin differs: " + name)
    return sources


def _recheck(sources):
    _require(all(_read(name) == data for name, data in sources.items()),
             "issuer source changed during reconstruction")


class _PrivateImports(ast.NodeTransformer):
    def __init__(self, prefix):
        self.prefix = prefix

    def visit_ImportFrom(self, node):
        if not node.level and node.module and (node.module in ("src", "tools")
                or node.module.startswith(("src.", "tools."))):
            node.module = self.prefix + "." + node.module
        return node


@contextmanager
def _private_modules(sources):
    prefix = "_clash95_hd_issuer_" + uuid.uuid4().hex
    modules = {}
    try:
        for suffix in ("", ".src", ".src.patcher", ".tools"):
            package = types.ModuleType(prefix + suffix)
            package.__path__ = []
            sys.modules[package.__name__] = package
            if suffix:
                parent, _, leaf = package.__name__.rpartition(".")
                setattr(sys.modules[parent], leaf, package)
        for name in MODULE_ORDER:
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__ = str(ROOT / name)
            module.__package__ = full.rpartition(".")[0]
            module._HD_MULTIRES_PRIVATE = True
            modules[name] = module
            sys.modules[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)

        def resolve(name, package=None):
            if name.startswith(("src.", "tools.")) or name in ("src", "tools"):
                full = prefix + "." + name
                _require(full in sys.modules, "unregistered private issuer dependency: " + name)
                return sys.modules[full]
            # Module-local import dispatch does not mutate Python's importlib.
            return importlib.import_module(name, package)

        for name in MODULE_ORDER:
            module = modules[name]
            tree = _PrivateImports(prefix).visit(ast.parse(sources[name], module.__file__))
            exec(compile(tree, module.__file__, "exec"), module.__dict__)
            _require(Path(module.__file__).resolve() == ROOT / name,
                     "private issuer module source identity changed")
            if "importlib" in module.__dict__:
                module.importlib = types.SimpleNamespace(import_module=resolve)
        yield modules
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]


def _make_issuer(issuer_bytes):
    # This function runs in its own unregistered raw-source namespace, so public
    # mutable pins/helpers/import aliases cannot select subsequent execution.
    def invoke(kind, original=None, resolution=None, profile=None):
        snapshots = _snapshot(issuer_bytes)
        with _private_modules(snapshots) as modules:
            module = modules["src/patcher/hd_multires_candidate.py"]
            base_sources = module._source_hashes
            context_hashes = {name: _sha(data) for name, data in snapshots.items()}

            def source_hashes(selected):
                result = base_sources(selected)
                _require(type(result) is dict, "private constructor source inventory is invalid")
                for name, digest in context_hashes.items():
                    _require(name not in result or result[name] == digest,
                             "private constructor source identity conflicts: " + name)
                return dict(sorted((result | context_hashes).items()))

            module._source_hashes = source_hashes
            try:
                result = (source_hashes(profile) if kind == "sources" else
                          module._build_candidate(original, resolution, profile=profile))
            finally:
                _recheck(snapshots)
        return result

    def build_candidate(original, resolution, *, profile):
        return invoke("build", original, resolution, profile)

    def source_hashes(profile):
        return invoke("sources", profile=profile)

    return build_candidate, source_hashes


def create_issuer():
    """Capture a private factory once; returned public signatures take no hooks."""
    path = Path(__file__).resolve()
    _require(path == ROOT / SOURCE, "noncanonical HD issuer module")
    source = _read(SOURCE)
    values = {"__file__": str(path), "__name__": "_clash95_hd_issuer_factory",
              "__package__": None}
    exec(compile(source, str(path), "exec"), values)
    return values["_make_issuer"](source)
