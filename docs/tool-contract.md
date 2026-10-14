# Tool contract

The bundled CLI delegates ontology search, example retrieval, and validation to one Python
implementation under `model-dwis-config/scripts/ddbot_toolkit/`. This document records the
repository's interface contract; it is not part of the installed Skill.

## CLI rules

- Invoke source checkouts with `uv run model-dwis-config/scripts/ddbot.py`.
- Invoke an installed Skill with its loader-derived `uv run <script-path>`.
- Write the machine-readable result to stdout as UTF-8 JSON.
- Reserve stderr for diagnostics and logs.
- Use exit code `0` for successful results.
- Use exit code `1` when validation ran successfully but the candidate is invalid.
- Use exit code `2` for invalid arguments, unreadable input, or execution errors.
- Accept file input where coding agents naturally work with files; accept stdin where composition
  and piping are useful.

## Stability

The command name, JSON field meanings, and exit-code semantics form the public contract. Add a
`schema_version` before changing result shapes incompatibly. Human-readable error messages may
improve over time; consumers should eventually branch on stable error codes instead of matching
message text.

## Commands

- `ontology <query> [--kind all|class|property] [--limit N]` searches the bundled ontology.
- `examples <query> [--corpus PATH] [--limit N]` ranks records in the bundled or selected JSONL
  example corpus.
- `validate [CONFIG]` validates a file, or stdin when `CONFIG` is omitted.

The global `--ontology PATH` option selects a different Turtle ontology for `ontology` and
`validate`. For direct CLI use, `DDBOT_ONTOLOGY_PATH` selects the default ontology and
`DDBOT_EXAMPLE_CORPUS_PATH` selects the default example corpus. Explicit command-line options
take precedence over these environment variables.

During Skill execution, the agent passes the bundled resource paths explicitly, following
`SKILL.md` and its [runtime guide](../model-dwis-config/references/environment.md).
