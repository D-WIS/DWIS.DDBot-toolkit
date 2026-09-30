# DDBot Toolkit

DDBot Toolkit is a portable DWIS skill for coding agents. It combines one Agent Skill with a
structured Python CLI while leaving planning, conversation, and file editing to the host agent.

The project is deliberately CLI-first:

```text
coding agent
     │
     ▼
model-dwis-config skill
     │
     ▼
collect inputs → confirm intent sketch → generate draft → validate/repair → deliver CONFIG
                                   │                         │
                                   └────── ddbot CLI ───────┘
                                                │
                                                ▼
                                      bundled Python toolkit
```

## Quick start

Install the repository development environment, then run the Skill's PEP 723 entry script:

```bash
uv sync --extra dev

uv run model-dwis-config/scripts/ddbot.py ontology "standpipe pressure"
uv run model-dwis-config/scripts/ddbot.py examples "measured standpipe pressure" --limit 3
uv run model-dwis-config/scripts/ddbot.py validate path/to/config.dwis
uv run pytest
```

`scripts/ddbot.py` declares its runtime dependencies inline, so an installed copy of the Skill does
not depend on the repository's `pyproject.toml` or `uv.lock`.

Every capability command writes JSON to stdout. `validate` exits with `0` when the configuration
is valid, `1` when validation completed but failed, and `2` for invocation or input errors. Omit
the file argument to read a configuration from stdin.

## Internal Python API

The CLI calls the implementation under the Skill's `scripts/` directory. Repository tests add that
directory to `PYTHONPATH` and can import:

```python
from ddbot_toolkit import DDBotToolkit

toolkit = DDBotToolkit()
matches = toolkit.ontology_search.search("pressure", kind="class")
report = toolkit.validate("DynamicDrillingSignal:pressure")
```

## Repository layout

```text
model-dwis-config/                 complete installable Skill package
  SKILL.md                         workflow and activation metadata
  references/                      runtime and modelling guidance
  assets/                          ontology and example corpus
  scripts/ddbot.py                 executable CLI entry point with inline dependencies
  scripts/ddbot_toolkit/           authoritative Python implementation
docs/                              repository design and maintenance documents
tests/                             repository capability tests
pyproject.toml                     repository development/test environment
uv.lock                            repository development dependency lock
```

The `model-dwis-config/` directory is the complete Skill boundary. Vendor or copy it into the target
project so its canonical path remains within that project's working directory:

```bash
cp -R <checkout>/model-dwis-config <project>/.agents/skills/model-dwis-config
```

Do not symlink it to a checkout outside the working directory. The Skill deliberately rejects
loader-resolved paths and resources outside that boundary.

See [installation](docs/installation.md) for repository-scoped installation and CLI invocation.

Environment overrides:

- `DDBOT_ONTOLOGY_PATH`: Turtle ontology file
- `DDBOT_EXAMPLE_CORPUS_PATH`: example corpus JSONL file

During Skill execution, any override must resolve within the host working directory. The Skill uses
its loader-derived bundled paths explicitly and rejects out-of-bound resources.

See the [architecture](docs/architecture.md), [tool contract](docs/tool-contract.md), and
[installation guide](docs/installation.md) for repository maintenance details.

## Sync upstream validation

The bundled `model-dwis-config/scripts/ddbot_toolkit/validation/` directory mirrors
`src/dwis_validation/` from [ddbot-benchmark](https://github.com/zl6977/ddbot-benchmark).
Make validation changes upstream, then sync them here:

```bash
bash scripts/sync_ddbot_benchmark.sh          # latest upstream master
bash scripts/sync_ddbot_benchmark.sh <sha>    # specific upstream commit
bash scripts/sync_ddbot_benchmark.sh --check  # compare with the recorded snapshot
uv run pytest
```

The script records the commit and path mapping in `scripts/.ddbot-benchmark-sync.json`.
It caches upstream Git objects under `.cache/`; `--check` works offline once the recorded commit
is cached. `DDBOT_BENCHMARK_URL` can override the upstream URL, including with a local checkout.
Only validation code is mirrored; ontology, examples, and upstream benchmark tests are excluded.
Review result-model changes against the toolkit's own `services.py` adapter and run its tests
after every sync.
