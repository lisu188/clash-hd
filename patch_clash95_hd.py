#!/usr/bin/env python3
"""Compatibility wrapper for the Clash95 HD patcher implementation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_IMPL_PATH = Path(__file__).resolve().parent / "src" / "patcher" / "patch_clash95_hd.py"
_SPEC = importlib.util.spec_from_file_location("_clash95_hd_patcher_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Could not load Clash95 HD patcher implementation: {_IMPL_PATH}")
_IMPL = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _IMPL
_SPEC.loader.exec_module(_IMPL)

for _name, _value in vars(_IMPL).items():
    if not _name.startswith("_"):
        globals()[_name] = _value


if __name__ == "__main__":
    main()
