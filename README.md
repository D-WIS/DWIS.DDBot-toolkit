# DDBot Toolkit

This repository is for developing and testing **`model-dwis-config`**, an Agent Skill for
generating, modifying, validating, and repairing DWIS CONFIG files from drilling-signal
descriptions.

The complete, installable Skill lives in [`model-dwis-config/`](model-dwis-config/). It bundles
the agent instructions, Python tools, DWIS ontology, and modelling examples.

## Prerequisites

- An installed agent CLI that supports Agent Skills and the `/skills` command.
- `uv` installed and available on `PATH` in the environment where your agent runs. [LINK](https://docs.astral.sh/uv/getting-started/installation/)

The Skill uses Python 3.11 or newer. `uv` can download a compatible Python version and install
the script's dependencies on first run, which may require network access.

## Install the Skill in your project

Copy the entire `model-dwis-config/` directory into your project's `.agents/skills/` directory:

```text
your-project/
  .agents/
    skills/
      model-dwis-config/
        SKILL.md
        references/
        assets/
        scripts/
```

For example, from this repository's root:

```bash
mkdir -p /path/to/your-project/.agents/skills
cp -R model-dwis-config /path/to/your-project/.agents/skills/
```

Only `model-dwis-config/` is needed. You do not need to copy the rest of this repository or
install its development environment.

## Use the Skill

Open the target project in your agent, enter `/skills`, and select `model-dwis-config`.
Then describe your task. For example:

> Generate a DWIS CONFIG for measured standpipe pressure.

> Validate signals.dwis and repair any errors.

The Skill guides the agent through clarifying the signal description, confirming the intended
model, generating a CONFIG, and validating and repairing it before delivery. It also supports
explicitly requested non-interactive, one-shot, and batch processing.

Ontology search, example retrieval, and validation run locally after setup. See the
[runtime guide](model-dwis-config/references/environment.md) for details.

## Develop the Skill

The following setup is for contributors working in this repository:

```bash
uv sync --extra dev
uv run ruff check
uv run pytest
```

```text
model-dwis-config/                 complete installable Skill
  SKILL.md                         agent workflow and activation metadata
  references/                      runtime and modelling guidance
  assets/                          ontology and example corpus
  scripts/ddbot.py                 CLI entry point
  scripts/ddbot_toolkit/           Python implementation
docs/                              design and maintenance documentation
tests/                             capability tests
scripts/                           repository maintenance scripts
pyproject.toml                     development and test dependencies
uv.lock                            development dependency lock
```

See the [architecture](docs/architecture.md) for implementation details and the
[tool contract](docs/tool-contract.md) for command interfaces.

### Sync upstream validation

The bundled `model-dwis-config/scripts/ddbot_toolkit/validation/` directory mirrors
`src/dwis_validation/` from [ddbot-benchmark](https://github.com/zl6977/ddbot-benchmark).
Make validation changes upstream, then sync them here:

```bash
bash scripts/sync_ddbot_benchmark.sh          # latest upstream master
bash scripts/sync_ddbot_benchmark.sh <sha>    # specific upstream commit
bash scripts/sync_ddbot_benchmark.sh --check  # compare with the recorded snapshot
uv run pytest
```

The script records the commit and path mapping in `scripts/.ddbot-benchmark-sync.json` and
caches upstream Git objects under `.cache/`. `--check` works offline once the recorded commit
is cached. Set `DDBOT_BENCHMARK_URL` to use a different upstream URL or a local checkout.
Only validation code is mirrored. Review result-model changes against the toolkit's
`services.py` adapter and run the tests after each sync.
