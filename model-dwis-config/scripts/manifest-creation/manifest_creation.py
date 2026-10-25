#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rdflib>=7.1,<8"]
# ///
"""Create DWIS manifests using the shared DWIS Turtle ontology.

Port of DWIS VocabularyParsing / ManifestFile.FromDWISInstance; see README.md
for intentional input-handling fixes and upstream attribution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from rdflib import Graph, OWL, RDF, RDFS, URIRef
from rdflib.collection import Collection
from rdflib.exceptions import ParserError

URI = "http://ddhub.no/"


def default_ontology_path() -> Path:
    """Resolve the shared asset in the skill bundle or the repository layout."""
    root = Path(__file__).resolve().parents[2]
    bundled = root / "assets" / "DWISVocabulary.ttl"
    if bundled.is_file():
        return bundled
    return root.parent / "model-dwis-config" / "assets" / "DWISVocabulary.ttl"


def load_vocabulary(ontology_path: str | Path | None = None) -> dict:
    """Project named classes, object properties, and field domains from Turtle.

    OWL restriction classes describe constraints rather than instantiable nouns.
    Field order is alphabetical within each class because RDF defines no such order.
    """
    path = Path(ontology_path) if ontology_path is not None else default_ontology_path()
    graph = Graph()
    try:
        graph.parse(path, format="turtle")
    except (ParserError, SyntaxError) as error:
        raise ValueError(f"Invalid Turtle ontology {path}: {error}") from error

    def is_named(term):
        return isinstance(term, URIRef) and str(term).startswith(URI)

    nouns = {}
    for term in sorted(set(graph.subjects(RDF.type, OWL.Class)), key=str):
        if not is_named(term) or (term, RDF.type, OWL.Restriction) in graph:
            continue
        name = str(term).removeprefix(URI)
        nouns[name] = {
            "Name": name,
            "ParentNounNames": sorted(
                str(parent).removeprefix(URI)
                for parent in graph.objects(term, RDFS.subClassOf)
                if is_named(parent)
            ),
            "NounAttributes": [],
        }
    if not nouns:
        raise ValueError(f"Ontology {path} contains no named DWIS classes.")

    for prop in sorted(set(graph.subjects(RDF.type, OWL.DatatypeProperty)), key=str):
        if not is_named(prop):
            continue
        domains = set()
        for domain in graph.objects(prop, RDFS.domain):
            union = graph.value(domain, OWL.unionOf)
            domains.update(Collection(graph, union) if union is not None else [domain])
        for domain in domains:
            name = str(domain).removeprefix(URI)
            if name in nouns:
                nouns[name]["NounAttributes"].append({"Name": str(prop).removeprefix(URI)})

    verbs = sorted(
        str(term).removeprefix(URI)
        for term in set(graph.subjects(RDF.type, OWL.ObjectProperty))
        if is_named(term)
    )
    return {"Nouns": nouns, "Verbs": verbs}


def _definition(name: str, kind: str) -> dict:
    result = dict.fromkeys(
        [
            "Name",
            "DisplayName",
            f"Parent{kind}Name",
            "Description",
            "Examples",
            "DefinitionSetName",
            "WillBeRemovedFromVersion",
            "ReplacedBy",
        ]
    )
    result.update(Name=name, IsDeprecated=False, WillBeRemovedBy="0001-01-01T00:00:00")
    if kind == "Noun":
        result.update(NounAttributes=None, SpecializedNounAttributes=None)
    else:
        result.update(DomainNounName=None, RangeNounName=None, MinCardinality=-1, MaxCardinality=-1)
    return result


def create_manifest(
    text: str, provider: str, company: str, *, ontology_path: str | Path | None = None
) -> dict:
    """Convert CONFIG text to a JSON-compatible manifest; raise ValueError on bad input.

    Declarations and attributes are processed in source order, like the C# parser.
    Attribute values remain literal strings (including quotes), as in the DTO.
    """
    if not provider.strip() or not company.strip():
        raise ValueError("Provider and company must not be empty.")
    vocabulary = load_vocabulary(ontology_path)
    nouns = vocabulary["Nouns"]
    verbs = set(vocabulary["Verbs"])
    local = {"Nouns": [], "Verbs": []}
    local_nouns, local_verbs, attributes, specialized = {}, {}, {}, {}
    population, sentences, assertions, implicit = [], [], [], []
    fenced = False
    meaningful = 0

    def fields_for(noun):
        fields, active, visited, field_names = [], set(), set(), set()

        def visit(noun):
            if noun is None:
                return
            name = noun["Name"]
            if name in active:
                raise ValueError("Cyclic noun inheritance.")
            if name in visited:
                return
            active.add(name)
            for attribute in noun.get("NounAttributes") or []:
                if attribute["Name"] not in field_names:
                    fields.append({"FieldName": attribute["Name"], "FieldValue": None})
                    field_names.add(attribute["Name"])
            # Upstream resolves inherited attributes against the standard vocabulary only.
            parents = noun.get("ParentNounNames", [noun.get("ParentNounName")])
            for parent in parents:
                visit(nouns.get(parent))
            active.remove(name)
            visited.add(name)

        visit(noun)
        return fields or None

    for number, raw in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("```"):
            if not fenced and line.lower() not in ("```dwis", "```config", "```text", "```"):
                raise ValueError(f"Line {number}: unsupported code fence.")
            fenced = not fenced
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        line = line.removesuffix(";").rstrip()
        meaningful += 1
        try:
            # Match assignments before declarations so URLs/date-times in values are preserved.
            assignment = re.fullmatch(r"([^\s.]+)\s*\.\s*(\w+)\s*=\s*(.+)", line)
            declaration = re.fullmatch(r"([^\s:]+)\s*:\s*([^\s:]+)", line)
            if assignment:
                subject, key, value = assignment.groups()
                key_lower = key.lower()
                individual = next((n for n in population if n["UniqueName"] == subject), None)
                if individual is not None:
                    field = next(
                        (
                            f
                            for f in individual["Fields"] or []
                            if f["FieldName"].lower() == key_lower
                        ),
                        None,
                    )
                    if field is None:
                        raise ValueError(f"Unknown attribute {subject}.{key}.")
                    field["FieldValue"] = value
                elif subject in local_nouns and key_lower == "parent":
                    local_nouns[subject]["ParentNounName"] = value
                elif subject in local_verbs and key_lower == "parent":
                    local_verbs[subject]["ParentVerbName"] = value
                elif subject.lower() in attributes:
                    attribute = attributes[subject.lower()]
                    if key_lower == "type":
                        attribute["Type"] = value
                    elif key_lower == "noun" and value in local_nouns:
                        noun = local_nouns[value]
                        noun["NounAttributes"] = (noun["NounAttributes"] or []) + [attribute]
                    else:
                        raise ValueError("Invalid local attribute assignment.")
                elif subject.lower() in specialized:
                    attribute = specialized[subject.lower()]
                    if key_lower == "value":
                        attribute["SpecializedValue"] = value
                    elif key_lower == "noun" and value in local_nouns:
                        noun = local_nouns[value]
                        noun["SpecializedNounAttributes"] = (
                            noun["SpecializedNounAttributes"] or []
                        ) + [attribute]
                    else:
                        raise ValueError("Invalid specialized attribute assignment.")
                else:
                    raise ValueError(f"Unknown assignment subject {subject}.")
            elif declaration:
                typename, name = declaration.groups()
                keyword = typename.lower()
                if keyword in ("noun", "verb"):
                    kind = keyword.capitalize()
                    definition = _definition(name, kind)
                    registry = local_nouns if kind == "Noun" else local_verbs
                    if name in registry:
                        raise ValueError(f"Duplicate local {keyword} {name}.")
                    registry[name] = definition
                    local[kind + "s"].append(definition)
                elif keyword == "noun-attribute":
                    attributes[name.lower()] = dict(
                        Type=None, Name=name, DisplayName=None, Description=None
                    )
                elif keyword == "specialized-noun-attribute":
                    specialized[name.lower()] = dict(AttributeName=name, SpecializedValue=None)
                else:
                    noun = nouns.get(typename) or local_nouns.get(typename)
                    if noun is None:
                        raise ValueError(f"Unknown noun {typename}.")
                    population.append(
                        dict(
                            TypeDictionaryURI=typename,
                            BrowseName=None,
                            UniqueName=name,
                            DisplayName=name,
                            Fields=fields_for(noun),
                        )
                    )
            else:
                parts = line.split()
                if len(parts) != 3:
                    raise ValueError("Expected a declaration, attribute assignment, or triple.")
                subject, verb, obj = parts
                if verb not in verbs:
                    raise ValueError(f"Unknown verb {verb}.")
                names = {n["UniqueName"] for n in population}
                if subject not in names:
                    raise ValueError(f"Subject {subject} must be declared first.")
                is_class = obj in nouns or obj in local_nouns
                if verb == "BelongsToClass" and is_class:
                    assertions.append(parts)
                elif verb != "BelongsToClass" and obj in names:
                    sentences.append(parts)
                elif verb != "BelongsToClass" and is_class:
                    implicit.append(parts)
                else:
                    raise ValueError(f"Unknown object or class {obj}.")
        except ValueError as error:
            raise ValueError(f"Line {number}: {error}") from error
    if fenced:
        raise ValueError("Unclosed code fence.")
    if not meaningful:
        raise ValueError("Input file is empty or contains only comments.")

    variables, nodes = [], []
    for node in population:
        if node["TypeDictionaryURI"] == "DynamicDrillingSignal":
            variables.append(
                dict(
                    NativeAddressSpaceNameSpace=None,
                    NativeAddressSpaceNodeID=None,
                    InjectedName=node["UniqueName"],
                    SamplingIntervalInMS=0.0,
                    Rank=0,
                    Dimensions=None,
                    DataType=None,
                )
            )
        else:
            nodes.append(node)
    variable_names = {v["InjectedName"] for v in variables}
    references = []
    for group, class_object in ((sentences, False), (assertions, True), (implicit, True)):
        for subject, verb, obj in group:
            subject_ns = "Nodes" if class_object or subject not in variable_names else "Variables"
            object_ns = URI if class_object else ("Variables" if obj in variable_names else "Nodes")
            references.append(
                dict(
                    Subject=dict(NameSpace=subject_ns, ID=subject),
                    VerbURI=URI + verb,
                    Object=dict(NameSpace=object_ns, ID=URI + obj if class_object else obj),
                )
            )
    return dict(
        ManifestName=None,
        Provider=dict(Name=provider.strip(), Company=company.strip()),
        InjectionInformation=dict(
            ServerName=None,
            EndPointURL=None,
            PublishingIntervalInMS=0.0,
            InjectedVariablesNamespaceAlias="Variables",
            InjectedNodesNamespaceAlias="Nodes",
            ProvidedVariablesNamespaceAlias="ProvidedVariables",
            InjectedVocabularyNamespaceAlias="Vocabulary",
        ),
        InjectedVariables=variables,
        InjectedNodes=nodes,
        InjectedReferences=references,
        ProvidedVariables=None,
        InjectedVocabulary=local,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for short, name in (("i", "input"), ("p", "provider"), ("c", "company"), ("o", "output")):
        parser.add_argument(f"-{short}", f"--{name}")
    parser.add_argument(
        "--ontology", help="DWIS Turtle ontology; defaults to the shared skill asset"
    )
    parser.add_argument(
        "positional",
        nargs="*",
        metavar="ARG",
        help="input.dwis provider company [output.json]; fills unset named options",
    )
    args = list(sys.argv[1:] if argv is None else argv)
    if "/?" in args:
        args = ["--help"]
    options = parser.parse_intermixed_args(args)
    positional = iter(options.positional)
    values = {
        key: getattr(options, key) if getattr(options, key) is not None else next(positional, None)
        for key in ("input", "provider", "company", "output")
    }
    try:
        if next(positional, None) is not None:
            raise ValueError("Too many positional arguments.")
        for key in ("input", "provider", "company"):
            if not values[key] or not values[key].strip():
                raise ValueError(f"The {key} argument is required.")
        source = Path(values["input"]).resolve()
        target = (
            Path(values["output"]).resolve()
            if values["output"] and values["output"].strip()
            else source.with_suffix(".json")
        )
        if source == target or (target.exists() and source.samefile(target)):
            raise ValueError("Output must differ from input.")
        ontology = Path(options.ontology) if options.ontology else default_ontology_path()
        if target == ontology.resolve() or (target.exists() and target.samefile(ontology)):
            raise ValueError("Output must differ from the ontology.")
        manifest = create_manifest(
            source.read_text(encoding="utf-8-sig"),
            values["provider"],
            values["company"],
            ontology_path=ontology,
        )
        target.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"Input file : {source}\nProvider   : {values['provider'].strip()}\n"
            f"Company    : {values['company'].strip()}\nOutput file: {target}"
        )
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
