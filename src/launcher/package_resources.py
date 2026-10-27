"""Fixed source resources for the standalone launcher; no game data is bundled.

The inventory digest is embedded as compiled build metadata. Raw Python files
retain their exact bytes and paths because candidate constructors authenticate
their own source. A frozen launcher imports those verified files directly,
instead of substituting PyInstaller bytecode paths for canonical source paths.
"""
from __future__ import annotations

import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys


SCHEMA = "clash_hd_launcher_resources_v1"
INVENTORY_NAME = "launcher-source-inventory.json"
# Reviewed application closure, never a directory glob or a checkout snapshot.
SOURCE_FILES = (
    "patch_clash95_hd.py",
    "src/display_plan.py",
    "src/launcher/__init__.py",
    "src/launcher/bootstrap.py",
    "src/launcher/classic.py",
    "src/launcher/completehd.py",
    "src/launcher/core.py",
    "src/launcher/framed.py",
    "src/launcher/gui.py",
    "src/launcher/ini.py",
    "src/launcher/modalwidgets.py",
    "src/launcher/multires.py",
    "src/launcher/package_resources.py",
    "src/launcher/presets.py",
    "src/launcher/run.py",
    "src/launcher/settings.py",
    "src/patcher/classic_all_presets_candidate.py",
    "src/patcher/classic_menu_candidate.py",
    "src/patcher/complete_hd_all_presets_candidate.py",
    "src/patcher/complete_hd_candidate.py",
    "src/patcher/four_sided_frame.py",
    "src/patcher/framed_all_presets_candidate.py",
    "src/patcher/framed_army_composition.py",
    "src/patcher/framed_army_draw.py",
    "src/patcher/framed_army_input.py",
    "src/patcher/framed_army_viewport.py",
    "src/patcher/framed_bounded_input.py",
    "src/patcher/framed_bounded_paint.py",
    "src/patcher/framed_camera.py",
    "src/patcher/framed_full_paint.py",
    "src/patcher/framed_input.py",
    "src/patcher/framed_minimap.py",
    "src/patcher/framed_modal_canvas.py",
    "src/patcher/framed_modal_primary.py",
    "src/patcher/framed_modal_primary_text.py",
    "src/patcher/framed_modal_slots.py",
    "src/patcher/framed_modal_widget_bounds.py",
    "src/patcher/framed_presentation.py",
    "src/patcher/framed_recipe.py",
    "src/patcher/framed_viewport.py",
    "src/patcher/hd_multires_candidate.py",
    "src/patcher/hd_multires_bounded.py",
    "src/patcher/hd_multires_classic_bounded.py",
    "src/patcher/hd_multires_issuer.py",
    "src/patcher/initial_map_paint.py",
    "src/patcher/modal_widgets_all_presets_candidate.py",
    "src/patcher/owned_modal_all_presets_emit.py",
    "src/patcher/partial_tile_clip.py",
    "src/patcher/partial_tile_hooks.py",
    "src/patcher/patch_clash95_hd.py",
    "src/patcher/pe_army_extension.py",
    "src/patcher/pe_extension.py",
    "src/patcher/pe_modal_extension.py",
    "src/patcher/pe_modal_primary_extension.py",
    "src/patcher/pe_modal_primary_text_extension.py",
    "src/patcher/pe_modal_slots_extension.py",
    "tools/build_framed_army_candidate.py",
    "tools/build_framed_candidate.py",
    "tools/build_framed_modal_candidate.py",
    "tools/build_framed_modal_primary_candidate.py",
    "tools/build_framed_modal_primary_text_candidate.py",
    "tools/build_framed_modal_slots_candidate.py",
    "tools/build_framed_modal_widgets_candidate.py",
    "tools/build_partial_tile_candidate.py",
    "tools/modal_primary_text_context.py",
    "tools/modal_widgets_context.py",
    "tools/partial_tile_trace_probe.py",
    "tools/process_hygiene_guard.py",
    "tools/run_framed_offline_tests.py",
)
DATA_FILES = ("src/launcher/resolutions.json", "dxcfg_windowed.ini")
RESOURCE_FILES = SOURCE_FILES + DATA_FILES
_SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_INVENTORY_BYTES = 128 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _plain_file(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or pure.as_posix() != relative or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError("Invalid bundled resource path: " + relative)
    path = root.joinpath(*pure.parts)
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink() or getattr(part.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Bundled resource aliases are forbidden: " + relative)
    if path.resolve() != path or not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Bundled resource is missing, oversized or noncanonical: " + relative)
    return path


def _read(root: Path, relative: str) -> bytes:
    path = _plain_file(root, relative)
    with path.open("rb") as stream:
        data = stream.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Bundled resource exceeds its read bound: " + relative)
    return data


def inventory_bytes(root: Path) -> bytes:
    """Build metadata from only the fixed public-source allowlist."""
    root = Path(root).resolve()
    resources = {relative: sha256(_read(root, relative)) for relative in RESOURCE_FILES}
    return (json.dumps({"schema": SCHEMA, "files": resources}, sort_keys=True, indent=2) + "\n").encode("utf-8")


def verify_resources(root: Path, expected_inventory_sha256: str) -> dict[str, str]:
    """Reject absent, changed or substituted resource inventories and source."""
    root = Path(root).resolve()
    if type(expected_inventory_sha256) is not str or not _SHA.fullmatch(expected_inventory_sha256):
        raise ValueError("Standalone launcher has no embedded resource identity.")
    raw = _read(root, INVENTORY_NAME)
    if len(raw) > MAX_INVENTORY_BYTES or sha256(raw) != expected_inventory_sha256:
        raise ValueError("Standalone launcher resource inventory differs from the build.")

    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("Duplicate bundled resource key: " + name)
            result[name] = value
        return result

    declared = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    if (type(declared) is not dict or set(declared) != {"schema", "files"}
            or declared["schema"] != SCHEMA or type(declared["files"]) is not dict
            or set(declared["files"]) != set(RESOURCE_FILES)):
        raise ValueError("Standalone launcher resource allowlist differs from the build.")
    for relative, expected in declared["files"].items():
        if type(expected) is not str or not _SHA.fullmatch(expected) or sha256(_read(root, relative)) != expected:
            raise ValueError("Standalone launcher source preflight failed: " + relative)
    return declared["files"]


class _RawSourceLoader(importlib.abc.Loader):
    def __init__(self, root: Path, relative: str, digest: str):
        self.root, self.relative, self.digest = root, relative, digest

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        source = _read(self.root, self.relative)
        if sha256(source) != self.digest:
            raise ImportError("Bundled source changed before import: " + self.relative)
        # Do not consume or create pyc files: source bytes and __file__ are part
        # of the candidate constructors' original authentication contract.
        exec(compile(source, str(self.root / self.relative), "exec", dont_inherit=True), module.__dict__)


class _BundledSources(importlib.abc.MetaPathFinder):
    def __init__(self, root: Path, files: dict[str, str]):
        self.root, self.files = root, files
        self.modules = {}
        for path in SOURCE_FILES:
            module = path.removesuffix(".py").replace("/", ".")
            if module.endswith(".__init__"):
                module = module.removesuffix(".__init__")
            self.modules[module] = path
            if path.startswith(("tools/", "src/launcher/")) and not path.endswith("/__init__.py"):
                self.modules[Path(path).stem] = path

    def find_spec(self, fullname, path=None, target=None):
        relative = self.modules.get(fullname)
        if relative is not None:
            package = relative.endswith("/__init__.py")
            return importlib.util.spec_from_file_location(fullname, self.root / relative,
                loader=_RawSourceLoader(self.root, relative, self.files[relative]),
                submodule_search_locations=[str((self.root / relative).parent)] if package else None)
        if fullname in ("src", "src.patcher", "tools"):
            spec = importlib.machinery.ModuleSpec(fullname, loader=None, is_package=True)
            spec.submodule_search_locations = [str(self.root / fullname.replace(".", "/"))]
            return spec
        if fullname.startswith(("src.", "tools.")):
            raise ModuleNotFoundError("Application module is outside the bundled source allowlist: " + fullname)
        return None


def install_source_importer(root: Path, verified_files: dict[str, str]) -> None:
    root = Path(root).resolve()
    if set(verified_files) != set(RESOURCE_FILES):
        raise ValueError("Only the complete verified resource closure can be imported.")
    for finder in sys.meta_path:
        if isinstance(finder, _BundledSources):
            if finder.root != root or finder.files != verified_files:
                raise ValueError("A different bundled source context is already active.")
            return
    sys.meta_path.insert(0, _BundledSources(root, dict(verified_files)))
