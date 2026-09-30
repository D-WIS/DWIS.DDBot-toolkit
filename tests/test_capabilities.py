from __future__ import annotations

from pathlib import Path

import pytest

from ddbot_toolkit import DDBotToolkit, ExampleRetriever, OntologySearch
from ddbot_toolkit.paths import example_corpus_path


def test_ontology_search_finds_pressure_terms() -> None:
    matches = OntologySearch().search("pressure", limit=20)
    assert matches
    assert any("pressure" in match.name.casefold() for match in matches)


def test_example_search_returns_structured_config() -> None:
    matches = ExampleRetriever().search("dynamic weight on bit bottom string", limit=1)
    assert len(matches) == 1
    assert matches[0].dwis_config
    assert matches[0].intent_sketch


def test_source_checkout_uses_shared_example_corpus() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert example_corpus_path() == (
        repo_root / "model-dwis-config" / "assets" / "dwis-config-examples.jsonl"
    )


def test_validation_accepts_known_connected_config() -> None:
    config = """\
DrillingSignal:f_bos_sp
DynamicDrillingSignal:f_bos_sp
SetPoint:f_bos_sp_01
WOB:f_bos_sp_01
ContinuousDataType:f_bos_sp_01
f_bos_sp_01 HasDynamicValue f_bos_sp
f_bos_sp_01 IsOfMeasurableQuantity ForceDrillingQuantity
BottomOfStringReferenceLocation:bos_01
f_bos_sp_01 IsPhysicallyLocatedAt bos_01
"""
    report = DDBotToolkit().validate(config)
    assert report["valid"] is True, report
    assert report["hard_errors"] == []


def test_validation_returns_repair_guidance() -> None:
    report = DDBotToolkit().validate("MadeUpClass:value")
    assert report["valid"] is False
    assert report["hard_errors"]
    assert report["repair_suggestions"]


@pytest.mark.parametrize("warning_ratio", [0.0, float("inf")])
def test_validation_reads_reasoning_diagnostics(warning_ratio: float) -> None:
    toolkit = DDBotToolkit()
    reasoner = toolkit._validation.rdf_reasoner
    reasoner.size_warning_ratio = warning_ratio
    reasoner.size_warning_floor = 0

    report = toolkit.validate("DynamicDrillingSignal:pressure")

    assert report["valid"] is True, report
    graph = report["graph"]
    assert graph["asserted_triples"] > 0
    assert graph["growth_ratio"] == round(
        graph["inferred_triples"] / graph["asserted_triples"], 3
    )
    growth_warnings = [
        message for message in report["soft_comments"]
        if "Inferred graph is" in message
    ]
    assert bool(growth_warnings) == (warning_ratio == 0.0)
