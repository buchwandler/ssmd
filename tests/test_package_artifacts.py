"""Tests for packaged runtime resources and metadata consistency."""

import importlib.resources as resources
import io
import tarfile
import zipfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib

from ssmd.capabilities import get_preset
from ssmd.segment import xsampa_to_ipa
from tools.check_release_version import check_artifact


def test_packaged_capability_data_available():
    data_dir = resources.files("ssmd").joinpath("data")

    for filename in (
        "amazon-alexa.json",
        "amazon-polly.json",
        "blank.json",
        "google-home.json",
        "ibm-watson.json",
        "microsoft-azure.json",
        "microsoft-cortana.json",
    ):
        assert data_dir.joinpath(filename).is_file()
    assert get_preset("google").ssml_green


def test_xsampa_known_conversion():
    assert xsampa_to_ipa("t@meItoU") == "təmeɪtoʊ"


def test_project_metadata_is_consistently_mit():
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = metadata["project"]

    assert project["keywords"] == ["ssml", "ssmd", "tts", "text-to-speech"]
    assert "License :: OSI Approved :: MIT License" in project["classifiers"]
    assert not any("Apache Software License" in value for value in project["classifiers"])


def test_typer_click_declared_dependencies():
    """Typer and Click are declared runtime dependencies."""
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    deps = metadata["project"]["dependencies"]

    dep_names = [d.split(">=")[0].split("==")[0].split("<")[0].strip().lower() for d in deps]
    assert "typer" in dep_names, "typer not in dependencies"
    assert "click" in dep_names, "click not in dependencies"


def test_console_script_targets_launcher():
    """Console script targets ssmd.launcher:main."""
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = metadata["project"]["scripts"]

    assert "ssmd" in scripts
    assert scripts["ssmd"] == "ssmd.launcher:main"


def test_release_version_checker_accepts_matching_wheel_and_sdist(tmp_path):
    wheel = tmp_path / "ssmd-0.8.1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "ssmd-0.8.1.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: ssmd\nVersion: 0.8.1\n",
        )

    sdist = tmp_path / "ssmd-0.8.1.tar.gz"
    metadata = b"Metadata-Version: 2.1\nName: ssmd\nVersion: 0.8.1\n"
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo("ssmd-0.8.1/PKG-INFO")
        info.size = len(metadata)
        archive.addfile(info, io.BytesIO(metadata))

    assert check_artifact(wheel, "v0.8.1") == []
    assert check_artifact(sdist, "v0.8.1") == []


def test_release_version_checker_rejects_filename_and_metadata_mismatch(tmp_path):
    wheel = tmp_path / "ssmd-0.8.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "ssmd-0.8.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: ssmd\nVersion: 0.8.0\n",
        )

    issues = check_artifact(wheel, "v0.8.1")

    assert len(issues) == 2
    assert "filename contains 0.8.0" in issues[0]
    assert "metadata contains 0.8.0" in issues[1]


def test_skills_not_in_package_data():
    """skills/ is not included in tool.setuptools.package-data."""
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    package_data = metadata.get("tool", {}).get("setuptools", {}).get("package-data", {})

    # skills should not be in package data
    for key in package_data:
        assert "skill" not in key.lower(), f"skills/ should not be in package-data: {key}"


def test_launcher_importable():
    """ssmd.launcher is importable."""
    import ssmd.launcher

    assert hasattr(ssmd.launcher, "main")
    assert callable(ssmd.launcher.main)


def test_cli_common_importable():
    """ssmd.cli_common is importable."""
    import ssmd.cli_common

    assert hasattr(ssmd.cli_common, "CLIState")
    assert hasattr(ssmd.cli_common, "render_json")
    assert hasattr(ssmd.cli_common, "emit_payload")
    assert hasattr(ssmd.cli_common, "emit_error")
    assert hasattr(ssmd.cli_common, "SSMDCLIError")


def test_command_inventory_importable():
    """ssmd.command_inventory is importable."""
    import ssmd.command_inventory

    assert hasattr(ssmd.command_inventory, "COMMAND_METADATA")
    assert hasattr(ssmd.command_inventory, "AGENT_GOLDEN_PATH_COMMANDS")
    assert hasattr(ssmd.command_inventory, "commands_inventory_json")


def test_cli_importable():
    """ssmd.cli is importable with the new Typer app."""
    import ssmd.cli

    assert hasattr(ssmd.cli, "app")
    assert hasattr(ssmd.cli, "cli_main")
    assert hasattr(ssmd.cli, "main")
