# Manifest creation

Convert DWIS CONFIG `.txt` files into manifest JSON, with provider and company metadata.
The two implementations live together here so their CLI and output contract can be
maintained as one module.

| Implementation | Requirements | Details |
| --- | --- | --- |
| [Python](python/README.md) | Python 3.11+, standard library only | Standalone distribution with a bundled vocabulary snapshot |
| [C#](csharp/README.md) | .NET 8 SDK to build; runtime needed for framework-dependent deployment | Original implementation using DWIS NuGet packages |

## Python usage

From the repository root:

```bash
python modules/manifest-creation/python/manifest_creation.py input.txt Provider Company
```

Both CLIs accept `input.txt provider company [output.json]` or the named arguments
`--input`, `--provider`, `--company`, and `--output`. The default output changes the input
extension to `.json`.

The intended conversion uses `DWIS.API.DTO` 2.2.32 and vocabulary 1.0.172. The Python
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
   over sweeps that use every noun and verb in the bundled vocabulary. They are skipped by
   default. Add `--run-reference` to enable them; missing SDKs, restore/build failures,
   timeouts, and conversion failures then fail the suite. The existing environment variable
   `MANIFEST_CREATION_REFERENCE=require` also enables this strict mode.

Run all module checks, including the C# reference checks (recommended for CI):

```bash
uv run pytest -q tests/manifest_creation --run-reference
```

The offline checks also enforce matching package versions in the C# module and harness.
See the [verification guide](../../tests/manifest_creation/README.md) for the test layout
and runtime requirements.

Regenerate a fixture or the vocabulary snapshot after a package or vocabulary change:

```bash
dotnet run --project tests/manifest_creation/harness -- \
  manifest tests/manifest_creation/fixtures/<name>.txt Provider Company \
  tests/manifest_creation/fixtures/<name>.json
dotnet run --project tests/manifest_creation/harness -- \
  vocabulary modules/manifest-creation/python/vocabulary.json
```

The vocabulary dump is field-for-field identical to `python/vocabulary.json`, so that command
regenerates the bundled snapshot; the test suite asserts the equality.

## Conversion prompt

The conversion brief below records the intended contract and has been updated for the
current test layout and execution policy. It can be reused as a template for another module:

```text
Convert the C# manifest-creation console tool in modules/manifest-creation/csharp into a
standalone Python 3.11+ module under modules/manifest-creation/python. The Python module must
produce the manifest JSON of the C# conversion for the same CONFIG input, using only the
standard library: no .NET, no third-party packages, no network access, and no installation,
on Windows, Linux, and macOS.

Source of truth
- Pin DWIS.API.DTO 2.2.32, DWIS.Vocabulary.Standard 1.0.172, and DWIS.Vocabulary.Utils
  1.0.172, the versions in manifest-creation.csproj.
- Reimplement the conversion path VocabularyParsing.FromLines with ordinary CONFIG parsing
  (not the Markdown default) and ManifestFile.FromDWISInstance, including the DTO defaults
  they emit: ManifestName, ProvidedVariables, server settings, and namespace aliases.
- Extract the vocabulary from VocabularyProvider.GetDWISVocabulary() into a bundled
  python/vocabulary.json: noun names, parent names, attribute definitions (type, name,
  display name, description), and verb names. Ship the Apache 2.0 vocabulary license and the
  MIT DTO license next to the Python script and attribute both sources in the README.

CLI contract (mirror the C# CommandLineOptions)
- Usage: input.txt provider company [output.json], or --input/--provider/--company/--output
  with the short aliases -i/-p/-c/-o. Positional arguments fill unset named options in
  input/provider/company/output order. -h, --help, and /? print help.
- Require a .txt input and non-blank provider and company. The default output is the input
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
  every verb, comparing the two implementations. Mark them reference and skip by default;
  --run-reference (or MANIFEST_CREATION_REFERENCE=require) enables strict execution, where
  missing SDKs, restore/build errors, timeouts, and conversion failures fail the suite.
- Add an offline check that the harness pins every direct package dependency of the C# module
  to the same version. Include stdout and stderr in process failures and bound execution time.
- Document the shared contract, the intentional differences from the C# entry point, and the
  upstream sources and licenses in modules/manifest-creation/README.md, python/README.md, and
  csharp/README.md, including the commands that regenerate fixtures and the vocabulary.
```
