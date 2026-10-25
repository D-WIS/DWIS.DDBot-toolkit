"""Live comparison with pinned DWIS libraries; enable with --run-reference."""

import json
from pathlib import Path

import pytest

from .support import (
    FIXTURE_NAMES,
    VOCABULARY,
    create,
    normalize_fields,
    read_fixture,
    run_checked,
    run_reference,
)

pytestmark = pytest.mark.reference

# TTL changes ComputedState inheritance, including fields on its descendants.
TTL_STATE_CLASSES = {
    "ComputedState",
    "PhysicalState",
    "ProceduralState",
    "ActivationState",
    "EnablementState",
    "IdlingState",
    "ProcessState",
}
SHARED_NOUNS = {
    name: noun
    for name, noun in VOCABULARY["Nouns"].items()
    if name not in TTL_STATE_CLASSES | {"Réaumur"}
}


CONVERSION_CORPUS = {
    "extra_whitespace": "DynamicDrillingSignal:s\nWOB:p\np   HasDynamicValue   s\n",
    "comment_and_blank_lines": "# note\n\nWOB:p\n",
    "spacing_around_separators": 'WOB : p\nDataProvider : q\nq . ProviderName = "x"\n',
    "unquoted_multi_word_value": "DataProvider:p\np.ProviderName = Acme Drilling Co\n",
    "repeated_declaration_and_triple": (
        "DynamicDrillingSignal:s\nWOB:p\np HasDynamicValue s\np HasDynamicValue s\n"
    ),
    "tab_indented_lines": "\tWOB:p\n\tDynamicDrillingSignal:s\n",
    "crlf_and_no_final_newline": "WOB:p\r\nDynamicDrillingSignal:s\r\np HasDynamicValue s",
    "local_noun_inheriting_standard_attributes": (
        "NOUN:LocalPoint\nLocalPoint.Parent = DataProvider\nLocalPoint:p\n"
    ),
    "non_ascii_individual_name": "WOB:压力\n",
    "mixed_reference_kinds": (
        "DynamicDrillingSignal:s\nDrillingSignal:s\nWOB:p\nDataProvider:q\n"
        "p HasDynamicValue s\np IsOfMeasurableQuantity ForceDrillingQuantity\n"
        "s BelongsToClass DrillingSignal\np IsProvidedBy q\n"
    ),
}


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_reference_harness_reproduces_pinned_fixtures(
    reference_harness: Path, tmp_path: Path, name: str
):
    """Guards the provenance of the committed fixtures."""
    assert run_reference(reference_harness, read_fixture(name, "txt"), tmp_path) == json.loads(
        read_fixture(name, "json")
    )


@pytest.mark.parametrize("name", sorted(CONVERSION_CORPUS))
def test_reference_harness_agrees_with_python(reference_harness: Path, tmp_path: Path, name: str):
    text = CONVERSION_CORPUS[name]
    expected = run_reference(reference_harness, text, tmp_path)
    assert expected["InjectedNodes"] or expected["InjectedVariables"], "empty reference manifest"
    assert normalize_fields(create(text)) == normalize_fields(expected)


def _sweep_declarations() -> str:
    return "\n".join(f"{noun}:ind_{index}" for index, noun in enumerate(SHARED_NOUNS)) + "\n"


def _sweep_attributes() -> str:
    lines: list[str] = []
    index = 0
    for noun in SHARED_NOUNS.values():
        if not noun["NounAttributes"]:
            continue
        lines.append(f"{noun['Name']}:ind_{index}")
        for attribute in noun["NounAttributes"]:
            lines.append(f'ind_{index}.{attribute["Name"]} = "value {attribute["Name"]}"')
        index += 1
    return "\n".join(lines) + "\n"


def _sweep_class_assertions() -> str:
    lines: list[str] = []
    for index, noun in enumerate(SHARED_NOUNS):
        lines.append(f"{noun}:ind_{index}")
        lines.append(f"ind_{index} BelongsToClass {noun}")
    return "\n".join(lines) + "\n"


def _sweep_implicit_references() -> str:
    lines = ["WOB:subject"]
    lines += [f"subject IsOfMeasurableQuantity {noun}" for noun in SHARED_NOUNS]
    return "\n".join(lines) + "\n"


