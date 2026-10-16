"""Guard against false-green reference checks without requiring .NET."""

import subprocess

import pytest

from . import support


def test_harness_packages_match_module():
    support.check_package_versions()


@pytest.mark.parametrize("version", ["0.0.0", None])
def test_missing_or_changed_package_is_rejected(tmp_path, version):
    project, harness = tmp_path / "module.csproj", tmp_path / "harness.csproj"
    project.write_text(
        '<Project><PackageReference Include="DWIS.API.DTO" Version="2.2.32"/></Project>'
    )
    package = (
        "" if version is None else f'<PackageReference Include="DWIS.API.DTO" Version="{version}"/>'
    )
    harness.write_text(f"<Project>{package}</Project>")
    with pytest.raises(AssertionError, match="DWIS.API.DTO"):
        support.check_package_versions(project, harness)


def test_build_failure_is_fatal_and_reports_both_streams(monkeypatch):
    monkeypatch.setattr(
        support.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(
            a[0], 1, stdout="compiler error on stdout", stderr="restore error on stderr"
        ),
    )
    with pytest.raises(pytest.fail.Exception) as error:
        support.run_checked(["dotnet", "build"])
    assert "compiler error on stdout" in str(error.value)
    assert "restore error on stderr" in str(error.value)


def test_timeout_is_a_failure(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output="partial build log")

    monkeypatch.setattr(support.subprocess, "run", timeout)
    with pytest.raises(pytest.fail.Exception, match="partial build log"):
        support.run_checked(["dotnet", "build"])


def test_requested_reference_without_dotnet_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(support.shutil, "which", lambda name: None)
    with pytest.raises(pytest.fail.Exception, match=".NET 8 SDK"):
        support.build_reference(tmp_path)
