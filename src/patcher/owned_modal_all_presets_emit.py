"""Private frozen-semantics adapters for an authenticated all-preset parent.

The constructor supplies a predecessor it has just reconstructed and audited.
Only the three recursive predecessor-build admissions are replaced. Each
frozen emitter's native spans, old bytes, ownership guards, instruction body,
allocation checks and declared operands remain in its exact pinned snapshot.
No public function, module alias, stage, revision or selector is monkeypatched.
This module installs nothing and establishes no runtime evidence.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import sys
import types

from . import complete_hd_all_presets_candidate as parent

ROOT = Path(__file__).resolve().parents[2]
PINNED_SOURCES = {
    "src/patcher/complete_hd_all_presets_candidate.py": "856de49937c5d66b83a3dc7d5d22c94503fd2890147781580635eeabb7a91043",
    "src/patcher/framed_modal_slots.py": "9f1f840f798efda8b24683b9b2dbae78370c746bf2402ba50be113074fb6d468",
    "src/patcher/framed_modal_primary.py": "89020d158d7764a1a10d7ce082cd807b522637b84c0dbb01767e424b4b7f9f59",
    "src/patcher/framed_modal_primary_text.py": "8c280d5019261c286078cefcd714d3c47ad27f36640c08521a9d9f45e95bb73c",
    "src/patcher/framed_modal_widget_bounds.py": "1c248c1009f9db443ab056f57ab5bcf245bb8588598943ee751d0d13d94913cc",
    "src/patcher/pe_modal_slots_extension.py": "ead0d31f14126610bef5e8f720e07bfe30805ebef33c7ab2a8565bc7b70253a1",
    "src/patcher/pe_modal_primary_extension.py": "7583b3ad908259213e084b1aa1ac387b600c399cd7c0c4d0f683b24da7e25e46",
    "src/patcher/pe_modal_primary_text_extension.py": "178d6849acf65056d6be6fffca927d4c06f19e36eaca2b399dc844fc95356231",
    "tools/build_framed_modal_slots_candidate.py": "dd7c856cb8f5c7481c7d65f743d86dd141ded8d661f60478fa0b8de2e1c47c73",
    "tools/build_framed_modal_primary_candidate.py": "38649d57feba9fb12694a80015284cdc6be9164b8f67f3f26fc4b99ae55eb272",
    "tools/build_framed_modal_primary_text_candidate.py": "c71ed8c370a3a577d1709ddf8a22d97275c64f16bb7c43688fcd7376982bca9a",
    "tools/build_framed_modal_widgets_candidate.py": "2ff2b1923f4220de862e9dac46f5238db3954122c5e451e8e2a15408fd041ba6",
}
MODULE_ORDER = (
    "src/patcher/complete_hd_all_presets_candidate.py",
    "src/patcher/complete_hd_candidate.py",
    "src/patcher/framed_modal_slots.py", "src/patcher/pe_modal_slots_extension.py",
    "tools/build_framed_modal_slots_candidate.py",
    "src/patcher/framed_modal_primary.py", "src/patcher/pe_modal_primary_extension.py",
    "tools/build_framed_modal_primary_candidate.py",
    "src/patcher/framed_modal_primary_text.py", "src/patcher/pe_modal_primary_text_extension.py",
    "tools/build_framed_modal_primary_text_candidate.py",
    "src/patcher/framed_modal_widget_bounds.py", "tools/build_framed_modal_widgets_candidate.py",
)
ADAPTERS = {
    "slots": ("src/patcher/framed_modal_slots.py", "emit_modal_slots", (
        "rebuilt, context, _ = complete.build_candidate(original, f'{width}x{height}')",
        "pe._require(candidate == rebuilt, 'exact complete-HD v1 candidate reconstruction required')",
        "pe._require(context['recipe_revision'] == 'complete_hd_v1', 'explicit v1 predecessor required')")),
    "primary": ("src/patcher/framed_modal_primary.py", "emit_modal_primary", (
        "from tools import build_framed_modal_slots_candidate as builder",
        "rebuilt, context, _ = builder.build_candidate(original, f'{width}x{height}')",
        "pe._require(candidate == rebuilt, 'exact slots candidate reconstruction required')",
        "pe._require(context['recipe_revision'] == slots.REVISION, 'exact slots revision required')")),
    "text": ("src/patcher/framed_modal_primary_text.py", "emit_modal_primary_text", (
        "from tools import build_framed_modal_primary_candidate as builder",
        "rebuilt, context, _ = builder.build_candidate(original, f'{width}x{height}')",
        "pe._require(candidate == rebuilt, 'exact primary-v1 candidate reconstruction required')",
        "pe._require(context['stage'] == primary.STAGE and context['recipe_revision'] == primary.REVISION, "
        "'exact primary-v1 stage and revision required')")),
}


def _sources():
    parent._require(Path(parent.__file__).resolve() == ROOT / "src/patcher/complete_hd_all_presets_candidate.py"
                    and parent.ROOT == ROOT, "noncanonical authenticated parent module")
    result = parent._sources()
    for name, digest in PINNED_SOURCES.items():
        path = ROOT / name
        parent._require(path.resolve() == path and path.is_relative_to(ROOT), "noncanonical modal producer path")
        data = path.read_bytes()
        parent._require(parent.sha256(data) == digest, "reviewed modal producer source differs: " + name)
        result[name] = data
    return result


def _adapter_tree(source, path, name, admissions):
    """Retain all other AST statements; removed admissions must match exactly."""
    tree = ast.parse(source, str(path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    parent._require(len(functions) == 1, "exact frozen emitter function required")
    fn = functions[0]
    expected = [ast.dump(ast.parse(row).body[0], include_attributes=False) for row in admissions]
    dumps = [ast.dump(row, include_attributes=False) for row in fn.body]
    parent._require(all(dumps.count(row) == 1 for row in expected), "frozen predecessor admission differs")
    fn.body = [row for row, dump in zip(fn.body, dumps) if dump not in expected]
    fn.name = "_emit_from_context"
    fn.args.kwonlyargs.append(ast.arg(arg="context"))
    fn.args.kw_defaults.append(None)
    return ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))


@contextmanager
def _producer(sources):
    """Extend the parent's private snapshot namespace; never use public aliases."""
    with parent._producer({name: sources[name] for name in parent.PINNED_SOURCES}) as (army, pe, geometry):
        prefix = army.__name__.split(".", 1)[0]
        transformer = parent._PrivateImports(prefix)
        transformer.bare_tools.update(Path(name).stem for name in MODULE_ORDER if name.startswith("tools/"))
        modules = {}
        for name in MODULE_ORDER:
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__ = str(ROOT / name)
            module.__package__ = full.rpartition(".")[0]
            sys.modules[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)
            tree = transformer.visit(ast.parse(sources[name], module.__file__))
            exec(compile(tree, module.__file__, "exec"), module.__dict__)
            modules[name] = module
        for kind, (name, fn, admissions) in ADAPTERS.items():
            tree = _adapter_tree(sources[name], ROOT / name, fn, admissions)
            exec(compile(tree, str(ROOT / name), "exec"), modules[name].__dict__)
        yield modules, pe, geometry