def _sweep_verbs(implicit: bool) -> str:
    """BelongsToClass is excluded: it needs a class object, covered by the assertions sweep."""
    lines = ["WOB:vsubj", "WOB:vobj"]
    lines += [
        f"vsubj {verb} {'DrillingSignal' if implicit else 'vobj'}"
        for verb in VOCABULARY["Verbs"]
        if verb != "BelongsToClass"
    ]
    return "\n".join(lines) + "\n"


def _sweep_variable_subjects() -> str:
    lines = _sweep_declarations().splitlines()
    lines.append("DynamicDrillingSignal:var")
    lines += [f"var IsOfMeasurableQuantity {noun}" for noun in SHARED_NOUNS]
    return "\n".join(lines) + "\n"


VOCABULARY_SWEEPS = {
    "declarations": _sweep_declarations,
    "attributes": _sweep_attributes,
    "class_assertions": _sweep_class_assertions,
    "implicit_references": _sweep_implicit_references,
    "verbs": lambda: _sweep_verbs(implicit=False),
    "implicit_verbs": lambda: _sweep_verbs(implicit=True),
    "variable_subjects": _sweep_variable_subjects,
}


@pytest.mark.parametrize("name", sorted(VOCABULARY_SWEEPS))
def test_reference_harness_agrees_across_the_vocabulary(
    reference_harness: Path, tmp_path: Path, name: str
):
    """Every noun and verb in the bundled vocabulary, converted by both implementations."""
    text = VOCABULARY_SWEEPS[name]()
    expected = run_reference(reference_harness, text, tmp_path)
    actual = create(text)

    nouns, verbs = len(SHARED_NOUNS), len(VOCABULARY["Verbs"])
    with_attributes = sum(1 for noun in SHARED_NOUNS.values() if noun["NounAttributes"])
    expected_counts = {
        "declarations": (nouns, 0),
        "attributes": (with_attributes, 0),
        "class_assertions": (nouns, nouns),
        "implicit_references": (1, nouns),
        "verbs": (2, verbs - 1),
        "implicit_verbs": (2, verbs - 1),
        "variable_subjects": (nouns + 1, nouns),
    }[name]
    assert len(expected["InjectedNodes"]) + len(expected["InjectedVariables"]) == expected_counts[0]
    assert len(expected["InjectedReferences"]) == expected_counts[1]
    assert normalize_fields(actual) == normalize_fields(expected)


def test_ttl_vocabulary_differences_from_the_pinned_library(
    reference_harness: Path, tmp_path: Path
):
    target = tmp_path / "pinned-vocabulary.json"
    run_checked(["dotnet", str(reference_harness), "vocabulary", str(target)])
    pinned = json.loads(target.read_text(encoding="utf-8"))
    assert set(VOCABULARY["Verbs"]) == set(pinned["Verbs"])
    assert set(VOCABULARY["Nouns"]) - set(pinned["Nouns"]) == {"Réaumur"}
    assert set(pinned["Nouns"]) - set(VOCABULARY["Nouns"]) == {"RÃ©aumur"}
    for name, noun in VOCABULARY["Nouns"].items():
        if name == "Réaumur":
            continue
        original = pinned["Nouns"][name]
        assert {a["Name"] for a in noun["NounAttributes"]} == {
            a["Name"] for a in original["NounAttributes"] or []
        }
        parents = [original["ParentNounName"]] if original["ParentNounName"] else []
        if name == "ComputedState":
            assert noun["ParentNounNames"] == ["DrillingDataPoint"]
            assert parents == ["ComputationUnit"]
        else:
            assert noun["ParentNounNames"] == parents


@pytest.mark.parametrize("noun", sorted(TTL_STATE_CLASSES))
def test_ttl_state_fields_intentionally_differ_from_csharp(reference_harness, tmp_path, noun):
    text = f"{noun}:state\n"
    expected = run_reference(reference_harness, text, tmp_path)
    actual = create(text)
    assert expected["InjectedNodes"][0]["Fields"] is None
    expected["InjectedNodes"][0]["Fields"] = [{"FieldName": "IsValid", "FieldValue": None}]
    assert actual == expected
