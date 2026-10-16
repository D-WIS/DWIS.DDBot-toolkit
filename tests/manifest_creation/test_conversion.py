"""Offline conversion contracts and pinned fixture parity."""

import json

import pytest

from .support import COMPANY, FIXTURE_NAMES, FIXTURES, PROVIDER, create, read_fixture


def test_fixtures_are_complete_pairs():
    assert FIXTURE_NAMES, "no fixtures found"
    assert FIXTURE_NAMES == sorted(path.stem for path in FIXTURES.glob("*.json"))


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_matches_pinned_dotnet_fixture(name: str):
    expected = json.loads(read_fixture(name, "json"))
    assert create(read_fixture(name, "txt")) == expected


def test_repeated_references_and_field_assignments_are_kept():
    """The example fixture pins repeated triples, multiple types, and a literal value."""
    manifest = json.loads(read_fixture("example", "json"))
    verbs = [reference["VerbURI"] for reference in manifest["InjectedReferences"]]
    assert verbs.count("http://ddhub.no/HasDynamicValue") == 2
    types = [node["TypeDictionaryURI"] for node in manifest["InjectedNodes"]]
    assert types.count("WOB") == 1 and types.count("ContinuousDataType") == 1
    provider = next(node for node in manifest["InjectedNodes"] if node["UniqueName"] == "provider")
    assert provider["Fields"] == [{"FieldName": "ProviderName", "FieldValue": '"Example Company"'}]


# --------------------------------------------------------------------------------------
# 2a. Manifest shape: DTO defaults and provider metadata
# --------------------------------------------------------------------------------------


def test_manifest_uses_pinned_dto_defaults():
    manifest = create("WOB:point\n")
    assert list(manifest) == [
        "ManifestName",
        "Provider",
        "InjectionInformation",
        "InjectedVariables",
        "InjectedNodes",
        "InjectedReferences",
        "ProvidedVariables",
        "InjectedVocabulary",
    ]
    assert manifest["ManifestName"] is None
    assert manifest["Provider"] == {"Name": PROVIDER, "Company": COMPANY}
    assert manifest["InjectionInformation"] == {
        "ServerName": None,
        "EndPointURL": None,
        "PublishingIntervalInMS": 0.0,
        "InjectedVariablesNamespaceAlias": "Variables",
        "InjectedNodesNamespaceAlias": "Nodes",
        "ProvidedVariablesNamespaceAlias": "ProvidedVariables",
        "InjectedVocabularyNamespaceAlias": "Vocabulary",
    }
    assert manifest["ProvidedVariables"] is None
    assert manifest["InjectedVocabulary"] == {"Nouns": [], "Verbs": []}


def test_provider_and_company_are_trimmed():
    assert create("WOB:point\n", " Provider ", "\tCompany ")["Provider"] == {
        "Name": PROVIDER,
        "Company": COMPANY,
    }


@pytest.mark.parametrize(
    "provider, company", [("", COMPANY), ("  ", COMPANY), (PROVIDER, ""), (PROVIDER, " ")]
)
def test_blank_provider_or_company_is_rejected(provider: str, company: str):
    with pytest.raises(ValueError, match="Provider and company"):
        create("WOB:point\n", provider, company)


# --------------------------------------------------------------------------------------
# 2b. Declarations, fields, and variables
# --------------------------------------------------------------------------------------


def test_declaration_becomes_node_with_attribute_fields():
    manifest = create("DataProvider:provider\n")
    assert manifest["InjectedNodes"] == [
        {
            "TypeDictionaryURI": "DataProvider",
            "BrowseName": None,
            "UniqueName": "provider",
            "DisplayName": "provider",
            "Fields": [{"FieldName": "ProviderName", "FieldValue": None}],
        }
    ]


def test_noun_without_attributes_has_null_fields():
    manifest = create("ContinuousDataType:point\n")
    assert manifest["InjectedNodes"][0]["Fields"] is None


def test_fields_follow_declared_then_inherited_attributes():
    """WitsMLTimeBasedLogEndPoint defines attributes and inherits one from DataEndPoint."""
    fields = create("WitsMLTimeBasedLogEndPoint:endpoint\n")["InjectedNodes"][0]["Fields"]
    assert [field["FieldName"] for field in fields] == [
        "WellUID",
        "WellName",
        "WellboreUID",
        "WellboreName",
        "LogUID",
        "LogName",
        "Mnemonic",
        "EndPointDescription",
    ]


