from __future__ import annotations

from pathlib import Path

from .ontology import OntologySearch
from .paths import ontology_path
from .retrieval import ExampleRetriever
from .validation import DWISOntology, build_validation_components


class DDBotToolkit:
    """Facade exposing the same structured capabilities used by the CLI."""

    def __init__(
        self,
        *,
        ontology: str | Path | None = None,
        example_corpus: str | Path | None = None,
    ):
        ontology_file = Path(ontology or ontology_path())
        self.ontology_search = OntologySearch(ontology_file)
        self.example_retriever = ExampleRetriever(example_corpus)
        self._validation = build_validation_components(DWISOntology(ontology_file))

    def validate(self, config: str) -> dict[str, object]:
        syntax = self._validation.dwis_config_checker.check(config)
        report: dict[str, object] = {
            "valid": False,
            "construction_valid": syntax.is_valid,
            "hard_errors": [message for message in syntax.messages if message.startswith("[error]")],
            "soft_comments": [message for message in syntax.messages if message.startswith("[warning]")],
            "repair_suggestions": self._repair_suggestions(syntax.messages),
            "checks": [check.to_dict() for check in syntax.check_results],
            "graph": {"asserted_triples": 0, "inferred_triples": 0, "growth_ratio": 1.0},
        }
        if not syntax.is_valid:
            return report

        construction = self._validation.dwis_to_rdf_translator.translate(
            syntax.lines, check_results=syntax.check_results
        )
        inferred, reasoning = self._validation.rdf_reasoner.reason(construction.graph)
        diagnostics = self._validation.rdf_diagnostic_checker.check(construction.graph, inferred)
        hard_errors = [message for message in diagnostics.messages if message.startswith("[error]")]
        soft_comments = [
            *[message for message in diagnostics.messages if message.startswith("[warning]")],
            *[
                message
                for diagnostic in reasoning.diagnostics
                for message in diagnostic.messages
            ],
        ]
        report.update(
            {
                "valid": not hard_errors,
                "hard_errors": hard_errors,
                "soft_comments": soft_comments,
                "repair_suggestions": self._repair_suggestions(hard_errors),
                "checks": [
                    *[check.to_dict() for check in syntax.check_results],
                    *[check.to_dict() for check in diagnostics.check_results],
                ],
                "graph": {
                    "asserted_triples": len(construction.graph),
                    "inferred_triples": len(inferred),
                    "growth_ratio": next(
                        (
                            diagnostic.details["graph_growth_ratio"]
                            for diagnostic in reasoning.diagnostics
                            if diagnostic.diagnostic_name == "reasoning_growth"
                        ),
                        1.0,
                    ),
                },
            }
        )
        return report

    @staticmethod
    def _repair_suggestions(messages: list[str]) -> list[dict[str, str]]:
        suggestions: list[dict[str, str]] = []
        for message in messages:
            if "Unknown class" in message:
                action = "Search the ontology for the intended noun and replace the class name."
            elif "Unknown predicate" in message:
                action = "Search ontology properties and replace the predicate with a valid DWIS verb."
            elif "not a declared instance" in message:
                action = "Add a Class:Instance declaration or correct the relation endpoint identifier."
            elif "disconnected components" in message:
                action = "Add the missing semantic relation between the listed graph components."
            elif "disjointness conflict" in message:
                action = "Remove or replace one of the incompatible types on the instance."
            elif "functional property conflict" in message:
                action = "Keep one object for the functional property or split the subject instance."
            else:
                action = "Correct the reported construction or semantic constraint and revalidate."
            suggestions.append({"message": message, "action": action})
        return suggestions
