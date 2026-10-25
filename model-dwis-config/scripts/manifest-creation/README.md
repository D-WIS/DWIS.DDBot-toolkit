# DWIS CONFIG to manifest

Convert a final, validated DWIS CONFIG file into a separate manifest JSON.
Input extensions are unrestricted, including `.dwis`.
Run only when the user requests conversion, following [SKILL.md](../../SKILL.md).
Provider and company names are required. The input CONFIG is preserved.

## Usage

From the skill root, using the runtime and cache established by the skill preflight:

```bash
uv run scripts/manifest-creation/manifest_creation.py \
  --ontology assets/DWISVocabulary.ttl \
  --input input.dwis --provider "Provider" --company "Company" --output manifest.json
```

Requires Python 3.11+ and `rdflib`, declared in the script's inline dependency metadata.
The default ontology is the skill's [DWISVocabulary.ttl](../../assets/DWISVocabulary.ttl).
Explicit paths are relative to the caller's working directory. Use `--help` for all options.

## Conversion behavior

- Classes, inheritance, relations, and attribute names come from the shared TTL ontology.
  Union attribute domains are supported; OWL restriction classes are excluded.
- Exact `DynamicDrillingSignal` declarations become `InjectedVariables`; other declarations
  become `InjectedNodes`. Fields are alphabetical within each class, followed by inherited
  fields, with duplicates removed. Attribute values remain literal strings.
- Blank lines, `# intent` comments, and supported CONFIG code fences are accepted.
  Declare individuals before their references and attribute assignments.
- This converter does not replace CONFIG validation. Parsing failures report an error before
  writing the manifest. An existing output file is overwritten on success; the output must
  differ from the CONFIG and ontology.

## Sources and licenses

Adapted parsing logic comes from [DWIS Vocabulary 1.0.172](https://github.com/D-WIS/DDHub-Semantic-Interoperability/tree/81a4245670dcfa189ce8406fe0f4a0ae27879987)
(`VocabularyParsing`, `TypedIndividual`, `Noun.GetAllAttributes`), covered by
[LICENSE-DWIS-Vocabulary](LICENSE-DWIS-Vocabulary) (Apache 2.0).
Manifest conversion and DTO defaults come from [DWIS API DTO 2.2.32](https://github.com/D-WIS/DWIS-Blackboard-Base/tree/1bfdaf53faae0db638a59af10b6c3791f03092cc)
(`ManifestFile.FromDWISInstance`), covered by [LICENSE-DWIS-DTO](LICENSE-DWIS-DTO) (MIT).
Vocabulary data is read from the skill's TTL at runtime.
