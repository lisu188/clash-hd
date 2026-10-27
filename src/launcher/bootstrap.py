#!/usr/bin/env python3
"""Path bootstrap for the Clash95 HD launcher modules.

Source and standalone import helper. Frozen builds authenticate their exact
raw-source resources before importing candidate constructors. It starts no
process and opens no window.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def require_bundled_sources() -> Path:
    if not getattr(sys, "frozen", False) or not getattr(sys, "_MEIPASS", None):
        raise ValueError("Verified standalone launcher resources are unavailable.")
    import launcher_bundle_identity
    import package_resources
    root = Path(sys._MEIPASS).resolve()
    files = package_resources.verify_resources(root, launcher_bundle_identity.INVENTORY_SHA256)
    package_resources.install_source_importer(root, files)
    return root


def bundled_sources_verified() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    try:
        require_bundled_sources()
    except (ImportError, AttributeError, OSError, ValueError):
        return False
    return True


def ensure_repo_paths() -> Path:
    if getattr(sys, "frozen", False):
        # The fixed importer supplies all application modules. Do not put the
        # raw resource tree on sys.path, where unlisted files could be loaded.
        return require_bundled_sources()
    root = REPO_ROOT
    for entry in (str(root / "tools"), str(root)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    return root
