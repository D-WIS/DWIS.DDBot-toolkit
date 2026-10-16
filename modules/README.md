# Standalone modules

Group tools by function, then by implementation language. These modules are maintained
outside the installable `model-dwis-config` Skill.

```text
modules/
  manifest-creation/
    README.md
    python/
      README.md
      manifest_creation.py
      vocabulary.json
      LICENSE-DWIS-*
    csharp/
      README.md
      manifest-creation.csproj
      manifest-creation.slnx
      Program.cs
  <next-module>/
    README.md
    csharp/                 # Only add implementations that exist.
```

| Module | Purpose | Implementations |
| --- | --- | --- |
| [manifest-creation](manifest-creation/README.md) | Convert DWIS CONFIG text to manifest JSON | Python, C# |

## Adding and maintaining modules

- Use a descriptive lowercase directory name with hyphens: `modules/<module-name>/`.
- Give each module a README describing its purpose, implementations, common input/output
  contract, and behavior differences. Put language-specific setup and commands in the
  implementation's README.
- Keep dependencies with their implementation. C# projects declare NuGet dependencies in
  `.csproj`; Python modules that need third-party packages should get their own
  `pyproject.toml`. A standard-library-only script needs no package manifest.
- A small C# module can keep its `.csproj` and sources directly in `csharp/`. When it grows
  into multiple projects, use `csharp/src/<Project>/` and `csharp/tests/<Project>.Tests/`,
  with a module-local solution. Do not couple unrelated modules through a shared solution
  unless they actually need to build together.
- Keep assets and required licenses with the implementation that distributes them. Keep
  shared conversion fixtures in `tests/<module_name>/fixtures/` and repository regression
  tests in `tests/<module_name>/test_*.py`. C# unit tests, if added, belong to their C# project.
- Treat CLI arguments and JSON output as the shared contract between language versions;
  compare them against common fixtures when conversion behavior changes. Document
  intentional differences rather than assuming every implementation behaves identically.
- When one language version is a port of another, treat the original implementation as
  read-only source and keep a verification-only harness in the repository's test
  infrastructure (`tests/<module_name>/harness/`), pinned to the same dependency versions. Use
  it to regenerate fixtures and to run differential tests; it is never part of a shipped tool.
  Mark live reference tests `reference` and enable them explicitly with `--run-reference`.
  Once enabled, environment and build failures must fail the tests. Check package-version
  alignment offline so dependency changes cannot silently leave the reference behind.
- Keep build output out of source control. `bin/`, `obj/`, Python caches, and root `dist/`
  are ignored. Put distributable archives under `dist/<module-name>/<platform>/` when
  packaging releases.

The repository's root `pyproject.toml` remains the development/test environment for the
toolkit. Standalone modules should document what their users need independently of that
environment.
