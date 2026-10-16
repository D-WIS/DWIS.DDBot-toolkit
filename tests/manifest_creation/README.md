# Manifest conversion verification

All verification for `modules/manifest-creation` lives here. Product code and the original
C# entry point remain under `modules/`.

```text
manifest_creation/
  test_conversion.py     # Offline DTO, parsing, and fixture contracts
  test_cli.py            # Offline Python command-line contract
  test_equivalence.py    # Live differential checks, marked reference
  test_verification.py   # Package alignment and reference failure handling
  support.py             # Paths, converter imports, and bounded process helpers
  conftest.py            # Session-scoped reference build
  fixtures/              # CONFIG input and pinned C# JSON pairs
  harness/               # Verification-only C# executable
```

From the repository root, using the development environment with pytest installed:

```bash
# Fast tests: no .NET invocation or NuGet restore; live tests are reported as skipped.
uv run pytest -q tests/manifest_creation

# Complete module verification: requires a .NET 8-compatible SDK and pinned NuGet packages.
uv run pytest -q tests/manifest_creation --run-reference

# Only live differential tests.
uv run pytest -q tests/manifest_creation --run-reference -m reference

# Complete repository verification, including live tests (recommended for CI).
uv run pytest -q --run-reference
```

`uv run` may provision the development environment on first use. For a provisioned environment,
`.venv/bin/python -m pytest` runs the offline checks without provisioning. On Windows, use
`.venv\Scripts\python.exe -m pytest`.

The legacy `MANIFEST_CREATION_REFERENCE=require` environment variable also enables strict
reference execution. The opt-in switch is portable across shells and is preferred. Enabling
live tests means missing SDKs, package restore errors, compiler errors, conversion failures,
and timeouts are failures, never skips. Build failures show both stdout and stderr. A build
has a 180-second timeout; each reference invocation has a 60-second timeout.

The harness builds once per session into pytest's temporary directory. Manual `dotnet run`
commands may produce `harness/bin/` and `harness/obj/`; these are ignored by Git.

## What is verified

Offline checks compare all discovered fixture pairs and cover the Python CLI and documented
input-handling fixes. An XML-based check requires the harness to pin every direct C# module
package to the same version; it also runs before a live build.

Live checks reproduce committed fixtures, compare a shared corpus, sweep all standard nouns
and verbs, and compare the bundled vocabulary with the library's vocabulary projection.
JSON comparisons ignore object-key order but preserve array order, repeated entries, null
values, and string contents.

The oracle is the pinned DWIS libraries with initialized instance collections and
`fromMD: false`. It is not the original console entry point: that entry point has documented
initialization and Markdown-mode issues. Passing these tests demonstrates agreement on the
covered conversion cases, not equivalence on every possible input or identical CLI behavior.
Python-specific improvements (strict errors, fences, and literal parsing) have separate
behavior tests. See the [conversion notes](../../modules/manifest-creation/python/README.md).

## Updating fixtures and vocabulary

Use the reference harness to generate expected outputs; do not generate them with the Python
implementation being tested. Review dependency updates and generated diffs together.

```bash
dotnet run --project tests/manifest_creation/harness -- \
  manifest tests/manifest_creation/fixtures/example.txt Provider Company \
  tests/manifest_creation/fixtures/example.json

dotnet run --project tests/manifest_creation/harness -- \
  vocabulary modules/manifest-creation/python/vocabulary.json
```

Every `.txt` fixture must have a matching `.json`, and vice versa. New pairs are discovered
automatically. Run the full module verification after regenerating them.
