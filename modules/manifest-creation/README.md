# Manifest creation

Convert DWIS CONFIG files into manifest JSON, with provider and company metadata.
The two implementations live together here so their CLI and output contract can be
maintained as one module.

| Implementation | Requirements | Details |
| --- | --- | --- |
| [Python](python/README.md) | Python 3.11+, rdflib | Uses the shared skill Turtle ontology |
| [C#](csharp/README.md) | .NET 8 SDK to build; runtime needed for framework-dependent deployment | Original implementation using DWIS NuGet packages |

## Python usage

From the repository root:

```bash
uv run modules/manifest-creation/python/manifest_creation.py input.dwis Provider Company
```

Both CLIs accept `input provider company [output.json]` or the named arguments
`--input`, `--provider`, `--company`, and `--output`. The default output changes the input
extension to `.json`. Python accepts any input extension, including `.dwis`, and extensionless
files; the original C# CLI requires `.txt`.

The manifest DTO defaults follow `DWIS.API.DTO` 2.2.32. Python reads vocabulary from
`model-dwis-config/assets/DWISVocabulary.ttl`; C# uses vocabulary 1.0.172 from NuGet. The Python
implementation includes input-handling fixes for the original C# entry point; the
[Python README](python/README.md#intentional-input-handling-fixes) describes those
differences. The C# source retains its original behavior.

## Verification

From the repository root:

```bash
uv run pytest -q tests/manifest_creation
```

`tests/manifest_creation` checks the two implementations at three levels:

1. **Pinned fixtures.** Every `tests/manifest_creation/fixtures/<name>.txt` is paired with a
   `<name>.json` reference produced by the pinned C# libraries, and every pair is discovered
   automatically. This layer needs neither .NET nor network access.
2. **Behavior tests.** DTO defaults, declaration and attribute conversion, reference ordering
   and namespaces, local vocabulary, input handling, error line numbers, and the CLI contract,
   including the documented differences from the C# entry point.
3. **Differential tests.** They build
   [`tests/manifest_creation/harness`](../../tests/manifest_creation/harness), a
   verification-only project outside this module, pinned to the same NuGet versions as the C#
   implementation, and compare its output with the Python output over a conversion corpus and
   over sweeps of the shared nouns and verbs. Known TTL/library differences are checked separately;
   field comparisons ignore `Fields` order because RDF does not specify attribute array order.
   They are skipped by default. Add `--run-reference` to enable them; missing SDKs, restore/build failures,
   timeouts, and conversion failures then fail the suite. The existing environment variable
   `MANIFEST_CREATION_REFERENCE=require` also enables this strict mode.

Run all module checks, including the C# reference checks (recommended for CI):

```bash
uv run pytest -q tests/manifest_creation --run-reference
```

The offline checks also enforce matching package versions in the C# module and harness.
See the [verification guide](../../tests/manifest_creation/README.md) for the test layout
and runtime requirements.

Regenerate a C# reference fixture after a package change:

```bash
dotnet run --project tests/manifest_creation/harness -- \
  manifest tests/manifest_creation/fixtures/<name>.txt Provider Company \
  tests/manifest_creation/fixtures/<name>.json
```

Python reads the shared TTL directly. The harness can export the pinned C# vocabulary with
`vocabulary <output.json>` for comparison; that export is not a Python runtime resource.

## Conversion prompt

The conversion brief below records the intended contract and has been updated for the
current test layout and execution policy. It can be reused as a template for another module:

```text
Convert the C# manifest-creation console tool in modules/manifest-creation/csharp into a
standalone Python 3.11+ module under modules/manifest-creation/python. The Python module must
preserve the C# manifest DTO shape while using rdflib to read the shared Turtle ontology.
No .NET runtime is required. Use uv inline dependency metadata for Python 3.11+ and rdflib.

Source of truth
- Pin DWIS.API.DTO 2.2.32, DWIS.Vocabulary.Standard 1.0.172, and DWIS.Vocabulary.Utils
  1.0.172, the versions in manifest-creation.csproj.
- Reimplement the conversion path VocabularyParsing.FromLines with ordinary CONFIG parsing
  (not the Markdown default) and ManifestFile.FromDWISInstance, including the DTO defaults
  they emit: ManifestName, ProvidedVariables, server settings, and namespace aliases.
- Use model-dwis-config/assets/DWISVocabulary.ttl for classes, inheritance, object properties,
  and datatype-property domains (including unionOf). Exclude OWL restriction classes; use
  deterministic alphabetical field order and deduplicate inherited fields. Provide --ontology
  for an explicit TTL path. Ship the Apache 2.0 parsing-logic license and MIT DTO license.

CLI contract (retain C# argument conventions, without its input suffix restriction)
- Usage: input.dwis provider company [output.json], or --input/--provider/--company/--output
  with the short aliases -i/-p/-c/-o. Positional arguments fill unset named options in
  input/provider/company/output order. -h, --help, and /? print help.
- Accept any input extension and require non-blank provider and company. The default output is the input
  path with a .json extension. Print the four-line summary the C# tool prints, with labels
  "Input file : ", "Provider   : ", "Company    : ", and "Output file: ".
- Exit 0 on success and report failures on stderr with a nonzero status.

Conversion rules
- Exact DynamicDrillingSignal declarations become InjectedVariables with DTO defaults; every
  other declaration becomes an InjectedNode whose fields are the declared type's attributes
  followed by inherited attributes, initially null.
- "subject.Attribute = value" updates the field of the first declaration with that individual
  name, and keeps the value a literal string including quotes, as the DTO does.
- Emit references in ordinary-reference, class-assertion, implicit-reference order, preserving
  source order within each group and keeping repeated declarations and triples.
- Use the Nodes namespace for subjects of class assertions and implicit references, Variables
  for dynamic-signal subjects of ordinary references, the vocabulary namespace
  http://ddhub.no/ for class objects, and Nodes or Variables for other objects.
- Send local NOUN, VERB, NOUN-ATTRIBUTE, and SPECIALIZED-NOUN-ATTRIBUTE declarations to
  InjectedVocabulary; local nouns can be instantiated and used as class objects; relation
  verbs must be standard verbs, as in the upstream parser.

Intentional input-handling fixes over the C# entry point (implement and document them)
- Initialize Population, Sentences, ClassAssertions, and ImplicitSentences; the C# entry point
  leaves them null and calls FromLines with its Markdown default, which silently ignores
  ordinary CONFIG lines.
- Report the line number of an invalid line instead of silently generating an incomplete
  manifest, and keep parsing separate from writing so a failure preserves an existing output.
- Additionally accept list prefixes, blank and comment lines, optional trailing semicolons,
  and fenced dwis, config, or text snippets; reject unclosed or unsupported fences.

Verification (do not skip it)
- Add tests/manifest_creation/fixtures/<name>.txt with reference JSON, and
  tests/manifest_creation/test_*.py covering fixture parity, DTO defaults, conversion rules,
  input handling, error line numbers, and the CLI contract, so that the regression tests need
  no .NET and no network. Discover fixtures instead of listing them, and assert that a parsing
  failure leaves an existing output untouched.
- Treat modules/manifest-creation/csharp as read-only source: do not change its files. Add
  tests/manifest_creation/harness instead, a verification-only project outside the module and
  outside the shipped tool, pinned to the same packages, that exposes
  "manifest <input.txt> <provider> <company> <output.json>" (an instance with initialized
  collections, FromLines with fromMD: false, then ManifestFile.FromDWISInstance) and
  "vocabulary <output.json>" (the snapshot dump). Use it in opt-in differential tests over a
  conversion corpus and over sweeps that declare every noun, assign every attribute, and use
  every verb, comparing the shared vocabulary and explicitly recording TTL/library differences. Mark them reference and skip by default;
  --run-reference (or MANIFEST_CREATION_REFERENCE=require) enables strict execution, where
  missing SDKs, restore/build errors, timeouts, and conversion failures fail the suite.
- Add an offline check that the harness pins every direct package dependency of the C# module
  to the same version. Include stdout and stderr in process failures and bound execution time.
- Document the shared contract, the intentional differences from the C# entry point, and the
  upstream sources and licenses in modules/manifest-creation/README.md, python/README.md, and
  csharp/README.md, including commands to regenerate fixtures and inspect the C# vocabulary.
```
