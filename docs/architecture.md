# Architecture

This document describes the implementation of the `model-dwis-config` Skill for contributors.
For installation and use, see the [README](../README.md).

## Dependency direction

```text
host coding agent
      │
      ├── collects user inputs through dialogue
      ├── summarizes and confirms an intent sketch
      ├── generates, validates, and repairs a draft
      └── delivers the final DWIS CONFIG
                 │
                 ▼
        bundled Python toolkit
                 │
        ┌────────┴─────────────┐
        ▼                      ▼
 shared ontology/examples   validation/reasoning
```

The bundled Python modules implement ontology search, example retrieval, and validation. The CLI
is their stable executable boundary; the Skill instructions own the conversational workflow and do
not duplicate that implementation.

The default interactive workflow clarifies inputs and confirms the intent sketch with the user.
When non-interactive, one-shot, or batch processing is explicitly requested, the agent extracts
the intent from the supplied description, records necessary assumptions, and proceeds without
confirmation. Both modes validate and repair the CONFIG before delivery.

## Interface priority

1. **Python modules** own implementations and structured result models.
2. **CLI** is the executable interface for local coding agents, people, and CI.
3. **Skill** owns the user-input, intent-sketch, draft-generation, validation, and repair workflow.
4. **Skill directory** packages the instructions and runtime as one directly installable unit.

## Runtime modes

During source development, run commands from the repository root:

```bash
uv run model-dwis-config/scripts/ddbot.py <command>
```

Because an agent normally works in the user's repository rather than the skill directory, invoke
the Skill's entry script by its resolved path:

```bash
uv run <script-path> <command>
```

Derive `<script-path>` from the exact loader-resolved `SKILL.md` as specified by the Skill. Never
hard-code a developer checkout path or search the filesystem for an installation.

## Current capabilities

| Capability | Python implementation | CLI command |
|---|---|---|
| Ontology search | `OntologySearch.search` | `ontology` |
| Example retrieval | `ExampleRetriever.search` | `examples` |
| Validation | `DDBotToolkit.validate` | `validate` |

## Single-source layout

`model-dwis-config/` is the skill root. Its `SKILL.md` and `references/` define the workflow;
`scripts/ddbot.py` is the sole entry point and `scripts/ddbot_toolkit/` is the only implementation.
The ontology and example corpus have one maintained copy under `assets/`, where both the agent and
CLI can find them. The repository root contains development tests, documentation, dependency
locking, and interface contracts without adding them to the installed Skill.