def test_dynamic_drilling_signal_declaration_becomes_injected_variable():
    manifest = create("DynamicDrillingSignal:signal\n")
    assert manifest["InjectedNodes"] == []
    assert manifest["InjectedVariables"] == [
        {
            "NativeAddressSpaceNameSpace": None,
            "NativeAddressSpaceNodeID": None,
            "InjectedName": "signal",
            "SamplingIntervalInMS": 0.0,
            "Rank": 0,
            "Dimensions": None,
            "DataType": None,
        }
    ]


@pytest.mark.parametrize("noun", ["DrillingSignal", "SetPoint", "ContinuousDataType"])
def test_only_the_exact_dynamic_signal_type_becomes_a_variable(noun: str):
    manifest = create(f"{noun}:signal\n")
    assert manifest["InjectedVariables"] == []
    assert [node["TypeDictionaryURI"] for node in manifest["InjectedNodes"]] == [noun]


def test_one_individual_can_carry_several_types():
    manifest = create("WOB:point\nContinuousDataType:point\n")
    assert [
        (node["TypeDictionaryURI"], node["UniqueName"]) for node in manifest["InjectedNodes"]
    ] == [
        ("WOB", "point"),
        ("ContinuousDataType", "point"),
    ]


# --------------------------------------------------------------------------------------
# 2c. Attribute assignments
# --------------------------------------------------------------------------------------


def test_attribute_assignment_sets_only_the_named_field():
    manifest = create('DataProvider:provider\nprovider.ProviderName = "Acme"\n')
    assert manifest["InjectedNodes"][0]["Fields"] == [
        {"FieldName": "ProviderName", "FieldValue": '"Acme"'}
    ]


def test_attribute_assignment_is_case_insensitive():
    manifest = create("DataProvider:provider\nprovider.PROVIDERNAME = Acme\n")
    assert manifest["InjectedNodes"][0]["Fields"][0]["FieldValue"] == "Acme"


def test_attribute_assignment_updates_the_first_declaration_with_that_name():
    manifest = create('DrillingSignal:s\nWOB:s\ns.Value = "7"\n')
    first, second = manifest["InjectedNodes"]
    assert first["Fields"] == [{"FieldName": "Value", "FieldValue": '"7"'}]
    assert second["Fields"] == [{"FieldName": "IsValid", "FieldValue": None}]


def test_attribute_values_keep_quotes_urls_and_equals_signs():
    """A documented fix: the C# parser drops values containing ':' or '='."""
    manifest = create('DataProvider:provider\nprovider.ProviderName = "https://example.com/?a=b"\n')
    assert manifest["InjectedNodes"][0]["Fields"] == [
        {"FieldName": "ProviderName", "FieldValue": '"https://example.com/?a=b"'}
    ]


# --------------------------------------------------------------------------------------
# 2d. References: ordering and namespaces
# --------------------------------------------------------------------------------------


def _reference_key(reference: dict) -> tuple:
    return (
        (reference["Subject"]["NameSpace"], reference["Subject"]["ID"]),
        reference["VerbURI"].removeprefix("http://ddhub.no/"),
        (reference["Object"]["NameSpace"], reference["Object"]["ID"]),
    )


def test_reference_groups_are_ordered_ordinary_then_class_then_implicit():
    manifest = create(
        "DynamicDrillingSignal:signal\n"
        "WOB:point\n"
        "point IsOfMeasurableQuantity ForceDrillingQuantity\n"
        "signal BelongsToClass DrillingSignal\n"
        "point HasDynamicValue signal\n"
    )
    assert [_reference_key(reference) for reference in manifest["InjectedReferences"]] == [
        (("Nodes", "point"), "HasDynamicValue", ("Variables", "signal")),
        (
            ("Nodes", "signal"),
            "BelongsToClass",
            ("http://ddhub.no/", "http://ddhub.no/DrillingSignal"),
        ),
        (
            ("Nodes", "point"),
            "IsOfMeasurableQuantity",
            ("http://ddhub.no/", "http://ddhub.no/ForceDrillingQuantity"),
        ),
    ]


def test_subjects_of_class_assertions_use_the_nodes_namespace_even_for_variables():
    manifest = create("DynamicDrillingSignal:signal\nsignal BelongsToClass DrillingSignal\n")
    assert manifest["InjectedReferences"][0]["Subject"] == {
        "NameSpace": "Nodes",
        "ID": "signal",
    }


