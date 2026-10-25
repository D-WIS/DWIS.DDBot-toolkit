"""The Turtle ontology is the authority for both Python distributions."""

import json
import shutil
import subprocess
import sys

import pytest

from .support import ROOT, manifest_creation, normalize_fields, read_fixture


PREFIXES = """@prefix d: <http://ddhub.no/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""


@pytest.mark.parametrize(
    "noun",
    [
        "ComputedState",
        "PhysicalState",
        "ProceduralState",
        "ActivationState",
        "EnablementState",
        "IdlingState",
        "ProcessState",
    ],
)
def test_ttl_inheritance_and_unicode_names(noun):
    result = manifest_creation.create_manifest(
        f"{noun}:state\nstate.IsValid = true\nRéaumur:unit\n", "P", "C"
    )
    state, unit = result["InjectedNodes"]
    assert state["Fields"] == [{"FieldName": "IsValid", "FieldValue": "true"}]
    assert unit["TypeDictionaryURI"] == "Réaumur"
    with pytest.raises(ValueError, match="Unknown noun RÃ©aumur"):
        manifest_creation.create_manifest("RÃ©aumur:unit", "P", "C")
    with pytest.raises(ValueError, match="Unknown noun DWISAttributeCardinalityRestriction"):
        manifest_creation.create_manifest("DWISAttributeCardinalityRestriction:x", "P", "C")


@pytest.mark.parametrize(
    "noun, field",
    [
        ("HighPassFilter", "CutOffFrequency"),
        ("LowPassFilter", "CutOffFrequency"),
        ("TimeWindowMovingAverage", "TimeWindow"),
        ("TimeWindowRangeExtraction", "TimeWindow"),
        ("DrillingSignal", "Value"),
        ("HydraulicConnectedState", "Value"),
        ("MechanicalElementState", "Value"),
    ],
)
def test_union_domains_supply_fields(noun, field):
    result = manifest_creation.create_manifest(f"{noun}:x\nx.{field} = 3", "P", "C")
    assert {"FieldName": field, "FieldValue": "3"} in result["InjectedNodes"][0]["Fields"]


def test_explicit_ontology_controls_classes_verbs_and_diamond_inheritance(tmp_path):
    ontology = tmp_path / "custom.ttl"
    ontology.write_text(
        PREFIXES
        + """
d:Root a owl:Class .
d:Left a owl:Class ; rdfs:subClassOf d:Root .
d:Right a owl:Class ; rdfs:subClassOf d:Root .
d:Child a owl:Class ; rdfs:subClassOf d:Left, d:Right .
d:Shared a owl:DatatypeProperty ; rdfs:domain d:Root .
d:Own a owl:DatatypeProperty ; rdfs:domain [ owl:unionOf ( d:Left d:Right ) ] .
d:Relates a owl:ObjectProperty .
"""
    )
    result = manifest_creation.create_manifest(
        "Child:a\nRoot:b\na Relates b\na.Shared = 7", "P", "C", ontology_path=ontology
    )
    assert result["InjectedNodes"][0]["Fields"] == [
        {"FieldName": "Own", "FieldValue": None},
        {"FieldName": "Shared", "FieldValue": "7"},
    ]
    assert result["InjectedReferences"][0]["VerbURI"] == "http://ddhub.no/Relates"
    with pytest.raises(ValueError, match="Unknown noun WOB"):
        manifest_creation.create_manifest("WOB:x", "P", "C", ontology_path=ontology)
    ontology.write_text(
        PREFIXES
        + """
d:A a owl:Class ; rdfs:subClassOf d:B .
d:B a owl:Class ; rdfs:subClassOf d:A .
"""
    )
    with pytest.raises(ValueError, match="Cyclic noun inheritance"):
        manifest_creation.create_manifest("A:x", "P", "C", ontology_path=ontology)


@pytest.mark.parametrize("content", [None, "invalid Turtle", PREFIXES])
def test_ontology_failure_preserves_config_and_existing_manifest(tmp_path, content):
    ontology = tmp_path / "bad.ttl"
    if content is not None:
        ontology.write_text(content)
    source = tmp_path / "input.txt"
    source.write_text("WOB:x")
    target = tmp_path / "output.json"
    target.write_text("existing manifest")
    assert (
        manifest_creation.main([str(source), "P", "C", str(target), "--ontology", str(ontology)])
        == 1
    )
    assert target.read_text() == "existing manifest"
    assert source.read_text() == "WOB:x"


def test_cli_refuses_overwriting_ontology(tmp_path):
    ontology = tmp_path / "vocabulary.ttl"
    original = PREFIXES + "d:WOB a owl:Class .\n"
    ontology.write_text(original)
    source = tmp_path / "input.txt"
    source.write_text("WOB:x")
    assert (
        manifest_creation.main([str(source), "P", "C", str(ontology), "--ontology", str(ontology)])
        == 1
    )
    assert ontology.read_text() == original


def test_relocated_skill_uses_its_shared_ttl_without_json_snapshot(tmp_path):
    installed = tmp_path / "renamed-skill"
    script_dir = installed / "scripts" / "manifest-creation"
    shutil.copytree(ROOT / "model-dwis-config/scripts/manifest-creation", script_dir)
    (installed / "assets").mkdir()
    shutil.copy(ROOT / "model-dwis-config/assets/DWISVocabulary.ttl", installed / "assets")
    source = tmp_path / "input.dwis"
    original = "# intent: example\n" + read_fixture("example", "txt")
    source.write_text(original)
    target = tmp_path / "output.json"
    result = subprocess.run(
        [
            sys.executable,
            str(script_dir / "manifest_creation.py"),
            str(source),
            "Provider",
            "Company",
            str(target),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert normalize_fields(json.loads(target.read_text())) == normalize_fields(
        json.loads(read_fixture("example", "json"))
    )
    assert source.read_text() == original
    assert not list(installed.rglob("vocabulary.json"))
