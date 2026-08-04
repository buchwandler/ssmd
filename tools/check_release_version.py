"""Verify release artifact names and metadata against an exact release tag."""

from __future__ import annotations

import argparse
import email
import re
import tarfile
import zipfile
from pathlib import Path

from packaging.utils import parse_sdist_filename, parse_wheel_filename
from packaging.version import InvalidVersion, Version


def _expected_version(tag: str) -> Version:
    """Parse a release tag using the project's ``v<version>`` convention."""
    if not re.fullmatch(r"v[^/\\\s]+", tag):
        raise ValueError(f"release tag must be exactly v<PEP-440-version>: {tag}")
    try:
        return Version(tag[1:])
    except InvalidVersion as exc:
        raise ValueError(f"release tag is not a valid PEP-440 version: {tag}") from exc


def _metadata_version(path: Path) -> str:
    """Read the distribution metadata version from a wheel or source archive."""
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            metadata_name = next(
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            )
            metadata = email.message_from_bytes(archive.read(metadata_name))
    elif path.name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path) as archive:
            pkg_info_name = next(name for name in archive.getnames() if name.endswith("/PKG-INFO"))
            member = archive.extractfile(pkg_info_name)
            if member is None:
                raise ValueError(f"missing PKG-INFO member: {path}")
            metadata = email.message_from_bytes(member.read())
    else:
        raise ValueError(f"unsupported artifact type: {path}")

    version = metadata.get("Version")
    if not version:
        raise ValueError(f"missing Version metadata: {path}")
    return version


def _filename_version(path: Path) -> Version:
    """Parse the version encoded in an artifact filename."""
    if path.suffix == ".whl":
        _, version, _, _ = parse_wheel_filename(path.name)
    elif path.name.endswith((".tar.gz", ".tgz", ".tar")):
        _, version = parse_sdist_filename(path.name)
    else:
        raise ValueError(f"unsupported artifact type: {path}")
    return Version(str(version))


def check_artifact(path: Path, expected_tag: str) -> list[str]:
    """Return version consistency issues for one built artifact."""
    expected = _expected_version(expected_tag)
    issues: list[str] = []

    try:
        filename_version = _filename_version(path)
    except (ValueError, StopIteration) as exc:
        return [f"{path}: invalid artifact filename: {exc}"]
    if filename_version != expected:
        issues.append(
            f"{path}: filename contains {filename_version}, expected {expected_tag.removeprefix('v')}"
        )

    try:
        metadata_version = Version(_metadata_version(path))
    except (InvalidVersion, ValueError, StopIteration) as exc:
        return [f"{path}: invalid artifact metadata: {exc}"]
    if metadata_version != expected:
        issues.append(
            f"{path}: metadata contains {metadata_version}, expected {expected_tag.removeprefix('v')}"
        )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", required=True, help="Release tag, for example v0.8.1")
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()

    try:
        _expected_version(args.expected)
        issues = [
            issue
            for artifact in args.artifacts
            for issue in check_artifact(artifact, args.expected)
        ]
    except ValueError as exc:
        print(f"release version check failed: {exc}")
        return 2

    if issues:
        print("\n".join(issues))
        return 1
    print(f"checked {len(args.artifacts)} artifact(s): release version matches {args.expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
