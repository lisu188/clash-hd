"""Stage only allowlisted launcher resources and embed their inventory identity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/launcher"))
import package_resources as resources


def prepare(destination: Path) -> dict:
    destination = destination.resolve()
    if destination.is_relative_to(ROOT) or destination.exists():
        raise ValueError("Bundle staging needs a fresh directory outside the checkout.")
    # Complete the read-only preflight before creating staging or copying data.
    inventory = resources.inventory_bytes(ROOT)
    files = json.loads(inventory)["files"]
    source_bytes = {name: resources._read(ROOT, name) for name in resources.RESOURCE_FILES}
    if any(resources.sha256(data) != files[name] for name, data in source_bytes.items()):
        raise ValueError("Launcher source changed during package preflight.")
    raw_root = destination / "resources"
    for name, data in source_bytes.items():
        target = raw_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    with (raw_root / resources.INVENTORY_NAME).open("xb") as stream:
        stream.write(inventory)
    digest = resources.sha256(inventory)
    with (destination / "launcher_bundle_identity.py").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write('"""Build-generated compiled launcher resource identity."""\n')
        stream.write("INVENTORY_SHA256 = " + repr(digest) + "\n")
    resources.verify_resources(raw_root, digest)
    # Source inputs are rechecked after staging as well.
    if resources.inventory_bytes(ROOT) != inventory:
        raise ValueError("Launcher source changed during package staging.")
    return {"resource_root": str(raw_root), "identity_root": str(destination),
            "inventory_sha256": digest, "resource_count": len(files),
            "hidden_imports": [name.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
                               for name in resources.SOURCE_FILES] + ["launcher_bundle_identity"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.destination), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
