"""Shared paths and process helpers for manifest verification."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = ROOT / "modules" / "manifest-creation" / "python"
SCRIPT = MODULE_DIR / "manifest_creation.py"
FIXTURES = Path(__file__).with_name("fixtures")
HARNESS_PROJECT = Path(__file__).with_name("harness") / "reference-harness.csproj"
CSHARP_PROJECT = ROOT / "modules/manifest-creation/csharp/manifest-creation.csproj"
VOCABULARY = json.loads((MODULE_DIR / "vocabulary.json").read_text(encoding="utf-8"))
PROVIDER = "Provider"
COMPANY = "Company"

FIXTURE_NAMES = sorted(path.stem for path in FIXTURES.glob("*.txt"))

SPEC = importlib.util.spec_from_file_location("manifest_creation_tool", SCRIPT)
manifest_creation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest_creation)


def create(text: str, provider: str = PROVIDER, company: str = COMPANY) -> dict:
    return manifest_creation.create_manifest(text, provider, company)


def read_fixture(name: str, suffix: str) -> str:
    return (FIXTURES / f"{name}.{suffix}").read_text(encoding="utf-8")


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True
    )


def run_checked(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Once requested, reference build/runtime failures must never become skips."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        pytest.fail(
            f"Command timed out after {timeout}s: {args}\n"
            f"stdout:\n{error.stdout or ''}\nstderr:\n{error.stderr or ''}",
            pytrace=False,
        )
    except OSError as error:
        pytest.fail(f"Cannot execute {args}: {error}", pytrace=False)
    if result.returncode:
        pytest.fail(
            f"Command failed ({result.returncode}): {args}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            pytrace=False,
        )
    return result


def check_package_versions(project: Path = CSHARP_PROJECT, harness: Path = HARNESS_PROJECT):
    def packages(path):
        return {
            node.attrib["Include"]: node.attrib.get("Version")
            for node in ET.parse(path).iter("PackageReference")
        }

    expected, actual = packages(project), packages(harness)
    assert expected, f"No PackageReference entries in {project}"
    for name, version in expected.items():
        assert version is not None, f"{name} has no explicit version in {project}"
        assert actual.get(name) == version, (
            f"{name}: module requires {version}, harness has {actual.get(name)!r}"
        )


def build_reference(artifacts: Path) -> Path:
    check_package_versions()
    if shutil.which("dotnet") is None:
        pytest.fail(
            "Reference tests require the .NET 8 SDK (or a compatible newer SDK).", pytrace=False
        )
    run_checked(
        [
            "dotnet",
            "build",
            str(HARNESS_PROJECT),
            "--nologo",
            "-v",
            "quiet",
            "--artifacts-path",
            str(artifacts),
        ],
        timeout=180,
    )
    dll = artifacts / "bin/reference-harness/debug/reference-harness.dll"
    assert dll.is_file(), f"Harness build did not produce {dll}"
    return dll


def run_reference(harness: Path, text: str, tmp_path: Path) -> dict:
    source = tmp_path / "reference-input.txt"
    target = tmp_path / "reference-output.json"
    source.write_text(text, encoding="utf-8")
    run_checked(["dotnet", str(harness), "manifest", str(source), PROVIDER, COMPANY, str(target)])
    return json.loads(target.read_text(encoding="utf-8"))