def test_ordinary_reference_subjects_use_the_variables_namespace():
    manifest = create("DynamicDrillingSignal:signal\nWOB:point\nsignal HasDynamicValue point\n")
    reference = manifest["InjectedReferences"][0]
    assert reference["Subject"] == {"NameSpace": "Variables", "ID": "signal"}
    assert reference["Object"] == {"NameSpace": "Nodes", "ID": "point"}


def test_reference_objects_follow_declared_types():
    manifest = create(
        "DynamicDrillingSignal:a\nDynamicDrillingSignal:b\nWOB:p\na IsProvidedBy p\np IsProvidedBy b\n"
    )
    assert [reference["Object"]["NameSpace"] for reference in manifest["InjectedReferences"]] == [
        "Nodes",
        "Variables",
    ]


def test_implicit_references_point_at_the_vocabulary_namespace():
    manifest = create("WOB:point\npoint IsOfMeasurableQuantity ForceDrillingQuantity\n")
    assert manifest["InjectedReferences"] == [
        {
            "Subject": {"NameSpace": "Nodes", "ID": "point"},
            "VerbURI": "http://ddhub.no/IsOfMeasurableQuantity",
            "Object": {
                "NameSpace": "http://ddhub.no/",
                "ID": "http://ddhub.no/ForceDrillingQuantity",
            },
        }
    ]


# --------------------------------------------------------------------------------------
# 2e. Local vocabulary
# --------------------------------------------------------------------------------------


def test_local_definitions_use_pinned_dto_defaults():
    manifest = create(
        "NOUN:LocalPoint\nLocalPoint.Parent = DWISNoun\nVERB:LocalRelation\nLocalRelation.Parent = DWISVerb\n"
    )
    noun, verb = (
        manifest["InjectedVocabulary"]["Nouns"][0],
        manifest["InjectedVocabulary"]["Verbs"][0],
    )
    assert noun == {
        "Name": "LocalPoint",
        "DisplayName": None,
        "ParentNounName": "DWISNoun",
        "Description": None,
        "Examples": None,
        "DefinitionSetName": None,
        "IsDeprecated": False,
        "WillBeRemovedBy": "0001-01-01T00:00:00",
        "WillBeRemovedFromVersion": None,
        "ReplacedBy": None,
        "NounAttributes": None,
        "SpecializedNounAttributes": None,
    }
    assert verb["Name"] == "LocalRelation"
    assert verb["ParentVerbName"] == "DWISVerb"
    assert verb["MinCardinality"] == -1 and verb["MaxCardinality"] == -1
    assert verb["DomainNounName"] is None and verb["RangeNounName"] is None


def test_local_noun_is_instantiated_and_used_as_class_object():
    manifest = create(
        "NOUN:LocalPoint\nLocalPoint.Parent = DWISNoun\nLocalPoint:local\nlocal BelongsToClass LocalPoint\n"
    )
    assert manifest["InjectedNodes"] == [
        {
            "TypeDictionaryURI": "LocalPoint",
            "BrowseName": None,
            "UniqueName": "local",
            "DisplayName": "local",
            "Fields": None,
        }
    ]
    assert manifest["InjectedReferences"][0]["Object"] == {
        "NameSpace": "http://ddhub.no/",
        "ID": "http://ddhub.no/LocalPoint",
    }


def test_local_noun_inherits_attributes_from_its_standard_parent():
    manifest = create("NOUN:LocalPoint\nLocalPoint.Parent = DataProvider\nLocalPoint:p\n")
    assert manifest["InjectedNodes"][0]["Fields"] == [
        {"FieldName": "ProviderName", "FieldValue": None}
    ]


def test_local_attribute_is_attached_to_a_local_noun():
    manifest = create(
        "NOUN:LocalPoint\n"
        "LocalPoint.Parent = DWISNoun\n"
        "NOUN-ATTRIBUTE:LocalWeight\n"
        "LocalWeight.Type = double\n"
        "LocalWeight.Noun = LocalPoint\n"
        "LocalPoint:p\n"
    )
    noun = manifest["InjectedVocabulary"]["Nouns"][0]
    assert noun["NounAttributes"] == [
        {
            "Type": "double",
            "Name": "LocalWeight",
            "DisplayName": None,
            "Description": None,
        }
    ]
    assert manifest["InjectedNodes"][0]["Fields"] == [
        {"FieldName": "LocalWeight", "FieldValue": None}
    ]


