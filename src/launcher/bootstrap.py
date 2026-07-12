#!/usr/bin/env python3
"""Path bootstrap for the Clash95 HD launcher modules.

Repo-only import helper: it prepends the repository root (for the
``patch_clash95_hd`` compatibility shim) and ``tools/`` (for repo helper
modules) to ``sys.path``. It starts no process and opens no window.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def ensure_repo_paths() -> Path:
    for entry in (str(REPO_ROOT / "tools"), str(REPO_ROOT)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    return REPO_ROOT
