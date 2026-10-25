"""Offline Python command-line contract."""

import json
from pathlib import Path

import pytest

from .support import COMPANY, PROVIDER, manifest_creation, normalize_fields, read_fixture, run_cli


@pytest.mark.parametrize("mode", ["positional", "named", "mixed"])
def test_cli_from_other_directory(tmp_path: Path, mode: str):
    source = tmp_path / "输入文件.TXT"
    source.write_text(read_fixture("example", "txt"), encoding="utf-8-sig")
    if mode == "positional":
        args = [str(source), PROVIDER, COMPANY]
        target = source.with_suffix(".json")
    elif mode == "named":
        target = tmp_path / "输出.json"
        args = [
            "--input",
            str(source),
            "--company",
            COMPANY,
            "--provider",
            PROVIDER,
            "--output",
            str(target),
        ]
    else:
        target = tmp_path / "mixed.json"
        args = [PROVIDER, "--input", str(source), COMPANY, "-o", str(target)]
    result = run_cli(*args, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert normalize_fields(json.loads(target.read_text(encoding="utf-8"))) == normalize_fields(
        json.loads(read_fixture("example", "json"))
    )


def test_cli_prints_csharp_style_summary_and_trims_names(tmp_path: Path):
    source = tmp_path / "input.txt"
    source.write_text("WOB:point\n", encoding="utf-8")
    target = tmp_path / "out.json"
    result = run_cli(
        "--input", str(source), "--provider", " Acme ", "--company", " Co ", "--output", str(target)
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        f"Input file : {source.resolve()}",
        "Provider   : Acme",
        "Company    : Co",
        f"Output file: {target.resolve()}",
    ]
    assert json.loads(target.read_text(encoding="utf-8"))["Provider"] == {
        "Name": "Acme",
        "Company": "Co",
    }


def test_cli_writes_indented_utf8_json_with_trailing_newline(tmp_path: Path):
    source = tmp_path / "input.txt"
    source.write_text("WOB:point\n", encoding="utf-8")
    target = tmp_path / "out.json"
    assert run_cli(str(source), "Ünïcode Æ", COMPANY, str(target)).returncode == 0
    text = target.read_text(encoding="utf-8")
    assert text.endswith("\n") and '\n  "Provider"' in text
    assert "Ünïcode Æ" in text and "\\u00dc" not in text
    assert json.loads(text)["Provider"]["Name"] == "Ünïcode Æ"


@pytest.mark.parametrize("suffix", [".dwis", ".txt", ".config", ".md", ""])
def test_cli_accepts_config_regardless_of_extension(tmp_path: Path, suffix: str):
    source = tmp_path / f"input{suffix}"
    original = "# intent: final config\nWOB:point\n"
    source.write_text(original, encoding="utf-8")
    result = run_cli(str(source), PROVIDER, COMPANY)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(source.with_suffix(".json").read_text(encoding="utf-8"))
    assert manifest["InjectedNodes"][0]["TypeDictionaryURI"] == "WOB"
    assert manifest["InjectedNodes"][0]["UniqueName"] == "point"
    assert source.read_text(encoding="utf-8") == original


def test_cli_reports_missing_input_file(tmp_path: Path):
    result = run_cli(str(tmp_path / "missing.txt"), PROVIDER, COMPANY)
    assert result.returncode == 1
    assert result.stderr


@pytest.mark.parametrize("flag", ["-h", "--help", "/?"])
def test_cli_help_exits_zero(flag: str):
    result = run_cli(flag)
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


@pytest.mark.parametrize(
    "args",
    [[], ["--unknown"], ["--provider"], ["--input"], ["a", "b", "c", "d", "e"], ["-p"]],
)
def test_cli_rejects_invalid_arguments(args: list[str]):
    result = run_cli(*args)
    assert result.returncode != 0
    assert result.stderr


def test_parse_failure_preserves_existing_output(tmp_path: Path):
    source, target = tmp_path / "bad.txt", tmp_path / "bad.json"
    source.write_text("WOB:x\nx HasDynamicValue missing")
    target.write_text("existing content")
    result = run_cli(str(source), "P", "C", str(target))
    assert result.returncode == 1
    assert "Line 2" in result.stderr
    assert target.read_text() == "existing content"


def test_refuses_overwriting_input(tmp_path: Path):
    source = tmp_path / "input.txt"
    source.write_text("WOB:x")
    assert manifest_creation.main([str(source), "P", "C", str(source)]) == 1
    assert source.read_text() == "WOB:x"