def test_specialized_attribute_is_attached_to_a_local_noun():
    manifest = create(
        "NOUN:LocalPoint\n"
        "LocalPoint.Parent = DWISNoun\n"
        "SPECIALIZED-NOUN-ATTRIBUTE:LocalSpec\n"
        "LocalSpec.Value = 3\n"
        "LocalSpec.Noun = LocalPoint\n"
        "LocalPoint:p\n"
    )
    noun = manifest["InjectedVocabulary"]["Nouns"][0]
    assert noun["SpecializedNounAttributes"] == [
        {"AttributeName": "LocalSpec", "SpecializedValue": "3"}
    ]


def test_local_verbs_are_declared_but_not_usable_in_triples():
    """Relation verbs must be standard verbs, as in the upstream parser."""
    with pytest.raises(ValueError, match="Line 5: Unknown verb LocalRelation"):
        create(
            "VERB:LocalRelation\n"
            "LocalRelation.Parent = DWISVerb\n"
            "DynamicDrillingSignal:s\n"
            "WOB:p\n"
            "p LocalRelation s\n"
        )


# --------------------------------------------------------------------------------------
# 2f. Input handling
# --------------------------------------------------------------------------------------


def test_input_decorations_match_plain_config_output():
    """BOM, markdown fences, list prefixes, comments, blank lines, and trailing semicolons."""
    plain = read_fixture("example", "txt")
    lines = [line for line in plain.splitlines() if not line.startswith("#")]
    decorated = "\ufeff# intent: example\n```dwis\n"
    decorated += "\n".join("- " + line + ";" for line in lines if line) + "\n```"
    assert create(decorated) == json.loads(read_fixture("example", "json"))


@pytest.mark.parametrize("opening", ["```dwis", "```config", "```text", "```", "```DWIS"])
def test_supported_code_fences(opening: str):
    assert create(f"{opening}\nWOB:point\n```\n") == create("WOB:point\n")


def test_unsupported_code_fence_is_rejected():
    with pytest.raises(ValueError, match="Line 1: unsupported code fence"):
        create("```json\nWOB:point\n```\n")


def test_unclosed_code_fence_is_rejected():
    with pytest.raises(ValueError, match="Unclosed code fence"):
        create("```dwis\nWOB:point\n")


@pytest.mark.parametrize("text", ["", "\n\n", "# only a comment\n", "# one\n\n# two\n"])
def test_empty_or_comment_only_input_is_rejected(text: str):
    with pytest.raises(ValueError, match="empty or contains only comments"):
        create(text)


def test_markdown_prose_is_not_supported():
    with pytest.raises(ValueError, match="Line 1: Expected a declaration"):
        create("Here is some prose about the configuration.\n")


# --------------------------------------------------------------------------------------
# 2g. Invalid input reports a line number
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, message",
    [
        ("UnknownClass:x", "Line 1: Unknown noun UnknownClass"),
        ("WOB:x\nx UnknownVerb x", "Line 2: Unknown verb UnknownVerb"),
        ("WOB:x\nx HasDynamicValue missing", "Line 2: Unknown object or class missing"),
        ("x HasDynamicValue x", "Line 1: Subject x must be declared first"),
        ("DataProvider:x\nx.UnknownAttribute = 1", "Line 2: Unknown attribute x.UnknownAttribute"),
        ("DataProvider:x\nother.Attribute = 1", "Line 2: Unknown assignment subject other"),
        ("NOUN:L\nNOUN:L\nL.Parent = DWISNoun", "Line 2: Duplicate local noun L"),
        ("NOUN-ATTRIBUTE:A\nA.Noun = Missing", "Line 2: Invalid local attribute assignment"),
        ("WOB:x\ny.z = 1", "Line 2: Unknown assignment subject y"),
        ("DataProvider:p\nq.ProviderName = 1", "Line 2: Unknown assignment subject q"),
        ("WOB:x\nz z", "Line 2: Expected a declaration"),
        ("a b c d", "Line 1: Expected a declaration"),
        ("```json\nWOB:x", "Line 1: unsupported code fence"),
    ],
)
def test_invalid_input_reports_line_number(text: str, message: str):
    with pytest.raises(ValueError, match=message):
        create(text)
