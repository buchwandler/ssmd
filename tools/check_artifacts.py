"""Check wheel and sdist contents for required SSMD runtime artifacts."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path

REQUIRED_SUFFIXES = (
    "ssmd/xsampa_to_ipa.txt",
    "ssmd/data/amazon-alexa.json",
    "ssmd/data/amazon-polly.json",
    "ssmd/data/blank.json",
    "ssmd/data/google-home.json",
    "ssmd/data/ibm-watson.json",
    "ssmd/data/microsoft-azure.json",
    "ssmd/data/microsoft-cortana.json",
)


def _names(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if path.name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path) as archive:
            return archive.getnames()
    raise ValueError(f"Unsupported artifact type: {path}")


def _metadata(path: Path) -> str:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            metadata = next(
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            )
            return archive.read(metadata).decode("utf-8")
    return ""


def check_artifact(path: Path) -> list[str]:
    names = _names(path)
    missing = [
        suffix for suffix in REQUIRED_SUFFIXES if not any(name.endswith(suffix) for name in names)
    ]
    issues = [f"{path}: missing {suffix}" for suffix in missing]
    metadata = _metadata(path)
    if metadata and "License :: OSI Approved :: MIT License" not in metadata:
        issues.append(f"{path}: missing MIT license classifier")
    if metadata and "Apache Software License" in metadata:
        issues.append(f"{path}: contradictory Apache license classifier")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()
    issues = [issue for artifact in args.artifacts for issue in check_artifact(artifact)]
    if issues:
        print("\n".join(issues))
        return 1
    print(
        f"checked {len(args.artifacts)} artifact(s): required SSMD resources and metadata present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
