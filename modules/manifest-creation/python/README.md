# Python manifest creation

Standalone Python equivalent of `modules/manifest-creation/csharp`, using the DWIS DTO conversion
rules and vocabulary versions pinned by that project. Requires Python 3.11 or newer;
uses only the standard library. No .NET, pip packages, network connection, or Skill
installation is needed to run it on Windows, Linux, or macOS.

Copy this whole directory when distributing the tool: `vocabulary.json` and the license
files travel alongside `manifest_creation.py`. Paths to input/output files are relative
to the caller's working directory; the vocabulary is loaded relative to the script.

## Usage

From the repository root:

```bash
python modules/manifest-creation/python/manifest_creation.py input.txt Provider Company
python modules/manifest-creation/python/manifest_creation.py input.txt Provider Company output.json
python modules/manifest-creation/python/manifest_creation.py --input input.txt --provider Provider --company Company --output output.json
```

On Windows, `py -3` can be used instead of `python`; on Linux/macOS, use `python3` if
that is the available Python command.

The named options have short aliases `-i`, `-p`, `-c`, and `-o`. Positional arguments fill
unset named options in input/provider/company/output order, as in the C# CLI. Quote
paths or names containing spaces. `-h`, `--help`, and `/?` show help.

The default output replaces the input's `.txt` extension with `.json`. Input is UTF-8
(with or without a BOM); output is indented UTF-8 JSON. Success exits with status 0;
invalid input, argument errors, and read/write failures return a nonzero status.
Parsing completes before opening the output file, so parsing errors preserve an existing
output. An explicit output path can overwrite an existing file, but cannot be the input.

Example `input.txt`:

```text
DynamicDrillingSignal:wobSignal
WOB:wobPoint
wobPoint HasDynamicValue wobSignal
wobPoint IsOfMeasurableQuantity ForceDrillingQuantity
```

## Conversion behavior

- Exact `DynamicDrillingSignal` declarations become `InjectedVariables`; all other
  declarations become `InjectedNodes`.
- Node fields include the declared type's attributes followed by inherited attributes,
  initially `null`. Assignments such as `provider.ProviderName = "Acme"` update a field
  on the first declaration with that individual name. Field values remain strings,
  including any literal quotes, matching the C# DTO.
- References to individuals use the `Nodes` or `Variables` namespace. `BelongsToClass`
  and class shorthand objects use the vocabulary namespace `http://ddhub.no/`. As in
  the DTO, subjects of class assertions and implicit references use `Nodes`, even for
  dynamic signals.
- References are emitted in ordinary-reference, class-assertion, implicit-reference
  order, preserving source order within each group. Repeated declarations and triples
  are preserved, including multiple types for the same individual.
- `ManifestName` and `ProvidedVariables` remain `null`; source-server settings retain
  their DTO defaults. Only the exact dynamic-signal type is treated as a variable,
  without subclass inference.
- Local vocabulary declarations (`NOUN`, `VERB`, `NOUN-ATTRIBUTE`, and
  `SPECIALIZED-NOUN-ATTRIBUTE`) are included in `InjectedVocabulary`. Local nouns can
  be instantiated and used as class objects. Relation verbs must be standard verbs,
  matching the upstream parser. Attribute inheritance resolves standard parents.

This converter checks syntax and vocabulary names, not full semantic consistency,
domains/ranges, or graph connectivity. Declare individuals before their references or
attribute assignments.

## Intentional input-handling fixes

The original C# entry point calls `FromLines` with its default `fromMD: true`, which
silently ignores ordinary CONFIG lines. Its `DWISInstance` also leaves the population
and reference collections uninitialized, causing recognized declarations to throw.
Those behaviors were reproduced with the project's pinned NuGet versions.

This tool implements the intended conversion with initialized collections and ordinary
CONFIG parsing. It additionally accepts `- ` list prefixes, blank/comment lines,
optional trailing semicolons, and fenced `dwis`, `config`, or `text` snippets. Invalid
lines fail with a line number instead of silently generating incomplete manifests.
Unclosed or unsupported fences are errors. Markdown prose surrounding snippets is not
supported. Attribute assignments are recognized before declarations so colons or equals
signs inside a literal value are preserved. Local attribute lists can be initialized
when first attached to a local noun.

## Sources and verification

The bundled `vocabulary.json` contains the 2692 nouns and 208 verbs from
`DWIS.Vocabulary.Standard` **1.0.172**, extracted from
`VocabularyProvider.GetDWISVocabulary()`. It retains only noun names, parent names,
attribute definitions, and verb names needed by this converter; documentation is omitted.
The vocabulary snapshot is independent of the ontology bundled in `model-dwis-config`.

Conversion sources:

- [DWIS Vocabulary](https://github.com/D-WIS/DDHub-Semantic-Interoperability/tree/81a4245670dcfa189ce8406fe0f4a0ae27879987),
  `VocabularyParsing`, `TypedIndividual`, and `Noun.GetAllAttributes`, version 1.0.172.
  The vocabulary and adapted logic are covered by `LICENSE-DWIS-Vocabulary` (Apache 2.0).
- [DWIS API DTO](https://github.com/D-WIS/DWIS-Blackboard-Base/tree/1bfdaf53faae0db638a59af10b6c3791f03092cc),
  `ManifestFile.FromDWISInstance` and DTO defaults, version 2.2.32.
  Adapted conversion logic is covered by `LICENSE-DWIS-DTO` (MIT, copyright 2025 D-WIS).

`tests/manifest_creation/fixtures/<name>.json` files were generated by these exact NuGet
packages, using provider `Provider` and company `Company`. The reference harness lives
outside this module in [`tests/manifest_creation/harness`](../../../tests/manifest_creation/harness)
and only borrows the pinned packages; it initialized
`Population = new SimplePopulation()`, `Sentences = new SimpleSentenceCollection()`,
`ClassAssertions = new SimpleClassAssertionCollection()`, and
`ImplicitSentences = new SimpleImplicitSentenceCollection()`, then called
`VocabularyParsing.FromLines(lines, vocabulary, instance, fromMD: false)` followed by
`ManifestFile.FromDWISInstance`. This isolates the intended library conversion from the
entry-point issues above. JSON objects are compared structurally rather than by bytes.
The bundled `vocabulary.json` is the harness's projection of
`VocabularyProvider.GetDWISVocabulary()`, which `reference-harness vocabulary` regenerates
and the test suite compares field by field. An additional development comparison instantiated
every one of the 2692 standard nouns; that sweep is now part of the test suite.

Run the regression tests from the repository root:

```bash
uv run pytest -q tests/manifest_creation
```

The fixture-parity and behavior tests need pytest, but neither .NET nor network access.
Live differential tests are skipped by default. Add `--run-reference` to enable them;
SDK, restore, build, timeout, or conversion failures then fail the suite. The legacy
`MANIFEST_CREATION_REFERENCE=require` environment variable also enables the same strict mode.
See the [verification guide](../../../tests/manifest_creation/README.md) for commands and
fixture regeneration.
