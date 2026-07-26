"""Compare the runnable files in a source tree with a reconstructed tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

INCLUDED_PATTERNS = (
    "**/*.py",
    "**/*.toml",
    "**/*.rst",
    "**/*.md",
    "**/*.typed",
    "**/*.json",
    "**/*.txt",
    "**/*.yaml",
    "**/*.yml",
    "**/*.ini",
    "**/*.cfg",
    "**/*.conf",
    "**/*.sh",
    "**/*.lock",
    "**/*.js",
    "**/*.css",
    "**/*.html",
    "LICENSE*",
    "Makefile",
    "requirements*.txt",
)
EXCLUDED_PARTS = {".git", ".taskledger", ".venv", "__pycache__"}
EXCLUDED_NAMES = {"todo.md", "context_ssmd.md"}


def _included(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    return any(path.match(pattern) for pattern in INCLUDED_PATTERNS)


def _inventory(root: Path) -> dict[str, str]:
    files = (path for path in root.rglob("*") if path.is_file())
    inventory: dict[str, str] = {}
    for path in files:
        relative = path.relative_to(root)
        if _included(relative):
            inventory[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return inventory


def _compare(source: Path, reconstructed: Path) -> dict[str, object]:
    source_files = _inventory(source)
    reconstructed_files = _inventory(reconstructed)
    missing = sorted(set(source_files) - set(reconstructed_files))
    unexpected = sorted(set(reconstructed_files) - set(source_files))
    changed = sorted(
        path
        for path in set(source_files) & set(reconstructed_files)
        if source_files[path] != reconstructed_files[path]
    )
    return {
        "source_files": len(source_files),
        "reconstructed_files": len(reconstructed_files),
        "missing": missing,
        "unexpected": unexpected,
        "changed": changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="source repository root")
    parser.add_argument("reconstructed", type=Path, help="reconstructed repository root")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args()

    result = _compare(args.source.resolve(), args.reconstructed.resolve())
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"source files: {result['source_files']}; "
            f"reconstructed files: {result['reconstructed_files']}"
        )
        for category in ("missing", "unexpected", "changed"):
            entries = result[category]
            if entries:
                print(f"{category}:")
                print("\n".join(f"  {entry}" for entry in entries))
    return int(any(result[category] for category in ("missing", "unexpected", "changed")))


if __name__ == "__main__":
    raise SystemExit(main())