def _emit(modules, kind, original, candidate, context, *, base_va, width, height):
    """Constructor-internal admission; a supplied manifest alone grants nothing."""
    parent._require(type(original) is bytes and parent.sha256(original) == parent.BASE_SHA256,
                    "unknown original executable SHA-256")
    parent._require(type(candidate) is bytes and type(context) is dict
                    and context.get("candidate_sha256") == parent.sha256(candidate)
                    and context.get("resolution") == f"{width}x{height}", "authenticated predecessor context differs")
    for key in parent.FALSE_CLAIMS:
        parent._require(context.get(key) is False, "predecessor acceptance must remain false")
    if kind == "widgets":
        module = modules["src/patcher/framed_modal_widget_bounds.py"]
        bundle = module._verified_bundle(original, candidate, context, base_va=base_va, width=width, height=height)
    else:
        parent._require(kind in ADAPTERS, "unknown private emitter")
        module = modules[ADAPTERS[kind][0]]
        bundle = module._emit_from_context(original, candidate, base_va=base_va, width=width, height=height, context=context)
    contract = dict(bundle.source_contract, predecessor_stage=context["stage"],
                    predecessor_revision=context["recipe_revision"], supplied_predecessor_reconstructed=True,
                    frozen_instruction_semantics=True, runtime_executed=False, primary_composition_proven=False,
                    manual_input_proof=False, promotion_ready=False)
    return replace(bundle, source_contract=contract)
